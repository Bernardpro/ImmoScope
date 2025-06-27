"use client";

import { TileLayer, useMap } from "react-leaflet";
import { useEffect, useMemo, useCallback, useRef, useState } from "react";
import { EquipmentData } from "@/api/data/data.types";
import { GetShape } from "@/api/maillage/maillage.types";
import Zone from "./Zone";
import { useSearchParams } from "next/navigation";
import { log } from "console";
//import EquipmentCluster from "./EquipmentCluster"; // Nouveau composant pour les équipements

// Type pour les données de réputation
interface ReputationData {
	code: string;
	value: number;
	ratio_pour_mille: number;
	color: string;
	value_percentage: number;
}

interface MapControllerProps {
	shapes: GetShape[];
	childShapes: GetShape[];
	equipementsState: EquipmentData;
	reputationsData?: ReputationData[] | undefined; // Nouvelles props ajoutées
	reputationsLoading?: boolean;
	reputationsError?: any;
	niveau: string | null;
	onZoomToShape: (mapInstance: any) => void;
}

// Fonction pour déterminer si une zone est visible dans les bounds actuels
const isZoneVisible = (zone: GetShape, bounds: any): boolean => {
	if (!bounds || !zone.centre?.coordinates?.[0]) return true;

	const [lat, lng] = zone.centre.coordinates[0];
	return bounds.contains([lat, lng]);
};

// Hook pour gérer la visibilité des zones selon le viewport
const useViewportCulling = (shapes: GetShape[], map: any) => {
	const [visibleShapes, setVisibleShapes] = useState<Set<string>>(new Set());
	const updateTimeoutRef = useRef<NodeJS.Timeout>();

	const updateVisibleShapes = useCallback(() => {
		if (!map || shapes.length === 0) return;

		const bounds = map.getBounds();
		const visible = new Set<string>();

		shapes.forEach((shape) => {
			if (isZoneVisible(shape, bounds)) {
				visible.add(shape.code);
			}
		});

		setVisibleShapes(visible);
	}, [map, shapes]);

	const debouncedUpdate = useCallback(() => {
		if (updateTimeoutRef.current) {
			clearTimeout(updateTimeoutRef.current);
		}
		updateTimeoutRef.current = setTimeout(updateVisibleShapes, 100);
	}, [updateVisibleShapes]);

	useEffect(() => {
		if (!map) return;

		// Mise à jour initiale
		updateVisibleShapes();

		// Écouter les événements de déplacement/zoom
		map.on("moveend", debouncedUpdate);
		map.on("zoomend", debouncedUpdate);

		return () => {
			map.off("moveend", debouncedUpdate);
			map.off("zoomend", debouncedUpdate);
			if (updateTimeoutRef.current) {
				clearTimeout(updateTimeoutRef.current);
			}
		};
	}, [map, debouncedUpdate, updateVisibleShapes]);

	return visibleShapes;
};

