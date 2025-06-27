import React, { useState, useEffect, useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from "recharts";
import TermsBySentiment from "./TermsBySentiment";
import "./SideBarRight.scss";
import { useSearchParams } from "next/navigation";

// Interfaces pour les données de réputation
interface ReputationDataItem {
	code_commune: string;
	annee: string;
	indicateur: string;
	unite_de_compte: string;
	value: number;
	taux_pour_mille: number;
}

// Interfaces pour les données de taxe foncière
interface TaxeFoncierDataItem {
	code: number;
	niveau: string;
	exercice: string;
	avg: number;
}

interface TaxeFoncierApiResponse {
	data: TaxeFoncierDataItem[];
	filtre: string[] | null;
	annee: string[];
}

interface ReputationApiResponse {
	data: ReputationDataItem[];
	filtre: string[];
	annee: string[];
}

// Interfaces pour les données foncières
interface FoncierDataItem {
	date_mutation: string;
	nature_mutation: string;
	value: number;
}

interface FoncierApiResponse {
	data: FoncierDataItem[];
	filtre: string[];
	annee: string[];
}

// Interfaces communes
interface EvolutionData {
	period: string;
	value: number;
	count?: number;
}

interface NatureStats {
	nature: string;
	total: number;
	count: number;
	percentage: number;
}

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6", "#F97316"];

const SidebarRight = ({ code_selecting }: { code_selecting: string }) => {
	const searchParams = useSearchParams();
	const urlParams = useMemo(() => {
		return {
			niveauMaille: searchParams.get("niveau_lower") || searchParams.get("niveau") || "region",
			typeDataDisplay: searchParams.get("typeDataDisplay") || "reputation",
		};
	}, [searchParams]);
	const { niveauMaille, typeDataDisplay } = urlParams;

	const [reputationData, setReputationData] = useState<ReputationDataItem[]>([]);
	const [foncierData, setFoncierData] = useState<FoncierDataItem[]>([]);
	const [evolutionData, setEvolutionData] = useState<EvolutionData[]>([]);
	const [evolutionDataTaxe, setEvolutionDataTaxe] = useState<EvolutionData[]>([]);
	const [natureStats, setNatureStats] = useState<NatureStats[]>([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [filtreDisplay, setFiltreDisplay] = useState("all");
	const [filtreList, setFiltreList] = useState<string[]>([]);
	const [taxeFoncierData, setTaxeFoncierData] = useState<TaxeFoncierDataItem[]>([]);

	// Stats pour réputation
	const [reputationStats, setReputationStats] = useState({
		max: 0,
		min: 0,
		avg: 0,
		evolution: 0,
		maxYear: "",
		minYear: "",
	});

	// Stats pour foncier
	const [foncierStats, setFoncierStats] = useState({
		totalValue: 0,
		totalTransactions: 0,
		avgValue: 0,
		maxTransaction: 0,
		minTransaction: 0,
		maxDate: "",
		minDate: "",
	});

	// Fonction pour formater les montants
	const formatCurrency = (value: number) => {
		return new Intl.NumberFormat("fr-FR", {
			style: "currency",
			currency: "EUR",
			maximumFractionDigits: 0,
		}).format(value);
	};

	// Fonction pour formater les dates selon la granularité
	const formatPeriod = (dateStr: string, typeDataDisplay: string) => {
		if (typeDataDisplay === "reputation") {
			return dateStr; // Année simple
		}

		// Pour foncier, adapter selon le format
		if (dateStr.includes("-S")) {
			// Format semaine: 2024-S01
			const [year, week] = dateStr.split("-S");
			return `Sem ${week} ${year}`;
		} else if (dateStr.length === 10) {
			// Format jour: 2024-01-15
			const date = new Date(dateStr);
			return date.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
		} else if (dateStr.length === 7) {
			// Format mois: 2024-01
			return formatMonth(dateStr);
		}
		return dateStr;
	};

	const formatMonth = (dateStr: string) => {
		const [year, month] = dateStr.split("-");
		const date = new Date(parseInt(year), parseInt(month) - 1);
		return date.toLocaleDateString("fr-FR", { year: "numeric", month: "short" });
	};

	// Fonction pour appeler l'API réputation
	const fetchReputationData = async (codeCommune: string) => {
		if (!codeCommune || typeDataDisplay !== "reputation") return;

		setLoading(true);
		setError(null);

		try {
			const response = await fetch(
				`https://api.homepedia.spectrum-app.cloud/data/reputations/chart?code=${codeCommune}&niveau=${niveauMaille}`,
				{
					method: "GET",
					headers: {
						accept: "application/json",
						"Content-Type": "application/json",
					},
				},
			);

			if (!response.ok) {
				throw new Error(`Erreur HTTP: ${response.status}`);
			}

			const result: ReputationApiResponse = await response.json();
			setReputationData(result.data || []);

			// get filtre
			const filtre = result.filtre || [];
			filtre.sort((a, b) => a.localeCompare(b));
			setFiltreList(filtre);

			// Extraire les données d'évolution selon le filtre sélectionné
			const filteredData = result.data
				.filter((item) => {
					return item.unite_de_compte === filtreDisplay;
				})
				.map((item) => ({
					period: item.annee,
					value: item.value,
				}))
				.sort((a, b) => parseInt(a.period) - parseInt(b.period));

			setEvolutionData(filteredData);

			// Calculer les statistiques
			if (filteredData.length > 0) {
				const values = filteredData.map((d) => d.value);
				const max = Math.max(...values);
				const min = Math.min(...values);
				const avg = Math.round(values.reduce((sum, val) => sum + val, 0) / values.length);
				const firstYear = filteredData[0];
				const lastYear = filteredData[filteredData.length - 1];
				const evolution = ((lastYear.value - firstYear.value) / firstYear.value) * 100;

				const maxItem = filteredData.find((d) => d.value === max);
				const minItem = filteredData.find((d) => d.value === min);

				setReputationStats({
					max,
					min,
					avg,
					evolution: parseFloat(evolution.toFixed(1)),
					maxYear: maxItem?.period || "",
					minYear: minItem?.period || "",
				});
			} else {
				setReputationStats({
					max: 0,
					min: 0,
					avg: 0,
					evolution: 0,
					maxYear: "",
					minYear: "",
				});
			}
		} catch (err) {
			console.error("Erreur lors de la récupération des données:", err);
			setError(err instanceof Error ? err.message : "Une erreur est survenue");
		} finally {
			setLoading(false);
		}
	};

	// Fonction pour appeler l'API foncier
	const fetchFoncierData = async (codeCommune: string) => {
		if (!codeCommune || typeDataDisplay !== "foncier") return;

		setLoading(true);
		setError(null);

		try {
			const response = await fetch(
				`https://api.homepedia.spectrum-app.cloud/data/fonciers?code=${codeCommune}&niveau=${niveauMaille}`,
				{
					method: "GET",
					headers: {
						accept: "application/json",
						"Content-Type": "application/json",
					},
				},
			);

			if (!response.ok) {
				throw new Error(`Erreur HTTP: ${response.status}`);
			}

			const result: FoncierApiResponse = await response.json();
			setFoncierData(result.data || []);

			// Récupérer la liste des filtres
			const filtres = ["all", ...result.filtre];
			setFiltreList(filtres);

			// Filtrer les données selon le filtre sélectionné
			const filteredData =
				filtreDisplay === "all" ? result.data : result.data.filter((item) => item.nature_mutation === filtreDisplay);

			// Traiter les données pour l'évolution mensuelle
			const monthlyData: { [key: string]: { total: number; count: number } } = {};

			filteredData.forEach((item) => {
				if (!item.date_mutation) return;
				const monthKey = item.date_mutation.substring(0, 7); // YYYY-MM
				if (!monthlyData[monthKey]) {
					monthlyData[monthKey] = { total: 0, count: 0 };
				}
				monthlyData[monthKey].total += item.value || 0;
				monthlyData[monthKey].count += 1;
			});

			const evolution = Object.entries(monthlyData)
				.map(([mois, data]) => ({
					period: mois,
					value: Math.round(data.total),
					count: data.count,
				}))
				.sort((a, b) => a.period.localeCompare(b.period));

			setEvolutionData(evolution);

			// Calculer les statistiques par nature de mutation
			const statsByNature: { [key: string]: { total: number; count: number } } = {};
			result.data.forEach((item) => {
				if (!statsByNature[item.nature_mutation]) {
					statsByNature[item.nature_mutation] = { total: 0, count: 0 };
				}
				statsByNature[item.nature_mutation].total += item.value;
				statsByNature[item.nature_mutation].count += 1;
			});

			const totalAllNatures = Object.values(statsByNature).reduce((sum, stat) => sum + stat.total, 0);

			const natureStatsArray = Object.entries(statsByNature)
				.map(([nature, stat]) => ({
					nature,
					total: stat.total,
					count: stat.count,
					percentage: (stat.total / totalAllNatures) * 100,
				}))
				.sort((a, b) => b.total - a.total);

			setNatureStats(natureStatsArray);

			// Récupération des données de taxe foncière
			try {
				const response_taxe = await fetch(
					`https://api.homepedia.spectrum-app.cloud/data/taxe/fonciers?code=${codeCommune}&niveau=${niveauMaille}`,
					{
						method: "GET",
						headers: {
							accept: "application/json",
							"Content-Type": "application/json",
						},
					},
				);

				if (response_taxe.ok) {
					const result_taxe: TaxeFoncierApiResponse = await response_taxe.json();
					setTaxeFoncierData(result_taxe.data || []);

					// Grouper les données par exercice et calculer la moyenne
					const dataByYear: { [key: string]: number[] } = {};
					result_taxe.data.forEach((item) => {
						if (!dataByYear[item.exercice]) {
							dataByYear[item.exercice] = [];
						}
						dataByYear[item.exercice].push(item.avg);
					});

					// Calculer la moyenne pour chaque année
					const evolution_taxe = Object.entries(dataByYear)
						.map(([year, values]) => ({
							period: year,
							value: Math.round(values.reduce((sum, val) => sum + val, 0) / values.length),
						}))
						.sort((a, b) => parseInt(a.period) - parseInt(b.period));

					setEvolutionDataTaxe(evolution_taxe);
				} else {
					console.warn("Données de taxe foncière non disponibles");
					setEvolutionDataTaxe([]);
				}
			} catch (taxeError) {
				console.warn("Erreur lors de la récupération des données de taxe foncière:", taxeError);
				setEvolutionDataTaxe([]);
			}

			// Calculer les statistiques globales
			if (filteredData.length > 0) {
				const values = filteredData.map((d) => d.value);
				const totalValue = values.reduce((sum, val) => sum + val, 0);
				const maxValue = Math.max(...values);
				const minValue = Math.min(...values);

				const maxItem = filteredData.find((d) => d.value === maxValue);
				const minItem = filteredData.find((d) => d.value === minValue);

				setFoncierStats({
					totalValue,
					totalTransactions: filteredData.length,
					avgValue: Math.round(totalValue / filteredData.length),
					maxTransaction: maxValue,
					minTransaction: minValue,
					maxDate: maxItem?.date_mutation || "",
					minDate: minItem?.date_mutation || "",
				});
			} else {
				setFoncierStats({
					totalValue: 0,
					totalTransactions: 0,
					avgValue: 0,
					maxTransaction: 0,
					minTransaction: 0,
					maxDate: "",
					minDate: "",
				});
			}
		} catch (err) {
			console.error("Erreur lors de la récupération des données:", err);
			setError(err instanceof Error ? err.message : "Une erreur est survenue");
		} finally {
			setLoading(false);
		}
	};

	// Effet pour charger les données quand le code change
	useEffect(() => {
		// Réinitialiser les données
		setReputationData([]);
		setFoncierData([]);
		setEvolutionData([]);
		setEvolutionDataTaxe([]);
		setNatureStats([]);
		setFiltreList([]);
		setError(null);
		setLoading(false);

		// Réinitialiser le filtre lors du changement de type
		setFiltreDisplay("all");

		if (typeDataDisplay === "reputation") {
			fetchReputationData(code_selecting);
		} else if (typeDataDisplay === "foncier") {
			fetchFoncierData(code_selecting);
		}
	}, [code_selecting, typeDataDisplay, niveauMaille]);

	// Effet pour recharger les données quand le filtre change
	useEffect(() => {
		if (typeDataDisplay === "reputation") {
			fetchReputationData(code_selecting);
		} else if (typeDataDisplay === "foncier") {
			fetchFoncierData(code_selecting);
		}
	}, [filtreDisplay]);

	// Composant Tooltip personnalisé pour réputation
	const ReputationTooltip = ({ active, payload, label }: any) => {
		if (active && payload && payload.length) {
			const data = payload[0].payload;
			return (
				<div className="tooltip-container">
					<p className="tooltip-title">Année {label}</p>
					<p className="tooltip-value">
						<span>Total:</span> {data.value.toLocaleString()} infractions
					</p>
				</div>
			);
		}
		return null;
	};

	// Composant Tooltip personnalisé pour foncier
	const FoncierTooltip = ({ active, payload, label }: any) => {
		if (active && payload && payload.length) {
			const data = payload[0].payload;
			return (
				<div className="tooltip-container">
					<p className="tooltip-title">{formatPeriod(label, "foncier")}</p>
					<p className="tooltip-value">
						<span>Montant:</span> {formatCurrency(data.value)}
					</p>
					{data.count && (
						<p className="tooltip-value">
							<span>Transactions:</span> {data.count}
						</p>
					)}
				</div>
			);
		}
		return null;
	};

	// Composant Tooltip pour les taxes foncières
	const TaxeFoncierTooltip = ({ active, payload, label }: any) => {
		if (active && payload && payload.length) {
			const data = payload[0].payload;
			return (
				<div className="tooltip-container">
					<p className="tooltip-title">Année {label}</p>
					<p className="tooltip-value">
						<span>Taxe moyenne:</span> {formatCurrency(data.value)}
					</p>
				</div>
			);
		}
		return null;
	};

	// Composant Tooltip pour le pie chart
	const CustomPieTooltip = ({ active, payload }: any) => {
		if (active && payload && payload.length) {
			const data = payload[0].payload;
			return (
				<div className="tooltip-container">
					<p className="tooltip-title">{data.nature}</p>
					<p className="tooltip-value">
						<span>Montant:</span> {formatCurrency(data.total)}
					</p>
					<p className="tooltip-value">
						<span>Transactions:</span> {data.count}
					</p>
					<p className="tooltip-value">
						<span>Part:</span> {data.percentage.toFixed(1)}%
					</p>
				</div>
			);
		}
		return null;
	};

	// Fonction de retry
	const handleRetry = () => {
		if (typeDataDisplay === "reputation") {
			fetchReputationData(code_selecting);
		} else if (typeDataDisplay === "foncier") {
			fetchFoncierData(code_selecting);
		}
	};

	// Calculer la variation par rapport à l'année précédente pour la dernière année (réputation)
	const getLastYearVariation = () => {
		if (evolutionData.length < 2 || typeDataDisplay !== "reputation") return null;
		const current = evolutionData[evolutionData.length - 1];
		const previous = evolutionData[evolutionData.length - 2];
		return (((current.value - previous.value) / previous.value) * 100).toFixed(1);
	};

	const lastYearVariation = getLastYearVariation();

	return (
		<div className="sidebar_right">
			<div className="sidebar-header">
				<h2>{typeDataDisplay === "reputation" ? "Évolution Infractions" : "Données Foncières"}</h2>
				<p className="commune-code">
					{niveauMaille}: {code_selecting}
				</p>
			</div>

			{/* Afficher TermsBySentiment uniquement pour réputation */}
			{typeDataDisplay === "reputation" && <TermsBySentiment codeCommune={code_selecting} />}

			{/* État de chargement */}
			{loading && (
				<div className="loading-container">
					<div className="spinner"></div>
					<p>Chargement...</p>
				</div>
			)}

			{/* État d'erreur */}
			{error && (
				<div className="no-data-container">
					{/* <p className="error-message">⚠️ {error}</p>
					<button onClick={handleRetry} className="retry-button">
						Réessayer
					</button> */}
					Pas de données disponibles pour cette maille.
				</div>
			)}

			{/* Contrôles */}
			{!loading && !error && filtreList.length > 0 && (
				<div className="controls-container">
					<div className="control-group">
						<label>{typeDataDisplay === "reputation" ? "Type d'infraction:" : "Type de mutation:"}</label>
						<select value={filtreDisplay} onChange={(e) => setFiltreDisplay(e.target.value)} className="control-select">
							{filtreList.map((filtre, index) => (
								<option key={index} value={filtre}>
									{filtre === "all" ? "Tous les types" : filtre}
								</option>
							))}
						</select>
					</div>
				</div>
			)}

			{/* Contenu principal pour réputation */}
			{!loading && !error && evolutionData.length > 0 && typeDataDisplay === "reputation" && (
				<>
					{/* Statistiques rapides */}
					<div className="stats-grid">
						<div className="stat-card">
							<div className="stat-label">Max</div>
							<div className="stat-value max">{reputationStats.max.toLocaleString()}</div>
							<div className="stat-year">{reputationStats.maxYear}</div>
						</div>
						<div className="stat-card">
							<div className="stat-label">Min</div>
							<div className="stat-value min">{reputationStats.min.toLocaleString()}</div>
							<div className="stat-year">{reputationStats.minYear}</div>
						</div>
						<div className="stat-card">
							<div className="stat-label">Évolution</div>
							<div className={`stat-value ${reputationStats.evolution >= 0 ? "positive" : "negative"}`}>
								{reputationStats.evolution >= 0 ? "+" : ""}
								{reputationStats.evolution}%
							</div>
							<div className="stat-year">total</div>
						</div>
					</div>

					{/* Graphique */}
					<div className="chart-container">
						<ResponsiveContainer width="100%" height={250}>
							<LineChart data={evolutionData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
								<CartesianGrid strokeDasharray="3 3" />
								<XAxis dataKey="period" fontSize={10} tick={{ fontSize: 10 }} />
								<YAxis fontSize={10} tickFormatter={(value) => `${value.toFixed(0)}`} />
								<Tooltip content={<ReputationTooltip />} />
								<Line type="monotone" dataKey="value" stroke="#3B82F6" strokeWidth={2} dot={{ r: 3, fill: "#3B82F6" }} />
							</LineChart>
						</ResponsiveContainer>
					</div>

					{/* Résumé de l'évolution */}
					<div className="summary-container">
						<h3>Analyse rapide</h3>
						<div className="summary-stats">
							<div className="stat-item">
								<span className="stat-label">Moyenne:</span>
								<span className="stat-value">{reputationStats.avg.toLocaleString()}</span>
							</div>
							<div className="stat-item">
								<span className="stat-label">Période:</span>
								<span className="stat-value">
									{evolutionData[0]?.period} - {evolutionData[evolutionData.length - 1]?.period}
								</span>
							</div>
							{lastYearVariation && (
								<div className="stat-item">
									<span className="stat-label">Dernière variation:</span>
									<span className={`stat-value ${parseFloat(lastYearVariation) >= 0 ? "positive" : "negative"}`}>
										{parseFloat(lastYearVariation) >= 0 ? "+" : ""}
										{lastYearVariation}%
									</span>
								</div>
							)}
						</div>
					</div>
				</>
			)}

			{/* Contenu principal pour foncier */}
			{!loading && !error && evolutionData.length > 0 && typeDataDisplay === "foncier" && (
				<>
					{/* Statistiques globales */}
					<div className="stats-grid">
						<div className="stat-card">
							<div className="stat-label">Volume total</div>
							<div className="stat-value">{formatCurrency(foncierStats.totalValue)}</div>
							<div className="stat-year">{foncierStats.totalTransactions} transactions</div>
						</div>
						<div className="stat-card">
							<div className="stat-label">Transaction max</div>
							<div className="stat-value max">{formatCurrency(foncierStats.maxTransaction)}</div>
							<div className="stat-year">
								{foncierStats.maxDate ? new Date(foncierStats.maxDate).toLocaleDateString("fr-FR") : ""}
							</div>
						</div>
						<div className="stat-card">
							<div className="stat-label">Moyenne</div>
							<div className="stat-value">{formatCurrency(foncierStats.avgValue)}</div>
							<div className="stat-year">par transaction</div>
						</div>
					</div>

					{/* Graphique d'évolution des transactions */}
					<div className="chart-container">
						<h3>Évolution des transactions foncières</h3>
						<ResponsiveContainer width="100%" height={250}>
							<LineChart data={evolutionData} margin={{ top: 10, right: 10, left: 10, bottom: 60 }}>
								<CartesianGrid strokeDasharray="3 3" />
								<XAxis
									dataKey="period"
									fontSize={10}
									tick={{ fontSize: 10 }}
									tickFormatter={(value) => formatPeriod(value, typeDataDisplay)}
									angle={-45}
									textAnchor="end"
									height={60}
								/>
								<YAxis fontSize={10} tickFormatter={(value) => `${(value / 1000000).toFixed(1)}M€`} />
								<Tooltip content={<FoncierTooltip />} />
								<Line type="monotone" dataKey="value" stroke="#3B82F6" strokeWidth={2} dot={{ r: 3, fill: "#3B82F6" }} />
							</LineChart>
						</ResponsiveContainer>
					</div>

					{/* Graphique d'évolution des taxes foncières */}
					{evolutionDataTaxe.length > 0 && (
						<div className="chart-container">
							<h3>Évolution des taxes foncières</h3>
							<ResponsiveContainer width="100%" height={250}>
								<LineChart data={evolutionDataTaxe} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
									<CartesianGrid strokeDasharray="3 3" />
									<XAxis dataKey="period" fontSize={10} tick={{ fontSize: 10 }} />
									<YAxis fontSize={10} tickFormatter={(value) => `${formatCurrency(value)}`} />
									<Tooltip content={<TaxeFoncierTooltip />} />
									<Line
										type="monotone"
										dataKey="value"
										stroke="#10B981"
										strokeWidth={2}
										dot={{ r: 3, fill: "#10B981" }}
									/>
								</LineChart>
							</ResponsiveContainer>
						</div>
					)}

					{/* Graphique en secteurs par nature de mutation */}
					{natureStats.length > 0 && (
						<div className="chart-container">
							<h3>Répartition par nature de mutation</h3>
							<ResponsiveContainer width="100%" height={300}>
								<PieChart>
									<Pie
										data={natureStats}
										cx="50%"
										cy="50%"
										labelLine={false}
										label={({ nature, percentage }) => `${nature}: ${percentage.toFixed(1)}%`}
										outerRadius={80}
										fill="#8884d8"
										dataKey="total"
									>
										{natureStats.map((entry, index) => (
											<Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
										))}
									</Pie>
									<Tooltip content={<CustomPieTooltip />} />
								</PieChart>
							</ResponsiveContainer>
						</div>
					)}
				</>
			)}

			{/* Message quand pas de données */}
			{!loading && !error && evolutionData.length === 0 && code_selecting && (
				<div className="no-data-container">
					<p>Aucune donnée disponible{filtreDisplay !== "all" ? ` pour le type "${filtreDisplay}"` : ""}.</p>
					{filtreList.length > 0 && filtreDisplay !== "all" && (
						<p className="hint">
							Essayez de sélectionner "Tous les types" ou un autre type{" "}
							{typeDataDisplay === "reputation" ? "d'infraction" : "de mutation"} dans le menu déroulant ci-dessus.
						</p>
					)}
				</div>
			)}
		</div>
	);
};

export default SidebarRight;
