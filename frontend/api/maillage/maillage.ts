import axios from "axios";
import { useEffect, useState } from "react";
import { GetInferiorShapesProps, GetShape, GetShapeProps } from "./maillage.types";

// Create axios instance
const createAxiosMaille = () => {
	return axios.create({
		baseURL: "https://maillage.homepedia.spectrum-app.cloud",
		responseType: "json",
	});
};

// Custom hook for fetching shape data
export function useGetShape({ maille, code, isEnabled = true }: GetShapeProps) {
	const [data, setData] = useState<GetShape[] | null>(null);
	const [error, setError] = useState<Error | null>(null);
	const [isLoading, setIsLoading] = useState<boolean>(false);

	useEffect(() => {
		const fetchData = async () => {
			if (!isEnabled) return;

			setIsLoading(true);
			try {
				const api = createAxiosMaille();
				const response = await api.get(`/maille/${maille}${code ? `/${code}` : ""}`);
				setData(response.data);
			} catch (err) {
				setError(err instanceof Error ? err : new Error("An error occurred"));
			} finally {
				setIsLoading(false);
			}
		};

		fetchData();
	}, [maille, code, isEnabled]);

	return { data, error, isLoading };
}

// Custom hook for fetching inferior shapes
export function useGetInferiorShapes({ maille_source, code, isEnabled = true }: GetInferiorShapesProps) {
	const [data, setData] = useState<GetShape[] | null>(null);
	const [error, setError] = useState<Error | null>(null);
	const [isLoading, setIsLoading] = useState<boolean>(false);

	useEffect(() => {
		const fetchData = async () => {
			if (!isEnabled) return;

			setIsLoading(true);
			try {
				const api = createAxiosMaille();
				// Correction: Utilisation de la nouvelle route /maille/enfants/
				const response = await api.get(`/maille/enfants/${maille_source}/${code}`);
				setData(response.data);
			} catch (err) {
				setError(err instanceof Error ? err : new Error("An error occurred"));
			} finally {
				setIsLoading(false);
			}
		};

		fetchData();
	}, [maille_source, code, isEnabled]);

	return { data, error, isLoading };
}

// Ajout d'un nouveau hook pour la recherche
export function useSearchMailles(q: string, niveau?: string, limit: number = 10) {
	const [data, setData] = useState<GetShape[] | null>(null);
	const [error, setError] = useState<Error | null>(null);
	const [isLoading, setIsLoading] = useState<boolean>(false);

	useEffect(() => {
		const fetchData = async () => {
			if (!q || q.length < 2) return;

			setIsLoading(true);
			try {
				const api = createAxiosMaille();
				let url = `/search?q=${encodeURIComponent(q)}&limit=${limit}`;
				if (niveau) {
					url += `&niveau=${niveau}`;
				}
				const response = await api.get(url);
				setData(response.data);
			} catch (err) {
				setError(err instanceof Error ? err : new Error("An error occurred"));
			} finally {
				setIsLoading(false);
			}
		};

		fetchData();
	}, [q, niveau, limit]);

	return { data, error, isLoading };
}

// Ajout d'un hook pour obtenir les statistiques
export function useGetStats() {
	const [data, setData] = useState<any[] | null>(null);
	const [error, setError] = useState<Error | null>(null);
	const [isLoading, setIsLoading] = useState<boolean>(false);

	useEffect(() => {
		const fetchData = async () => {
			setIsLoading(true);
			try {
				const api = createAxiosMaille();
				const response = await api.get("/stats");
				setData(response.data);
			} catch (err) {
				setError(err instanceof Error ? err : new Error("An error occurred"));
			} finally {
				setIsLoading(false);
			}
		};

		fetchData();
	}, []);

	return { data, error, isLoading };
}

/* curl -X 'GET' \
  'http://localhost:81/maille/{niveau}/{code}/arianne' \
  -H 'accept: application/json'
  */

// Hook pour récupérer le fil d'Ariane
export function useGetArianne({ maille, code, isEnabled = true }: { maille: string; code: string; isEnabled?: boolean }) {
	const [data, setData] = useState<GetShape[] | null>(null);
	const [error, setError] = useState<Error | null>(null);
	const [isLoading, setIsLoading] = useState<boolean>(false);

	useEffect(() => {
		const fetchData = async () => {
			if (!isEnabled || !maille || !code) return;

			setIsLoading(true);
			try {
				const api = createAxiosMaille();
				const response = await api.get(`/maille/${maille}/${code}/arianne`);
				setData(response.data);
			} catch (err) {
				setError(err instanceof Error ? err : new Error("An error occurred"));
			} finally {
				setIsLoading(false);
			}
		};

		fetchData();
	}, [maille, code, isEnabled]);

	return { data, error, isLoading };
}
