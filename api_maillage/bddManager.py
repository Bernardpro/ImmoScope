from configparser import ConfigParser

from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from geopy.distance import geodesic
from dotenv import load_dotenv
import pandas as pd
import logging
import time
from functools import wraps

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("db_manager")

# Chargement des variables d'environnement
load_dotenv()

# Configuration pour la connexion
config_docker = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": os.getenv("PG_PORT", "5433"),
    "database": os.getenv("PG_DATABASE", "maillage"),
    "user": os.getenv("PG_USER", "trainuser"),
    "password": os.getenv("PG_PASSWORD", "trainpass123"),
}


# Création de l'URL de connexion SQLAlchemy
def get_connection_url():
    return f"postgresql://{config_docker['user']}:{config_docker['password']}@{config_docker['host']}:{config_docker['port']}/{config_docker['database']}"


# Création du moteur SQLAlchemy avec pool_size et max_overflow pour optimiser les connexions
engine = create_engine(
    get_connection_url(),
    pool_size=5,  # Nombre de connexions permanentes
    max_overflow=10,  # Nombre de connexions supplémentaires autorisées
    pool_timeout=30,  # Délai d'attente en secondes pour obtenir une connexion
    pool_recycle=1800,  # Recycler les connexions après 30 minutes
)

Session = sessionmaker(bind=engine)


# Décorateur pour mesurer les performances des requêtes
def query_timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        logger.info(
            f"Function {func.__name__} executed in {execution_time:.4f} seconds"
        )
        return result

    return wrapper


# Classe pour gérer la connexion avec un context manager
class DatabaseConnection:
    """
    Context manager pour garantir la fermeture de la connexion à la base de données
    """

    def __init__(self):
        self.session = None

    def __enter__(self):
        self.session = Session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type is not None:
                logger.error(f"Exception during database operation: {exc_val}")
                self.session.rollback()
            self.session.close()
        return False  # Propagate exceptions


# Fonction générique pour exécuter des requêtes SQL
def execute_query(query_text, params=None):
    """
    Exécute une requête SQL et retourne le résultat sous forme de DataFrame

    Args:
        query_text (str): La requête SQL à exécuter
        params (dict, optional): Les paramètres de la requête

    Returns:
        pandas.DataFrame: Le résultat de la requête
    """
    try:
        with DatabaseConnection() as session:
            query = text(query_text)
            start_time = time.time()
            result = session.execute(query, params or {})
            execution_time = time.time() - start_time

            df = pd.DataFrame(result.fetchall())
            if not df.empty:
                df.columns = result.keys()
                logger.debug(
                    f"Query executed in {execution_time:.4f}s, returned {len(df)} rows"
                )
            else:
                logger.debug(
                    f"Query executed in {execution_time:.4f}s, returned no data"
                )
            return df
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        logger.error(f"Query: {query_text}")
        logger.error(f"Params: {params}")
        # Renvoyer un DataFrame vide en cas d'erreur plutôt que de laisser l'exception se propager
        return pd.DataFrame()


# Fonctions optimisées pour récupérer les shapes
@query_timer
def get_shape(code, niveau):
    """
    Récupère un shape par son code et son niveau

    Args:
        code (str): Le code de la maille
        niveau (str): Le niveau administratif (région, département, commune)

    Returns:
        pandas.DataFrame: Les données de la maille
    """
    query = """
        SELECT code, libelle, shape, centre 
        FROM maillage 
        WHERE code = :code AND niveau = :niveau
    """

    return execute_query(query, {"code": code, "niveau": niveau})


