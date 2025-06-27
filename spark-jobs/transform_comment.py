# ──────────────────────────────
# 0.  LIBRAIRIES & GLOBAL CONFIG
# ──────────────────────────────
import os, ssl, logging, urllib3, json, re
from datetime import datetime
from bs4 import BeautifulSoup
from minio import Minio
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (StructType, StructField, StringType,
                               FloatType, IntegerType, BooleanType,
                               DateType, MapType)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)s  %(message)s")


# ─────────────────────────────
# 1   CONFIG  (edit to taste)   
# ─────────────────────────────
MINIO_HOST     = os.getenv("MINIO_URL",       "35.241.212.205")
MINIO_ACCESS   = os.getenv("MINIO_ACCESS_KEY","console")
MINIO_SECRET   = os.getenv("MINIO_SECRET_KEY","console123")
BUCKET         = "comment"

ES_NODES       = os.getenv("ES_NODES",        "es01:9200")  
ES_INDEX       = "city-comments"
ES_USER        = os.getenv("ES_USER")         
ES_PASSWORD    = os.getenv("ES_PASSWORD")

SPARK_MASTER   = "local[*]"                  
PARTITIONS_MAX = 64

# ─────────────────────────────
# 2   Spark session
# ─────────────────────────────
spark = (SparkSession.builder
         .appName("City-Comments → Elasticsearch")
         .master(SPARK_MASTER)
         .config("spark.sql.shuffle.partitions", "16")
         .getOrCreate())

# ─────────────────────────────
# 3   MinIO client (driver only)
# ─────────────────────────────
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode    = ssl.CERT_NONE
http     = urllib3.PoolManager(ssl_context=ssl_ctx)

mc = Minio(MINIO_HOST,
           access_key=MINIO_ACCESS,
           secret_key=MINIO_SECRET,
           secure=True,
           http_client=http)

# html_keys = [objet.object_name for objet in mc.list_objects(BUCKET, recursive=True)
#              if objet.object_name.endswith(".html")]


html_keys = []
for i, objet in enumerate(mc.list_objects(BUCKET, recursive=True)) :
    if (i>3 & i<7) and objet.object_name.endswith(".html"):
        html_keys.append(objet.object_name )

if not html_keys:
    logging.warning("No HTML files found in bucket '%s'.", BUCKET)
    spark.stop()
    raise SystemExit

logging.info("Found %d HTML files to process.", len(html_keys))

# ─────────────────────────────
# 4   Utility functions
# ─────────────────────────────
def safe_text(tag, default=None):
    """Return tag text (replace <br>) or default if tag is None."""
    return tag.get_text(" ", strip=True) if tag else default

def parse_comment(div):
    """Return a dict of the extracted comment fields (never crashes)."""
    
    author    = safe_text(div.select_one(".auteur"))
    date_txt  = safe_text(div.select_one(".date"))
    cid       = div.get("data-pouce") or f"{author}-{date_txt}"
    note_raw  = safe_text(div.select_one(".note_total"))
    note_tot  = float(note_raw.replace(",", ".")) if note_raw else None
    notes_map = {span["title"]: int(safe_text(span))
                 for span in div.select("div.notes span")}
    date_obj  = (datetime.strptime(date_txt, "%d/%m/%Y").date()
                 if date_txt else None)
    body      = safe_text(div.select_one("p.description"))

    def count_thumb(val):
        s = div.select_one(f'.pouce[data-pouce="{val}"] span')
        return int(s.text) if s else 0
    likes     = count_thumb("1")
    dislikes  = count_thumb("0")
    top_flag  = "topcommentaire" in div.get("class", [])

    return {"comment_id":  cid,
            "author":      author,
            "note_total":  note_tot,
            "notes":       notes_map,  
            "date":        date_obj,
            "text_fr":     body,
            "likes":       likes,
            "dislikes":    dislikes,
            "top":         top_flag}

