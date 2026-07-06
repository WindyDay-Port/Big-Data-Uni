from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    'owner': 'windyday',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='steam_analytics_pipeline',
    default_args=default_args,
    description='This is just a demo',
    schedule='@daily',
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=['steam', 'etl', 'dbt'],
) as dag:

    start = EmptyOperator(task_id='start')

    run_etl = BashOperator(
        task_id='run_etl',
        bash_command='cd /opt/airflow/steam_project && python src/etl_steam.py',
    )

    run_dbt = BashOperator(
        task_id='run_dbt',
        bash_command='cd /opt/airflow/steam_project && dbt run',
    )

    run_dbt_test = BashOperator(
        task_id='run_dbt_test',
        bash_command='cd /opt/airflow/steam_project && dbt test',
    )

    end = EmptyOperator(task_id='end')

    start >> run_etl >> run_dbt >> run_dbt_test >> end