#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
SPARK_HOME = Path("/opt/bitnami/spark")

JOB_SCRIPTS = {
    "logic-immo": [
        "spark-submit",
        
        f"{SPARK_HOME}/transform_html_data.py"
        ],
    "sentiment": [
        "spark-submit",
        "--master" ,       "local[*]",
        "--driver-memory", "10G",
        "--conf",          "spark.driver.memoryOverhead=2G",
        "--conf",          "spark.kryoserializer.buffer.max=1024m",
        "--packages",      "org.elasticsearch:elasticsearch-hadoop:9.0.2",
        
        f"{SPARK_HOME}/spark_sentiment.py"
        ],
    "comment": [
        SPARK_HOME / "bin" / "spark-submit",
        "--master" ,       "local[*]",
        "--driver-memory", "10G",
        "--conf",          "spark.driver.memoryOverhead=1G",
        "--conf",          "spark.kryoserializer.buffer.max=1024m",
        "--packages",      "org.elasticsearch:elasticsearch-hadoop:9.0.2",
        
        SPARK_HOME / "transform_comment.py"            
    ],
    "test" : ["spark-submit",f"{SPARK_HOME}/test.py"],
    "nlp" : [
        SPARK_HOME / "bin" /"spark-submit", 
        "--master" ,       "local[*]",
        "--driver-memory", "14G",
        "--conf",          "spark.driver.memoryOverhead=2G",
        "--conf",          "spark.kryoserializer.buffer.max=1024m",
        "--conf",          "spark.es.batch.size.bytes=2mb",
        "--conf",          "spark.es.batch.size.entries=500",
        "--packages",
        "org.elasticsearch:elasticsearch-hadoop:9.0.2,"
        "com.johnsnowlabs.nlp:spark-nlp_2.12:6.0.1", 
        f"{SPARK_HOME}/nlp.py"                 
    ]
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py [logic-immo|comment|test]")
        sys.exit(1)
    job = sys.argv[1]
    if job not in JOB_SCRIPTS:
        print(f"Job inconnu '{job}'. Valeurs possibles: {', '.join(JOB_SCRIPTS.keys())}.")
        sys.exit(1)
    script_path = JOB_SCRIPTS[job]
    print(f"Lancement du job Spark '{job}' via le script {script_path} ...")
    try:
        result = subprocess.run(
            [str(arg) for arg in script_path], check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Le job Spark a échoué avec le code de retour {e.returncode}.")
        sys.exit(e.returncode)