def get_shape_arround(code, niveau):
    """
    Récupère un shape par son code et son niveau, ainsi que les shapes environnants

    Args:
        code (str): Le code de la maille
        niveau (str): Le niveau administratif (région, département, commune)

    Returns:
        tuple: (maille_principale, mailles_proches)
            - maille_principale (pandas.DataFrame): La maille demandée
            - mailles_proches (pandas.DataFrame): Les mailles dans un rayon de 10km
    """
    query = """
        SELECT id, code, libelle, shape, centre 
        FROM maillage 
        WHERE code = :code AND niveau = :niveau
    """

    # Exécute la requête principale pour récupérer la maille demandée
    result = execute_query(query, {"code": code, "niveau": niveau})

    # Si aucun résultat, retourne des DataFrames vides
    if result.empty:
        return result, pd.DataFrame()

    # Récupère le centre de la maille trouvée
    print(f"Maille trouvée: {result.iloc[0]}")


    # creation du file d'arianne
    id_maille = result.iloc[0]["id"]
    code_region = id_maille[:2]  # Les 2 premiers caractères pour la région
    # if niveau == "commune":
    #     code_region = id_maille[:2]  # Les 2 premiers caractères pour la région
    #     code_departement = id_maille[2:4]  # Les 2 suivants pour le département
    #     file_arianne = f"{code_region} > {code_departement} > {code}"
    # elif niveau == "departement":
    #     code_region = id_maille[:2]
    #     file_arianne = f"{code_region} > {code}"
    # else:
    #     file_arianne = code
    # print(f"File d'arianne: {file_arianne}")

    # Extraction des coordonnées depuis le format de données retourné
    if niveau in ["region", "departement"]:
        return result, pd.DataFrame()
    centre_data = result.iloc[0]["centre"]

    # Extraction des coordonnées selon le format [latitude, longitude]
    if isinstance(centre_data, dict) and "coordinates" in centre_data:
        # Format GeoJSON: coordinates[0] = [latitude, longitude]
        coords = centre_data["coordinates"][0]
        centre_coords = (coords[0], coords[1])  # (latitude, longitude) pour geopy
    elif hasattr(centre_data, "x") and hasattr(centre_data, "y"):
        # Si c'est un objet géométrique Point
        centre_coords = (centre_data.y, centre_data.x)  # (latitude, longitude)
    elif isinstance(centre_data, (list, tuple)) and len(centre_data) >= 2:
        # Si c'est directement une liste/tuple [lat, lon]
        centre_coords = (centre_data[0], centre_data[1])
    else:
        print(f"Format de coordonnées non reconnu: {type(centre_data)} - {centre_data}")
        return result, pd.DataFrame()

    print(f"Centre de la maille {code}: {centre_coords}")
    mailles_proches = pd.DataFrame()

    # Si le centre existe, trouve les shapes proches
    if centre_coords is not None:
        try:
            # Sélectionne tous les shapes du même niveau
            query_all = """
                SELECT id, code, libelle, shape, centre 
                FROM maillage 
                WHERE niveau = :niveau and id  LIKE :code_region ||'_______'
            """
            all_shapes = execute_query(query_all, {"niveau": niveau, "code_region": code_region})

            if not all_shapes.empty:
                # Calcule la distance entre le centre de la maille et les autres shapes
                def calculate_distance(geom):
                    try:
                        if geom is not None:
                            # Extraction des coordonnées de l'autre point
                            if isinstance(geom, dict) and "coordinates" in geom:
                                # Format GeoJSON
                                other_coords = geom["coordinates"][0]
                                other_point = (
                                    other_coords[0],
                                    other_coords[1],
                                )  # (lat, lon)
                            elif hasattr(geom, "x") and hasattr(geom, "y"):
                                # Objet géométrique (Point)
                                other_point = (geom.y, geom.x)
                            elif isinstance(geom, (list, tuple)) and len(geom) >= 2:
                                # Liste/tuple direct
                                other_point = (geom[0], geom[1])
                            else:
                                return float("inf")

                            # Calcul de la distance géodésique en mètres
                            distance = geodesic(centre_coords, other_point).meters
                            return distance
                        else:
                            return float("inf")
                    except Exception as e:
                        print(f"Erreur calcul distance pour {geom}: {e}")
                        return float("inf")

                all_shapes["distance"] = all_shapes["centre"].apply(calculate_distance)

                # Filtre les shapes à moins de 10 km (10000 mètres)
                # mailles_proches = all_shapes[all_shapes['distance'] <= 10000].copy()

                # Trie par distance
                mailles_proches = all_shapes.sort_values(by="distance").reset_index(
                    drop=True
                )
                # supp distance
                mailles_proches = mailles_proches.drop(columns=["distance"])

                # take 5 first rows
                mailles_proches = mailles_proches.head(9)

        except Exception as e:
            print(f"Erreur lors du calcul des distances: {e}")
            mailles_proches = pd.DataFrame()

    return result, mailles_proches


