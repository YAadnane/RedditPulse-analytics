from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace, udf, expr
from pyspark.sql.types import StringType, FloatType
import sys
import os

# Configuration Spark
spark = (
    SparkSession.builder.appName("RedditProcessing")
    .config("spark.jars.packages", "org.postgresql:postgresql:42.2.18")
    .getOrCreate()
)


def clean_text(text):
    if text is None:
        return ""
    # Simple cleaning example
    return text.lower().strip()


def analyze_sentiment(text):
    # Utilisation de TextBlob pour une vraie analyse de sentiment
    # Retourne un score entre -1.0 (Négatif) et 1.0 (Positif)
    try:
        from textblob import TextBlob

        if not text:
            return 0.0
        return float(TextBlob(text).sentiment.polarity)
    except ImportError:
        # Fallback si TextBlob n'est pas installé
        if not text:
            return 0.0
        return 0.5 if "good" in text else -0.5 if "bad" in text else 0.0
    except Exception:
        return 0.0


import traceback


def process_data(hdfs_dir, db_url, db_props):
    try:
        print(f"Lecture depuis le dossier HDFS : {hdfs_dir}")

        # --- TRAITEMENT DES POSTS ---
        posts_path = f"{hdfs_dir}/posts.csv"
        print(f"Lecture des Posts ({posts_path})...")

        df_posts = (
            spark.read.option("header", "true")
            .option("multiLine", "true")
            .option("escape", '"')
            .csv(posts_path)
        )

        if df_posts.count() > 0:
            clean_udf = udf(clean_text, StringType())
            sent_udf = udf(analyze_sentiment, FloatType())

            df_posts_clean = (
                df_posts.withColumn("clean_body", clean_udf(col("body")))
                .withColumn("sentiment", sent_udf(col("clean_body")))
                .withColumn("score", expr("try_cast(score as float)"))
                .withColumn("num_comments", expr("try_cast(num_comments as int)"))
            )

            # Stats par subreddit
            df_stats = df_posts_clean.groupBy("subreddit").avg(
                "score", "sentiment", "num_comments"
            )

            print("Écriture Posts dans PostgreSQL...")
            df_posts_clean.write.jdbc(
                url=db_url, table="reddit_posts", mode="append", properties=db_props
            )
            df_stats.write.jdbc(
                url=db_url, table="reddit_stats", mode="overwrite", properties=db_props
            )
        else:
            print("Aucun post trouvé.")

        # --- TRAITEMENT DES COMMENTAIRES ---
        comments_path = f"{hdfs_dir}/comments.csv"
        print(f"Lecture des Commentaires ({comments_path})...")

        # On utilise try/except ou on vérifie si le fichier existe (difficile en pur Spark sans API Hadoop)
        # On suppose que le fichier existe si l'extraction a marché.
        try:
            df_comments = (
                spark.read.option("header", "true")
                .option("multiLine", "true")
                .option("escape", '"')
                .csv(comments_path)
            )

            if df_comments.count() > 0:
                df_comments_clean = (
                    df_comments.withColumn("clean_body", clean_udf(col("body")))
                    .withColumn("sentiment", sent_udf(col("clean_body")))
                    .withColumn("score", expr("try_cast(score as float)"))
                )

                print("Écriture Commentaires dans PostgreSQL...")
                df_comments_clean.write.jdbc(
                    url=db_url,
                    table="reddit_comments",
                    mode="append",
                    properties=db_props,
                )
            else:
                print("Fichier commentaires vide.")
        except Exception as e:
            print(f"Pas de fichier commentaires ou erreur lecture: {e}")

        print("Traitement terminé avec succès.")

    except Exception as e:
        print("ERREUR CRITIQUE DANS LE JOB SPARK :")
        traceback.print_exc()
        with open("/app/spark_error.log", "w") as f:
            f.write("ERREUR SPARK:\n")
            traceback.print_exc(file=f)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: spark_processor.py <hdfs_directory>")
        sys.exit(1)

    hdfs_dir = sys.argv[1]

    # Config Postgres
    db_url = "jdbc:postgresql://postgres_db:5432/reddit_db"
    db_props = {
        "user": "admin",
        "password": "password",
        "driver": "org.postgresql.Driver",
    }

    process_data(hdfs_dir, db_url, db_props)
    spark.stop()
