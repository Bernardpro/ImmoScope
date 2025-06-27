import axios from "axios";
import { useState, useEffect } from "react";

// Create axios instance
const createAxiosMaille = () => {
	return axios.create({
		//baseURL: "https://api.homepedia.spectrum-app.cloud",
		baseURL: "https://api.homepedia.spectrum-app.cloud/",
		responseType: "json",
	});
};

// Types pour les réponses
interface ReputationData {
	data: any[];
	filtre: string[];
	annee: number[];
}

interface FoncierData {
	data: any[];
	filtre: string[];
	annee: any[];
}

interface EquipementData {
	data: any[];
	filtre: string[];
	annee: any[];
}

interface ReputationMultiMapData {
	data: any[];
	filtre: string[];
	annee: any[];
}

interface ApiResponse<T> {
	data: T;
	status: number;
	headers: Record<string, string>;
}

// Service pour les réputations
export const getReputationsByCommune = async (code: string): Promise<ReputationData> => {
	try {
		const axiosInstance = createAxiosMaille();
		const response = await axiosInstance.get<ReputationData>(`/data/reputations?code=${code}`);
		return response.data;
	} catch (error) {
		console.error("Erreur lors de la récupération des réputations:", error);
		throw error;
	}
};

// Service pour les fonciers
export const getFonciersByCommune = async (code: string): Promise<FoncierData> => {
	try {
		const axiosInstance = createAxiosMaille();
		const response = await axiosInstance.get<FoncierData>(`/data/fonciers?code=${code}`);
		return response.data;
	} catch (error) {
		console.error("Erreur lors de la récupération des fonciers:", error);
		throw error;
	}
};

// Service pour les équipements
export const getEquipementsByCommune = async (code: string): Promise<EquipementData> => {
	try {
		const axiosInstance = createAxiosMaille();
		const response = await axiosInstance.get<EquipementData>(`/data/equipements?code=${code}`);
		return response.data;
	} catch (error) {
		console.error("Erreur lors de la récupération des équipements:", error);
		throw error;
	}
};

// Service pour les réputations multi-map
export const getReputationsMultiMap = async (codes: string[], niveau: string = "commune"): Promise<ReputationMultiMapData> => {
	try {
		const axiosInstance = createAxiosMaille();

		// Données envoyées dans le body de la requête
		const requestBody = {
			codes: codes,
			niveau: niveau,
		};

		const response = await axiosInstance.post<ReputationMultiMapData>(`/data/reputations/multi/map`, requestBody);

		return response.data;
	} catch (error) {
		console.error("Erreur lors de la récupération des réputations multi-map:", error);
		throw error;
	}
};

// Fonction utilitaire pour gérer les erreurs d'API
export const handleApiError = (error: any) => {
	if (axios.isAxiosError(error)) {
		if (error.response) {
			// Le serveur a répondu avec un code d'erreur
			console.error("Erreur de réponse:", error.response.status, error.response.data);
			return {
				status: error.response.status,
				message: error.response.data?.detail || "Erreur du serveur",
			};
		} else if (error.request) {
			// La requête a été faite mais pas de réponse
			console.error("Erreur de réseau:", error.request);
			return {
				status: 0,
				message: "Erreur de connexion au serveur",
			};
		}
	}

	console.error("Erreur inattendue:", error);
	return {
		status: 500,
		message: "Erreur inattendue",
	};
};

// Hook personnalisé pour les réputations
export const useReputations = (code: string) => {
	const [data, setData] = useState<ReputationData | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!code) return;

		const fetchData = async () => {
			setLoading(true);
			setError(null);
			try {
				const result = await getReputationsByCommune(code);
				setData(result);
			} catch (err) {
				const errorInfo = handleApiError(err);
				setError(errorInfo.message);
			} finally {
				setLoading(false);
			}
		};

		fetchData();
	}, [code]);

	return { data, loading, error };
};

// Hook personnalisé pour les fonciers
export const useFonciers = (code: string) => {
	const [data, setData] = useState<FoncierData | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!code) return;

		const fetchData = async () => {
			setLoading(true);
			setError(null);
			try {
				const result = await getFonciersByCommune(code);
				setData(result);
			} catch (err) {
				const errorInfo = handleApiError(err);
				setError(errorInfo.message);
			} finally {
				setLoading(false);
			}
		};

		fetchData();
	}, [code]);

	return { data, loading, error };
};

// Hook personnalisé pour les équipements
export const useEquipements = (code: string) => {
	const [data, setData] = useState<EquipementData | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!code) return;

		const fetchData = async () => {
			setLoading(true);
			setError(null);
			try {
				const result = await getEquipementsByCommune(code);
				setData(result);
			} catch (err) {
				const errorInfo = handleApiError(err);
				setError(errorInfo.message);
			} finally {
				setLoading(false);
			}
		};

		fetchData();
	}, [code]);

	return { data, loading, error };
};

export const useReputationsMultiMap = (codes: string[], niveau: string = "commune", isEnabled: boolean = true) => {
	const [data, setData] = useState<ReputationMultiMapData | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	console.log("Fetching reputations for codes:", codes, "at niveau:", niveau, "Enabled:", isEnabled);

	useEffect(() => {
		if (!isEnabled || !codes || codes.length === 0) return;

		const fetchData = async () => {
			setLoading(true);
			setError(null);
			try {
				const result = await getReputationsMultiMap(codes, niveau);
				setData(result);
			} catch (err) {
				const errorInfo = handleApiError(err);
				setError(errorInfo.message);
			} finally {
				setLoading(false);
			}
		};

		fetchData();
	}, [JSON.stringify(codes), niveau, isEnabled]); // JSON.stringify pour comparer les tableaux

	return { data, loading, error };
};

// Hook générique pour les appels API avec paramètres optionnels
export const useApiCall = <T>(endpoint: string, params: Record<string, string> = {}, enabled: boolean = true) => {
	const [data, setData] = useState<T | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!enabled) return;

		const fetchData = async () => {
			setLoading(true);
			setError(null);
			try {
				const axiosInstance = createAxiosMaille();
				const queryParams = new URLSearchParams(params).toString();
				const url = queryParams ? `${endpoint}?${queryParams}` : endpoint;
				const response = await axiosInstance.get<T>(url);
				setData(response.data);
			} catch (err) {
				const errorInfo = handleApiError(err);
				setError(errorInfo.message);
			} finally {
				setLoading(false);
			}
		};

		fetchData();
	}, [endpoint, JSON.stringify(params), enabled]);

	return { data, loading, error };
};

// Hook avec possibilité de refetch
export const useApiCallWithRefetch = <T>(endpoint: string, params: Record<string, string> = {}, enabled: boolean = true) => {
	const [data, setData] = useState<T | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const fetchData = async () => {
		setLoading(true);
		setError(null);
		try {
			const axiosInstance = createAxiosMaille();
			const queryParams = new URLSearchParams(params).toString();
			const url = queryParams ? `${endpoint}?${queryParams}` : endpoint;
			const response = await axiosInstance.get<T>(url);
			setData(response.data);
		} catch (err) {
			const errorInfo = handleApiError(err);
			setError(errorInfo.message);
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		if (!enabled) return;
		fetchData();
	}, [endpoint, JSON.stringify(params), enabled]);

	return { data, loading, error, refetch: fetchData };
};