@query_timer
def get_shape_by_id(id):
    """
    Récupère un shape par son identifiant

    Args:
        id (str): L'identifiant de la maille

    Returns:
        pandas.DataFrame: Les données de la maille
    """
    query = """
        SELECT code, libelle, shape, centre 
        FROM maillage 
        WHERE id = :id
    """
    return execute_query(query, {"id": id})


@query_timer
def get_all_shapes_by_level(niveau, limit=None):
    """
    Récupère tous les shapes d'un niveau administratif donné

    Args:
        niveau (str): Le niveau administratif (région, département, commune)
        limit (int, optional): Nombre maximum de résultats à retourner

    Returns:
        pandas.DataFrame: Les données des mailles
    """
    query = """
        SELECT code, libelle, shape, centre 
        FROM maillage 
        WHERE niveau = :niveau
    """

    if limit is not None and isinstance(limit, int) and limit > 0:
        query += " LIMIT :limit"
        return execute_query(query, {"niveau": niveau, "limit": limit})

    return execute_query(query, {"niveau": niveau})


@query_timer
def get_shape_inf(code, niveau):
    """
    Récupère les shapes inférieurs en fonction du code et du niveau

    Args:
        code (str): Le code de la maille parente
        niveau (str): Le niveau administratif de la maille parente

    Returns:
        pandas.DataFrame: Les données des mailles enfants
    """
    if niveau not in ["region", "departement"]:
        logger.warning(f"Niveau '{niveau}' non pris en charge pour get_shape_inf")
        return pd.DataFrame()

    id_pattern = None
    if niveau == "region":
        id_pattern = f"{code}__" + "_____"
        niveau_search = "departement"
    elif niveau == "departement":
        id_pattern = "__" + f"{code}" + "_____"
        niveau_search = "commune"

    query = """
        SELECT code, libelle, shape, centre 
        FROM maillage 
        WHERE id LIKE :id AND niveau <> :niveau AND niveau = :niveau_search
    """
    return execute_query(query, {"id": id_pattern, "niveau": niveau, "niveau_search": niveau_search})


def get_arianne(code, niveau):
    """
    Génère une liste simple des mailles pour le fil d'Ariane.

    Args:
        code (str): Code de l'entité géographique
        niveau (str): Niveau géographique ('commune', 'departement', 'region')

    Returns:
        list: Liste ordonnée des mailles [région, département, commune] ou None si inexistant
    """
    # Récupération de la maille demandée
    query = """
        SELECT id, code, libelle, niveau
        FROM maillage 
        WHERE code = :code AND niveau = :niveau
    """
    result = execute_query(query, {"code": code, "niveau": niveau})

    if result.empty:
        return None

    maille = result.iloc[0]
    id_maille = maille["id"]

    # Liste des mailles pour le fil d'Ariane
    mailles = []

    # Ajout de la région (toujours présente)
    if len(id_maille) >= 2:
        code_region = id_maille[:2]
        id_region = code_region + "00" + "00000"

        query_region = """
            SELECT code, libelle, niveau
            FROM maillage 
            WHERE id = :id
        """
        region_result = execute_query(query_region, {"id": id_region})

        if not region_result.empty:
            region = region_result.iloc[0]
            mailles.append({
                "code": region["code"],
                "libelle": region["libelle"],
                "niveau": region["niveau"]
            })

    # Ajout du département si nécessaire
    if niveau in ["commune", "departement"] and len(id_maille) >= 4:
        code_dept = id_maille[2:4]
        id_dept = id_maille[:2] + code_dept + "00000"

        query_dept = """
            SELECT code, libelle, niveau
            FROM maillage 
            WHERE id = :id
        """
        dept_result = execute_query(query_dept, {"id": id_dept})

        if not dept_result.empty:
            dept = dept_result.iloc[0]
            mailles.append({
                "code": dept["code"],
                "libelle": dept["libelle"],
                "niveau": dept["niveau"]
            })

    # Ajout de la commune/entité demandée
    mailles.append({
        "code": maille["code"],
        "libelle": maille["libelle"],
        "niveau": maille["niveau"]
    })

    # drop les doublons
    mailles = pd.DataFrame(mailles).drop_duplicates(subset=["code"]).to_dict(orient="records")

    return mailles



