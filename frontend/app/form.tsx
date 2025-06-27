"use client";

import { useEffect, useState } from "react";
import styles from "./page.module.css";
import { useSearchMailles } from "@/api/maillage";
import { GetShape } from "@/api/maillage/maillage.types";
import { useDispatch, useSelector } from "react-redux";
import { useRouter, useSearchParams } from "next/navigation";

import { AppDispatch } from "@/store/store";
import {
	selectIsLoadingSuggestions,
	selectLocationSuggestion,
	selectLocationSuggestions,
	selectSearchParams,
	setLoadingSuggestions,
	setLocationSuggestions,
	setSearchParams,
	updateSearchParam,
} from "@/store/searchSlice";

export default function Form() {
	const dispatch = useDispatch<AppDispatch>();
	const router = useRouter();
	const urlSearchParams = useSearchParams();

	// Récupérer les données depuis Redux
	const searchParams = useSelector(selectSearchParams);
	const locationSuggestions = useSelector(selectLocationSuggestions);
	const isLoadingLocations = useSelector(selectIsLoadingSuggestions);

	// État local uniquement pour l'UI
	const [showSuggestions, setShowSuggestions] = useState(false);

	// Utilisation du hook useSearchMailles
	const { data: apiLocationSuggestions, isLoading: apiIsLoading } = useSearchMailles(searchParams.location, "commune", 5);

	// Initialiser les paramètres de recherche depuis l'URL au chargement
	useEffect(() => {
		const params: Record<string, string> = {};

		// Vérifier les paramètres possibles
		if (urlSearchParams.has("location")) {
			params.location = urlSearchParams.get("location") || "";
		}

		if (urlSearchParams.has("locationCode")) {
			params.locationCode = urlSearchParams.get("locationCode") || "";
		}

		if (urlSearchParams.has("locationLibelle")) {
			params.locationLibelle = urlSearchParams.get("locationLibelle") || "";
		}

		if (urlSearchParams.has("transactionType")) {
			params.transactionType = urlSearchParams.get("transactionType") || "louer";
		}

		if (urlSearchParams.has("propertyType")) {
			params.propertyType = urlSearchParams.get("propertyType") || "tous";
		}

		if (urlSearchParams.has("minPrice")) {
			params.minPrice = urlSearchParams.get("minPrice") || "";
		}

		if (urlSearchParams.has("maxPrice")) {
			params.maxPrice = urlSearchParams.get("maxPrice") || "";
		}

		// Si des paramètres existent dans l'URL, mettre à jour le state Redux
		if (Object.keys(params).length > 0) {
			dispatch(setSearchParams(params));
		}
	}, [urlSearchParams, dispatch]);

	// Mise à jour des suggestions dans Redux
	useEffect(() => {
		if (apiLocationSuggestions) {
			dispatch(setLocationSuggestions(apiLocationSuggestions));
		}
		dispatch(setLoadingSuggestions(apiIsLoading));
	}, [apiLocationSuggestions, apiIsLoading, dispatch]);

	// Mise à jour de l'URL quand les paramètres de recherche changent
	useEffect(() => {
		// Créer un objet URLSearchParams pour construire l'URL
		const newUrlParams = new URLSearchParams();

		// Ajouter seulement les paramètres qui ont une valeur
		if (searchParams.location) {
			newUrlParams.set("location", searchParams.location);
		}

		if (searchParams.locationCode) {
			newUrlParams.set("locationCode", searchParams.locationCode);
		}

		if (searchParams.locationLibelle) {
			newUrlParams.set("locationLibelle", searchParams.locationLibelle);
		}

		if (searchParams.transactionType) {
			newUrlParams.set("transactionType", searchParams.transactionType);
		}

		if (searchParams.propertyType && searchParams.propertyType !== "tous") {
			newUrlParams.set("propertyType", searchParams.propertyType);
		}

		if (searchParams.minPrice) {
			newUrlParams.set("minPrice", searchParams.minPrice);
		}

		if (searchParams.maxPrice) {
			newUrlParams.set("maxPrice", searchParams.maxPrice);
		}

		// Construire la nouvelle URL
		const newUrl = `${window.location.pathname}?${newUrlParams.toString()}`;

		// Mettre à jour l'URL sans recharger la page
		window.history.replaceState({}, "", newUrl);
	}, [searchParams]);

	const handleInputChange = (e) => {
		const { name, value } = e.target;

		// Dispatch l'action pour mettre à jour le state Redux
		dispatch(updateSearchParam({ name, value }));

		// Si c'est le champ de localisation, on montre les suggestions
		if (name === "location" && value.length >= 2) {
			setShowSuggestions(true);
		} else if (name === "location" && value.length < 2) {
			setShowSuggestions(false);
		}
	};

	// Fonction pour sélectionner une suggestion
	const handleSuggestionSelect = (suggestion: GetShape) => {
		dispatch(
			selectLocationSuggestion({
				libelle: suggestion.libelle,
				code: suggestion.code,
			}),
		);
		// Mettre à jour le champ de recherche avec la suggestion sélectionnée
		dispatch(updateSearchParam({ name: "location", value: suggestion.libelle }));
		setShowSuggestions(false);
	};

	const handleSubmit = (e) => {
		e.preventDefault();

		// Rediriger vers la page de résultats avec les paramètres de recherche
		const params = new URLSearchParams();

		if (searchParams.location) {
			params.set("location", searchParams.location);
		}

		if (searchParams.locationCode) {
			params.set("locationCode", searchParams.locationCode);
		}

		if (searchParams.transactionType) {
			params.set("transactionType", searchParams.transactionType);
		}

		if (searchParams.propertyType && searchParams.propertyType !== "tous") {
			params.set("propertyType", searchParams.propertyType);
		}

		if (searchParams.minPrice) {
			params.set("minPrice", searchParams.minPrice);
		}

		if (searchParams.maxPrice) {
			params.set("maxPrice", searchParams.maxPrice);
		}

		// Rediriger vers la page de résultats
		router.push(`/resultats?${params.toString()}`);
	};

	// Ferme les suggestions en cliquant ailleurs
	useEffect(() => {
		const handleClickOutside = () => {
			setShowSuggestions(false);
		};

		document.addEventListener("click", handleClickOutside);
		return () => {
			document.removeEventListener("click", handleClickOutside);
		};
	}, []);

	return (
		<main className={styles.main}>
			<div className={styles.hero}>
				<div className={styles.heroContent}>
					<h1 className={styles.title}>Trouvez votre logement idéal</h1>
					<p className={styles.subtitle}>Des milliers de biens à louer ou à acheter partout en France</p>

					<div className={styles.searchContainer}>
						<form onSubmit={handleSubmit} className={styles.searchForm}>
							<div className={styles.formRow}>
								<div className={styles.radioGroup}>
									<label className={styles.radioLabel}>
										<input
											type="radio"
											name="transactionType"
											value="louer"
											checked={searchParams.transactionType === "louer"}
											onChange={handleInputChange}
										/>
										Louer
									</label>
									<label className={styles.radioLabel}>
										<input
											type="radio"
											name="transactionType"
											value="acheter"
											checked={searchParams.transactionType === "acheter"}
											onChange={handleInputChange}
										/>
										Acheter
									</label>
								</div>
							</div>

							<div className={styles.formRow}>
								<div className={styles.inputGroup}>
									<label htmlFor="location" className={styles.inputLabel}>
										Où souhaitez-vous {searchParams.transactionType === "louer" ? "louer" : "acheter"} ?
									</label>
									<div className={styles.locationInputContainer}>
										<input
											type="text"
											id="location"
											name="location"
											placeholder="Ville, code postal, quartier..."
											value={searchParams.location}
											onChange={handleInputChange}
											className={styles.input}
											required
											onClick={(e) => {
												e.stopPropagation();
												if (searchParams.location.length >= 2) {
													setShowSuggestions(true);
												}
											}}
										/>

										{/* Indicateur de chargement */}
										{isLoadingLocations && searchParams.location.length >= 2 && (
											<div className={styles.loadingIndicator}>Chargement...</div>
										)}

										{/* Liste des suggestions */}
										{showSuggestions && locationSuggestions && locationSuggestions.length > 0 && (
											<ul className={styles.suggestionsList}>
												{locationSuggestions.map((suggestion) => (
													<li
														key={suggestion.code}
														className={styles.suggestionItem}
														onClick={(e) => {
															e.stopPropagation();
															handleSuggestionSelect(suggestion);
														}}
													>
														{suggestion.libelle}
														{suggestion.code_postal && ` (${suggestion.code_postal})`}
													</li>
												))}
											</ul>
										)}
									</div>
								</div>
							</div>

							<div className={styles.formRow}>
								<div className={styles.selectGroup}>
									<label htmlFor="propertyType" className={styles.inputLabel}>
										Type de bien
									</label>
									<select
										id="propertyType"
										name="propertyType"
										value={searchParams.propertyType}
										onChange={handleInputChange}
										className={styles.select}
									>
										<option value="tous">Tous les biens</option>
										<option value="appartement">Appartement</option>
										<option value="maison">Maison</option>
										<option value="terrain">Terrain</option>
										<option value="commerce">Local commercial</option>
									</select>
								</div>

								<div className={styles.priceRange}>
									<div className={styles.priceInput}>
										<label htmlFor="minPrice" className={styles.inputLabel}>
											Prix min
										</label>
										<input
											type="number"
											id="minPrice"
											name="minPrice"
											placeholder="Min €"
											value={searchParams.minPrice}
											onChange={handleInputChange}
											className={styles.input}
										/>
									</div>
									<div className={styles.priceInput}>
										<label htmlFor="maxPrice" className={styles.inputLabel}>
											Prix max
										</label>
										<input
											type="number"
											id="maxPrice"
											name="maxPrice"
											placeholder="Max €"
											value={searchParams.maxPrice}
											onChange={handleInputChange}
											className={styles.input}
										/>
									</div>
								</div>
							</div>

							<button type="submit" className={styles.searchButton}>
								Rechercher
							</button>
						</form>
					</div>
				</div>
			</div>

			{/* <section className={styles.featuredSection}>
				<h2 className={styles.sectionTitle}>Nos biens à la une</h2>
				<div className={styles.propertyGrid}>
					<div className={styles.propertyCard}>
						<div className={styles.propertyImageContainer}>
							<div className={styles.propertyImagePlaceholder}></div>
						</div>
						<div className={styles.propertyInfo}>
							<h3 className={styles.propertyTitle}>Appartement 3 pièces</h3>
							<p className={styles.propertyLocation}>Paris 15e</p>
							<p className={styles.propertyPrice}>1 500 € /mois</p>
						</div>
					</div>
				</div>
			</section> */}
		</main>
	);
}
