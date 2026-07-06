import os
import time
import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date
from pyspark.sql.types import FloatType, IntegerType

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"etl_steam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler(log_filename)
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)

MONGODB_URI = "mongodb://localhost:27017/"

def create_spark_session():
    logger.info("Creating Spark session...")
    return SparkSession.builder \
        .appName("Steam ETL") \
        .config("spark.mongodb.read.connection.uri", MONGODB_URI) \
        .config("spark.jars.packages",
                "org.mongodb.spark:mongo-spark-connector_2.12:10.4.0") \
        .config("spark.driver.host", "127.0.0.1") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .config("spark.mongodb.input.partitioner", "MongoSinglePartitioner") \
        .getOrCreate()

def main():
    start_time = time.time()
    spark = create_spark_session()
    try:
        logger.info("Reading from MongoDB...")
        df = spark.read \
            .format("mongodb") \
            .option("uri", MONGODB_URI) \
            .option("database", "steam_db") \
            .option("collection", "raw_games") \
            .load()

        logger.info("Flattening...")
        df_flat = df.select(
            col("_id").alias("game_id"),
            col("name"),
            col("genres"),
            col("price").cast(FloatType()),
            col("positive").cast(IntegerType()),
            col("negative").cast(IntegerType()),
            col("estimated_owners"),
            to_date(col("release_date"), "MMM d, yyyy").alias("release_date")
        ).filter(col("name").isNotNull())

        logger.info("Filtering removed games...")
        df_clean = df_flat.filter(~col("name").contains("(Removed from steam store)"))
        count = df_clean.count()
        logger.info(f"Records to write: {count}")

        output_path = "data/processed/stg_game.parquet"
        logger.info(f"Writing to Parquet: {output_path}")
        df_clean.write.mode("overwrite").parquet(output_path)

        elapsed = time.time() - start_time
        logger.info(f"ETL completed successfully in {elapsed:.2f} seconds")
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        spark.stop()
        logger.info("Spark session stopped")

if __name__ == "__main__":
    main()