import pandas as pd
import os

# Définir le chemin du fichier CSV
csv_path = os.path.join("api", "scraping", "villes.csv")

# Charger le fichier CSV
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()

df = df[df['url'] != "https://www.seloger.com/"]

# Trouver les villes dupliquées (celles qui apparaissent plus d'une fois)
villes_en_doublon = df['libelle'].duplicated(keep='first')

# Supprimer toutes les lignes où la ville est en doublon
df_sans_villes_duplicated = df[~villes_en_doublon]

# Sauvegarder le résultat dans un nouveau fichier
output_path = os.path.join("api", "scraping", "villes_sans_doublons.csv")
df_sans_villes_duplicated.to_csv(output_path, index=False)