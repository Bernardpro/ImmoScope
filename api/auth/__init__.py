"""Module d'authentification pour l'API"""
from .dependencies import get_current_user, require_scope, require_admin
from .models import UserResponse, UserCreate, TokenWithUser

# Exporter les éléments principaux pour faciliter l'importation
__all__ = ['get_current_user', 'require_scope', 'require_admin',
           'UserResponse', 'UserCreate', 'TokenWithUser']