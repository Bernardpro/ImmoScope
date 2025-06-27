"""Configuration pour le module d'authentification"""
import logging
import os

from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer

# Configurer le logger
logger = logging.getLogger("auth_bis")

# Charger les variables d'environnement
load_dotenv()

# Configuration pour le JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "votre_clé_secrète_par_défaut")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDES", "3600"))

# Configuration OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")
