{{
    config(
        materialized='table'
    )
}}

SELECT
    game_id,
    name,
    genres,
    price,
    positive,
    negative,
    estimated_owners,
    release_date,
    EXTRACT(YEAR FROM release_date) AS release_year
FROM read_parquet('data/processed/stg_game.parquet')
WHERE name IS NOT NULL
  AND NOT CONTAINS(LOWER(name), '(removed from steam store)')
  AND estimated_owners != '0 - 0'