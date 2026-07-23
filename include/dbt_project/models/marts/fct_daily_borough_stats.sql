-- Mart: daily borough trip statistics.
-- Grain: one row per (pickup_borough, pickup_date).
-- Used to answer: trip volume, revenue, tipping behaviour, and distance profile
-- per borough per day for January 2024.

WITH trips AS (
    SELECT *
    FROM {{ ref('stg_trips') }}
),

zones AS (
    SELECT *
    FROM {{ ref('stg_zones') }}
)

SELECT
    z.borough AS pickup_borough,
    t.pickup_datetime::date AS pickup_date,
    COUNT(*) AS trip_count,
    SUM(t.fare_amount) AS total_fare,
    AVG(t.tip_pct) AS avg_tip_pct,
    AVG(t.trip_distance) AS avg_trip_distance

FROM trips t

INNER JOIN zones z
    ON t.pickup_location_id = z.location_id

GROUP BY
    z.borough,
    t.pickup_datetime::date