@query_timer
def search_shape(search_term, niveau=None, limit=10):
    """
    Recherche des mailles par terme de recherche dans le libellé avec améliorations:
    - Recherche par mots-clés séparés
    - Recherche exacte prioritaire
    - Support des accents et casse insensible
    - Tri par pertinence

    Args:
        search_term (str): Le terme à rechercher
        niveau (str, optional): Filtrer par niveau administratif
        limit (int): Nombre maximum de résultats

    Returns:
        pandas.DataFrame: Les mailles correspondant à la recherche
    """
    if not search_term or search_term.strip() == "":
        return pd.DataFrame()  # Retourne un DataFrame vide si recherche vide

    # Nettoyage du terme de recherche
    search_term = search_term.strip()

    # Création des paramètres pour la requête
    params = {"limit": limit}

    # Construction de la requête de base
    query = """
        WITH search_results AS (
            SELECT 
                code, 
                libelle, 
                shape, 
                centre, 
                niveau,
                CASE
                    WHEN libelle ILIKE :exact_term THEN 1
                    WHEN libelle ILIKE :start_term THEN 2
                    WHEN libelle ILIKE :contains_term THEN 3
    """

    # Ajout des paramètres pour la recherche exacte et partielle
    params["exact_term"] = search_term
    params["start_term"] = f"{search_term}%"
    params["contains_term"] = f"%{search_term}%"

    # Support pour la recherche par mots-clés séparés
    words = search_term.split()
    if len(words) > 1:
        query += """
                    WHEN """
        word_conditions = []
        for i, word in enumerate(words):
            word_param = f"word_{i}"
            params[word_param] = f"%{word}%"
            word_conditions.append(f"libelle ILIKE :{word_param}")

        query += " AND ".join(word_conditions) + " THEN 4"

    # Fin de la requête
    query += """
                    ELSE 5
                END AS rank
            FROM maillage
            WHERE (
                libelle ILIKE :contains_term
    """

    # Ajout des conditions pour la recherche par mots-clés
    if len(words) > 1:
        query += " OR ("
        query += " AND ".join(word_conditions)
        query += ")"

    query += ")"

    # Filtrage par niveau si spécifié
    if niveau:
        query += " AND niveau = :niveau"
        params["niveau"] = niveau

    # Fin de la requête avec tri et limite
    query += """
        )
        SELECT 
            code, 
            libelle, 
            shape, 
            centre, 
            niveau
        FROM search_results
        ORDER BY rank, niveau, libelle
        LIMIT :limit
    """

    return execute_query(query, params)


@query_timer
def get_shape_stats():
    """
    Récupère des statistiques sur les mailles disponibles dans la base

    Returns:
        pandas.DataFrame: Statistiques par niveau administratif
    """
    query = """
        SELECT niveau, COUNT(*) as total
        FROM maillage
        GROUP BY niveau
        ORDER BY niveau
    """
    return execute_query(query)


# Exemple d'utilisation
if __name__ == "__main__":
    # Afficher les informations de connexion (à des fins de débogage uniquement)
    logger.info(
        f"Connexion à la base de données: {config_docker['database']} sur {config_docker['host']}:{config_docker['port']}"
    )

    code = "21032"  # Exemple de code pour une commune
    niveau = "commune"  # Niveau administratif

    data_arianne = get_arianne(code, niveau)
    logger.info(f"Fil d'Ariane pour {code} ({niveau}): {data_arianne}")

    #data, maille_proche = get_shape_arround("41", "departement")
    #print(maille_proche.columns)

    #result = jsonable_encoder(maille_proche.to_dict(orient="records"))

    # # Récupérer des statistiques
    # stats = get_shape_stats()
    # logger.info(f"Statistiques des mailles:\n{stats}")
    #
    # # Exemple de récupération d'un shape
    # commune_df = get_shape("21032", "commune")
    # logger.info(f"Commune: {len(commune_df)} lignes")
    #
    # # Exemple de recherche
    # search_results = search_shape("Dijon", limit=5)
    # logger.info(f"Recherche 'Dijon': {len(search_results)} résultats")
    # logger.info(search_results[['code', 'libelle', 'niveau']].head())
    #
    # # Test de performance avec Timer
    # for niveau in ['region', 'departement', 'commune']:
    #     result = get_all_shapes_by_level(niveau, limit=50)
    #     logger.info(f"{niveau.capitalize()}: {len(result)} lignes (limité à 50)")
