from __future__ import annotations

import logging
from pathlib import Path

from google.cloud import bigquery

# CẤU HÌNH BIGQUERY

PROJECT_ID = "olist-ecommerce-dwh"

LOCATION = "US"



# PROJECT ROOT

PROJECT_ROOT = Path(__file__).resolve().parents[1]



# THƯ MỤC SQL


DIMENSION_SQL_DIR = (
    PROJECT_ROOT
    / "sql"
    / "ddl"
    / "dimensions"
)

FACT_SQL_DIR = (
    PROJECT_ROOT
    / "sql"
    / "ddl"
    / "facts"
)


# DANH SÁCH DIMENSION

DIMENSION_SQL_FILES = [
    "dim_customers.sql",
    "dim_products.sql",
    "dim_sellers.sql",
    "dim_date.sql",
]



# DANH SÁCH FACT

FACT_SQL_FILES = [
    "fact_orders.sql",
    "fact_order_items.sql",
    "fact_payments.sql",
    "fact_reviews.sql",
]

# LOGGER

logger = logging.getLogger(__name__)

# BIGQUERY CLIENT


def create_bigquery_client() -> bigquery.Client:

    return bigquery.Client(
        project=PROJECT_ID,
        location=LOCATION,
    )



# ĐỌC FILE SQL

def read_sql_file(
    file_path: Path
) -> str:

    if not file_path.exists():

        raise FileNotFoundError(
            f"Không tìm thấy SQL file: {file_path}"
        )

    return file_path.read_text(
        encoding="utf-8"
    )


# CHẠY MỘT FILE SQL

def execute_sql_file(
    client: bigquery.Client,
    file_path: Path,
) -> None:

    logger.info(
        "Đang chạy SQL: %s",
        file_path.name,
    )

    sql = read_sql_file(
        file_path
    )

    query_job = client.query(
        sql,
        location=LOCATION,
    )

    # Chờ BigQuery chạy hoàn tất.
    query_job.result()

    logger.info(
        "SQL SUCCESS: %s",
        file_path.name,
    )


# BUILD DIMENSIONS

def build_dimensions(
    client: bigquery.Client
) -> None:

    logger.info("=" * 70)
    logger.info("BẮT ĐẦU BUILD DIMENSIONS")
    logger.info("=" * 70)

    for file_name in DIMENSION_SQL_FILES:

        file_path = (
            DIMENSION_SQL_DIR
            / file_name
        )

        execute_sql_file(
            client=client,
            file_path=file_path,
        )

    logger.info("=" * 70)
    logger.info("BUILD DIMENSIONS: SUCCESS")
    logger.info("=" * 70)


# BUILD FACTS

def build_facts(
    client: bigquery.Client
) -> None:

    logger.info("=" * 70)
    logger.info("BẮT ĐẦU BUILD FACTS")
    logger.info("=" * 70)

    for file_name in FACT_SQL_FILES:

        file_path = (
            FACT_SQL_DIR
            / file_name
        )

        execute_sql_file(
            client=client,
            file_path=file_path,
        )

    logger.info("=" * 70)
    logger.info("BUILD FACTS: SUCCESS")
    logger.info("=" * 70)


# BUILD TOÀN BỘ DWH

def build_dwh() -> bool:

    logger.info("=" * 70)
    logger.info("BẮT ĐẦU BUILD DATA WAREHOUSE")
    logger.info("=" * 70)

    client = create_bigquery_client()

    logger.info(
        "BigQuery Project: %s",
        PROJECT_ID,
    )

    # Dimension phải tạo trước Fact.
    build_dimensions(
        client
    )

    # Fact dùng Surrogate Key từ Dimension.
    build_facts(
        client
    )

    logger.info("=" * 70)
    logger.info("BUILD DATA WAREHOUSE: SUCCESS")
    logger.info("=" * 70)

    return True


# TEST RIÊNG FILE

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    build_dwh()