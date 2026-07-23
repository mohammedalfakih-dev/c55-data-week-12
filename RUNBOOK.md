# RUNBOOK

## How to trigger the DAG manually

1. Start the local Astro environment:

```bash
astro dev start
```

2. Confirm that `include/dbt_project/profiles.yml` exists. For a fresh clone,
   copy it from `include/dbt_project/profiles.yml.example`.
3. Confirm that the `azure_pg` Airflow connection exists.
4. Open the Airflow UI and unpause `taxi_pipeline`.
5. Trigger a historical month whose TLC parquet file exists:

```bash
astro dev run dags trigger taxi_pipeline \
  --logical-date 2024-08-01T00:00:00+00:00
```

6. In the Airflow UI, confirm that `ingest_taxi_month`, `dbt_run`, and `dbt_test` finish successfully.

## How to run a backfill

Run the seven monthly partitions sequentially to prevent concurrent dbt runs:

```bash
astro dev run backfill create \
  --dag-id taxi_pipeline \
  --from-date 2024-01-01 \
  --to-date 2024-07-31 \
  --max-active-runs 1
```

To rerun completed partitions for an idempotency check:

```bash
astro dev run backfill create \
  --dag-id taxi_pipeline \
  --from-date 2024-01-01 \
  --to-date 2024-07-31 \
  --max-active-runs 1 \
  --reprocess-behavior completed
```

## How to inspect task logs

1. Open `taxi_pipeline` in the Airflow UI.
2. Select **Runs** and open the required DAG run.
3. Select the failed or successful task.
4. Open the **Logs** tab.
5. Read the final error message and traceback before retrying or clearing the task.

## Top 3 likely failures and first response

1. **TLC parquet file is unavailable** — `ingest_taxi_month` reports an HTTP error and retries. Check the logical date in the run. Trigger a historical month with an available parquet file instead of a future or unavailable month.
2. **PostgreSQL connection fails** — tasks report that `azure_pg` is missing or authentication failed. Check the `azure_pg` connection in Airflow, including its host, database, login, port, and `sslmode=require`. Never commit its password.
3. **dbt run or test fails** — `dbt_run` or `dbt_test` turns red. Inspect its log, confirm that the project exists under `include/dbt_project`, and check `profiles.yml`, source names, and `PG_SCHEMA`. Keep dbt running through the configured `uvx --python 3.11` command.
