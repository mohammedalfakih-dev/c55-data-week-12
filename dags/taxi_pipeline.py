import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task
from sqlalchemy import text


STUDENT = os.environ.get("AIRFLOW_STUDENT") or Path(__file__).parent.name
SCHEMA = f"airflow_{STUDENT}"
TLC_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def find_dbt_dir() -> str:
    """Return the mounted dbt project path."""
    for candidate in (
        "/usr/local/airflow/include/dbt_project",
        "/opt/airflow/include/dbt_project",
    ):
        if Path(candidate).is_dir():
            return candidate

    return "/usr/local/airflow/include/dbt_project"


DBT_DIR = find_dbt_dir()
DBT_COMMAND = "uvx --python 3.11 --from dbt-postgres==1.10.2 dbt"

DBT_ENV = {
    "PG_HOST": "{{ conn.azure_pg.host }}",
    "PG_USER": "{{ conn.azure_pg.login }}",
    "PG_PASSWORD": "{{ conn.azure_pg.password }}",
    "PG_DBNAME": "{{ conn.azure_pg.schema }}",
    "PG_SCHEMA": SCHEMA,
}


@dag(
    dag_id="taxi_pipeline",
    schedule="@monthly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["week12"],
)
def taxi_pipeline():
    @task
    def ingest_taxi_month(ds: str) -> int:
        """Load one logical month into the personal raw_trips table."""
        year_month = ds[:7]
        month_start = pd.Timestamp(f"{year_month}-01")
        next_month = month_start + pd.DateOffset(months=1)

        url = f"{TLC_BASE}/green_tripdata_{year_month}.parquet"
        trips = pd.read_parquet(url)

        trips = trips[
            [
                "lpep_pickup_datetime",
                "PULocationID",
                "fare_amount",
                "tip_amount",
                "trip_distance",
            ]
        ].rename(
            columns={
                "lpep_pickup_datetime": "pickup_datetime",
                "PULocationID": "pickup_location_id",
            }
        )

        trips = trips[
            (trips["pickup_datetime"] >= month_start)
            & (trips["pickup_datetime"] < next_month)
        ]

        hook = PostgresHook(postgres_conn_id="azure_pg")
        engine = hook.get_sqlalchemy_engine()

        with engine.begin() as connection:
            connection.execute(
                text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
            )

            trips.head(0).to_sql(
                "raw_trips",
                connection,
                schema=SCHEMA,
                if_exists="append",
                index=False,
            )

            connection.execute(
                text(
                    f'DELETE FROM "{SCHEMA}"."raw_trips" '
                    "WHERE pickup_datetime >= :month_start "
                    "AND pickup_datetime < :next_month"
                ),
                {
                    "month_start": month_start.to_pydatetime(),
                    "next_month": next_month.to_pydatetime(),
                },
            )

            trips.to_sql(
                "raw_trips",
                connection,
                schema=SCHEMA,
                if_exists="append",
                index=False,
                chunksize=1000,
            )

        return len(trips)

    ingest = ingest_taxi_month(ds="{{ ds }}")

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"{DBT_COMMAND} deps "
            f"--project-dir {DBT_DIR} "
            f"--profiles-dir {DBT_DIR} && "
            f"{DBT_COMMAND} run "
            f"--project-dir {DBT_DIR} "
            f"--profiles-dir {DBT_DIR}"
        ),
        env=DBT_ENV,
        append_env=True,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"{DBT_COMMAND} test "
            f"--project-dir {DBT_DIR} "
            f"--profiles-dir {DBT_DIR}"
        ),
        env=DBT_ENV,
        append_env=True,
    )
    ingest >> dbt_run >> dbt_test

taxi_pipeline()