Steam Game Analytics - Data Warehouse Project
Overview
This project builds a complete data warehouse system for analyzing Steam game data, targeting indie game developers and small publishers who lack market research resources. The system processes over 134,000 games from the Steam Games Dataset (Kaggle) and answers three core business questions to support data-driven decision making before starting game development.

The architecture follows Kimball Data Warehouse principles with modern adaptations for the current data engineering landscape. The pipeline transforms raw JSON data into a star schema optimized for analytical queries.

Business Questions
Which game genre is growing and which is saturated?

What is the optimal price point for launch?

Which genre has the largest actual player base?

System Architecture
The data pipeline flows through the following layers:

Raw JSON Data (Kaggle) → MongoDB (Raw Layer) → PySpark (Flatten & Clean) → Parquet (Staging) → dbt (Transform) → DuckDB (Star Schema Marts)

This architecture separates concerns clearly: raw storage, ETL processing, staging, business transformation, and serving layer each have distinct responsibilities.

Technology Stack
MongoDB 7.0 serves as the raw data layer, storing the complete original JSON documents. PySpark 3.5.3 handles the initial ETL process, connecting to MongoDB via the MongoDB Spark Connector (2.12:10.4.0). The flattened data is written to Parquet files as staging.

dbt 1.11.12 with the dbt-duckdb adapter performs the business transformation layer, building the star schema. DuckDB serves as the analytical database, providing fast local query execution without cloud dependencies.

Apache Airflow orchestrates the entire pipeline, with DAGs that trigger the ETL process and dbt runs sequentially. Logging captures execution details across all pipeline components.

Pipeline Details
Raw Layer - MongoDB
The raw JSON file is imported into MongoDB using mongoimport, creating the raw_games collection. Each document retains the complete original game data without transformation.

ETL Layer - PySpark
PySpark reads from MongoDB with a projection that selects only the 8 required fields: _id, name, genres, price, positive, negative, estimated_owners, and release_date. The data undergoes type casting and filtering to remove games that have been removed from the Steam store. The processed data is written to Parquet format for staging.

Key optimizations include increasing driver and executor memory to 4GB and using MongoSinglePartitioner to avoid Out Of Memory errors.

Transformation Layer - dbt
Six models build the star schema:

stg_game creates the staging table and adds release_year derived from release_date. dim_genre extracts distinct genres from the genres array. dim_owners_tier provides a hard-coded dimension with six ownership tiers ranging from No Data to Blockbuster. dim_game selects descriptive fields from staging. bridge_game_genre maps the many-to-many relationship between games and genres. fact_game_stats creates the fact table with tier_id mapped from estimated_owners.

The schema includes 6 tables: 1 fact table, 3 dimension tables, and 1 bridge table.

Serving Layer - DuckDB
DuckDB stores all star schema tables in a single local file. This provides fast analytical queries without cloud costs or network latency.

Data Model
Grain: one row in fact_game_stats represents one game.

Dimension Tables:

dim_game: game attributes including name, price, release_year

dim_genre: unique genre names with surrogate keys

dim_owners_tier: six tiers from No Data to Blockbuster with range boundaries

Bridge Table:

bridge_game_genre: maps game_id to genre_id for many-to-many relationships

Fact Table:

fact_game_stats: fact_id, game_id, tier_id, positive reviews, negative reviews

Query Examples
Business Question 1 - Genre Growth Trend
Join fact_game_stats with dim_game, bridge_game_genre, and dim_genre. Group by genre_name and release_year to count games per genre annually. This reveals which genres are growing and which are saturated.

Business Question 2 - Price Optimization
Join fact_game_stats with dim_game and dim_owners_tier. Group by price to analyze average positive review rate and estimated owner tiers. This identifies the price range with best review performance and highest ownership.

Business Question 3 - Player Demand by Genre
Join fact_game_stats with dim_owners_tier, bridge_game_genre, and dim_genre. Aggregate estimated owners by genre to identify which genres have the largest player bases.

Setup Instructions
Install Python dependencies from requirements.txt

Import raw JSON data into MongoDB using import_to_mongo.py

Run PySpark ETL script to generate Parquet staging files

Execute dbt run to build the star schema

Run dbt test to validate data quality

Connect to steam_analytics.duckdb for analysis

Additional Features
Logging is implemented for both ETL scripts, writing timestamped log files to the logs directory. Airflow orchestration manages the pipeline with three tasks: ETL execution, dbt run, and dbt test. The system can be fully reset by removing the DuckDB file and processed Parquet data.

Project Structure
data/ contains both raw and processed data. models/ holds dbt SQL models organized into staging and marts directories. src/ contains Python ETL scripts. dags/ stores Airflow DAGs. Configuration files include dbt_project.yml and docker-compose.yaml.
