import pandas as pd
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from starlette import status
from starlette.responses import JSONResponse

from db.session import get_engine
from services.cache_service import CacheService

router = APIRouter(prefix="/proprietes", tags=["Propriétés"])


@router.get("/", response_model=None)
async def get_proprietes(
        code: str = Query(None, description="Code de maille"),
        niveau: str = Query(None, description="Niveau de maille", regex="^(departement|commune)$"),
        page: int = Query(1, ge=1, description="Numéro de page"),
        limit: int = Query(10, ge=1, le=100, description="Nombre d'éléments par page"),
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
    cache_key = f"properties_code_{code}_niveau_{niveau}_page_{page}_limit_{limit}"
    engine = get_engine()

    # Vérification du cache
    if cached_result := await cache_service.get_cache(cache_key):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    try:
        result = await get_properties_paginated(engine, code, niveau, page, limit)
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


async def get_properties_paginated(engine, code: str, niveau: str, page: int, limit: int):
    """
    Récupère les propriétés avec pagination depuis la base de données.

    Args:
        engine: Moteur de base de données
        code: Code de maille
        niveau: Niveau de maille (departement ou commune)
        page: Numéro de page
        limit: Nombre d'éléments par page

    Returns:
        dict: Données paginées avec métadonnées
    """
    # Calcul de l'offset
    offset = (page - 1) * limit

    # Construction de la clause WHERE
    where_clause = ""
    params = {"limit": limit, "offset": offset}

    if code and niveau:
        if niveau == "departement":
            where_clause = "WHERE code_commune LIKE :code_pattern"
            params["code_pattern"] = f"{code}___"
        elif niveau == "commune":
            where_clause = "WHERE code_commune = :code"
            params["code"] = code

    # Requête pour les données avec paramètres liés
    query_data = text(f"""
    select annonce_id, titre, prix, surface, pieces, prix_m2, ville
    FROM proprietes
    {where_clause}
    ORDER BY code_commune
    LIMIT :limit OFFSET :offset;
    """)

    # Requête pour le total
    query_total = text(f"""
    SELECT COUNT(*) as total
    FROM proprietes
    {where_clause};
    """)

    # Exécution des requêtes avec paramètres liés pour éviter l'injection SQL
    with engine.connect() as conn:
        df = pd.read_sql(query_data, conn, params=params)

        # Pour la requête total, on n'a pas besoin de limit/offset
        total_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
        df_total = pd.read_sql(query_total, conn, params=total_params)

    # Conversion des types numpy en types Python natifs
    total_items = int(df_total['total'].iloc[0])
    total_pages = max(1, (total_items + limit - 1) // limit)  # Au moins 1 page

    # Conversion du DataFrame en dictionnaire avec types natifs
    # Utilisation de to_dict avec 'records' pour une meilleure performance
    data = df.to_dict(orient='records')

    # S'assurer que tous les types numpy sont convertis
    for record in data:
        for key, value in record.items():
            if hasattr(value, 'item'):  # Type numpy
                record[key] = value.item()
            elif pd.isna(value):  # Valeurs NaN
                record[key] = None

    # Construction de la réponse
    return {
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "filters": {
            "code": code,
            "niveau": niveau
        }
    }
