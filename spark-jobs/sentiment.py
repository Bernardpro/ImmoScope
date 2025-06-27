#!/usr/bin/env python
"""
Étiquette chaque commentaire avec un sentiment (positive | negative | neutral).

↳  pip install elasticsearch openai backoff tqdm python-dotenv
↳  Variables d’env. obligatoires :
        OPENAI_API_KEY       (ex. sk-…)
        ELASTICSEARCH_URL    (ex. http://localhost:9200)   [facultatif : défaut localhost]
"""
import os, textwrap, backoff
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm
from openai import OpenAI, RateLimitError

# ---------- Config ----------
load_dotenv()                             # charge .env si présent

INDEX_PATTERN = "city-comments-*"
BATCH_SIZE    = 100                       # 100 updates ES à la fois
OPENAI_MODEL  = "gpt-4o-mini"

SYSTEM_PROMPT = textwrap.dedent("""
    Tu es un classificateur de sentiment français.
    Retourne exactement : positive • negative • neutral
""").strip()
# -----------------------------

# 1) Connexions
es     = Elasticsearch(os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))     # ← lève une erreur si la clé manque

# 2) Appel OpenAI avec back-off automatique
@backoff.on_exception(backoff.expo, RateLimitError, max_tries=5)
def classify(text: str) -> str:
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": text[:4000]},   # coupe à 4 k tokens au cas où
        ],
    )
    label = resp.choices[0].message.content.strip().lower()
    return label if label in {"positive", "negative", "neutral"} else "neutral"

# 3) Générateur : scanne *tous* les documents de city-comments-*
def iter_comments():
    return helpers.scan(
        es,
        index=INDEX_PATTERN,
        query={               # aucune condition ⇒ match_all implicite
            "_source": ["text_fr"]        # on ne rapatrie que le texte utile
        },
        size=500,                          # taille du scroll
    )

# 4) Boucle principale : sentiment → bulk update
def main():
    actions = []
    for doc in tqdm(iter_comments(), desc="Analyse", total=None):
        texte = doc["_source"].get("text_fr", "")
        sentiment = classify(texte)
        actions.append({
            "_op_type": "update",
            "_index":   doc["_index"],
            "_id":      doc["_id"],
            "doc":      {"sentiment": sentiment},
            "doc_as_upsert": True,
        })
        if len(actions) >= BATCH_SIZE:
            helpers.bulk(es, actions, request_timeout=120)
            actions.clear()
    if actions:
        helpers.bulk(es, actions, request_timeout=120)
    print("✓ Terminé")

if __name__ == "__main__":
    main()
