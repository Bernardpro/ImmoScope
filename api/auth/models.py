"""Modèles Pydantic pour la validation des données d'authentification"""
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List
from datetime import datetime

class UserBase(BaseModel):
    mail: str

    @validator('mail')
    def email_must_be_valid(cls, v):
        if '@' not in v:
            raise ValueError('email invalide')
        return v.lower()  # Normaliser les emails en minuscules

class UserCreate(UserBase):
    name: str
    password: str

    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('le mot de passe doit contenir au moins 8 caractères')
        return v

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    name: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    issued_at: datetime

class TokenWithUser(Token):
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None
    exp: Optional[datetime] = None