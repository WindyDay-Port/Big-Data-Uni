{{
    config(
        materialized='table',
        dataset='steam_marts'
    )
}}

WITH mapped AS (
    SELECT
        game_id,
        positive,
        negative,
        estimated_owners,
        CASE 
            WHEN estimated_owners = '0 - 0' THEN 1
            WHEN estimated_owners = '0 - 20000' THEN 2
            WHEN estimated_owners = '20000 - 50000' THEN 3
            WHEN estimated_owners = '50000 - 100000' THEN 4
            WHEN estimated_owners IN ('100000 - 200000', '200000 - 500000') THEN 5
            WHEN estimated_owners IN ('500000 - 1000000', '1000000 - 2000000', 
                                      '2000000 - 5000000', '5000000 - 10000000',
                                      '10000000 - 20000000', '20000000 - 50000000',
                                      '50000000 - 100000000', '100000000 - 200000000') THEN 6
            ELSE 1  -- fallback
        END AS tier_id
    FROM {{ ref('stg_game') }}
)
SELECT
    ROW_NUMBER() OVER (ORDER BY game_id) AS fact_id,
    game_id,
    tier_id,
    positive,
    negative
FROM mapped