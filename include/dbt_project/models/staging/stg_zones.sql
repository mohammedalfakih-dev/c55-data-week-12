-- Staging model: one row per TLC zone (265 zones).
-- Exposes location_id and borough for use as a lookup in the mart.

SELECT
    location_id,
    borough
FROM {{ source('nyc_taxi', 'raw_zones') }}
