{{
    config(
        materialized='table',
        dataset='steam_marts'
    )
}}

SELECT 
    1 AS tier_id,
    'No Data' AS tier_label,
    0 AS range_min,
    0 AS range_max
UNION ALL
SELECT 
    2 AS tier_id,
    'Niche' AS tier_label,
    0 AS range_min,
    20000 AS range_max
UNION ALL
SELECT 
    3 AS tier_id,
    'Small' AS tier_label,
    20000 AS range_min,
    50000 AS range_max
UNION ALL
SELECT 
    4 AS tier_id,
    'Medium' AS tier_label,
    50000 AS range_min,
    100000 AS range_max
UNION ALL
SELECT 
    5 AS tier_id,
    'Large' AS tier_label,
    100000 AS range_min,
    500000 AS range_max
UNION ALL
SELECT 
    6 AS tier_id,
    'Blockbuster' AS tier_label,
    500000 AS range_min,
    200000000 AS range_max
ORDER BY tier_id