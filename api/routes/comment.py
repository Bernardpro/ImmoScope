from fastapi import APIRouter, HTTPException, Query
from elasticsearch import AsyncElasticsearch 
from db.models import SentimentTerms


router = APIRouter(prefix="/comment", tags=["Comment"])


es = AsyncElasticsearch(
    hosts=["http://es01:9200"],
    basic_auth=("kibana_system", "password123"),
    verify_certs=False,         
    request_timeout=30
)

@router.on_event("shutdown")
async def _close_es():
    await es.close()
    
@router.get(
    "/data/sentiment-terms",
    response_model=SentimentTerms,
    summary="Liste des mots les plus utilisées positifs/négatifs pour une commune",
)
async def sentiment_terms(
    code: str = Query(..., regex="^\\d{5}$|^\\d{2}$", description="Code INSEE (5 chiffres)")
):
    """
    Exécute l'agrégation Elasticsearch :

    - Filtre sur `code_commune`
    - Bucket par `sentiment`
    - Récupère les 10 tokens les plus fréquents (`terms`)
    """
    body = {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"code_commune": code}}
                ]
            }
        },
        "aggs": {
            "by_sentiment": {
                "terms": {"field": "sentiment", "size": 2},
                "aggs": {
                    "top_terms": {"terms": {"field": "tokens", "size": 10}}
                }
            }
        },
    }

    try:
        resp = await es.search(index="city-comments-*", body=body)
    except Exception as err:
        raise HTTPException(500, f"Elasticsearch error: {err}") from err

    result: dict[str, list[str]] = {"positive": [], "negative": []}
    for bucket in resp["aggregations"]["by_sentiment"]["buckets"]:
        sentiment = bucket["key"]          
        tokens = [t["key"] for t in bucket["top_terms"]["buckets"]]
        result[sentiment] = tokens

    return result


@router.get(
    "/data/top-terms",
    response_model=list[str],
    summary="Mots les plus fréquents d’une commune",
)
async def top_terms(
    code: str = Query(
        ...,
        regex="^\\d{5}$|^\\d{2}$",
        description="Code INSEE (5 chiffres ou 2 chiffres pour un département)",
    )
):
    """
    Exécute l’agrégation Elasticsearch :

    - Filtre sur `code_commune`
    - Récupère les *n* tokens les plus fréquents (`terms`)
    """
    body = {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"code_commune": code}}
                ]
            }
        },
        "aggs": {
            "top_tokens": {
                "terms": {
                    "field": "tokens",
                    "size": 5
                }
            }
        },
    }

    try:
        resp = await es.search(index="city-comments-*", body=body)
    except Exception as err:          # connexion ES, mapping, etc.
        raise HTTPException(500, f"Elasticsearch error: {err}") from err

    # On extrait les mots (clé « key » dans chaque bucket)
    tokens = [bucket["key"] for bucket in resp["aggregations"]["top_tokens"]["buckets"]]

    return tokens