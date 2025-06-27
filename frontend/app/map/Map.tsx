"use client";

import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";

import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import "leaflet-defaulticon-compatibility";
import { useGetInferiorShapes, useGetShape } from "@/api/maillage";
import { ControleMaille, ControleMailleInferieur } from "@/api/maillage/constant";
import Zone from "./Zone";
import { GetShape } from "@/api/maillage/maillage.types";
import { useEquipements, useReputationsMultiMap } from "@/api/data/data";
import { EquipmentData } from "@/api/data/data.types";
import MapController from "./MapController";
import { log } from "console";

interface MapProps {
	zoom?: number;
}

const defaults = {
	zoom: 6,
};

// Debounce utility
const useDebounce = (value: any, delay: number) => {
	const [debouncedValue, setDebouncedValue] = useState(value);

	useEffect(() => {
		const handler = setTimeout(() => {
			setDebouncedValue(value);
		}, delay);

		return () => {
			clearTimeout(handler);
		};
	}, [value, delay]);

	return debouncedValue;
};

const Map = (mapProps: MapProps) => {
	const { zoom = defaults.zoom } = mapProps;
	const [center, setCenter] = useState<[number, number]>([46.5, 3]);
	const [currentZoom, setCurrentZoom] = useState(zoom);
	const mapInstanceRef = useRef<any>(null);
	const lastFlyToRef = useRef<string>("");

	// get params from the URL - mémorisés
	const searchParams = useSearchParams();
	const urlParams = useMemo(
		() => ({
			niveau: searchParams.get("niveau"),
			code: searchParams.get("code"),
			code_selecting: searchParams.get("code_selecting"),
			niveau_lower: searchParams.get("niveau_lower") || searchParams.get("niveau") || "region", // Valeur par défaut si non spécifiée
			typeDataDisplay: searchParams.get("typeDataDisplay") || "reputations", // Valeur par défaut
		}),
		[searchParams],
	);

	const { niveau, code, code_selecting, niveau_lower, typeDataDisplay } = urlParams;

	// Debounce des paramètres pour éviter les appels API trop fréquents
	const debouncedParams = useDebounce(urlParams, 100);

	const router = useRouter();

	// State to store processed GeoJSON data - mémorisés
	const [shapes, setShapes] = useState<GetShape[]>([]);
	const [childShapes, setChildShapes] = useState<GetShape[]>([]);
	const [equipementsState, setEquipementsState] = useState<EquipmentData>({ data: [] } as EquipmentData);

	// Mémorisation des paramètres API
	const shapeParams = useMemo(
		() => ({
			maille: niveau ? ControleMaille[niveau as keyof typeof ControleMaille] : ControleMaille.region,
			code: code || undefined,
			isEnabled: true,
		}),
		[niveau, code],
	);

	const childShapeParams = useMemo(
		() => ({
			maille_source: niveau ? ControleMailleInferieur[niveau as keyof typeof ControleMailleInferieur] : ControleMaille.region,
			code: code || "84",
			isEnabled: niveau === "region" || niveau === "departement",
		}),
		[niveau, code],
	);

	// Get shape data based on niveau and code
	const { data: ShapesApi, isLoading, error } = useGetShape(shapeParams);

	// Get child shapes data
	const { data: childShapesApi, isLoading: childrenLoading, error: childrenError } = useGetInferiorShapes(childShapeParams);

	const codesForReputations = useMemo(() => {
		// 🟢 PRIORITÉ 1: Si childShapes existe → utilise leurs codes
		if (childShapes.length > 0) {
			return childShapes.map((shape) => shape.code).filter(Boolean);
		}

		// 🟡 PRIORITÉ 2: Sinon, utilise les main shapes (temporaire au démarrage)
		if (shapes.length > 1) {
			return shapes.map((shape) => shape.code).filter(Boolean);
		}

		return [];
	}, [childShapes, ShapesApi, childShapesApi, shapes, niveau]);

	console.log({ codesForReputations, niveau_lower });

	const {
		data: RepuMutliData,
		loading: RepuMutliloading,
		error: RepuMutliError,
	} = useReputationsMultiMap(codesForReputations, niveau_lower, codesForReputations.length > 0 && typeDataDisplay === "reputation");

	// Debug: Log des codes utilisés
	useEffect(() => {
		console.log("🔍 Debug codes:");
		console.log("  - childShapes.length:", childShapes.length);
		console.log("  - shapes.length:", shapes.length);
		console.log("  - niveau:", niveau);
		console.log("  - codesForReputations:", codesForReputations);
		console.log("  - niveau_lower:", niveau_lower);
	}, [childShapes.length, shapes.length, niveau, codesForReputations, niveau_lower]);

	// Fonction pour calculer le zoom selon le niveau
	const getZoomForLevel = useCallback((level: string | null): number => {
		switch (level) {
			case "commune":
				return 13;
			case "departement":
				return 10;
			case "region":
				return 8;
			default:
				return 6;
		}
	}, []);

	// Process shape data when it's loaded - optimisé
	useEffect(() => {
		if (ShapesApi && ShapesApi.length > 0) {
			// Éviter les re-renders inutiles
			setShapes((prev) => {
				const isSame = prev.length === ShapesApi.length && prev.every((shape, index) => shape.code === ShapesApi[index]?.code);
				return isSame ? prev : ShapesApi;
			});

			// Gestion optimisée du center/zoom
			const firstShape = ShapesApi[0];
			if (
				firstShape.centre?.coordinates?.[0] &&
				Array.isArray(firstShape.centre.coordinates[0]) &&
				firstShape.centre.coordinates[0].length === 2
			) {
				const newCenter = firstShape.centre.coordinates[0] as [number, number];
				const newZoom = getZoomForLevel(niveau);
				console.log(`Zooming to shape: ${firstShape.code} at center: ${newCenter} with zoom: ${newZoom}`);

				const flyToKey = `${newCenter[0]}-${newCenter[1]}-${newZoom}`;

				// Éviter les flyTo multiples
				if (mapInstanceRef.current && lastFlyToRef.current !== flyToKey) {
					lastFlyToRef.current = flyToKey;
					mapInstanceRef.current.flyTo(newCenter, newZoom, {
						animate: true,
						duration: 0.8,
						easeLinearity: 0.25,
					});
				}

				setCenter(newCenter);
				setCurrentZoom(newZoom);
			}
		}
	}, [ShapesApi, niveau, getZoomForLevel]);

	// Process child shapes - optimisé
	useEffect(() => {
		if (childShapesApi && childShapesApi.length > 0) {
			setChildShapes((prev) => {
				const isSame =
					prev.length === childShapesApi.length && prev.every((shape, index) => shape.code === childShapesApi[index]?.code);
				return isSame ? prev : childShapesApi;
			});
		} else {
			setChildShapes([]);
		}
	}, [childShapesApi]);

	// Fonction optimisée pour le zoom sur forme
	const handleZoomOnShape = useCallback(() => {
		if (!code_selecting) return;

		const levelMap: Record<string, string> = {
			region: "departement",
			departement: "commune",
		};

		const newNiveau = levelMap[niveau || ""] || "region";
		const lowerNiveau = levelMap[newNiveau || ""] || "region";

		const params = new URLSearchParams(searchParams.toString());
		params.set("code", code_selecting);
		params.set("niveau", newNiveau);
		params.set("niveau_lower", lowerNiveau);

		params.delete("code_selecting");

		router.push(`?${params.toString()}`);
	}, [code_selecting, niveau, searchParams, router]);

	// Fonction optimisée pour gérer l'instance de carte
	const handleMapInstance = useCallback((map: any) => {
		mapInstanceRef.current = map;
	}, []);

	// Mémorisation des props pour MapController
	console.log(RepuMutliData);

	const mapControllerProps = useMemo(
		() => ({
			shapes,
			childShapes,
			equipementsState,
			reputationsData: RepuMutliData, // Données de réputation
			reputationsLoading: RepuMutliloading, // État de chargement
			reputationsError: RepuMutliError, // État d'erreur
			niveau,
			onZoomToShape: handleMapInstance,
		}),
		[shapes, childShapes, equipementsState, RepuMutliData, RepuMutliloading, RepuMutliError, niveau, handleMapInstance],
	);

	return (
		<div style={{ position: "relative", height: "100%", width: "100%" }}>
			<MapContainer
				center={center}
				zoom={currentZoom}
				scrollWheelZoom={true}
				style={{ height: "100%", width: "100%" }}
				// Optimisations Leaflet
				preferCanvas={true} // Utilise Canvas au lieu de SVG pour de meilleures performances
				updateWhenIdle={true} // Mise à jour seulement quand la carte est idle
				updateWhenZooming={false} // Pas de mise à jour pendant le zoom
			>
				<MapController {...mapControllerProps} />
			</MapContainer>

			{niveau !== "commune" && (
				<button onClick={handleZoomOnShape} className="zoom_button" disabled={!code_selecting || niveau === "commune"}>
					Zoom sur la maille
				</button>
			)}

			{/* Debug panel - à supprimer en production */}
			<div
				style={{
					position: "absolute",
					top: "10px",
					left: "10px",
					background: "rgba(255,255,255,0.9)",
					padding: "10px",
					borderRadius: "5px",
					fontSize: "12px",
					maxWidth: "300px",
					zIndex: 1000,
				}}
			>
				<strong>Debug Info:</strong>
				<br />
				Niveau: {niveau}
				<br />
				Niveau Lower: {niveau_lower}
				<br />
				Child Shapes: {childShapes.length}
				<br />
				Main Shapes: {shapes.length}
				<br />
				Codes pour réputations: {codesForReputations.length}
				<br />
				Réputations chargées: {RepuMutliData?.length || 0}
				<br />
				Loading: {RepuMutliloading ? "Oui" : "Non"}
			</div>
		</div>
	);
};

export default Map;
