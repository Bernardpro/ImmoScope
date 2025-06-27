import os

import psycopg2.pool
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Charger les variables d'environnement
load_dotenv()

POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://trainuser:trainpass123@postgres:5432/traindb")

print(f"Connexion à la base de données: {POSTGRES_URL}")

# Créer le moteur SQLAlchemy
engine = create_engine(POSTGRES_URL, echo=True)

# crée les tables
from db.models import Base

Base.metadata.create_all(bind=engine)

# Créer une session locale
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Fonction pour obtenir une session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_engine():
    return engine


# ===== PARTIE PSYCOPG2 =====

# Parser l'URL pour psycopg2
from urllib.parse import urlparse

parsed = urlparse(POSTGRES_URL)

PSYCOPG2_CONFIG = {
    'host': parsed.hostname,
    'port': parsed.port or 5432,
    'database': parsed.path[1:],  # Remove leading '/'
    'user': parsed.username,
    'password': parsed.password
}

# Pool de connexions psycopg2 pour les performances
psycopg2_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=20,
    **PSYCOPG2_CONFIG
)


def get_psycopg2_connection():
    """Obtenir une connexion psycopg2 depuis le pool."""
    try:
        return psycopg2_pool.getconn()
    except Exception as e:
        print(f"Erreur lors de l'obtention de la connexion psycopg2: {e}")
        raise


if __name__ == '__main__':
    # test bdd

    import pandas as pd
    from sqlalchemy import text
    import time

    time_start = time.time()
    engine = get_engine()
    # Requête avec le filtre sur libelle
    df = pd.read_sql(
        text("SELECT * FROM valeurs_foncieres WHERE nom_commune LIKE '%ourg-en%'"),
        engine
    )
    time_end = time.time()
    print(f"Temps d'exécution SQLAlchemy: {time_end - time_start:.2f} secondes")

    # Test avec psycopg2
    time_start = time.time()
    conn = get_psycopg2_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM valeurs_foncieres WHERE nom_commune LIKE '%ourg-en%'")
    rows = cursor.fetchall()
    cursor.close()
    psycopg2_pool.putconn(conn)  # Remettre la connexion dans le pool
    time_end = time.time()
    print(f"Temps d'exécution psycopg2: {time_end - time_start:.2f} secondes")

    # Test avec une session (exemple d'utilisation alternative)
    db_session = next(get_db())

    # Vous pouvez aussi faire la requête avec la session
    result = db_session.execute(
        text("SELECT * FROM valeurs_foncieres WHERE nom_commune LIKE '%ourg-en%'")
    )

    db_session.close()
