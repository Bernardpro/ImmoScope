import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from db.session import get_engine
from services.cache_service import CacheService
from services.data_service import (

    get_equipements_by_commune,
    get_reputations_by_maille,
    get_reputations_color_by_maille, get_multiple_reputations_by_mailles, get_foncier_by_maille, get_taxe_foncier_by_maille
)

router = APIRouter(prefix="/data", tags=["data"])


# Fonction helper pour gérer le cache de manière cohérente
async def handle_cached_request(
        cache_key: str,
        data_fetcher,
        cache_service: CacheService,
        error_message: str = "No data found"
):
    """
    Gère la logique de cache de manière cohérente pour tous les endpoints.

    Args:
        cache_key: Clé pour le cache
        data_fetcher: Fonction ou coroutine qui récupère les données
        cache_service: Service de cache
        error_message: Message d'erreur si aucune donnée trouvée

    Returns:
        JSONResponse avec les données et headers de cache appropriés
    """
    # Vérifier le cache
    if cached_result := await cache_service.get_cache(cache_key):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    # Récupérer les données
    if asyncio.iscoroutine(data_fetcher):
        result = await data_fetcher
    else:
        result = await data_fetcher()

    print(f"Data fetched for {cache_key}: {result}")

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_message
        )

    # Mettre en cache
    await cache_service.set_cache(cache_key, result)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result,
        headers={"X-Cache": "MISS"}
    )


# Fonction générique pour exécuter des requêtes async
async def execute_async(func, *args, **kwargs):
    """Exécute une fonction synchrone dans un thread pool pour éviter de bloquer l'event loop"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


@router.get("/reputations/chart", response_model=None)
async def get_reputations(
        code: str = Query(..., min_length=1, max_length=10),
        niveau: str = Query(..., regex="^(commune|departement|region)$"),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère les données de réputation pour une maille donnée.

    - **code**: Code de la maille
    - **niveau**: Niveau géographique (commune, departement, region)
    """
    cache_key = f"reputations:{code}:{niveau}"
    engine = get_engine()

    return await handle_cached_request(
        cache_key=cache_key,
        data_fetcher=execute_async(get_reputations_by_maille, code, niveau, engine),
        cache_service=cache_service,
        error_message="No reputation data found for this commune"
    )


