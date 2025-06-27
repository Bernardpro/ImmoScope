#!/usr/bin/env python
"""
City‑Comments Sentiment ETL (driver‑side pipelines)
==================================================

This version removes the Pandas UDF that was failing with
`AttributeError: Cannot load _jvm from SparkContext` inside Arrow workers.
Instead we rely on **Spark NLP PipelineModels** whose `transform()` method
runs natively on the Spark executors (JVM side). The workflow is now:

1. Read French comments missing the `sentiment` field from Elasticsearch.
2. Translate FR→EN with the pre‑trained pipeline **`translate_fr_en`**.
3. Feed the English text to **`analyze_sentimentdl_use_twitter`**.
4. Extract label + positive/negative scores and upsert them back into ES.

Because everything is expressed as DataFrame transformations, the job
remains fully distributed and Arrow/PyArrow is no longer required.
"""

import os
import logging

import pyspark.sql.functions as F
from pyspark.sql import SparkSession
from sparknlp.pretrained import PretrainedPipeline

# ─────────────────────────────
# 0. Logging
# ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger("city-comments-etl")

# ─────────────────────────────
# 1. Environment
# ─────────────────────────────
ES_NODES        = os.getenv("ES_NODES", "es01:9200")
ES_USER         = os.getenv("ES_USER", "elastic")
ES_PASSWORD     = os.getenv("ES_PASSWORD", "password123")
ES_INDEX_SOURCE = os.getenv("ES_INDEX_SOURCE", "city-comments-*")
ES_INDEX_TARGET = os.getenv("ES_INDEX_TARGET", "city-comments-v2")

SPARK_MASTER    = os.getenv("SPARK_MASTER_URL", "spark:spark-master:7077")
EXECUTORS       = os.getenv("SPARK_EXECUTORS", "2")
EXEC_CORES      = os.getenv("SPARK_EXECUTOR_CORES", "4")
EXEC_MEMORY     = os.getenv("SPARK_EXECUTOR_MEMORY", "14g")
SHUFFLE_PARTS   = os.getenv("SPARK_SHUFFLE_PARTITIONS", "200")

# ─────────────────────────────
# 2. Spark session
# ─────────────────────────────
logger.info("⚙️  Starting SparkSession (master=%s)…", SPARK_MASTER)

spark = (
    SparkSession.builder
    .appName("CityCommentsSentiment")
    .master(SPARK_MASTER)
    .config("spark.executor.instances", EXECUTORS)
    .config("spark.executor.cores", EXEC_CORES)
    .config("spark.executor.memory", EXEC_MEMORY)
    .config("spark.sql.shuffle.partitions", SHUFFLE_PARTS)
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    .config("spark.kryoserializer.buffer.max", "1024m")
    # Spark NLP cache
    .config("spark.jsl.settings.pretrained.cache_folder", "/tmp/sparknlp_cache")
    # Elasticsearch
    .config("es.nodes", ES_NODES.split(",")[0].split(":")[0])
    .config("es.port", ES_NODES.split(":")[-1])
    .config("es.nodes.wan.only", "true")
    .config("es.net.http.auth.user", ES_USER)
    .config("es.net.http.auth.pass", ES_PASSWORD)
    .getOrCreate()
)

# ─────────────────────────────
# 3. Read comments to score
# ─────────────────────────────
logger.info("📥 Loading comments from '%s'…", ES_INDEX_SOURCE)

comments_df = (
    spark.read.format("es")
    .option("es.read.field.include", "comment_id,text_fr,sentiment")
    .load(ES_INDEX_SOURCE)
    .where(F.col("sentiment").isNull())
    .select("comment_id", F.col("text_fr").alias("text"))
    .repartition(int(SHUFFLE_PARTS))
    .cache()
)

count_to_score = comments_df.count()
logger.info("🔍 %s comments to process", count_to_score)
if count_to_score == 0:
    logger.info("Nothing to do — exiting.")
    spark.stop()
    raise SystemExit

# ─────────────────────────────
# 4. Load pipelines once (driver) and broadcast to executors
# ─────────────────────────────
logger.info("📦 Loading Spark NLP pipelines…")
translator_pipe = PretrainedPipeline("translate_fr_en", lang="xx")
sentiment_pipe  = PretrainedPipeline("analyze_sentimentdl_use_twitter", lang="en")
logger.info("   ✨ Pipelines ready")

# ─────────────────────────────
# 5. Apply translation then sentiment
# ─────────────────────────────
logger.info("🧠 Translating FR→EN …")
translated_df = (
    translator_pipe
    .transform(comments_df)
    .select(
        "comment_id",
        F.col("translation.result")[0].alias("text_en")
    )
)

logger.info("🧠 Running sentiment analysis …")
scored_df = (
    sentiment_pipe
    .transform(translated_df.select("comment_id", F.col("text_en").alias("text")))
    .select(
        "comment_id",
        # first element of array<struct>, then its 'result'
        F.expr("sentiment[0].result").alias("sentiment_label"),
        F.expr("double(sentiment[0].metadata['positive'])").alias("sentiment_pos"),
        F.expr("double(sentiment[0].metadata['negative'])").alias("sentiment_neg"),
    )
)

# ─────────────────────────────
# 6. Write back to Elasticsearch
# ─────────────────────────────
translated_df.unpersist()
logger.info("💾 Upserting results into '%s' …", ES_INDEX_TARGET)
(
    scored_df.write
    .format("es")
    .option("es.mapping.id", "comment_id")
    .option("es.write.operation", "upsert")
    .option("es.batch.size.entries", "5000")
    .option("es.batch.size.bytes", "5mb")
    .option("es.batch.write.refresh", "false")
    .mode("append")
    .save(ES_INDEX_TARGET)
)

logger.info("✅ Finished. Indexed %s comments (UTC %s)", count_to_score)

spark.stop()
