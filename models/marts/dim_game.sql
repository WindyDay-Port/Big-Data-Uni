{{
    config(
        materialized='table',
        dataset='steam_marts'
    )
}}

SELECT
    game_id,
    name,
    price,
    release_year
FROM {{ ref('stg_game') }}