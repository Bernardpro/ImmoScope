# MAILLAGE

# SOMMAIRE

1. Démarrage
2. Api
3. Fonctionnalité


## Démarrage : 

### Prérequis :

1. Postgresql
1. Ide Pycharm

### Mettre la table dans **pgAdmin** :

Cliquer droit sur un database puis clic sur **Restore..**

![screen de ou cliquer pour Restore](./image/restore_postgresql.png)

Sélectionner le fichier avec l'extension **.sql** puis clic sur le bouton **restore**

### Mettre à jour les informations de connexion dans database.ini

Ouvrir le fichier avec le bloc-notes et mettez votre **mdp** et **nom de database**.

Vérifier sur les autres champs s'ils sont bien remplie et valide selon votre PostgreSQL.

### Lancer l'api en local 

Ouvrir le projet avec l'ide.

Comment réaliser les imports nécessaires
```bash
pip install psycopg2
pip install requests

pip install Fastapi
pip install uvicorn
```
Puis pour lancer l'api en locale dans le **Terminal**
```bash
uvicorn api:app --reload
```
![texte quand l'api est lancer](./image/screen_startApi.png) 

Quand l'api est bien lancer, se texte apparaît.

Pour pouvoir faire des request à l'api, l'ip est:
```
http://127.0.0.1:8000/
```

# Api

### Api utilisé dans le module python

Pour réaliser la recherche avec une adresse source, j'utilise l'api :
``` 
https://pyris.datajazz.io/doc/
```

Et plus précisément :
```
https://pyris.datajazz.io/api/search/?geojson=false&q={adresse}
```

# Fonctionnalité
### Requête
Il est disponible 2 request :

1. une requête de changement de maille avec maille source, code source et une maille destination (non obligatoire)
    1. ```http://127.0.0.1:8000/maille/{maille source}/{code source}```
    2. ```http://127.0.0.1:8000/maille/{maille source}/{code source}/{maille destination}```
2.  une requête de recherche de maille avec une adresse source 
    1. ```http://127.0.0.1:8000/adress/{adresse source}```


Les possibilités de {maille source} sont :

``` iris ; commune ; departement ; region ; ti : epci```

Puis l'écriture correcte de {adresse source} :

```adresse postale nom de ville```

Elle est composée de 2 paramètre, le premier est une **adresse postale** et le second est un **nom de ville**. 
Exemple : ``` 1 Place Bellecour Lyon```
