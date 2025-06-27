import time
import pandas as pd
from sqlalchemy import text
from geopy.distance import geodesic

from api import dataframe_to_json_response
from bddManager import DatabaseConnection, logger


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
                logger.debug(f"Query executed in {execution_time:.4f}s, returned {len(df)} rows")
            else:
                logger.debug(f"Query executed in {execution_time:.4f}s, returned no data")
            return df
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        logger.error(f"Query: {query_text}")
        logger.error(f"Params: {params}")
        # Renvoyer un DataFrame vide en cas d'erreur plutôt que de laisser l'exception se propager
        return pd.DataFrame()


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
        SELECT code, libelle, shape, centre 
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

    # Extraction des coordonnées depuis le format de données retourné
    centre_data = result.iloc[0]['centre']

    # Extraction des coordonnées selon le format [latitude, longitude]
    if isinstance(centre_data, dict) and 'coordinates' in centre_data:
        # Format GeoJSON: coordinates[0] = [latitude, longitude]
        coords = centre_data['coordinates'][0]
        centre_coords = (coords[0], coords[1])  # (latitude, longitude) pour geopy
    elif hasattr(centre_data, 'x') and hasattr(centre_data, 'y'):
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
                SELECT code, libelle, shape, centre 
                FROM maillage 
                WHERE niveau = :niveau
            """
            all_shapes = execute_query(query_all, {"niveau": niveau})

            if not all_shapes.empty:
                # Calcule la distance entre le centre de la maille et les autres shapes
                def calculate_distance(geom):
                    try:
                        if geom is not None:
                            # Extraction des coordonnées de l'autre point
                            if isinstance(geom, dict) and 'coordinates' in geom:
                                # Format GeoJSON
                                other_coords = geom['coordinates'][0]
                                other_point = (other_coords[0], other_coords[1])  # (lat, lon)
                            elif hasattr(geom, 'x') and hasattr(geom, 'y'):
                                # Objet géométrique (Point)
                                other_point = (geom.y, geom.x)
                            elif isinstance(geom, (list, tuple)) and len(geom) >= 2:
                                # Liste/tuple direct
                                other_point = (geom[0], geom[1])
                            else:
                                return float('inf')

                            # Calcul de la distance géodésique en mètres
                            distance = geodesic(centre_coords, other_point).meters
                            return distance
                        else:
                            return float('inf')
                    except Exception as e:
                        print(f"Erreur calcul distance pour {geom}: {e}")
                        return float('inf')

                all_shapes['distance'] = all_shapes['centre'].apply(calculate_distance)

                # Filtre les shapes à moins de 10 km (10000 mètres)
                #mailles_proches = all_shapes[all_shapes['distance'] <= 10000].copy()

                # Trie par distance
                mailles_proches = all_shapes.sort_values(by='distance').reset_index(drop=True)

                # take 5 first rows
                mailles_proches = mailles_proches.head(6)


                # Affiche les résultats
                print(f"Maille principale: {code}")
                print(f"Nombre de mailles proches trouvées: {len(mailles_proches)}")
                if not mailles_proches.empty:
                    print("\nMailles dans un rayon de 10km:")
                    for idx, row in mailles_proches.iterrows():
                        distance_km = row['distance'] / 1000  # Conversion en km
                        print(f"  - {row['code']} ({row['libelle']}) - Distance: {distance_km:.2f} km")

        except Exception as e:
            print(f"Erreur lors du calcul des distances: {e}")
            mailles_proches = pd.DataFrame()

    return result, mailles_proches


if __name__ == '__main__':
    data, data_ = get_shape_arround("01004", "commune")
    print(data)

    test = dataframe_to_json_response(
        pd.concat([data, data_])[data.columns]
    )
