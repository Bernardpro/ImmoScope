import styles from "./page.module.scss";

const fakeData = [
	{
		annonce_id: "1",
		titre: "Appartement 3 pièces lumineux",
		prix: 1500,
		surface: 65,
		ville: "Paris",
		code_postal: "75015",
		site_id: "site_001",
		source: "leboncoin",
		prix_m2: 23.08,
		created_at: "2024-01-15T10:30:00Z",
		updated_at: "2024-01-15T10:30:00Z",
	},
	{
		annonce_id: "2",
		titre: "Studio moderne centre-ville",
		prix: 850,
		surface: 25,
		ville: "Lyon",
		code_postal: "69001",
		site_id: "site_002",
		source: "seloger",
		prix_m2: 34.0,
		created_at: "2024-01-16T14:20:00Z",
		updated_at: "2024-01-16T14:20:00Z",
	},
	{
		annonce_id: "3",
		titre: "Maison avec jardin",
		prix: 2200,
		surface: 120,
		ville: "Marseille",
		code_postal: "13008",
		site_id: "site_003",
		source: "pap",
		prix_m2: 18.33,
		created_at: "2024-01-17T09:15:00Z",
		updated_at: "2024-01-17T09:15:00Z",
	},
	{
		annonce_id: "4",
		titre: "Appartement 2 pièces rénové",
		prix: 1200,
		surface: 45,
		ville: "Toulouse",
		code_postal: "31000",
		site_id: "site_004",
		source: "leboncoin",
		prix_m2: 26.67,
		created_at: "2024-01-18T16:45:00Z",
		updated_at: "2024-01-18T16:45:00Z",
	},
	{
		annonce_id: "5",
		titre: "T4 avec balcon",
		prix: 1800,
		surface: 85,
		ville: "Nice",
		code_postal: "06000",
		site_id: "site_005",
		source: "seloger",
		prix_m2: 21.18,
		created_at: "2024-01-19T11:30:00Z",
		updated_at: "2024-01-19T11:30:00Z",
	},
	{
		annonce_id: "6",
		titre: "Loft atypique",
		prix: 2500,
		surface: 95,
		ville: "Bordeaux",
		code_postal: "33000",
		site_id: "site_006",
		source: "pap",
		prix_m2: 26.32,
		created_at: "2024-01-20T13:10:00Z",
		updated_at: "2024-01-20T13:10:00Z",
	},
];

export default function Page() {
	return (
		<div>
			<section className={styles.featuredSection}>
				<h2 className={styles.sectionTitle}>Nos biens à la une</h2>
				<div className={styles.propertyGrid}>
					{fakeData.map((propriete) => (
						<div key={propriete.annonce_id} className={styles.propertyCard}>
							<div className={styles.propertyImageContainer}>
								<div className={styles.propertyImagePlaceholder}></div>
							</div>
							<div className={styles.propertyInfo}>
								<h3 className={styles.propertyTitle}>{propriete.titre}</h3>
								<p className={styles.propertyLocation}>
									{propriete.ville} {propriete.code_postal}
								</p>
								<p className={styles.propertyPrice}>{propriete.prix.toLocaleString()} € /mois</p>
								<p style={{ fontSize: "0.8rem", color: "#999", marginTop: "0.5rem" }}>
									{propriete.surface} m² • {propriete.prix_m2.toFixed(2)} €/m²
								</p>
							</div>
						</div>
					))}
				</div>
			</section>
		</div>
	);
}
