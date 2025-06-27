import pandas as pd

from db.session import get_engine

if __name__ == '__main__':
    engine = get_engine()
    from sqlalchemy import text

    query = """select "Nom de la manifestation", région, domaine, "Complément domaine", département, périodicité, "Mois habituel de début", "Site web"
from panorama_des_festivals;"""

    df = pd.read_sql(text(query), engine)
