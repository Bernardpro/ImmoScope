import pandas as pd, numpy as np, re, os

input_path = "./osm-france-healthcare2.csv"
output_path = "./hopitaux_clean.csv"

df = pd.read_csv(input_path, sep=";", encoding="utf-8-sig", low_memory=False)

rename_map = {
    "Type": "type",
    "Nom": "nom",
    "Opérateur": "operateur",
    "Urgence": "urgence",
    "Accès handicapés": "acces_handicapes",
    "Heures d'ouverture": "heures_ouverture",
    "Capacité": "capacite",
    "Bénéficiaire": "beneficiaire",
    "Téléphone": "telephone",
    "No. FINESS": "no_finess",
    "Type FINESS": "type_finess",
    "No. NAF": "no_naf",
    "No. SIRET": "no_siret",
    "Commune": "commune",
    "Code Commune": "code_commune",
    "Département": "departement",
    "Code Département": "code_departement",
    "Région": "region",
    "Code Région": "code_region",
    "OSM Point": "osm_point",
    "OSM Id": "osm_id",
    "OSM URL": "osm_url",
    "OSM Date création": "osm_date_creation",
    "OSM Date mise à jour": "osm_date_maj",
    "OSM Versions": "osm_versions",
    "OSM Contributeurs": "osm_contributeurs",
}
df = df.rename(columns=rename_map)

for col in ["urgence", "acces_handicapes"]:
    norm = df[col].astype(str).str.strip().str.lower()
    df[col] = (
        norm.replace({"yes": True, "no": False})
           .where(lambda s: s.isin([True, False]), pd.NA)
           .astype("boolean")
    )

df["capacite"] = (
    df["capacite"]
      .astype(str)
      .str.extract(r"(\d+)", expand=False)
      .astype("Int64")
)

lat, lon = [], []
for v in df["osm_point"].astype(str):
    if pd.isna(v) or v.strip() == "":
        lat.append(np.nan); lon.append(np.nan)
    else:
        try:
            la, lo = [float(s.strip()) for s in v.split(",")]
            lat.append(la); lon.append(lo)
        except Exception:
            lat.append(np.nan); lon.append(np.nan)
df["lat"] = lat
df["lon"] = lon

def parse_date(series):
    iso = pd.to_datetime(series, errors='coerce', utc=True).dt.tz_localize(None)
    fr  = pd.to_datetime(series, dayfirst=True, errors='coerce')
    combined = iso.fillna(fr)
    return combined.dt.strftime('%Y-%m-%d')

df["osm_date_creation"] = parse_date(df["osm_date_creation"])
df["osm_date_maj"] = parse_date(df["osm_date_maj"])

df["osm_id"] = pd.to_numeric(df["osm_id"], errors='coerce').astype("Int64")
df["osm_versions"] = pd.to_numeric(df["osm_versions"], errors='coerce').astype("Int64")

df = df.drop(columns=["osm_point"])

df.to_csv(output_path, sep=";", index=False, na_rep="")

print("✅ Transformation terminée & fichier enregistré : ", output_path)

