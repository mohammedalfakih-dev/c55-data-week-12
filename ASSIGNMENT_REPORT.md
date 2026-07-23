# Assignment report

## Schedule choice and reason

The DAG uses @monthly because the NYC green-taxi source files and ingestion logic are partitioned by month. A daily schedule would unnecessarily process the same monthly file repeatedly. Normal catchup is disabled with catchup=False.

## Task dependency graph

The tasks run in this strict order:

ingest_taxi_month -> dbt_run -> dbt_test

Ingestion must finish before dbt transforms the data, and the models must build successfully before their tests run. A failed task therefore prevents downstream tasks from processing incomplete data.

## dbt project used

I copied my Week 10 dbt project into include/dbt_project/. Airflow runs it with uvx --python 3.11 so dbt works with the Astro image.

## One debugging case I resolved

The shared Airflow ingestion task failed with permission denied for schema airflow_mohammedalfakih. I found the cause in the task log and reported the shared connection problem to the teacher. The shared Airflow connection was corrected, and the teacher reran the DAG. ingest_taxi_month, dbt_run, and dbt_test then completed successfully.

## Parameterized execution

Airflow passes {{ ds }} to ingest_taxi_month. The task takes the year and month from this logical date and uses it to select the parquet URL, filter the rows, and delete and replace only that month in raw_trips. It does not use datetime.now().

## Backfill and idempotency

I ran the initial seven-month backfill with:

astro dev run backfill create \
 --dag-id taxi_pipeline \
 --from-date 2024-01-01 \
 --to-date 2024-07-31 \
 --max-active-runs 1

I recorded these row counts:

2024-01: 56,549

2024-02: 53,571

2024-03: 57,447

2024-04: 56,467

2024-05: 60,994

2024-06: 54,735

2024-07: 51,811

I then reran the same range with:

astro dev run backfill create \
 --dag-id taxi_pipeline \
 --from-date 2024-01-01 \
 --to-date 2024-07-31 \
 --max-active-runs 1 \
 --reprocess-behavior completed

All seven reruns succeeded. The monthly counts remained identical, proving that rerunning a partition does not create duplicate rows.

## Shared Airflow deployment

Merged deployment PR: https://github.com/lassebenni/c55-shared-airflow/pull/5

The deployed DAG is named mohammedalfakih_taxi_pipeline and tagged student:mohammedalfakih.

Evidence:

- Successful shared run: `screenshots/shared-airflow-green.png`
- Shared DAG filtered by student tag: `screenshots/shared-airflow-tag-filter.png`
- Local successful run: `screenshots/airflow-ui.png`
- DAG dependency graph: `screenshots/dag-graph.png`
- Task log snippet: `screenshots/ingest-log.png`
- Backfill evidence: `screenshots/backfill-green.png`
- Idempotency rerun: `screenshots/backfill-rerun-green.png`
- Row counts before rerun: `screenshots/idempotency-before.png`
- Row counts after rerun: `screenshots/idempotency-after.png`
