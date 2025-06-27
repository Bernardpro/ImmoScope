"""Dépendances pour l'authentification FastAPI"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jwt.exceptions import PyJWTError
import jwt
from datetime import datetime
from typing import Optional

from db.models import User
from db.session import get_db
from .config import SECRET_KEY, ALGORITHM, oauth2_scheme
from .models import TokenData

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dépendance pour obtenir l'utilisateur actuel à partir du token JWT
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identification invalide",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, exp=datetime.fromtimestamp(payload.get("exp")))
    except PyJWTError:
        raise credentials_exception

    # Vérifier si le token a expiré
    if token_data.exp < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.mail == token_data.email).first()
    if user is None:
        raise credentials_exception

    return user

def require_scope(required_scope: str):
    """
    Crée une dépendance pour vérifier qu'un utilisateur a le scope requis
    """
    async def verify_scope(token: str = Depends(oauth2_scheme)):
        try:
            # Décoder le token JWT
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            # Vérifier si le token contient des scopes
            scopes = payload.get("scope", "").split() if "scope" in payload else []

            # Vérifier si le scope requis est présent
            if required_scope not in scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission insuffisante. Le scope '{required_scope}' est requis.",
                    headers={"WWW-Authenticate": f"Bearer scope=\"{required_scope}\""},
                )

            # Récupérer l'utilisateur depuis la base de données
            email = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token invalide",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            db = next(get_db())  # Obtenir une session de base de données
            user = db.query(User).filter(User.mail == email).first()
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Utilisateur non trouvé",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user

        except PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide ou expiré",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return verify_scope

def require_admin(user: User = Depends(get_current_user)):
    """Vérifie si l'utilisateur est administrateur"""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès administrateur requis",
        )
    return user