from __future__ import annotations

import logging
from pathlib import Path

from google.cloud import bigquery


# CẤU HÌNH BIGQUERY


PROJECT_ID = "olist-ecommerce-dwh"

DATASET_ID = "olist_staging"

LOCATION = "US"



# ĐƯỜNG DẪN PROJECT

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# THƯ MỤC STAGING LOCAL


STAGING_DIR = (
    PROJECT_ROOT
    / "data"
    / "staging"
)

DERIVED_DIR = (
    STAGING_DIR
    / "derived"
)



# DANH SÁCH TABLE CẦN LOAD

STAGING_FILES = {

    "customers":
        STAGING_DIR / "customers.parquet",

    "geolocation":
        STAGING_DIR / "geolocation.parquet",

    "order_items":
        STAGING_DIR / "order_items.parquet",

    "payments":
        STAGING_DIR / "payments.parquet",

    "reviews":
        STAGING_DIR / "reviews.parquet",

    "orders":
        STAGING_DIR / "orders.parquet",

    "products":
        STAGING_DIR / "products.parquet",

    "sellers":
        STAGING_DIR / "sellers.parquet",

    "category_translation":
        STAGING_DIR / "category_translation.parquet",

    "geolocation_lookup":
        DERIVED_DIR / "geolocation_lookup.parquet",
}


# LOGGER


logger = logging.getLogger(__name__)



# TẠO BIGQUERY CLIENT

def create_bigquery_client() -> bigquery.Client:
    client = bigquery.Client(
        project=PROJECT_ID,
        location=LOCATION,
    )

    return client


# KIỂM TRA FILE STAGING LOCAL

def validate_staging_files() -> None:

    missing_files = []

    for table_name, file_path in STAGING_FILES.items():

        if not file_path.exists():

            missing_files.append(
                f"{table_name}: {file_path}"
            )

    if missing_files:

        message = (
            "Thiếu file Staging:\n"
            + "\n".join(missing_files)
        )

        raise FileNotFoundError(
            message
        )

    logger.info(
        "BIGQUERY INPUT CHECK - "
        "Tất cả file Staging đều tồn tại."
    )


# LOAD MỘT FILE PARQUET

def load_parquet_table(
    client: bigquery.Client,
    table_name: str,
    file_path: Path,
) -> int:

    table_id = (
        f"{PROJECT_ID}."
        f"{DATASET_ID}."
        f"{table_name}"
    )


    # Cấu hình Load Job

    job_config = bigquery.LoadJobConfig(

        source_format=(
            bigquery.SourceFormat.PARQUET
        ),

        write_disposition=(
            bigquery.WriteDisposition.WRITE_TRUNCATE
        ),
    )


    logger.info(
        "BIGQUERY LOAD - %-25s -> %s",
        table_name,
        table_id,
    )

    # Mở file Parquet và gửi lên BigQuery

    with file_path.open("rb") as source_file:

        load_job = client.load_table_from_file(
            source_file,
            table_id,
            job_config=job_config,
            location=LOCATION,
        )


    # Chờ BigQuery xử lý xong.

    load_job.result()


    # Lấy metadata table sau khi load.

    table = client.get_table(
        table_id
    )

    row_count = table.num_rows


    logger.info(
        "BIGQUERY VERIFY - %-25s PASS (%s dòng)",
        table_name,
        f"{row_count:,}",
    )

    return row_count



# LOAD TOÀN BỘ STAGING LÊN BIGQUERY

def load_all_staging_to_bigquery() -> bool:

    logger.info("=" * 70)
    logger.info(
        "BẮT ĐẦU LOAD STAGING -> BIGQUERY"
    )
    logger.info("=" * 70)


    # KIỂM TRA FILE LOCAL

    validate_staging_files()


    # KẾT NỐI BIGQUERY

    client = create_bigquery_client()

    logger.info(
        "BIGQUERY CONNECTION - Project: %s",
        PROJECT_ID,
    )

    logger.info(
        "BIGQUERY CONNECTION - Dataset: %s",
        DATASET_ID,
    )

    logger.info(
        "BIGQUERY CONNECTION - Location: %s",
        LOCATION,
    )

    # LOAD TỪNG TABLE

    for table_name, file_path in STAGING_FILES.items():

        load_parquet_table(
            client=client,
            table_name=table_name,
            file_path=file_path,
        )


    logger.info("=" * 70)
    logger.info(
        "LOAD STAGING -> BIGQUERY: SUCCESS"
    )
    logger.info(
        "Dữ liệu đã sẵn sàng "
        "cho bước xây dựng DWH."
    )
    logger.info("=" * 70)

    return True

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

    load_all_staging_to_bigquery()