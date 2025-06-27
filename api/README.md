# 🚀 HomePedia API

**API REST FastAPI pour l'analyse de données immobilières françaises**

API backend complète pour la plateforme HomePedia, offrant des endpoints optimisés pour les données immobilières, l'analyse de sentiment et la gestion cartographique avec cache Redis et recherche Elasticsearch.

---

## 📋 Table des matières

-   [🎯 Aperçu](#-aperçu)
-   [⚡ Installation](#-installation)
-   [🔐 Authentification](#-authentification)
-   [📡 Endpoints API](#-endpoints-api)
-   [💾 Cache & Performance](#-cache--performance)
-   [🔍 Elasticsearch](#-elasticsearch)
-   [📊 Exemples d'utilisation](#-exemples-dutilisation)
-   [⚙️ Configuration](#️-configuration)

---

## 🎯 Aperçu

### 🛠️ Technologies

-   **Framework** : FastAPI 0.100+
-   **Base de données** : PostgreSQL + SQLAlchemy
-   **Cache** : Redis avec TTL automatique
-   **Recherche** : Elasticsearch 7.17+
-   **Authentification** : JWT avec OAuth2 Bearer
-   **Processing** : Pandas pour l'analyse de données

### 🌟 Fonctionnalités principales

-   🏠 **Données immobilières** : Propriétés, prix, surfaces, localisation
-   📊 **Analyses de réputation** : Scoring par zone géographique
-   💬 **Sentiment analysis** : Analyse NLP des commentaires citoyens
-   🗺️ **Données géographiques** : Maillage commune/département/région
-   ⚡ **Cache intelligent** : Redis avec invalidation automatique
-   🔒 **Sécurité JWT** : Authentification avec scopes (read/write/admin)

---

## ⚡ Installation

### 🐳 Démarrage rapide avec Docker

```bash
# Dans le répertoire racine du projet
cd T-DAT-902-LYO_4

# Démarrer l'API (port 82)
docker compose up api -d

# L'API est accessible sur http://localhost:82
```

### 📦 Installation locale

```bash
cd api/

# Installer les dépendances
pip install -r requirements.txt

# Variables d'environnement
cp .env.example .env

# Démarrer l'API
uvicorn main:app --host 0.0.0.0 --port 82 --reload
```

### 🔗 Services requis

-   **PostgreSQL** : Base de données principale
-   **Redis** : Cache haute performance
-   **Elasticsearch** : Moteur de recherche

---

## 🔐 Authentification

L'API utilise **JWT (JSON Web Tokens)** avec OAuth2 Password Bearer flow.

### 🎫 Scopes disponibles

| Scope   | Description            |
| ------- | ---------------------- |
| `read`  | Lecture des données    |
| `write` | Écriture des données   |
| `admin` | Actions administrateur |

### 🔑 Headers requis

```http
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

### 🚪 Workflow d'authentification

1. **Inscription** : `POST /user/signup`
2. **Connexion** : `POST /user/login` → Récupération du token
3. **Utilisation** : Ajouter le token dans le header `Authorization`

---

## 📡 Endpoints API

### 👤 Authentification (`/user`)

| Méthode | Endpoint              | Description                       | Auth     |
| ------- | --------------------- | --------------------------------- | -------- |
| `POST`  | `/user/signup`        | Créer un compte utilisateur       | ❌       |
| `POST`  | `/user/login`         | Connexion et récupération token   | ❌       |
| `GET`   | `/user/me`            | Informations utilisateur connecté | ✅       |
| `POST`  | `/user/logout`        | Déconnexion utilisateur           | ❌       |
| `POST`  | `/user/token/refresh` | Rafraîchir le token JWT           | ✅       |
| `POST`  | `/user/admin/action`  | Action admin (test scope)         | ✅ Admin |

### 🏠 Propriétés immobilières (`/proprietes`)

| Méthode | Endpoint       | Description                      | Paramètres                        |
| ------- | -------------- | -------------------------------- | --------------------------------- |
| `GET`   | `/proprietes/` | Liste propriétés avec pagination | `code`, `niveau`, `page`, `limit` |

**Paramètres de filtrage :**

-   `code` : Code INSEE (commune 5 chiffres, département 2 chiffres)
-   `niveau` : `commune` \| `departement`
-   `page` : Numéro de page (défaut: 1)
-   `limit` : Éléments par page (max: 100, défaut: 10)

### 📊 Données d'analyse (`/data`)

| Méthode | Endpoint                      | Description                          | Paramètres       |
| ------- | ----------------------------- | ------------------------------------ | ---------------- |
| `GET`   | `/data/reputations/chart`     | Données réputation (graphique)       | `code`, `niveau` |
| `GET`   | `/data/reputations/one/map`   | Réputation avec couleurs             | `code`, `niveau` |
| `POST`  | `/data/reputations/multi/map` | Réputation zones multiples           | Body JSON        |
| `GET`   | `/data/fonciers`              | Données foncières                    | `code`, `niveau` |
| `GET`   | `/data/equipements`           | Équipements publics                  | `code`           |
| `GET`   | `/data/taxe/fonciers`         | Taxes foncières                      | `code`, `niveau` |
| `GET`   | `/data/commune/{code}/all`    | **Toutes les données** d'une commune | `code`           |

### 💬 Commentaires et sentiment (`/comment`)

| Méthode | Endpoint                        | Description             | Paramètres     |
| ------- | ------------------------------- | ----------------------- | -------------- |
| `GET`   | `/comment/data/sentiment-terms` | Mots positifs/négatifs  | `code` (INSEE) |
| `GET`   | `/comment/data/top-terms`       | Mots les plus fréquents | `code` (INSEE) |

### ⚡ Cache management (`/cache`)

| Méthode  | Endpoint           | Description       | Paramètres            |
| -------- | ------------------ | ----------------- | --------------------- |
| `GET`    | `/cache/clear`     | Vider le cache    | `pattern` (optionnel) |
| `DELETE` | `/cache/{key}`     | Supprimer une clé | `key`                 |
| `GET`    | `/cache/ttl/{key}` | TTL d'une clé     | `key`                 |

### 🔧 Utilitaires

| Méthode | Endpoint       | Description          |
| ------- | -------------- | -------------------- |
| `GET`   | `/data/health` | Santé de l'API et DB |
| `GET`   | `/`            | Endpoint racine      |

---

## 💾 Cache & Performance

### ⚡ Système de cache Redis

-   **Cache automatique** : Toutes les réponses GET sont cachées
-   **TTL intelligent** : Durée adaptée par type de donnée
-   **Headers informatifs** : `X-Cache: HIT/MISS`
-   **Patterns configurables** : Cache par type d'endpoint

### ⏱️ TTL par type de données

```python
# Configuration des durées de cache
cache_patterns = {
    "properties_*": 1800,      # 30 minutes - propriétés
    "reputations_*": 3600,     # 1 heure - réputations
    "equipements_*": 7200,     # 2 heures - équipements
    "sentiment_*": 1800        # 30 minutes - sentiment
}
```

### 📈 Optimisations performance

-   **Requêtes parallèles** : `/data/commune/{code}/all` exécute plusieurs requêtes en parallèle
-   **Pagination intelligente** : Métadonnées complètes (total, pages, navigation)
-   **Requêtes SQL optimisées** : Paramètres liés contre injection SQL
-   **Monitoring** : Log des requêtes lentes (>1s)

---

## 🔍 Elasticsearch

### 🛠️ Configuration

```python
# Configuration Elasticsearch
es = AsyncElasticsearch(
    hosts=["http://es01:9200"],
    basic_auth=("kibana_system", "password123"),
    verify_certs=False,
    request_timeout=30
)
```

### 📚 Index utilisés

-   **`city-comments-*`** : Commentaires avec analyse de sentiment
    -   Champs : `code_commune`, `sentiment`, `tokens`
    -   Agrégations : Termes les plus fréquents par sentiment

### 🔎 Requêtes supportées

-   **Sentiment par commune** : Mots positifs/négatifs
-   **Top termes** : Mots les plus mentionnés
-   **Filtres géographiques** : Par code INSEE

---

## 📊 Exemples d'utilisation

### 1️⃣ Authentification complète

```bash
# 📝 Inscription
curl -X POST "http://localhost:82/user/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "mail": "user@example.com",
    "name": "Jean Dupont",
    "password": "motdepasse123"
  }'

# 🔑 Connexion
curl -X POST "http://localhost:82/user/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=motdepasse123"

# Réponse:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "mail": "user@example.com",
    "name": "Jean Dupont"
  }
}
```

### 2️⃣ Données immobilières avec pagination

```bash
# 🏠 Propriétés de Villeurbanne (69266) - Page 1
curl -X GET "http://localhost:82/proprietes/?code=69266&niveau=commune&page=1&limit=5" \
  -H "Authorization: Bearer <token>"

# Réponse:
{
  "data": [
    {
      "annonce_id": "12345",
      "titre": "Appartement T3 proche métro",
      "prix": 280000,
      "surface": 68,
      "pieces": 3,
      "prix_m2": 4118,
      "ville": "Villeurbanne"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 5,
    "total_items": 847,
    "total_pages": 170,
    "has_next": true,
    "has_prev": false
  }
}
```

### 3️⃣ Analyse de réputation

```bash
# 📊 Réputation de Lyon 3ème (69383)
curl -X GET "http://localhost:82/data/reputations/chart?code=69383&niveau=commune" \
  -H "Authorization: Bearer <token>"

# 🗺️ Réputation avec couleurs pour la carte
curl -X GET "http://localhost:82/data/reputations/one/map?code=69383&niveau=commune" \
  -H "Authorization: Bearer <token>"

# 🌍 Réputation de plusieurs communes du Rhône
curl -X POST "http://localhost:82/data/reputations/multi/map" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "codes": ["69381", "69382", "69383", "69266"],
    "niveau": "commune"
  }'
```

### 4️⃣ Analyse de sentiment

```bash
# 💭 Mots positifs/négatifs sur Villeurbanne
curl -X GET "http://localhost:82/comment/data/sentiment-terms?code=69266" \
  -H "Authorization: Bearer <token>"

# Réponse:
{
  "positive": ["calme", "pratique", "transport", "commerces"],
  "negative": ["bruyant", "circulation", "parking", "cher"]
}

# 🔝 Mots les plus mentionnés
curl -X GET "http://localhost:82/comment/data/top-terms?code=69266" \
  -H "Authorization: Bearer <token>"

# Réponse:
["transport", "métro", "commerces", "quartier", "pratique"]
```

### 5️⃣ Données complètes d'une commune

```bash
# 🏘️ TOUTES les données de Villeurbanne en une requête
curl -X GET "http://localhost:82/data/commune/69266/all" \
  -H "Authorization: Bearer <token>"

# Réponse consolidée:
{
  "code": "69266",
  "foncier": { /* données foncières */ },
  "equipements": { /* équipements publics */ },
  "reputations": { /* scores réputation */ },
  "reputations_color": { /* données cartographiques */ }
}
```

### 6️⃣ Gestion du cache

```bash
# ⚡ Vider tout le cache
curl -X GET "http://localhost:82/cache/clear"

# 🗑️ Supprimer le cache des propriétés
curl -X GET "http://localhost:82/cache/clear?pattern=properties_*"

# ❌ Supprimer une clé spécifique
curl -X DELETE "http://localhost:82/cache/reputations:69266:commune"

# ⏰ Vérifier le TTL d'une clé
curl -X GET "http://localhost:82/cache/ttl/properties_69266_commune_1_10"
```

---

## ⚙️ Configuration

### 🌍 Variables d'environnement

```env
# 🐘 PostgreSQL
POSTGRES_USER=trainuser
POSTGRES_PASSWORD=trainpass123
POSTGRES_DB=traindb
DATABASE_URL=postgresql://trainuser:trainpass123@postgres:5432/traindb

# ⚡ Redis
REDIS_PASSWORD=redis123
REDIS_URL=redis://redis:6379

# 🔍 Elasticsearch
ELASTICSEARCH_USERNAME=kibana_system
ELASTICSEARCH_PASSWORD=password123
ELASTICSEARCH_HOST=http://es01:9200

# 🔐 JWT
SECRET_KEY=your-super-secret-jwt-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_SECONDES=3600

# ⚡ Performance
CACHE_TTL=3600
SPARK_WORKER_MEMORY=2g
```

### 📍 Codes géographiques supportés

-   **Commune** : Code INSEE 5 chiffres (ex: `69266` pour Villeurbanne)
-   **Département** : Code INSEE 2 chiffres (ex: `69` pour le Rhône)
-   **Région** : Code région (ex: `84` pour Auvergne-Rhône-Alpes)

### 🔧 Endpoints de monitoring

```bash
# 🏥 Santé de l'API
curl http://localhost:82/data/health

# 📚 Documentation interactive
http://localhost:82/docs          # Swagger UI
http://localhost:82/redoc         # ReDoc
```

---

## 🐛 Dépannage

### ⚠️ Codes d'erreur courants

| Code  | Description          | Solution                             |
| ----- | -------------------- | ------------------------------------ |
| `401` | Token JWT invalide   | Se reconnecter via `/user/login`     |
| `403` | Scope insuffisant    | Vérifier les permissions utilisateur |
| `404` | Données non trouvées | Vérifier le code INSEE               |
| `422` | Paramètres invalides | Consulter `/docs` pour le format     |
| `500` | Erreur serveur       | Vérifier les logs et la DB           |

### 📝 Logs et debugging

```bash
# 📋 Logs de l'API
docker compose logs api -f

# 🔍 Logs détaillés avec timestamps
docker compose logs api --timestamps

# 💾 État des services
docker compose ps
```

### ⚡ Performance

-   **Cache MISS fréquents** → Augmenter le TTL Redis
-   **Requêtes lentes** → Vérifier les index PostgreSQL
-   **Timeouts Elasticsearch** → Augmenter `request_timeout`

---

## 🏗️ Architecture et développement

### 📁 Structure du projet

```
api/
├── auth/                   # Module d'authentification
│   ├── __init__.py         # Exports des éléments principaux
│   ├── config.py           # Configuration JWT & OAuth2
│   ├── dependencies.py     # Dépendances FastAPI (get_current_user)
│   ├── models.py           # Modèles Pydantic validation
│   └── utils.py            # Utilitaires (hash_password, etc.)
├── db/                     # Module base de données
│   ├── models.py           # Modèles SQLAlchemy (User, etc.)
│   └── session.py          # Configuration connexion DB
├── routes/                 # Routes API
│   ├── auth.py             # Routes authentification
│   ├── cache.py            # Routes gestion cache
│   ├── comment.py          # Routes commentaires/sentiment
│   ├── data.py             # Routes données principales
│   └── proprietes.py       # Routes propriétés immobilières
├── services/               # Services métier
│   ├── cache_service.py    # Service cache Redis
│   ├── data_service.py     # Service données immobilières
│   └── resource_monitor.py # Service monitoring
├── scraping/               # Scripts collecte données
├── main.py                 # Point d'entrée application
└── requirements.txt        # Dépendances Python
```

### 🔧 Architecture des services

L'API suit le modèle **Routes-Services-Repositories** :

-   **Routes** (`routes/`) : Endpoints API et gestion requêtes HTTP
-   **Services** (`services/`) : Logique métier centralisée
-   **Models** (`db/models.py`) : Accès données SQLAlchemy

### ➕ Créer une nouvelle route

**1. Créer le fichier route**

```python
# routes/nouvelle_route.py
from fastapi import APIRouter, Depends
from auth.dependencies import get_current_user
from db.models import User

router = APIRouter(prefix="/nouvelle", tags=["Nouvelle"])

@router.get("/")
def get_data(current_user: User = Depends(get_current_user)):
    """Récupérer des données"""
    return {"message": "Données récupérées"}
```

**2. Créer le service associé**

```python
# services/nouvelle_service.py
class NouvelleService:
    """Service métier pour la nouvelle fonctionnalité"""

    def get_data(self):
        # Logique métier ici
        return {"data": "exemple"}
```

**3. Enregistrer dans main.py**

```python
from routes.nouvelle_route import router as nouvelle_router

app.include_router(nouvelle_router)
```

---

## 📖 Documentation

-   **📚 Swagger UI** : http://localhost:82/docs
-   **📄 ReDoc** : http://localhost:82/redoc
-   **🗂️ Schema OpenAPI** : http://localhost:82/openapi.json
-   **📮 Collection Postman** : [Documentation complète](https://documenter.getpostman.com/view/13153597/2sAYkGKeU7)

---

**🏠 HomePedia API** - _Données immobilières françaises optimisées pour l'analyse cartographique_
