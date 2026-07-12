{{
    config(
        materialized='table'
    )
}}

WITH genre_list AS (
    SELECT DISTINCT CAST(genre AS VARCHAR) AS genre_name
    FROM {{ ref('stg_game') }}
    CROSS JOIN UNNEST(genres) AS t(genre)
    WHERE genres IS NOT NULL 
      AND ARRAY_LENGTH(genres) > 0 
      AND CAST(genre AS VARCHAR) != ''
)
SELECT
    ROW_NUMBER() OVER (ORDER BY genre_name) AS genre_id,
    genre_name
FROM genre_list
ORDER BY genre_id