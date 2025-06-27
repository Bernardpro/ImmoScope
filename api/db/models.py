# db/models.py - AJOUTEZ le modèle Propriete

from typing import List, Optional
from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime, func, Boolean, Float, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pydantic import BaseModel

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user_account"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    mail: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, mail={self.mail!r}, is_admin={self.is_admin!r})"

class Propriete(Base):
    __tablename__ = "proprietes"
    
    annonce_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    
    titre: Mapped[Optional[str]] = mapped_column(String(255))
    prix: Mapped[Optional[float]] = mapped_column(Float)
    surface: Mapped[Optional[float]] = mapped_column(Float)
    pieces: Mapped[Optional[int]] = mapped_column(Integer)
    taille_terrain: Mapped[Optional[float]] = mapped_column(Float)
    ville: Mapped[Optional[str]] = mapped_column(String(100))
    
    code_commune: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    
    source: Mapped[Optional[str]] = mapped_column(String(500))
    
    prix_m2: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"Propriete(annonce_id={self.annonce_id!r}, titre={self.titre!r}, prix={self.prix!r})"

class SentimentTerms(BaseModel):
    positive: list[str] = []
    negative: list[str] = []