const MapController = ({
	shapes,
	childShapes,
	equipementsState,
	reputationsData = [],
	reputationsLoading = false,
	reputationsError = null,
	niveau,
	onZoomToShape,
}: MapControllerProps) => {
	const map = useMap();
	const previousShapesRef = useRef<GetShape[]>([]);
	const isInitialMount = useRef(true);

	// Utilisation du viewport culling pour optimiser le rendu
	const visibleMainShapes = useViewportCulling(shapes, map);
	const visibleChildShapes = useViewportCulling(childShapes, map);

	// Créer un map pour un accès rapide aux données de réputation par code
	const reputationMap = useMemo(() => {
		const map = new Map<string, ReputationData>();
		console.log(reputationsData);
		if (!reputationsData || reputationsData.length === 0 || reputationsData === {}) {
			console.warn("Aucune donnée de réputation disponible.");
			return map;
		}
		console.log("Création de la map de réputation avec les données:", reputationsData);

		reputationsData?.forEach((reputation) => {
			map.set(reputation.code, reputation);
		});
		return map;
	}, [reputationsData]);

	// Fonction pour obtenir la couleur d'une zone
	const getZoneColor = useCallback(
		(zoneCode: string): string | undefined => {
			const reputation = reputationMap.get(zoneCode);
			return reputation?.color;
		},
		[reputationMap],
	);

	// Fonction pour obtenir les données de réputation d'une zone
	const getZoneReputationData = useCallback(
		(zoneCode: string): ReputationData | undefined => {
			return reputationMap.get(zoneCode);
		},
		[reputationMap],
	);

	// Debug: Log des données de réputation
	useEffect(() => {
		if (reputationsData && reputationsData.length > 0) {
			console.log("Données de réputation reçues:", reputationsData);
			console.log("Map de réputation créée:", reputationMap);
		}
	}, [reputationsData, reputationMap]);

	// Exposer l'instance de carte au parent
	useEffect(() => {
		onZoomToShape(map);
	}, [map, onZoomToShape]);

	// Gestion optimisée du centrage/zoom
	useEffect(() => {
		if (!map || shapes.length === 0) return;

		// Éviter les animations inutiles si les shapes n'ont pas changé
		const shapesChanged =
			shapes.length !== previousShapesRef.current.length ||
			shapes.some((shape, index) => shape.code !== previousShapesRef.current[index]?.code);

		if (!shapesChanged && !isInitialMount.current) return;

		const firstShape = shapes[0];
		if (
			firstShape.centre?.coordinates?.[0] &&
			Array.isArray(firstShape.centre.coordinates[0]) &&
			firstShape.centre.coordinates[0].length === 2
		) {
			const zoom = getZoomForLevel(niveau);
			console.log(
				`Controller Zooming to shape: ${firstShape.code} at center: ${firstShape.centre.coordinates[0]} with zoom: ${zoom}`,
			);

			const center = firstShape.centre.coordinates[0] as [number, number];

			// Animation seulement si nécessaire
			if (isInitialMount.current) {
				map.setView(center, zoom);
				isInitialMount.current = false;
			} else {
				map.flyTo(center, zoom, {
					animate: true,
					duration: 0.6,
					easeLinearity: 0.3,
				});
			}
		}

		previousShapesRef.current = shapes;
	}, [map, shapes, niveau]);

	// Fonction utilitaire pour le zoom
	const getZoomForLevel = useCallback((level: string | null): number => {
		switch (level) {
			case "commune":
				return 12;
			case "departement":
				return 10;
			case "region":
				return 8;
			default:
				return 6;
		}
	}, []);

	// Mémorisation des zones principales visibles avec couleurs
	const renderedMainShapes = useMemo(() => {
		return shapes
			.filter((zone) => !(niveau === "region" || niveau === "departement"))
			.filter((zone) => visibleMainShapes.has(zone.code))
			.map((zone) => {
				const color = getZoneColor(zone.code);
				const reputationData = getZoneReputationData(zone.code);

				return <Zone key={zone.code} zone={zone} isVisible={true} customColor={color} reputationData={reputationData} />;
			});
	}, [shapes, visibleMainShapes, niveau, getZoneColor, getZoneReputationData]);

	// Mémorisation des zones enfants visibles avec couleurs
	const renderedChildShapes = useMemo(() => {
		return childShapes
			.filter((shape) => visibleChildShapes.has(shape.code))
			.map((shape) => {
				const color = getZoneColor(shape.code);
				const reputationData = getZoneReputationData(shape.code);

				return <Zone key={shape.code} zone={shape} isVisible={true} customColor={color} reputationData={reputationData} />;
			});
	}, [childShapes, visibleChildShapes, getZoneColor, getZoneReputationData]);

	// Affichage du statut de chargement des réputations (optionnel)
	useEffect(() => {
		if (reputationsLoading) {
			console.log("Chargement des données de réputation...");
		}
		if (reputationsError) {
			console.error("Erreur lors du chargement des réputations:", reputationsError);
		}
	}, [reputationsLoading, reputationsError]);

	// Mémorisation des équipements (avec clustering si nécessaire)
	// const renderedEquipments = useMemo(() => {
	// 	if (equipementsState.data.length === 0) return null;

	// 	// Si trop d'équipements, utiliser le clustering
	// 	if (equipementsState.data.length > 50) {
	// 		return <EquipmentCluster equipments={equipementsState.data} />;
	// 	}

	// 	// Sinon, affichage direct
	// 	return equipementsState.data.map((equipement: any) => (
	// 		<Marker key={equipement.id || Math.random().toString()} position={[equipement.latitude, equipement.longitude]}>
	// 			<Popup>
	// 				<strong>{equipement.nomrs}</strong>
	// 				<br />
	// 				Type: {equipement.lib_mod}
	// 			</Popup>
	// 		</Marker>
	// 	));
	// }, [equipementsState.data]);

	return (
		<>
			<TileLayer
				attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
				url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
				// Optimisations pour les tuiles
				maxZoom={14}
				minZoom={5}
				keepBuffer={2} // Garde 2 tuiles en buffer
				updateWhenIdle={true}
				updateWhenZooming={false}
			/>

			{/* Affichage des formes enfants avec couleurs */}
			{renderedChildShapes}

			{/* Affichage des formes principales avec couleurs */}
			{renderedMainShapes}

			{/* Debug: Affichage du statut des réputations */}
			{reputationsLoading && (
				<div
					style={{
						position: "absolute",
						top: "10px",
						right: "10px",
						background: "rgba(255,255,255,0.9)",
						padding: "5px 10px",
						borderRadius: "3px",
						fontSize: "12px",
						zIndex: 9000,
					}}
				>
					Chargement des réputations...
				</div>
			)}
		</>
	);
};

export default MapController;
