from cache_service import CacheService
from fastapi import FastAPI, HTTPException, Path, Depends, status, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from bddManager import (
    get_shape, get_shape_by_id, get_shape_inf,
    get_all_shapes_by_level, search_shape, get_shape_stats, get_shape_arround, get_arianne
)
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import logging
import pandas as pd
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('api')

app = FastAPI(
    title="API Maillage Géographique",
    description="API pour récupérer des données géographiques par maille administrative",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionnaire des niveaux de maille pour la validation
NIVEAUX_MAILLE = {
    "region": "region",
    "departement": "departement",
    "commune": "commune",
}


# Modèles de données pour la documentation
class ShapeResponse(BaseModel):
    code: str
    libelle: str
    shape: str  # Format GeoJSON
    centre: str  # Format GeoJSON de type Point

    class Config:
        schema_extra = {
            "example": {
                "code": "21",
                "libelle": "Côte-d'Or",
                "shape": "{\"type\":\"MultiPolygon\",\"coordinates\":[[...]]}",
                "centre": "{\"type\":\"Point\",\"coordinates\":[4.70093,47.42216]}"
            }
        }


class ShapeWithNiveauResponse(ShapeResponse):
    niveau: str

    class Config:
        schema_extra = {
            "example": {
                "code": "21",
                "libelle": "Côte-d'Or",
                "shape": "{\"type\":\"MultiPolygon\",\"coordinates\":[[...]]}",
                "centre": "{\"type\":\"Point\",\"coordinates\":[4.70093,47.42216]}",
                "niveau": "departement"
            }
        }


class StatResponse(BaseModel):
    niveau: str
    total: int

    class Config:
        schema_extra = {
            "example": {
                "niveau": "departement",
                "total": 101
            }
        }


class ErrorResponse(BaseModel):
    detail: str


# Fonction utilitaire pour convertir un DataFrame en résultat JSON
def dataframe_to_json_response(df, cache_service=None, cache_key=None, headers=None):
    """
    Convertit un DataFrame en réponse JSON avec gestion de cache optionnelle
    """
    if df.empty:
        result = []
    else:
        result = jsonable_encoder(df.to_dict(orient="records"))

    response_headers = headers or {}
    if not cache_key or not cache_service:
        response_headers["X-Cache"] = "MISS"
        return JSONResponse(content=result, headers=response_headers)

    # Mise en cache et réponse
    async def process():
        await cache_service.set_cache(cache_key, result)
        response_headers["X-Cache"] = "MISS"
        return JSONResponse(content=result, headers=response_headers)

    return process()


# Routes pour les mailles
@app.get(
    "/maille/{niveau_maille}/{code_maille}",
    response_model=List[ShapeResponse],
    responses={
        200: {"description": "Shape trouvé et retourné avec succès"},
        404: {"description": "Aucune donnée trouvée", "model": ErrorResponse},
        500: {"description": "Erreur lors de la récupération des données", "model": ErrorResponse},
    },
    summary="Récupère la shape d'une maille par niveau et code",
    tags=["Shapes"]
)
async def get_shape_for_code(
        niveau_maille: str = Path(..., description="Niveau de maille (region, departement, commune)"),
        code_maille: str = Path(..., description="Code de la maille"),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère la shape d'une maille spécifique.

    - **niveau_maille**: Niveau administratif (region, departement, commune)
    - **code_maille**: Code administratif de la maille (ex: 21 pour la Côte d'Or)

    Retourne les données géographiques complètes de la maille.
    """
    # Logging de la requête
    logger.info(f"Récupération shape: niveau={niveau_maille}, code={code_maille}")

    # Vérification du niveau de maille
    if niveau_maille not in NIVEAUX_MAILLE:
        logger.warning(f"Niveau de maille invalide: {niveau_maille}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Niveau de maille invalide. Valeurs acceptées: {', '.join(NIVEAUX_MAILLE.keys())}"
        )

    cache_key = f"maillage:{niveau_maille}:{code_maille}"

    # Tentative de récupération depuis le cache
    cached_result = await cache_service.get_cache(cache_key)
    if cached_result:
        logger.debug(f"Cache HIT pour {cache_key}")
        print(cached_result)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    try:
        # Récupération des données
        #shape_df = get_shape(code_maille, niveau_maille)
        shape_df, shape_df_proche = get_shape_arround(code_maille, niveau_maille)


        if shape_df.empty:
            logger.warning(f"Aucune donnée trouvée: niveau={niveau_maille}, code={code_maille}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aucune donnée trouvée pour le niveau {niveau_maille} avec le code {code_maille}"
            )

        # Conversion et mise en cache
        return await dataframe_to_json_response(
            pd.concat([shape_df, shape_df_proche])[shape_df.columns],
            cache_service=cache_service,
            cache_key=cache_key
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des données: {str(e)}"
        )


@app.get(
    "/maille/{niveau_maille}",
    response_model=List[ShapeResponse],
    responses={
        200: {"description": "Liste des shapes retournée avec succès"},
        404: {"description": "Niveau de maille non trouvé", "model": ErrorResponse},
        500: {"description": "Erreur lors de la récupération des données", "model": ErrorResponse},
    },
    summary="Récupère toutes les shapes d'un niveau de maille",
    tags=["Shapes"]
)
async def get_all_shapes_for_level(
        niveau_maille: str = Path(..., description="Niveau de maille (region, departement, commune)"),
        limit: Optional[int] = Query(None, description="Limite le nombre de résultats retournés"),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère toutes les shapes d'un niveau de maille spécifique.

    - **niveau_maille**: Niveau administratif (region, departement, commune)
    - **limit**: Limite optionnelle pour le nombre de résultats

    Retourne les données géographiques de toutes les mailles du niveau spécifié.
    """
    logger.info(f"Récupération de toutes les shapes: niveau={niveau_maille}, limit={limit}")

    # Vérification du niveau de maille
    if niveau_maille not in NIVEAUX_MAILLE:
        logger.warning(f"Niveau de maille invalide: {niveau_maille}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Niveau de maille invalide. Valeurs acceptées: {', '.join(NIVEAUX_MAILLE.keys())}"
        )

    cache_key = f"maillage:{niveau_maille}:all"
    if limit:
        cache_key += f":limit:{limit}"

    # Tentative de récupération depuis le cache
    cached_result = await cache_service.get_cache(cache_key)
    if cached_result:
        logger.debug(f"Cache HIT pour {cache_key}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    try:
        # Récupération des données avec limite optionnelle
        shapes_df = get_all_shapes_by_level(niveau_maille, limit)

        # Conversion et mise en cache
        return await dataframe_to_json_response(
            shapes_df,
            cache_service=cache_service,
            cache_key=cache_key
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des données: {str(e)}"
        )


@app.get(
    "/maille/enfants/{niveau_parent}/{code_parent}",
    response_model=List[ShapeResponse],
    responses={
        200: {"description": "Liste des shapes enfants retournée avec succès"},
        400: {"description": "Niveau parent invalide", "model": ErrorResponse},
        500: {"description": "Erreur lors de la récupération des données", "model": ErrorResponse},
    },
    summary="Récupère les shapes des mailles enfants",
    tags=["Shapes"]
)
async def get_children_shapes(
        niveau_parent: str = Path(..., description="Niveau de la maille parente (region, departement)"),
        code_parent: str = Path(..., description="Code de la maille parente"),
        limit: Optional[int] = Query(None, description="Limite le nombre de résultats retournés"),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère toutes les shapes des mailles enfants d'une maille parente.

    - **niveau_parent**: Niveau administratif parent (region, departement)
    - **code_parent**: Code administratif de la maille parente
    - **limit**: Limite optionnelle pour le nombre de résultats

    Par exemple, pour obtenir toutes les communes d'un département.
    """
    logger.info(f"Récupération des enfants: niveau={niveau_parent}, code={code_parent}, limit={limit}")

    # Vérifier que le niveau parent est valide
    if niveau_parent not in ["region", "departement"]:
        logger.warning(f"Niveau parent invalide: {niveau_parent}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les niveaux 'region' et 'departement' peuvent avoir des enfants"
        )

    cache_key = f"maillage:{niveau_parent}:{code_parent}:enfants"
    if limit:
        cache_key += f":limit:{limit}"

    # Tentative de récupération depuis le cache
    cached_result = await cache_service.get_cache(cache_key)
    if cached_result:
        logger.debug(f"Cache HIT pour {cache_key}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    try:
        # Récupération des données
        enfants_df = get_shape_inf(code_parent, niveau_parent)

        # Application de la limite si définie
        if limit and not enfants_df.empty:
            enfants_df = enfants_df.head(limit)

        # Conversion et mise en cache
        return await dataframe_to_json_response(
            enfants_df,
            cache_service=cache_service,
            cache_key=cache_key
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des données: {str(e)}"
        )


# Nouvelles routes utilisant les fonctions optimisées
@app.get(
    "/search",
    response_model=List[ShapeWithNiveauResponse],
    responses={
        200: {"description": "Résultats de la recherche"},
        500: {"description": "Erreur lors de la recherche", "model": ErrorResponse},
    },
    summary="Recherche des mailles par terme",
    tags=["Recherche"]
)
async def search_mailles(
        q: str = Query(..., description="Terme de recherche", min_length=2),
        niveau: Optional[str] = Query(None, description="Filtrer par niveau (region, departement, commune)"),
        limit: int = Query(10, description="Nombre maximum de résultats", ge=1, le=100),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Recherche des mailles par terme dans le libellé.

    - **q**: Terme à rechercher (minimum 2 caractères)
    - **niveau**: Filtre optionnel par niveau administratif
    - **limit**: Nombre maximum de résultats (défaut: 10, max: 100)

    Retourne les mailles dont le libellé contient le terme recherché.
    """
    logger.info(f"Recherche: q={q}, niveau={niveau}, limit={limit}")

    # Vérification du niveau si spécifié
    if niveau and niveau not in NIVEAUX_MAILLE:
        logger.warning(f"Niveau de maille invalide: {niveau}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Niveau de maille invalide. Valeurs acceptées: {', '.join(NIVEAUX_MAILLE.keys())}"
        )

    cache_key = f"search:{q}"
    if niveau:
        cache_key += f":{niveau}"
    cache_key += f":limit:{limit}"

    # Tentative de récupération depuis le cache
    cached_result = await cache_service.get_cache(cache_key)
    if cached_result:
        logger.debug(f"Cache HIT pour {cache_key}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    try:
        # Recherche avec la nouvelle fonction
        results_df = search_shape(q, niveau, limit)

        # Conversion et mise en cache
        return await dataframe_to_json_response(
            results_df,
            cache_service=cache_service,
            cache_key=cache_key
        )
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )


@app.get(
    "/stats",
    response_model=List[StatResponse],
    responses={
        200: {"description": "Statistiques des mailles"},
        500: {"description": "Erreur lors de la récupération des statistiques", "model": ErrorResponse},
    },
    summary="Récupère des statistiques sur les mailles",
    tags=["Info"]
)
async def get_maille_stats(
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère des statistiques sur les mailles disponibles dans la base.

    Retourne le nombre de mailles par niveau administratif.
    """
    logger.info("Récupération des statistiques")

    cache_key = "maillage:stats"

    # Tentative de récupération depuis le cache
    cached_result = await cache_service.get_cache(cache_key)
    if cached_result:
        logger.debug(f"Cache HIT pour {cache_key}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    try:
        # Utilisation de la nouvelle fonction stats
        stats_df = get_shape_stats()

        # Conversion et mise en cache
        return await dataframe_to_json_response(
            stats_df,
            cache_service=cache_service,
            cache_key=cache_key
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}"
        )


@app.get(
    "/maille/{niveau_maille}/{code_maille}/arianne",
    response_model=List[Dict[str, str]],
    responses={
        200: {"description": "Fil d'Ariane retourné avec succès"},
        404: {"description": "Maille non trouvée", "model": ErrorResponse},
        500: {"description": "Erreur lors de la récupération du fil d'Ariane", "model": ErrorResponse},
    },
    summary="Récupère le fil d'Ariane d'une maille",
    tags=["Navigation"]
)
async def get_maille_arianne(
        niveau_maille: str = Path(..., description="Niveau de maille (region, departement, commune)"),
        code_maille: str = Path(..., description="Code de la maille"),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère le fil d'Ariane (breadcrumb) d'une maille spécifique.

    - **niveau_maille**: Niveau administratif (region, departement, commune)
    - **code_maille**: Code administratif de la maille

    Retourne une liste ordonnée des mailles parentes jusqu'à la maille demandée.
    Exemple pour une commune : [région, département, commune]
    """
    logger.info(f"Récupération fil d'Ariane: niveau={niveau_maille}, code={code_maille}")

    # Vérification du niveau de maille
    if niveau_maille not in NIVEAUX_MAILLE:
        logger.warning(f"Niveau de maille invalide: {niveau_maille}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Niveau de maille invalide. Valeurs acceptées: {', '.join(NIVEAUX_MAILLE.keys())}"
        )

    cache_key = f"arianne:{niveau_maille}:{code_maille}"

    # Tentative de récupération depuis le cache
    cached_result = await cache_service.get_cache(cache_key)
    if cached_result:
        logger.debug(f"Cache HIT pour {cache_key}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    try:
        # Récupération du fil d'Ariane
        arianne = get_arianne(code_maille, niveau_maille)

        if arianne is None:
            logger.warning(f"Maille non trouvée: niveau={niveau_maille}, code={code_maille}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aucune maille trouvée pour le niveau {niveau_maille} avec le code {code_maille}"
            )

        # Mise en cache et retour
        result = jsonable_encoder(arianne)
        await cache_service.set_cache(cache_key, result)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result,
            headers={"X-Cache": "MISS"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du fil d'Ariane: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du fil d'Ariane: {str(e)}"
        )

@app.get("/clear")
async def clear_cache(
    pattern: str = None, cache_service: CacheService = Depends(CacheService)
):
    """Clear all cache or pattern-specific cache"""
    success = await cache_service.clear_cache(pattern)
    if success:
        return {"message": "Cache cleared successfully"}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error clearing cache"
    )

@app.get(
    "/",
    summary="Page d'accueil de l'API",
    tags=["Info"]
)
async def read_root():
    """
    Page d'accueil de l'API Maillage.

    Fournit des informations de base et les points d'entrée de l'API.
    """
    return {
        "api": "Maillage Géographique API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "mailles": ["/maille/{niveau_maille}", "/maille/{niveau_maille}/{code_maille}"],
            "enfants": ["/maille/enfants/{niveau_parent}/{code_parent}"],
            "recherche": ["/search?q={terme}&niveau={niveau_optionnel}&limit={limite_optionnelle}"],
            "statistiques": ["/stats"]
        }
    }
