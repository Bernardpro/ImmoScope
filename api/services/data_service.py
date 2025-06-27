import logging
from functools import lru_cache
from typing import Optional, Dict, Any, List

import pandas as pd
from sqlalchemy import text

from db.session import get_engine

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_foncier_by_maille(code: str, niveau: str, engine=None) -> Optional[Dict[str, Any]]:
    """
    Récupère les données foncières par commune avec optimisations.

    Optimisations :
    - Sélection uniquement des colonnes nécessaires
    - Index sur code_commune recommandé
    """
    if engine is None:
        engine = get_engine()

    # Optimisation : ne sélectionner que les colonnes nécessaires
    query = text("""
        SELECT date_mutation, nature_mutation, somme_valeur_fonciere
        FROM fonciers 
        WHERE code = :code AND niveau = :niveau
    """)

    try:
        df = pd.read_sql(query, engine, params={"code": str(code), "niveau": str(niveau)})

        if df.empty:
            logger.info(f"Aucune donnée foncière trouvée pour la commune {code} niveau {niveau}")
            return []

        # Renommer la colonne
        # df.rename(columns={"somme_valeur_fonciere": "value"}, inplace=True)
        # Convertir les dates en format lisible
        df['date_mutation'] = pd.to_datetime(df['date_mutation'], errors='coerce').dt.strftime('%Y-%m-%d')
        # somme_valeur_fonciere eror fload json
        df.rename(columns={"somme_valeur_fonciere": "value"}, inplace=True)
        df['value'] = df['value'].astype(float).fillna(0)

        print(df)

        return {
            "data": df.to_dict(orient="records"),
            "filtre": df['nature_mutation'].unique().tolist(),
            "annee": df['date_mutation'].unique().tolist(),
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données foncières: {e}")
        return []


def get_taxe_foncier_by_maille(code: str, niveau: str, engine=None) -> Optional[Dict[str, Any]]:
    query_region = """select distinct code, niveau, exercice, somme
        from taxe_fonciers
        where code = :code and niveau = :niveau"""

    if engine is None:
        engine = get_engine()

    query = text(query_region)

    # Normaliser le niveau de maille
    niveau = 'dep'
    if niveau == 'departement':
        niveau = 'dep'
    elif niveau == 'commune':
        niveau = 'commune'
    elif niveau == 'region':
        niveau = 'region'
    else:
        logger.error(f"Niveau de maille non supporté: {niveau}")
        return None
    try:
        df = pd.read_sql(query, engine, params={"code": code, "niveau": str(niveau)})

        if df.empty:
            logger.info(f"Aucune donnée de taxe foncière trouvée pour {code} niveau {niveau}")
            return []

        # Renommer la colonne
        df.rename(columns={"avg(taux_global_tfb)": "value"}, inplace=True)
        # Convertir les exercices en format lisible
        # df['exercice'] = pd.to_datetime(df['exercice'], errors='coerce').dt.strftime('%Y')

        return {
            "data": df.to_dict(orient="records"),
            "filtre": None,  # Pas de filtre spécifique pour la taxe foncièrea
            "annee": sorted(df['exercice'].unique().tolist())
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données de taxe foncière: {e}")
        return []


def get_reputations_by_maille(code: str, niveau: str, engine=None) -> Optional[Dict[str, Any]]:
    """
    Récupère les réputations par maille avec optimisations.

    Optimisations :
    - Index composé sur (code, niveau) recommandé
    - Agrégation optimisée
    """
    if engine is None:
        engine = get_engine()

    query = text("""
        SELECT 
            code, 
            annee, 
            unite_de_compte, 
            SUM(nombre) as value, 
            SUM(taux_pour_mille) as taux_pour_mille 
        FROM reputations 
        WHERE code = :code AND niveau = :niveau 
        GROUP BY code, annee, unite_de_compte
        ORDER BY annee, unite_de_compte
    """)

    try:
        df = pd.read_sql(query, engine, params={"code": code, "niveau": niveau})

        if df.empty:
            logger.info(f"Aucune réputation trouvée pour {code} niveau {niveau}")
            return None

        return {
            "data": df.to_dict(orient="records"),
            'filtre': df['unite_de_compte'].unique().tolist(),
            "annee": sorted(df['annee'].unique().tolist())
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réputations: {e}")
        return None


def get_reputations_color_by_maille(code: str, niveau: str, engine=None) -> Optional[Dict[str, Any]]:
    """
    Récupère les réputations avec couleurs par maille.
    La couleur est calculée en fonction du ratio de la valeur par rapport au total du niveau.

    Optimisations :
    - Requête filtrée dès le départ
    - Index composé sur (unite_de_compte, annee, code, niveau) recommandé
    """
    if engine is None:
        engine = get_engine()

    # get all value of same niveau
    query_niveau = text("""
        SELECT 
            SUM(nombre) as value 
        FROM reputations 
        WHERE unite_de_compte = 'all' 
            AND annee = '2024' 
            AND niveau = :niveau 
    """)
    try:
        df_niveau = pd.read_sql(query_niveau, engine, params={"niveau": niveau})
        if df_niveau.empty or df_niveau['value'].iloc[0] == 0:
            logger.info(f"Aucune réputation trouvée pour le niveau {niveau}")
            return None
        total_value = df_niveau['value'].iloc[0]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la valeur totale pour le niveau {niveau}: {e}")
        return None

    query = text("""
        SELECT 
            code, 
            SUM(nombre) as value 
        FROM reputations 
        WHERE unite_de_compte = 'all' 
            AND annee = '2024' 
            AND code = :code 
            AND niveau = :niveau 
        GROUP BY code
    """)

    try:
        df = pd.read_sql(query, engine, params={"code": code, "niveau": niveau})

        if df.empty:
            logger.info(f"Aucune réputation 2024 trouvée pour {code} niveau {niveau}")
            return None

        # Calculer le ratio en pourcentage pour mille (‰)
        df['ratio_pour_mille'] = (df['value'] / total_value) * 1000

        # Appliquer la fonction de couleur basée sur le ratio
        logger.info(f"Calcul des couleurs pour le code {code} niveau {niveau} (total niveau: {total_value})")
        df['color'] = df['ratio_pour_mille'].apply(calculate_color_from_ratio)

        # Ajouter les informations de ratio dans le résultat
        df['value_percentage'] = (df['value'] / total_value) * 100

        return {
            "data": df.to_dict(orient="records"),
            "total_niveau": total_value,
            'filtre': [
                {"seuil": 3, "couleur": "#E8F5E8", "description": "Maille très sûre (< 3‰)"},
                {"seuil": 5, "couleur": "#C8E6C9", "description": "Maille sûre (3-5‰)"},
                {"seuil": 7, "couleur": "#A5D6A7", "description": "Maille plutôt sûre (5-7‰)"},
                {"seuil": 9, "couleur": "#81C784", "description": "Maille modérément sûre (7-9‰)"},
                {"seuil": 14, "couleur": "#FFE082", "description": "Maille légèrement risquée (9-14‰)"},
                {"seuil": 18, "couleur": "#FFCC02", "description": "Maille attention (14-18‰)"},
                {"seuil": 25, "couleur": "#FF9800", "description": "Maille vigilance (18-25‰)"},
                {"seuil": 50, "couleur": "#F57C00", "description": "Maille risquée (25-50‰)"},
                {"seuil": 75, "couleur": "#F4511E", "description": "Maille très risquée (50-75‰)"},
                {"seuil": 100, "couleur": "#F44336", "description": "Maille dangereuse (75-100‰)"},
                {"seuil": 150, "couleur": "#D32F2F", "description": "Maille très dangereuse (100-150‰)"},
                {"seuil": 200, "couleur": "#B71C1C", "description": "Maille peu sûre (150-200‰)"},
                {"seuil": 300, "couleur": "#880E4F", "description": "Maille critique (200-300‰)"},
                {"seuil": 400, "couleur": "#6A1B9A", "description": "Maille très critique (300-400‰)"},
                {"seuil": 500, "couleur": "#4A148C", "description": "Maille extrêmement critique (400-500‰)"},
                {"seuil": 1000, "couleur": "#311B92", "description": "Maille hautement dangereuse (500‰-1%)"},
                {"seuil": 2000, "couleur": "#1A237E", "description": "Maille très hautement dangereuse (1-2%)"},
                {"seuil": 3000, "couleur": "#0D47A1", "description": "Maille exceptionnellement dangereuse (2-3%)"},
                {"seuil": 5000, "couleur": "#01579B", "description": "Maille maximum danger (3-5%)"},
                {"seuil": 10000, "couleur": "#006064", "description": "Maille pas sûre (> 5%)"}
            ]
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réputations colorées: {e}")
        return None


@lru_cache(maxsize=1000)
def calculate_color_from_ratio(ratio_pour_mille: float) -> str:
    """
    Fonction optimisée pour calculer la couleur basée sur le ratio pour mille.
    Utilise un cache LRU pour éviter les recalculs.

    Args:
        ratio_pour_mille: Ratio en pour mille (‰) par rapport au total du niveau

    Returns:
        Code couleur hexadécimal
    """
    if pd.isna(ratio_pour_mille) or ratio_pour_mille == 0:
        return '#FFFFFF'  # Blanc par défaut pour les valeurs nulles ou zéro

    # Définition des seuils en pour mille (‰) et couleurs correspondantes
    color_mapping = [
        (3, '#E8F5E8'),  # < 0.3% - Vert très clair
        (5, '#C8E6C9'),  # < 0.5% - Vert clair
        (7, '#A5D6A7'),  # < 0.7% - Vert moyen
        (9, '#81C784'),  # < 0.9% - Vert
        (14, '#FFE082'),  # < 1.4% - Jaune clair
        (18, '#FFCC02'),  # < 1.8% - Jaune
        (25, '#FF9800'),  # < 2.5% - Orange
        (50, '#F57C00'),  # < 5% - Orange foncé
        (75, '#F4511E'),  # < 7.5% - Rouge orangé
        (100, '#F44336'),  # < 10% - Rouge
        (150, '#D32F2F'),  # < 15% - Rouge foncé
        (200, '#B71C1C'),  # < 20% - Rouge très foncé
        (300, '#880E4F'),  # < 30% - Violet foncé
        (400, '#6A1B9A'),  # < 40% - Violet
        (500, '#4A148C'),  # < 50% - Violet très foncé
        (1000, '#311B92'),  # < 100% - Bleu foncé
        (2000, '#1A237E'),  # < 200% - Bleu (impossible mais gardé pour compatibilité)
        (3000, '#0D47A1'),  # < 300% - Bleu clair
        (5000, '#01579B'),  # < 500% - Cyan foncé
        (10000, '#006064')  # < 1000% - Cyan très foncé
    ]

    for threshold, color in color_mapping:
        if ratio_pour_mille < threshold:
            return color

    # retour gris par défaut pour les valeurs supérieures à 1000% (impossible en théorie)
    return '#9E9E9E'


def get_equipements_by_commune(code: str, engine=None) -> Optional[Dict[str, Any]]:
    """
    Récupère les équipements géolocalisés par commune.

    Optimisations :
    - Sélection des colonnes nécessaires
    - Filtrage des coordonnées vides dans la requête
    - Index sur code_commune recommandé
    """
    if engine is None:
        engine = get_engine()

    query = text("""
        SELECT 
            e.code_commune,
            e.typequ,
            e.longitude,
            e.latitude,
            e.nom,
            et.lib_mod
        FROM equipements e
        LEFT JOIN equipements_type et ON et.cod_mod = e.typequ
        WHERE e.code_commune = :code 
            AND e.longitude IS NOT NULL 
            AND e.longitude != ''
            AND e.latitude IS NOT NULL
            AND e.latitude != ''
        ORDER BY e.typequ, e.nom
    """)

    try:
        df = pd.read_sql(query, engine, params={"code": code})

        if df.empty:
            logger.info(f"Aucun équipement trouvé pour la commune {code}")
            return None

        return {
            "data": df.to_dict(orient="records"),
            'filtre': sorted(df['typequ'].unique().tolist()),
            "annee": []
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des équipements: {e}")
        return None


def get_multiple_reputations_by_mailles(codes: List[str], niveau: str, engine=None):
    """
    Nouvelle fonction pour récupérer les réputations de plusieurs mailles en une seule requête.
    Plus efficace que d'appeler get_reputations_by_maille en boucle.
    Calcule les couleurs basées sur le ratio par rapport au total du niveau.
    """
    print(f"Récupération des réputations pour les codes {codes} niveau {niveau}")
    if engine is None:
        engine = get_engine()

    if not codes:
        return []

    # Récupérer d'abord le total du niveau
    query_niveau = text("""
        SELECT 
            SUM(nombre) as value 
        FROM reputations 
        WHERE unite_de_compte = 'all' 
            AND annee = '2024' 
            AND niveau = :niveau 
    """)

    try:
        df_niveau = pd.read_sql(query_niveau, engine, params={"niveau": niveau})
        if df_niveau.empty or df_niveau['value'].iloc[0] == 0:
            logger.info(f"Aucune réputation trouvée pour le niveau {niveau}")
            return []
        total_value = df_niveau['value'].iloc[0]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la valeur totale pour le niveau {niveau}: {e}")
        return []

    # Créer la requête pour les codes multiples
    # Utiliser une approche plus sûre avec SQLAlchemy pour éviter l'injection SQL
    query = text("""
        SELECT 
            code, 
            SUM(nombre) as value 
        FROM reputations 
        WHERE unite_de_compte = 'all' 
            AND annee = '2024' 
            AND code IN :codes 
            AND niveau = :niveau 
        GROUP BY code
        ORDER BY code
    """)

    try:
        print(f"Récupération des réputations pour les codes {codes} niveau {niveau} (total niveau: {total_value})")
        df = pd.read_sql(query, engine, params={"codes": tuple(codes), "niveau": niveau})

        if df.empty:
            logger.info(f"Aucune réputation trouvée pour les codes {codes} niveau {niveau}")
            return []

        # Calculer le ratio en pour mille (‰) et la couleur pour chaque code
        df['ratio_pour_mille'] = (df['value'] / total_value) * 1000
        df['color'] = df['ratio_pour_mille'].apply(calculate_color_from_ratio)
        df['value_percentage'] = (df['value'] / total_value) * 100

        # Grouper par code pour retourner un dictionnaire
        result = {
            "total_niveau": total_value,
            "data": {},
            'filtre': [
                {"seuil": 3, "couleur": "#E8F5E8", "description": "Maille très sûre (< 3‰)"},
                {"seuil": 5, "couleur": "#C8E6C9", "description": "Maille sûre (3-5‰)"},
                {"seuil": 7, "couleur": "#A5D6A7", "description": "Maille plutôt sûre (5-7‰)"},
                {"seuil": 9, "couleur": "#81C784", "description": "Maille modérément sûre (7-9‰)"},
                {"seuil": 14, "couleur": "#FFE082", "description": "Maille légèrement risquée (9-14‰)"},
                {"seuil": 18, "couleur": "#FFCC02", "description": "Maille attention (14-18‰)"},
                {"seuil": 25, "couleur": "#FF9800", "description": "Maille vigilance (18-25‰)"},
                {"seuil": 50, "couleur": "#F57C00", "description": "Maille risquée (25-50‰)"},
                {"seuil": 75, "couleur": "#F4511E", "description": "Maille très risquée (50-75‰)"},
                {"seuil": 100, "couleur": "#F44336", "description": "Maille dangereuse (75-100‰)"},
                {"seuil": 150, "couleur": "#D32F2F", "description": "Maille très dangereuse (100-150‰)"},
                {"seuil": 200, "couleur": "#B71C1C", "description": "Maille peu sûre (150-200‰)"},
                {"seuil": 300, "couleur": "#880E4F", "description": "Maille critique (200-300‰)"},
                {"seuil": 400, "couleur": "#6A1B9A", "description": "Maille très critique (300-400‰)"},
                {"seuil": 500, "couleur": "#4A148C", "description": "Maille extrêmement critique (400-500‰)"},
                {"seuil": 1000, "couleur": "#311B92", "description": "Maille hautement dangereuse (> 500‰)"}
            ]
        }

        # Créer un dictionnaire avec les données pour chaque code
        result = []
        for code in codes:
            code_data = df[df['code'] == code]
            if not code_data.empty:
                result.append(code_data.to_dict(orient="records")[0])
            else:
                # Si aucune donnée pour ce code, mettre des valeurs par défaut
                # result["data"][code] = {
                #     "code": code,
                #     "value": 0,
                #     "ratio_pour_mille": 0,
                #     "color": "#FFFFFF",
                #     "value_percentage": 0
                # }

                result.append({
                    "code": code,
                    "value": 0,
                    "ratio_pour_mille": 0,
                    "color": "#FFFFFF",
                    "value_percentage": 0
                })
        print(result)
        return result

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réputations multiples: {e}")
        return []


# Recommandations d'index pour optimiser les performances
INDEX_RECOMMENDATIONS = """
-- Index recommandés pour optimiser les requêtes :

-- Pour la table fonciers
CREATE INDEX IF NOT EXISTS idx_fonciers_code_commune ON fonciers(code_commune);

-- Pour la table reputations
CREATE INDEX IF NOT EXISTS idx_reputations_code_niveau ON reputations(code, niveau);
CREATE INDEX IF NOT EXISTS idx_reputations_filters ON reputations(unite_de_compte, annee, code, niveau);

-- Pour la table equipements
CREATE INDEX IF NOT EXISTS idx_equipements_commune ON equipements(code_commune);
CREATE INDEX IF NOT EXISTS idx_equipements_coords ON equipements(code_commune) WHERE longitude IS NOT NULL AND longitude != '';

-- Pour la table equipements_type (si pas déjà présent)
CREATE INDEX IF NOT EXISTS idx_equipements_type_cod_mod ON equipements_type(cod_mod);
"""

if __name__ == '__main__':
    # Test avec gestion d'erreur
    try:
        data = get_reputations_color_by_maille('42249', 'commune')
        print("Résultat:", data)

        # Test de la nouvelle fonction batch
        batch_data = get_multiple_reputations_by_mailles(['42249', '42250'], 'commune')
        print("Résultat batch:", batch_data)

    except Exception as e:
        logger.error(f"Erreur dans le test principal: {e}")

    # Afficher les recommandations d'index
    print("\n" + INDEX_RECOMMENDATIONS)
