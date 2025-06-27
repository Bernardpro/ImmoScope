"""Routes d'authentification de l'API"""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from auth.config import logger
from auth.dependencies import get_current_user, require_scope
from auth.models import UserCreate, UserResponse, TokenWithUser, Token
from auth.utils import hash_password, verify_password, create_access_token
from db.models import User
from db.session import get_db

router = APIRouter(prefix="/user", tags=["Authentication"])


# Routes
@router.post("/signup", response_model=TokenWithUser, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    """
    Créer un nouvel utilisateur et renvoyer un token d'accès
    """
    try:
        # Journaliser la tentative de création (sans le mot de passe)
        logger.info(f"Tentative de création d'utilisateur: {user.mail} depuis {request.client.host}")

        # Vérifier si l'utilisateur existe déjà
        existing_user = db.query(User).filter(User.mail == user.mail).first()
        if existing_user:
            logger.warning(f"Tentative de création d'un utilisateur avec un email déjà existant: {user.mail}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un utilisateur avec cet email existe déjà"
            )

        # Créer le nouvel utilisateur
        hashed_password = hash_password(user.password)
        new_user = User(
            name=user.name,
            mail=user.mail,
            password=hashed_password
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Générer le token
        token_data = create_access_token(data={"sub": user.mail}, scopes=["read", "write"])

        # Créer la réponse utilisateur
        user_response = UserResponse.model_validate(new_user)

        logger.info(f"Utilisateur créé avec succès: {new_user.mail}")

        return {**token_data, "user": user_response}

    except HTTPException as he:
        raise he
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Erreur SQL lors de la création de l'utilisateur: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de l'utilisateur dans la base de données"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur inattendue lors de la création de l'utilisateur: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur inattendue lors de la création de l'utilisateur"
        )


@router.post("/login", response_model=TokenWithUser)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db),
                     request: Request = None):
    """
    Authentifier un utilisateur et renvoyer un token d'accès
    """
    try:
        logger.info(f"Tentative de connexion: {form_data.username}")

        # Rechercher l'utilisateur
        db_user = db.query(User).filter(User.mail == form_data.username).first()

        # Vérifier si l'utilisateur existe et si le mot de passe est correct
        if not db_user or not verify_password(form_data.password, db_user.password):
            logger.warning(f"Tentative de connexion échouée pour: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Si admin, ajouter le scope "admin"
        scopes = ["read", "write"]
        if db_user.is_admin:
            scopes.append("admin")

        # Générer token
        token_data = create_access_token(data={"sub": db_user.mail}, scopes=scopes)

        # Créer la réponse utilisateur
        user_response = UserResponse.model_validate(db_user)

        logger.info(f"Connexion réussie pour: {db_user.mail}")

        return {**token_data, "user": user_response}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erreur lors de la connexion pour {form_data.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur inattendue lors de la connexion"
        )


@router.get("/me", response_model=UserResponse)
async def get_user_me(current_user: User = Depends(get_current_user)):
    """
    Renvoyer les informations de l'utilisateur connecté
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout_user(request: Request):
    """
    Déconnexion de l'utilisateur
    Note: Côté serveur, nous ne pouvons pas vraiment 'invalider' un JWT.
    La déconnexion réelle doit être gérée côté client en supprimant le token.
    """
    return {"detail": "Déconnexion réussie"}


@router.post("/token/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Rafraîchir le token d'accès
    """
    token_data = create_access_token(data={"sub": current_user.mail})
    return token_data


# Route admin qui nécessite le scope "admin"
@router.post("/admin/action")
async def admin_action(current_user: User = Depends(require_scope("admin"))):
    # Fonction accessible uniquement avec le scope "admin"
    return {
        "detail": "Action admin réussie",
        "user": current_user.name,
        "timestamp": datetime.utcnow()
    }
