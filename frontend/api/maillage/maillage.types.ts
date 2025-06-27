// Types pour l'API Maillage

export interface GetShapeProps {
	maille: "region" | "departement" | "commune";
	code?: string;
	isEnabled?: boolean;
}

export interface GetInferiorShapesProps {
	maille_source: "region" | "departement";
	code: string;
	maille_cible?: "departement" | "commune";
	isEnabled?: boolean;
}

export interface GeoJSONPoint {
	type: "Point";
	coordinates: [number, number][] | [number, number];
}

export interface GeoJSONPolygon {
	type: "Polygon";
	coordinates: [number, number][][];
}

export interface GeoJSONMultiPolygon {
	type: "MultiPolygon";
	coordinates: [number, number][][][];
}

export type GeoJSONGeometry = GeoJSONPoint | GeoJSONPolygon | GeoJSONMultiPolygon;

export interface GetShape {
	code: string;
	libelle: string;
	shape: GeoJSONGeometry; // Format GeoJSON
	centre: GeoJSONGeometry; // Format GeoJSON Point
	niveau?: string; // Présent dans certaines réponses
}

export interface StatResponse {
	niveau: string;
	total: number;
}