@router.get("/taxe/fonciers", response_model=None)
async def get_taxe_fonciers(
        code: str = Query(None, description="Code de maille"),
        niveau: str = Query(None, description="Niveau de maille", regex="^(departement|commune)$"),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère les propriétés avec pagination.

    - **code**: Code de maille (département ou commune)
    - **niveau**: Niveau de maille (departement ou commune)
    - **page**: Numéro de page (commence à 1)
    - **limit**: Nombre d'éléments par page (max 100)
    """
    # Clé de cache incluant tous les paramètres
    cache_key = f"taxe_fonciers_{code}_niveau_{niveau}"
    engine = get_engine()

    # Vérification du cache
    if cached_result := await cache_service.get_cache(cache_key):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    try:
        result = get_taxe_foncier_by_maille(code, niveau, engine)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des données: {str(e)}"
        )

    # Mise en cache du résultat
    await cache_service.set_cache(cache_key, result)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result,
        headers={"X-Cache": "MISS"}
    )


@router.get("/reputations/one/map", response_model=None)
async def get_reputations_color_single(
        code: str = Query(..., min_length=1, max_length=10),
        niveau: str = Query(..., regex="^(commune|departement|region)$"),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère les données de réputation avec couleurs pour une maille donnée.

    - **code**: Code de la maille
    - **niveau**: Niveau géographique (commune, departement, region)
    """
    cache_key = f"reputations_color:{code}:{niveau}"
    time_start = time.time()
    engine = get_engine()
    time_end = time.time()
    print(f"Engine initialized in {time_end - time_start:.2f} seconds")

    # Log performance en développement
    start_time = time.time()

    async def fetch_with_timing():
        result = await execute_async(get_reputations_color_by_maille, code, niveau, engine)
        execution_time = time.time() - start_time

        if execution_time > 1.0:  # Log si la requête prend plus d'1 seconde
            print(f"⚠️ Slow query: reputations/color took {execution_time:.2f}s for code={code}, niveau={niveau}")

        return result

    return await handle_cached_request(
        cache_key=cache_key,
        data_fetcher=fetch_with_timing(),
        cache_service=cache_service,
        error_message="No reputation data found for this commune"
    )


from pydantic import BaseModel, Field
from typing import List


# Modèle Pydantic pour le body de la requête
class ReputationRequest(BaseModel):
    codes: List[str] = Field(..., min_items=1, max_items=10000, description="Liste des codes de mailles")
    niveau: str = Field(..., pattern="^(commune|departement|region)$", description="Niveau géographique")


@router.post("/reputations/multi/map", response_model=None)
async def get_reputations_color_multiple(
        request: ReputationRequest,
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère les données de réputation avec couleurs pour plusieurs mailles.

    - **codes**: Liste de codes de mailles
    - **niveau**: Niveau géographique (commune, departement, region)
    """
    # Nettoyer la liste des codes (enlever les espaces)
    codes_list = [code.strip() for code in request.codes if code.strip()]

    print("Codes list after processing:", codes_list)

    # Vérifier que la liste n'est pas vide après nettoyage
    if not codes_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid code must be provided"
        )

    cache_key = f"reputations_color:multi:{','.join(sorted(codes_list))}:{request.niveau}"
    engine = get_engine()

    return await handle_cached_request(
        cache_key=cache_key,
        data_fetcher=execute_async(get_multiple_reputations_by_mailles, codes_list, request.niveau, engine),
        cache_service=cache_service,
        error_message="No reputation data found for the provided codes"
    )


@router.get("/fonciers", response_model=None)
async def get_fonciers(
        code: str = Query(..., min_length=1, max_length=10),
        niveau: str = Query(..., regex="^(commune|departement|region)$"),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère les données foncières pour une commune.

    - **code**: Code INSEE de la commune
    """
    cache_key = f"fonciers:{code}: {niveau}"

    print(f"Fetching foncier data for code={code}, niveau={niveau}")

    return await handle_cached_request(
        cache_key=cache_key,
        data_fetcher=execute_async(get_foncier_by_maille, code, niveau),
        cache_service=cache_service,
        error_message="No foncier data found for this commune"
    )


@router.get("/equipements", response_model=None)
async def get_equipements(
        code: str = Query(..., min_length=1, max_length=10),
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère les données d'équipements pour une commune.

    - **code**: Code INSEE de la commune
    """
    cache_key = f"equipements:{code}"

    return await handle_cached_request(
        cache_key=cache_key,
        data_fetcher=execute_async(get_equipements_by_commune, code),
        cache_service=cache_service,
        error_message="No equipment data found for this commune"
    )


# Endpoint pour récupérer plusieurs types de données en une seule requête
@router.get("/commune/{code}/all")
async def get_all_commune_data(
        code: str,
        include_foncier: bool = True,
        include_equipements: bool = True,
        include_reputations: bool = True,
        niveau: str = "commune",
        cache_service: CacheService = Depends(CacheService)
):
    """
    Récupère toutes les données disponibles pour une commune en une seule requête.
    Utilise des requêtes parallèles pour optimiser les performances.
    """
    cache_key = f"all_data:{code}:{niveau}:{include_foncier}:{include_equipements}:{include_reputations}"

    if cached_result := await cache_service.get_cache(cache_key):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    tasks = []
    result = {"code": code}

    # Créer les tâches parallèles selon les paramètres
    if include_foncier:
        tasks.append(("foncier", execute_async(get_foncier_by_commune, code)))

    if include_equipements:
        tasks.append(("equipements", execute_async(get_equipements_by_commune, code)))

    if include_reputations:
        engine = get_engine()
        tasks.append(("reputations", execute_async(get_reputations_by_maille, code, niveau, engine)))
        tasks.append(("reputations_color", execute_async(get_reputations_color_by_maille, code, niveau, engine)))

    # Exécuter toutes les tâches en parallèle
    if tasks:
        task_names = [name for name, _ in tasks]
        task_coroutines = [task for _, task in tasks]

        results = await asyncio.gather(*task_coroutines, return_exceptions=True)

        for name, data in zip(task_names, results):
            if isinstance(data, Exception):
                result[name] = {"error": str(data)}
            else:
                result[name] = data

    await cache_service.set_cache(cache_key, result, ttl=300)  # Cache 5 minutes

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result,
        headers={"X-Cache": "MISS"}
    )


# Endpoint de santé pour vérifier la disponibilité des services
@router.get("/health")
async def health_check():
    """Vérifie la santé de l'API et la connexion à la base de données"""
    try:
        engine = get_engine()
        # Test simple de connexion
        await execute_async(lambda: engine.execute("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )
