#!/usr/bin/env python
"""
City-Comments Sentiment ETL — OpenAI version
-------------------------------------------
1. Charge dans Spark tous les commentaires dépourvus du champ `sentiment`.
2. Chaque partition appelle OpenAI GPT-4o-mini pour renvoyer « positive » ou « negative ».
3. Le résultat est ré-injecté dans Elasticsearch via le connecteur ES-Hadoop.
"""
import os, logging, textwrap, backoff
import pyspark.sql.functions as F
from pyspark.sql import SparkSession, Row
from openai import OpenAI, RateLimitError

# ─────────────────────────────
# 0. Paramètres
# ─────────────────────────────
ES_NODES        = os.getenv("ES_NODES", "es01:9200")
ES_USER         = os.getenv("ES_USER", "elastic")
ES_PASSWORD     = os.getenv("ES_PASSWORD", "password123")
ES_INDEX_SOURCE = os.getenv("ES_INDEX_SOURCE", "city-comments-*")
ES_INDEX_TARGET = os.getenv("ES_INDEX_TARGET", "city-comments-v2")

SPARK_MASTER    = os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077")
EXECUTORS       = int(os.getenv("SPARK_EXECUTORS", "2"))
EXEC_CORES      = int(os.getenv("SPARK_EXECUTOR_CORES", "4"))
EXEC_MEMORY     = os.getenv("SPARK_EXECUTOR_MEMORY", "14g")
SHUFFLE_PARTS   = int(os.getenv("SPARK_SHUFFLE_PARTITIONS", "200"))

OPENAI_MODEL    = "gpt-4o-mini"
SYSTEM_PROMPT   = textwrap.dedent("""
    Tu es un classificateur de sentiment français.
    Retourne exactement : positive ou negative
""").strip()

# ─────────────────────────────
# 1. Logging
# ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
)
log = logging.getLogger("city-comments-etl")

# ─────────────────────────────
# 2. SparkSession
# ─────────────────────────────
log.info("⚙️  Creating SparkSession (master=%s)…", SPARK_MASTER)
spark = (
    SparkSession.builder
    .appName("CityCommentsSentiment-OpenAI")
    .master(SPARK_MASTER)
    .config("spark.executor.instances", EXECUTORS)
    .config("spark.executor.cores", EXEC_CORES)
    .config("spark.executor.memory", EXEC_MEMORY)
    .config("spark.sql.shuffle.partitions", SHUFFLE_PARTS)
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    .config("spark.kryoserializer.buffer.max", "1024m")
    # Elasticsearch connector
    .config("es.nodes", ES_NODES.split(",")[0].split(":")[0])
    .config("es.port",  ES_NODES.split(":")[-1])
    .config("es.nodes.wan.only", "true")
    .config("es.net.http.auth.user", ES_USER)
    .config("es.net.http.auth.pass", ES_PASSWORD)
    .getOrCreate()
)

# ─────────────────────────────
# 3. Charger les commentaires à taguer
# ─────────────────────────────
log.info("📥 Lecture depuis '%s'…", ES_INDEX_SOURCE)
comments_df = (
    spark.read.format("es")
    .option("es.read.metadata", "true")
    .option("es.read.metadata.field", "_meta")
    .option("es.read.field.include", "comment_id,text_fr,sentiment")
    .load(ES_INDEX_SOURCE)
    .where(F.col("sentiment").isNull())
    .select(
        F.col("_meta._id").alias("doc_id"),
        F.col("_meta._index").alias("idx"),
        "comment_id",
        F.col("text_fr").alias("text")
    )
    .repartition(SHUFFLE_PARTS)
    .cache()
)

to_score = comments_df.count()
log.info("🔍 %s commentaires à classifier", to_score)
if to_score == 0:
    spark.stop()
    quit()

# ─────────────────────────────
# 4. Fonction de classification par partition
# ─────────────────────────────
def classify_partition(rows):
    """
    Exécuté sur chaque executor.  Un seul client OpenAI par partition.
    Rend des Row(comment_id, idx, sentiment)
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    @backoff.on_exception(backoff.expo, RateLimitError, max_tries=5)
    def classify(text: str) -> str:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": text[:4000]},
            ],
        )
        return resp.choices[0].message.content.strip().lower()

    for r in rows:
        yield Row(
            comment_id=r["comment_id"],
            idx=r["idx"],
            sentiment=classify(r["text"] or "")
        )

# ─────────────────────────────
# 5. Exécuter la classification
# ─────────────────────────────
log.info("🧠 Appels OpenAI en parallèle …")
scored_df = comments_df.rdd.mapPartitions(classify_partition).toDF().cache()

# ─────────────────────────────
# 6. Upsert vers Elasticsearch
# ─────────────────────────────
log.info("💾 Upsert dans '%s' …", ES_INDEX_TARGET)
(
    scored_df.write
    .format("es")
    .option("es.resource.write", "{idx}")     # ré-injecte dans l’index source
    .option("es.mapping.id", "comment_id")
    .option("es.write.operation", "update")   # upsert partiel
    .option("es.mapping.exclude", "idx")      # idx ne va pas dans _source
    .mode("append")
    .save(ES_INDEX_TARGET)
)

log.info("✅ Terminé — %s documents mis à jour", to_score)
spark.stop()
