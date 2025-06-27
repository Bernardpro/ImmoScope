# ──────────────────────────────
# 0.  LIBRAIRIES & GLOBAL CONFIG
# ──────────────────────────────
import os, ssl, re, hashlib, urllib3, logging
from minio import Minio
from bs4 import BeautifulSoup
from pyspark.sql import SparkSession
from pyspark.sql import functions as F 
from pyspark.sql.types import (StructType, StructField, StringType,
                               FloatType, IntegerType)

logging.basicConfig(level=logging.INFO, format="%(asctime)s – %(levelname)s – %(message)s")

# 1.  ENVIRONMENT VARIABLES
MINIO_HOST        = os.getenv("MINIO_URL",     "35.241.212.205")
MINIO_ACCESS_KEY  = os.getenv("MINIO_ACCESS_KEY",  "console")
MINIO_SECRET_KEY  = os.getenv("MINIO_SECRET_KEY",  "console123")
BUCKET            = "web-scraping"
DB_TABLE          = "proprietes"   
PG_URL            = os.getenv("DATABASE_URL",  "jdbc:postgresql://postgres:5432/traindb")
PG_USER           = os.getenv("PG_USER", "trainuser")
PG_PASSWORD       = os.getenv("PG_PASSWORD", "trainpass123")


# 2.  SPARK SCHEMA
schema = (StructType()
  .add("annonce_id",     StringType())
  .add("titre",          StringType())
  .add("prix",           FloatType())
  .add("surface",        FloatType())
  .add("pieces",         IntegerType())
  .add("ville",          StringType())
  .add("source",         StringType())
  .add("code_commune",   StringType())
  .add("taille_terrain", FloatType()))

# 3.  SPARK SESSION
spark = (SparkSession.builder
         .appName("Logic-Immo – HTML Parser MinIO")
         .master("local[*]")          
         .config("spark.sql.shuffle.partitions", "16")
         .getOrCreate())

# ──────────────────────────────
# 4.  DRIVER: LIST ALL .html FILES
# ──────────────────────────────
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode    = ssl.CERT_NONE
http   = urllib3.PoolManager(ssl_context=ssl_ctx)

mc = Minio(MINIO_HOST,
           access_key=MINIO_ACCESS_KEY,
           secret_key=MINIO_SECRET_KEY,
           secure=True,
           http_client=http)

html_keys = [object.object_name for object in mc.list_objects(BUCKET, recursive=True)
             if object.object_name.endswith(".html")]


if not html_keys:
    logging.warning("No HTML files found in the bucket.")
    spark.stop()
    raise SystemExit

logging.info("⚙️  %d HTML files detected :", len(html_keys))

# ──────────────────────────────
# 5.  WORKER FUNCTION (mapPartitions)
# ──────────────────────────────
def parse_partition(iterator):
    """
    Each partition gets a chunk of HTML keys:
    1) initialise ONE MinIO client
    2) stream HTML into memory
    3) parse with BeautifulSoup + regex
    4) yield one dict (one ad) at a time
    """
    import ssl, urllib3, os, re, hashlib
    from minio import Minio
    from bs4 import BeautifulSoup

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode    = ssl.CERT_NONE
    http   = urllib3.PoolManager(ssl_context=ssl_ctx)
    cli    = Minio(MINIO_HOST,
                   access_key=MINIO_ACCESS_KEY,
                   secret_key=MINIO_SECRET_KEY,
                   secure=True,
                   http_client=http)

    for key in iterator:
        try:
            obj  = cli.get_object(BUCKET, key)
            html = obj.read().decode("utf-8", errors="ignore")
            obj.close()
        except Exception as err:
            logging.warning("⛔ %s – téléchargement impossible : %s", key, err)
            continue

        soup  = BeautifulSoup(html, "lxml")   
        cards = soup.select('[data-testid="cardmfe-description-box-text-test-id"]')
        if not cards:
            continue

        file_name     = os.path.basename(key)
        code_commune  = file_name.split("_")[0]

        for card in cards:
            # — prix
            price_match = re.search(r'aria-label=\"([\d\s]+) ?€\"', str(card))
            prix = float(price_match.group(1).replace(" ", "")) if price_match else None

            # — surface
            surf_match = re.search(r'(\d+(?:[\.,]\d+)?) ?m²', card.text)
            surface = float(surf_match.group(1).replace(",", ".")) if surf_match else None

            # — pièces
            piece_match = re.search(r'(\d+)\s+pièce', card.text, re.I)
            pieces = int(piece_match.group(1)) if piece_match else None

            # — titre
            titre = next((d.get_text(strip=True) for d in card.find_all('div', class_=re.compile('css-'))
                          if re.search(r'(vendre|louer|appartement|maison|duplex|studio)', d.text, re.I)), None)

            # — ville
            ville_div = card.find('div', {'data-testid': 'cardmfe-description-box-address'})
            ville = ville_div.get_text(strip=True) if ville_div else None

            # — terrain
            keyfacts   = card.select_one('[data-testid="classified-card-key-facts"]')
            terr_match = re.search(r'([\d\s,]+) m² de terrain', keyfacts.text) if keyfacts else None
            terrain = float(terr_match.group(1).replace(" ", "").replace(",", ".")) if terr_match else None

            uid_str = f"{prix}_{surface}_{code_commune}_{ville}"
            annonce_id = hashlib.md5(uid_str.encode()).hexdigest()[:16]

            yield {"annonce_id": annonce_id,
                   "titre": titre,
                   "prix": prix,
                   "surface": surface,
                   "pieces": pieces,
                   "ville": ville,
                   "source": key,
                   "code_commune": code_commune,
                   "taille_terrain": terrain}

