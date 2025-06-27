"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { GetShape } from "@/api/maillage/maillage.types";
import React, { useCallback, useMemo, useState, useRef, useEffect } from "react";
import { Polygon, LayerGroup, Tooltip } from "react-leaflet";

// Types optimisés
interface PolygonStyle {
	color: string;
	fillColor: string;
	opacity: number;
	weight: number;
	fillOpacity: number;
}

// Type pour les données de réputation (venant du MapController)
interface ReputationData {
	code: string;
	value: number;
	ratio_pour_mille: number;
	color: string;
	value_percentage: number;
}

interface ZoneProps {
	zone: GetShape;
	style?: PolygonStyle;
	isVisible?: boolean;
	niveau?: string;
	selectedYear?: string;
	customColor?: string; // Couleur passée depuis le MapController
	reputationData?: ReputationData; // Données de réputation complètes
}

// Styles constants
const DEFAULT_STYLE: PolygonStyle = {
	color: "#000000",
	fillColor: "#ffffff",
	opacity: 0.5,
	weight: 2,
	fillOpacity: 0.5,
} as const;

const ZONE_STYLES = {
	hover: {
		weight: 3,
		fillOpacity: 0.3,
		opacity: 1,
	},
	selected: {
		color: "#0066ff",
		weight: 3,
		fillOpacity: 0.5,
	},
	highlighted: {
		color: "red",
		weight: 5,
		opacity: 1,
	},
} as const;

// Fonction pure pour calculer le style
const getPolygonStyle = (
	isHovered: boolean,
	isSelected: boolean,
	isHighlighted: boolean,
	customStyle: PolygonStyle,
	customColor?: string,
): PolygonStyle => {
	const baseStyle = { ...customStyle };

	// Utiliser la couleur personnalisée si disponible
	if (customColor) {
		baseStyle.fillColor = customColor;
		baseStyle.fillOpacity = 1; // Augmenter l'opacité pour mieux voir la couleur
	}

	// Priorité des styles : highlighted > selected > hovered
	if (isHighlighted) {
		return { ...baseStyle, ...ZONE_STYLES.highlighted };
	}
	if (isSelected) {
		return { ...baseStyle, ...ZONE_STYLES.selected };
	}
	if (isHovered) {
		return { ...baseStyle, ...ZONE_STYLES.hover };
	}

	return baseStyle;
};

// Simplification des coordonnées pour améliorer les performances
const simplifyCoordinates = (coordinates: any, tolerance: number = 0.001): any => {
	if (!Array.isArray(coordinates) || coordinates.length < 3) return coordinates;

	// Simplification plus agressive pour les polygones très détaillés
	if (coordinates.length > 200) {
		return coordinates.filter((_: any, index: number) => index % 3 === 0);
	} else if (coordinates.length > 100) {
		return coordinates.filter((_: any, index: number) => index % 2 === 0);
	}

	return coordinates;
};

