{{
    config(
        materialized='table'
    )
}}

SELECT
    s.game_id,
    dg.genre_id
FROM {{ ref('stg_game') }} s
CROSS JOIN UNNEST(s.genres) AS genre
INNER JOIN {{ ref('dim_genre') }} dg 
    ON CAST(genre AS VARCHAR) = dg.genre_name
WHERE s.genres IS NOT NULL 
  AND ARRAY_LENGTH(s.genres) > 0 
  AND CAST(genre AS VARCHAR) != ''