# ──────────────────────────────
# 6.  SPARK PIPELINE
# ──────────────────────────────
rdd         = spark.sparkContext.parallelize(html_keys,
                                            numSlices=min(len(html_keys), 64))
rows_rdd    = rdd.mapPartitions(parse_partition)
df          = spark.createDataFrame(rows_rdd, schema)
df          = df.withColumn("prix_m2", F.when(F.col("surface") > 0, F.col("prix") / F.col("surface")).otherwise(F.lit(None)))

logging.info("💾 %d unique ads extracted.", df.count())


# ──────────────────────────────
# 7.  PARALLEL JDBC WRITE
# ──────────────────────────────
# (df.write
#    .format("jdbc")
#    .mode("overwrite")  
#    .option("url", PG_URL)
#    .option("dbtable", DB_TABLE)
#    .option("user", PG_USER)
#    .option("password", PG_PASSWORD)
#    .option("driver", "org.postgresql.Driver")
#    .mode("append")
#    .save())


# 1) Nettoyer le DataFrame : une seule ligne par annonce_id
scraped_df = (df            # <- ton DataFrame après le parsing
              .dropDuplicates(["annonce_id"]))

# 2) Récupérer la liste (souvent petite) des PK déjà en base
existing_ids = (spark.read
    .format("jdbc")
    .option("url", PG_URL)
    .option("dbtable", f"(SELECT annonce_id FROM {DB_TABLE}) AS t")  # push-down = rapide
    .option("user", PG_USER)
    .option("password", PG_PASSWORD)
    .option("driver", "org.postgresql.Driver")
    .load()
    .select("annonce_id")        # on ne conserve que la colonne PK
    .distinct())

# 3) Anti-join : ne garder que les IDs absents de Postgres
new_rows = scraped_df.join(existing_ids, on="annonce_id", how="left_anti")

# 4) Écrire uniquement ces nouveautés
# jvm = spark.sparkContext._jvm
# Properties = jvm.java.util.Properties
# props = Properties()
# props["user"]     = PG_USER
# props["password"] = PG_PASSWORD
# props["driver"]   = "org.postgresql.Driver"

# (new_rows.write
#    .format("jdbc")
#    .option("batchsize", 5000)    
#    .mode("append")
#    .jdbc(PG_URL, DB_TABLE))

(new_rows.write
   .format("jdbc") 
   .option("url", PG_URL)
   .option("dbtable", DB_TABLE)
   .option("user", PG_USER)
   .option("password", PG_PASSWORD)
   .option("driver", "org.postgresql.Driver")
   .mode("append")
   .save())

logging.info("✅ Data successfully written to PostgreSQL.")
spark.stop()