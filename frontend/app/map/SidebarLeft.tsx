"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useGetArianne } from "@/api/maillage";
import Link from "next/link";

// Types pour les localisations
interface Localisation {
	code: string;
	libelle: string;
}

// Types pour les propriétés de l'API
interface Propriete {
	annonce_id: string;
	titre: string;
	prix: number;
	surface: string | null;
	ville: string;
	code_commune: string;
	prix_m2: string | null;
	pieces: string | null;
	taille_terrain: string | null;
}

interface ApiResponse {
	data: Propriete[];
	pagination: {
		page: number;
		limit: number;
		total_items: number;
		total_pages: number;
		has_next: boolean;
		has_prev: boolean;
	};
	filters?: {
		code?: string;
		niveau?: string;
	};
}

// Props du composant SidebarLeft
interface SidebarLeftProps {
	isOpen: boolean;
	onToggle: () => void;
	onApplyFilters?: (location: string) => void;
	onReset?: () => void;
	useSearchMailles: (
		query: string,
		type: string,
		limit: number,
	) => {
		data: Localisation[] | undefined;
		error: any;
		isLoading: boolean;
	};
	children?: React.ReactNode;
	className?: string;
}

const SidebarLeft: React.FC<SidebarLeftProps> = ({
	isOpen,
	onToggle,
	onApplyFilters,
	onReset,
	useSearchMailles,
	children,
	className = "",
}) => {
	const [location, setLocation] = useState("");
	const [debouncedLocation, setDebouncedLocation] = useState("");
	const [showSuggestions, setShowSuggestions] = useState(false);
	const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);

	// États pour les données de l'API
	const [proprietes, setProprietes] = useState<Propriete[]>([]);
	const [isLoadingProprietes, setIsLoadingProprietes] = useState(false);
	const [errorProprietes, setErrorProprietes] = useState<string | null>(null);
	const [pagination, setPagination] = useState<any>(null);

	const suggestionRef = useRef<HTMLUListElement>(null);
	const inputRef = useRef<HTMLInputElement>(null);

	const searchParams = useSearchParams();
	const router = useRouter();

	// Fonction pour récupérer les propriétés depuis l'API
	const fetchProprietes = useCallback(
		async (page: number = 1, limit: number = 10) => {
			setIsLoadingProprietes(true);
			setErrorProprietes(null);

			try {
				// Construire l'URL avec les paramètres de recherche
				const params = new URLSearchParams();
				params.append("page", page.toString());
				params.append("limit", limit.toString());

				// Ajouter les filtres code et niveau s'ils existent dans l'URL
				const code = searchParams.get("code_selecting");
				const niveau = searchParams.get("niveau_lower");

				if (code) params.append("code", code);
				if (niveau) params.append("niveau", niveau);

				const url = `https://api.homepedia.spectrum-app.cloud/proprietes/?${params.toString()}`;
				console.log("Fetching properties with URL:", url);

				const response = await fetch(url, {
					method: "GET",
					headers: {
						accept: "application/json",
					},
				});

				if (!response.ok) {
					throw new Error(`Erreur HTTP: ${response.status}`);
				}

				const data: ApiResponse = await response.json();
				setProprietes(data.data);
				setPagination(data.pagination);
			} catch (error) {
				console.error("Erreur lors de la récupération des propriétés:", error);
				setErrorProprietes(error instanceof Error ? error.message : "Erreur inconnue");
			} finally {
				setIsLoadingProprietes(false);
			}
		},
		[searchParams],
	);

	// Charger les propriétés quand les paramètres de recherche changent
	useEffect(() => {
		fetchProprietes();
	}, [fetchProprietes]);

	// Debounce pour éviter trop d'appels API
	useEffect(() => {
		const timer = setTimeout(() => {
			setDebouncedLocation(location);
		}, 300);

		return () => clearTimeout(timer);
	}, [location]);

	const { data: localisations, error, isLoading } = useSearchMailles(debouncedLocation, "commune", 10);

	// Gestion de l'input de recherche
	const handleLocationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const value = e.target.value;
		setLocation(value);
		setShowSuggestions(value.length > 0);
		setSelectedSuggestionIndex(-1);
	};

	// Sélection d'une suggestion
	const handleSuggestionClick = (localisation: Localisation) => {
		setLocation(localisation.libelle);
		setShowSuggestions(false);
		setSelectedSuggestionIndex(-1);
		inputRef.current?.blur();

		// Mettre à jour l'URL avec les paramètres
		const params = new URLSearchParams(searchParams.toString());
		params.set("code", localisation.code);
		params.set("niveau", "commune");

		// Appliquer les changements à l'URL
		router.push(`?${params.toString()}`);
	};

	// Gestion des touches clavier pour la navigation dans les suggestions
	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (!showSuggestions || !localisations || localisations.length === 0) return;

		switch (e.key) {
			case "ArrowDown":
				e.preventDefault();
				setSelectedSuggestionIndex((prev) => (prev < localisations.length - 1 ? prev + 1 : 0));
				break;
			case "ArrowUp":
				e.preventDefault();
				setSelectedSuggestionIndex((prev) => (prev > 0 ? prev - 1 : localisations.length - 1));
				break;
			case "Enter":
				e.preventDefault();
				if (selectedSuggestionIndex >= 0) {
					handleSuggestionClick(localisations[selectedSuggestionIndex]);
				}
				break;
			case "Escape":
				setShowSuggestions(false);
				setSelectedSuggestionIndex(-1);
				inputRef.current?.blur();
				break;
		}
	};

	// Fermer les suggestions en cliquant en dehors
	const handleClickOutside = useCallback((event: MouseEvent) => {
		if (
			suggestionRef.current &&
			!suggestionRef.current.contains(event.target as Node) &&
			inputRef.current &&
			!inputRef.current.contains(event.target as Node)
		) {
			setShowSuggestions(false);
			setSelectedSuggestionIndex(-1);
		}
	}, []);

	useEffect(() => {
		document.addEventListener("mousedown", handleClickOutside);
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, [handleClickOutside]);

	// Réinitialiser la recherche
	const handleReset = () => {
		setLocation("");
		setDebouncedLocation("");
		setShowSuggestions(false);
		setSelectedSuggestionIndex(-1);
		inputRef.current?.focus();

		// Supprimer les paramètres de l'URL
		const params = new URLSearchParams(searchParams.toString());
		params.delete("code");
		params.delete("niveau");
		params.delete("code_selecting");
		params.delete("niveau_lower");

		// Si il n'y a plus de paramètres, naviguer vers l'URL sans query string
		const newUrl = params.toString() ? `?${params.toString()}` : window.location.pathname;
		router.push(newUrl);

		// Callback personnalisé si fourni
		onReset?.();
	};

	// Appliquer les filtres
	const handleApplyFilters = () => {
		console.log("Filtres appliqués avec localisation:", location);
		setShowSuggestions(false);
		// Les propriétés se rechargeront automatiquement grâce à l'useEffect
		onApplyFilters?.(location);
	};

	// Fonction pour formater le prix
	const formatPrice = (prix: number): string => {
		return new Intl.NumberFormat("fr-FR", {
			style: "currency",
			currency: "EUR",
			minimumFractionDigits: 0,
		}).format(prix);
	};

	// Fonction pour extraire le nom de la ville
	const extractCityName = (ville: string): string => {
		// Extrait le nom de la ville avant la parenthèse du code postal
		const match = ville.match(/^([^(]+)/);
		return match ? match[1].trim() : ville;
	};

	// Initialiser depuis l'URL au chargement
	useEffect(() => {
		const code = searchParams.get("code");
		const niveau = searchParams.get("niveau");

		if (code && niveau) {
			// Optionnel: charger les détails de la localisation depuis le code
			// et mettre à jour le champ location avec le libellé
			console.log("Localisation depuis URL:", { code, niveau });

			// Si vous avez une API pour récupérer le libellé depuis le code
			// vous pouvez l'appeler ici pour pré-remplir le champ location
		}
	}, [searchParams]);

	// Obtenir les informations de filtre actuelles
	const getCurrentFilter = () => {
		const code = searchParams.get("code_selecting");
		const niveau = searchParams.get("niveau_lower");
		if (code && niveau) {
			return { code, niveau };
		}
		return null;
	};

	const currentFilter = getCurrentFilter();

	return (
		<aside className={`sidebar_left ${isOpen ? "sidebar_open" : "sidebar_closed"} ${className}`}>
			<div className="sidebar_header">
				{isOpen ? <h2>Filtres & Options</h2> : <></>}
				<button className="sidebar_toggle" onClick={onToggle} aria-label={isOpen ? "Fermer la sidebar" : "Ouvrir la sidebar"}>
					{isOpen ? "←" : "→"}
				</button>
			</div>

			<div className="sidebar_content">
				<div className="filter_section">
					<div className="filter_group">
						<label htmlFor="location">Localisation</label>
						<div className="search_container">
							<input
								ref={inputRef}
								type="text"
								id="location"
								placeholder="Rechercher une ville..."
								className="filter_input"
								value={location}
								onChange={handleLocationChange}
								onKeyDown={handleKeyDown}
								onFocus={() => location.length > 0 && setShowSuggestions(true)}
								autoComplete="off"
							/>

							{/* Indicateur de chargement dans l'input */}
							{isLoading && (
								<div className="search_loading">
									<span className="loading_spinner">⏳</span>
								</div>
							)}

							{/* Bouton pour vider la recherche */}
							{location && (
								<button type="button" className="clear_search" onClick={handleReset} aria-label="Effacer la recherche">
									×
								</button>
							)}
						</div>

						{/* Liste des suggestions */}
						{showSuggestions && (
							<div className="suggestions_container">
								{isLoading && (
									<div className="suggestion_loading">
										<p>Recherche en cours...</p>
									</div>
								)}

								{error && (
									<div className="suggestion_error">
										<p>Erreur lors de la recherche</p>
									</div>
								)}

								{localisations && localisations.length > 0 && (
									<ul ref={suggestionRef} className="location_suggestions">
										{localisations.map((loc, index) => (
											<li
												key={loc.code}
												className={`suggestion_item ${index === selectedSuggestionIndex ? "selected" : ""}`}
												onClick={() => handleSuggestionClick(loc)}
												onMouseEnter={() => setSelectedSuggestionIndex(index)}
											>
												<span className="suggestion_name">{loc.libelle}</span>
												<span className="suggestion_code">({loc.code})</span>
											</li>
										))}
									</ul>
								)}

								{localisations && localisations.length === 0 && debouncedLocation && !isLoading && (
									<div className="no_suggestions">
										<p>Aucune localisation trouvée</p>
									</div>
								)}
							</div>
						)}
					</div>
				</div>

				{/* Contenu personnalisé */}
				{children}

				<div className="action_section">
					<button className="btn_primary btn_full" onClick={handleApplyFilters} disabled={!location}>
						Appliquer les filtres
					</button>
					<button className="btn_secondary btn_full" onClick={handleReset}>
						Réinitialiser
					</button>
				</div>

				<div className="results_section">
					<h3>Résultats</h3>

					{/* Affichage du filtre actuel */}
					{currentFilter && (
						<div className="current_filter">
							<p>
								<strong>Filtre actif :</strong> {currentFilter.niveau} - Code {currentFilter.code}
							</p>
						</div>
					)}

					{location && (
						<div className="current_location">
							<strong>Recherche : {location}</strong>
						</div>
					)}

					{/* Affichage des propriétés depuis l'API */}
					<div className="results_list">
						{isLoadingProprietes && (
							<div className="loading_message">
								<p>Chargement des propriétés...</p>
							</div>
						)}

						{errorProprietes && (
							<div className="error_message">
								<p>Erreur: {errorProprietes}</p>
							</div>
						)}

						{proprietes && proprietes.length > 0 && (
							<>
								{proprietes.map((propriete) => (
									<div key={propriete.annonce_id} className="result_item">
										<h4>{propriete.titre}</h4>
										<p>
											{propriete.surface && `${propriete.surface}m²`}
											{propriete.pieces && ` • ${propriete.pieces} pièces`}
											{propriete.prix_m2 && ` • ${Math.round(parseFloat(propriete.prix_m2))}€/m²`}
										</p>
										<div className="price_location">
											<span className="price">{formatPrice(propriete.prix)}</span>
											<span className="location">{extractCityName(propriete.ville)}</span>
										</div>
									</div>
								))}
							</>
						)}

						{proprietes && proprietes.length === 0 && !isLoadingProprietes && (
							<div className="no_results">
								<p>Aucune propriété trouvée</p>
							</div>
						)}
					</div>

					{/* Pagination */}
					{pagination && (
						<div className="pagination_info">
							<p>
								Page {pagination.page} sur {pagination.total_pages} ({pagination.total_items} résultats)
							</p>
							<div className="pagination_controls">
								<button
									onClick={() => fetchProprietes(pagination.page - 1)}
									disabled={!pagination.has_prev}
									className="btn_secondary"
								>
									Précédent
								</button>
								<button
									onClick={() => fetchProprietes(pagination.page + 1)}
									disabled={!pagination.has_next}
									className="btn_secondary"
								>
									Suivant
								</button>
							</div>
						</div>
					)}
				</div>
			</div>
		</aside>
	);
};

export default SidebarLeft;
