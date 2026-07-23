-- Staging model: one row per NYC green taxi trip (January 2024).
-- Renames source columns, adds derived columns, and filters bad rows.
-- Downstream: fct_daily_borough_stats joins this to stg_zones.

SELECT
    pickup_datetime,
    pickup_location_id,
    fare_amount,
    tip_amount,
    trip_distance,
    {{ safe_divide('tip_amount', 'fare_amount') }} AS tip_pct

FROM {{ source('airflow_taxi', 'raw_trips') }}

WHERE
    pickup_location_id IS NOT NULL
    AND fare_amount >= 0
