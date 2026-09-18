from pathlib import Path
import subprocess
from datetime import timedelta

import pendulum
from airflow.sdk import DAG, task
from google.cloud import bigquery


PROJECT_DIR = Path("/opt/airflow/project")
RAW_DIR = PROJECT_DIR / "data" / "raw"

GCP_PROJECT_ID = "olist-ecommerce-dwh"
DWH_DATASET = "olist_dwh"

EXPECTED_FILES = {
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
}


@task
def check_source_files():
    """
    Kiểm tra đủ 9 file CSV nguồn trước khi chạy ETL.
    """
    existing_files = {
        path.name
        for path in RAW_DIR.glob("*.csv")
    }

    missing_files = EXPECTED_FILES - existing_files

    if missing_files:
        raise FileNotFoundError(
            f"Thiếu file nguồn: {sorted(missing_files)}"
        )

    print("SOURCE CHECK: PASS")
    print(f"Đã tìm thấy đủ {len(EXPECTED_FILES)} file CSV.")


@task
def run_etl_pipeline():
    """
    Chạy pipeline ETL + DWH hiện tại.
    """
    pipeline_file = PROJECT_DIR / "etl" / "pipeline.py"

    subprocess.run(
        ["python", str(pipeline_file)],
        cwd=str(PROJECT_DIR),
        check=True,
    )

    print("ETL + DWH PIPELINE: PASS")


@task
def verify_dwh():
    """
    Kiểm tra 8 bảng DWH tồn tại và có dữ liệu.
    """
    client = bigquery.Client(project=GCP_PROJECT_ID)

    tables = [
        "dim_customers",
        "dim_products",
        "dim_sellers",
        "dim_date",
        "fact_orders",
        "fact_order_items",
        "fact_payments",
        "fact_reviews",
    ]

    for table_name in tables:
        sql = f"""
        SELECT COUNT(*) AS row_count
        FROM `{GCP_PROJECT_ID}.{DWH_DATASET}.{table_name}`
        """

        result = list(client.query(sql).result())
        row_count = result[0]["row_count"]

        if row_count <= 0:
            raise ValueError(
                f"{table_name} không có dữ liệu."
            )

        print(
            f"DWH CHECK - {table_name}: "
            f"{row_count:,} dòng"
        )

    print("DWH VERIFY: PASS")


with DAG(
    dag_id="olist_etl_pipeline",

    description=(
        "Tự động hóa ETL và Data Warehouse "
        "cho dữ liệu Olist E-Commerce"
    ),

    start_date=pendulum.datetime(
        2026, 9, 1,
        tz="Asia/Ho_Chi_Minh",
    ),

    # Tự động chạy lúc 02:00 mỗi ngày
    schedule="0 2 * * *",

    catchup=False,

    # Không cho 2 lần pipeline chạy chồng nhau
    max_active_runs=1,

    default_args={
        "owner": "xuyen",
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
    },

    tags=[
        "olist",
        "etl",
        "bigquery",
        "data-warehouse",
    ],
) as dag:

    check = check_source_files()
    run_pipeline = run_etl_pipeline()
    verify = verify_dwh()

    check >> run_pipeline >> verify