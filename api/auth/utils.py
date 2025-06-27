"""Fonctions utilitaires pour l'authentification"""
from datetime import datetime, timedelta
from typing import Dict, Any, List

import jwt
from passlib.context import CryptContext

from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_SECONDS

# Configuration pour le hachage de mot de passe avec bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash le mot de passe avec bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie si le mot de passe correspond au hash stocké"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], scopes: List[str] = None) -> Dict[str, Any]:
    """
    Crée un nouveau token JWT avec les données et scopes fournis

    Args:
        data: Les données à encoder dans le token
        scopes: Liste de scopes à attribuer à l'utilisateur

    Returns:
        Un dictionnaire contenant le token et ses métadonnées
    """
    to_encode = data.copy()
    issued_at = datetime.utcnow()
    expires_at = issued_at + timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)

    to_encode.update({
        "exp": expires_at,
        "iat": issued_at,
    })

    # Ajouter les scopes au token si fournis
    if scopes:
        to_encode["scope"] = " ".join(scopes)

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": encoded_jwt,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
        "issued_at": issued_at
    }


def check_token_expired(token: str) -> bool:
    """
    Vérifie si le token JWT est expiré

    Args:
        token: Le token JWT à vérifier

    Returns:
        True si le token est expiré, False sinon
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return True
    except jwt.ExpiredSignatureError:
        return True
    except jwt.DecodeError:
        return True
    return False
