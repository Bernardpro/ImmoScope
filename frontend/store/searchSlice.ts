import { createSlice } from "@reduxjs/toolkit";

// État initial simplifié pour la recherche immobilière
const initialState = {
	// Paramètres de recherche
	searchParams: {
		location: "", // Nom de la commune ou de la ville
		locationLibelle: "",
		locationCode: "", // Code de la commune sélectionnée
		transactionType: "louer", // 'louer' ou 'acheter'
		propertyType: "tous", // 'tous', 'appartement', 'maison', 'terrain', 'commerce'
		minPrice: "",
		maxPrice: "",
	},
	// État des suggestions et résultats
	locationSuggestions: [],
	isLoadingSuggestions: false,
	searchResults: [],
	isSearching: false,
	error: null,
};

const searchSlice = createSlice({
	name: "search",
	initialState,
	reducers: {
		// Mise à jour d'un paramètre de recherche individuel
		updateSearchParam: (state, action) => {
			const { name, value } = action.payload;
			state.searchParams[name] = value;
		},

		// Mise à jour de tout le formulaire de recherche
		setSearchParams: (state, action) => {
			state.searchParams = {
				...state.searchParams,
				...action.payload,
			};
		},

		// Réinitialisation du formulaire de recherche
		resetSearchForm: (state) => {
			state.searchParams = initialState.searchParams;
		},

		// Gestion des suggestions de localisation
		setLocationSuggestions: (state, action) => {
			state.locationSuggestions = action.payload;
		},

		setLoadingSuggestions: (state, action) => {
			state.isLoadingSuggestions = action.payload;
		},

		// Sélection d'une suggestion de localisation
		selectLocationSuggestion: (state, action) => {
			const { libelle, code } = action.payload;
			state.searchParams.locationLibelle = libelle;
			state.searchParams.locationCode = code;
			state.locationSuggestions = []; // Vider les suggestions après sélection
		},

		// Gestion des résultats de recherche
		setSearchResults: (state, action) => {
			state.searchResults = action.payload;
		},

		setIsSearching: (state, action) => {
			state.isSearching = action.payload;
		},

		// Gestion des erreurs
		setError: (state, action) => {
			state.error = action.payload;
		},

		clearError: (state) => {
			state.error = null;
		},
	},
});

// Export des actions
export const {
	updateSearchParam,
	setSearchParams,
	resetSearchForm,
	setLocationSuggestions,
	setLoadingSuggestions,
	selectLocationSuggestion,
	setSearchResults,
	setIsSearching,
	setError,
	clearError,
} = searchSlice.actions;

// Sélecteurs
export const selectSearchParams = (state) => state.search.searchParams;
export const selectLocationSuggestions = (state) => state.search.locationSuggestions;
export const selectIsLoadingSuggestions = (state) => state.search.isLoadingSuggestions;
export const selectSearchResults = (state) => state.search.searchResults;
export const selectIsSearching = (state) => state.search.isSearching;
export const selectError = (state) => state.search.error;

export default searchSlice.reducer;