# ─────────────────────────────
# 5   Parser executed per partition
# ─────────────────────────────
def parse_partition(keys):
    """
    For each partition:
      • create ONE MinIO client
      • stream HTML into memory
      • yield 1 Python dict per comment
    """
    import ssl, urllib3
    from minio import Minio
    from bs4 import BeautifulSoup

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode    = ssl.CERT_NONE
    http   = urllib3.PoolManager(ssl_context=ssl_ctx)
    cli    = Minio(MINIO_HOST, access_key=MINIO_ACCESS,
                   secret_key=MINIO_SECRET, secure=True,
                   http_client=http)

    for key in keys:
        try:
            obj  = cli.get_object(BUCKET, key)
            html = obj.read().decode("utf-8", errors="ignore")
            obj.close()
        except Exception as err:
            logging.warning("Download failed for %s – %s", key, err)
            continue
        file_name = os.path.basename(key)
        code_commune = file_name.split("-")[-1].split(".")[0]  if "page" not in file_name.split("-")[-1] else file_name.split("-")[-2] 
        soup  = BeautifulSoup(html, "lxml")
        for div in soup.select("div.commentaire"):    
            out = parse_comment(div)
            if out["comment_id"]: 
                out["code_commune"] = code_commune
                yield out

# ─────────────────────────────
# 6   Spark pipeline
# ─────────────────────────────
rdd = (spark.sparkContext
              .parallelize(html_keys,
                           numSlices=min(len(html_keys), PARTITIONS_MAX))
              .mapPartitions(parse_partition))

comment_schema = (StructType()
    .add("comment_id",   StringType())
    .add("author",       StringType())
    .add("note_total",   FloatType())
    .add("notes",        MapType(StringType(), IntegerType()))
    .add("date",         DateType())
    .add("text_fr",         StringType())
    .add("likes",        IntegerType())
    .add("dislikes",     IntegerType())
    .add("top",          BooleanType())
    .add("code_commune", StringType()))

df = spark.createDataFrame(rdd, comment_schema)
df.show()

logging.info("⚙️ Extracted %d comments.", df.count())

# ─────────────────────────────
# 7  NLP COMPUTATION
# ─────────────────────────────
# from sparknlp.pretrained import PretrainedPipeline

# trans_pipe = PretrainedPipeline("translate_fr_en", lang="xx")

# df = df.withColumnRenamed("text", "text_fr")  
# df_alias = df.withColumn("text", F.col("text_fr"))

# df_en = (trans_pipe.transform(df_alias)
#          .withColumn("text_en", F.col("translation.result").getItem(0)) 
#          .drop("translation", "text"))


# sent_pipe = PretrainedPipeline("analyze_sentimentdl_use_twitter", lang="en")

# sent_df = (sent_pipe
#            .transform(df_en.select("*", F.col("text_en").alias("text")))  
#            .withColumn("sentiment", F.col("sentiment").getItem(0))
#            .drop("document", "token", "sentence_embeddings",
#                  "sentiment_metadata", "text_en"))

# df = sent_df

# ─────────────────────────────
# 8  Stop word Computation
# ─────────────────────────────
from stop_words import get_stop_words

stop_words_fr = get_stop_words("fr")
b_stop = spark.sparkContext.broadcast(stop_words_fr)

token_re = re.compile(r"[A-Za-zÀ-ÿ]{3,}")

@F.udf(returnType="array<string>")
def tokenize(txt):
    return [w.lower() for w in token_re.findall(txt or "")
            if w.lower() not in b_stop.value]
    
df_tok = df.withColumn("tokens", tokenize("text_fr"))

top_words = (df_tok
    .select(F.explode("tokens").alias("token"))
    .groupBy("token").count()
    .orderBy(F.desc("count")).limit(20))


top_words.show(truncate=False)

# ─────────────────────────────
# 9   Write to Elasticsearch
# ─────────────────────────────
logging.info("💾 Registery in Elastisearch database")
es_options = {
    "es.nodes"       : ES_NODES,
    "es.port"        : "9200",
    "es.nodes.wan.only": "true",
    "es.mapping.id"  : "comment_id",
    "es.resource"    : "city-comments-v2"
}

if ES_USER and ES_PASSWORD:          
    es_options["es.net.http.auth.user"]     = ES_USER
    es_options["es.net.http.auth.pass"]     = ES_PASSWORD

df_out = (df_tok
    # 1) Date ISO 'yyyy-MM-dd' pour coller au mapping existant
    .withColumn("date", F.date_format("date", "yyyy-MM-dd"))
)

(df_out.write
   .format("org.elasticsearch.spark.sql")
   .options(**es_options)
   .mode("append")
   .save())

logging.info("✅ Indexed into Elasticsearch index %s", ES_INDEX)
spark.stop()