const Zone = ({ zone, style = DEFAULT_STYLE, isVisible = true, niveau, selectedYear, customColor, reputationData }: ZoneProps) => {
	const router = useRouter();
	const [isHovered, setIsHovered] = useState(false);
	const hoverTimeoutRef = useRef<NodeJS.Timeout>();

	const searchParams = useSearchParams();

	// Extraction des paramètres avec valeurs par défaut
	const urlParams = useMemo(() => {
		return {
			niveauMaille: niveau || searchParams.get("niveau_lower") || "region",
			codeSelecting: searchParams.get("code_selecting"),
			code: searchParams.get("code") || "",
		};
	}, [searchParams, niveau]);

	const { codeSelecting, code } = urlParams;

	// Early return si pas visible
	if (!isVisible) return null;

	// États de sélection et de mise en évidence
	const isSelected = zone.code === codeSelecting;
	const isHighlighted = zone.code === code && code !== ""; // Vérifier que code n'est pas vide

	// Calcul du style mémorisé avec la couleur personnalisée
	const polygonStyle = useMemo(
		() => getPolygonStyle(isHovered, isSelected, isHighlighted, style, customColor),
		[isHovered, isSelected, isHighlighted, style, customColor],
	);

	// Simplification des coordonnées pour améliorer les performances
	const simplifiedCoordinates = useMemo(() => simplifyCoordinates(zone.shape.coordinates), [zone.shape.coordinates]);

	// Event handlers optimisés
	const handleMouseOver = useCallback(() => {
		if (hoverTimeoutRef.current) {
			clearTimeout(hoverTimeoutRef.current);
		}
		setIsHovered(true);
	}, []);

	const handleMouseOut = useCallback(() => {
		hoverTimeoutRef.current = setTimeout(() => {
			setIsHovered(false);
		}, 100); // Petite temporisation pour éviter les flickers
	}, []);

	const handleClick = useCallback(() => {
		const params = new URLSearchParams(searchParams.toString());

		if (zone.code === codeSelecting) {
			params.delete("code_selecting");
		} else {
			params.set("code_selecting", zone.code);
		}

		router.push(`?${params.toString()}`);
	}, [zone.code, codeSelecting, searchParams, router]);

	// Cleanup effect pour les timeouts
	useEffect(() => {
		return () => {
			if (hoverTimeoutRef.current) {
				clearTimeout(hoverTimeoutRef.current);
			}
		};
	}, []);

	// Mémorisation des event handlers
	const eventHandlers = useMemo(
		() => ({
			mouseover: handleMouseOver,
			mouseout: handleMouseOut,
			click: handleClick,
		}),
		[handleMouseOver, handleMouseOut, handleClick],
	);

	// Mémorisation du contenu du tooltip avec les données de réputation
	const tooltipContent = useMemo(
		() => (
			<div style={{ textAlign: "center", fontSize: "12px", minWidth: "120px" }}>
				<strong>{zone.libelle}</strong>
				<br />
				<small>Code: {zone.code}</small>
				{reputationData && (
					<>
						<br />
						<small>Valeur: {reputationData.value.toLocaleString()}</small>
						<br />
						<small>Ratio ‰: {reputationData.ratio_pour_mille.toFixed(3)}</small>
						<br />
						<small>Pourcentage: {(reputationData.value_percentage * 100).toFixed(2)}%</small>
					</>
				)}
				{customColor && (
					<>
						<br />
						<div
							style={{
								display: "inline-block",
								width: "12px",
								height: "12px",
								backgroundColor: customColor,
								border: "1px solid #ccc",
								marginTop: "2px",
							}}
						/>
					</>
				)}
			</div>
		),
		[zone.libelle, zone.code, reputationData, customColor],
	);

	// Debug: Log pour vérifier la réception des données
	useEffect(() => {
		if (reputationData) {
			console.log(`Zone ${zone.code} a reçu des données de réputation:`, reputationData);
		}
		if (customColor) {
			console.log(`Zone ${zone.code} a reçu la couleur:`, customColor);
		}
		if (isHighlighted) {
			console.log(`Zone ${zone.code} est mise en évidence (bordure rouge)`);
		}
	}, [zone.code, reputationData, customColor, isHighlighted]);

	return (
		<LayerGroup>
			<Polygon
				positions={simplifiedCoordinates}
				pathOptions={polygonStyle}
				eventHandlers={eventHandlers}
				smoothFactor={1.5}
				noClip={false}
			>
				{/* Tooltip conditionnel */}
				<Tooltip permanent={false} direction="top" opacity={0.95} sticky={true} className="zone-tooltip">
					{tooltipContent}
				</Tooltip>
			</Polygon>
		</LayerGroup>
	);
};

// Mémorisation avec comparaison custom pour éviter les re-renders
const areEqual = (prevProps: ZoneProps, nextProps: ZoneProps) => {
	return (
		prevProps.zone.code === nextProps.zone.code &&
		prevProps.isVisible === nextProps.isVisible &&
		prevProps.niveau === nextProps.niveau &&
		prevProps.selectedYear === nextProps.selectedYear &&
		prevProps.customColor === nextProps.customColor &&
		JSON.stringify(prevProps.reputationData) === JSON.stringify(nextProps.reputationData) &&
		JSON.stringify(prevProps.style) === JSON.stringify(nextProps.style)
	);
};

export default React.memo(Zone, areEqual);
export type { ZoneProps, PolygonStyle, ReputationData };
