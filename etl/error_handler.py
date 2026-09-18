from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from google.cloud import bigquery


logger = logging.getLogger(__name__)


# PROJECT / BIGQUERY CONFIGURATION

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ERROR_DIR = PROJECT_ROOT / "data" / "error"

PROJECT_ID = "olist-ecommerce-dwh"
ERROR_DATASET_ID = "olist_error"
LOCATION = "US"

VALIDATION_ERRORS_TABLE = "validation_errors"
ERROR_RECORDS_TABLE = "error_records"
DATA_QUALITY_ISSUES_TABLE = "data_quality_issues"


# CLIENT / INIT

def create_bigquery_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID, location=LOCATION)


def create_error_directory() -> None:
    ERROR_DIR.mkdir(parents=True, exist_ok=True)


def generate_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def ensure_bigquery_error_zone(client: bigquery.Client) -> None:
    """Tạo dataset + 3 bảng quản lý lỗi/DQ nếu chưa tồn tại."""
    dataset_id = f"{PROJECT_ID}.{ERROR_DATASET_ID}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)

    validation_schema = [
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("error_time", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("validation_stage", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("check_name", "STRING"),
        bigquery.SchemaField("source_table", "STRING"),
        bigquery.SchemaField("error_message", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("failed_row_count", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("local_error_path", "STRING"),
    ]

    records_schema = [
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("error_time", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("validation_stage", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("check_name", "STRING"),
        bigquery.SchemaField("source_table", "STRING"),
        bigquery.SchemaField("source_row_index", "STRING"),
        bigquery.SchemaField("error_message", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("row_data", "STRING", mode="REQUIRED"),
    ]

    quality_schema = [
        bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("issue_time", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("pipeline_stage", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("severity", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("issue_code", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_table", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_row_index", "STRING"),
        bigquery.SchemaField("message", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("disposition", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("row_data", "STRING", mode="REQUIRED"),
    ]

    for table_name, schema in [
        (VALIDATION_ERRORS_TABLE, validation_schema),
        (ERROR_RECORDS_TABLE, records_schema),
        (DATA_QUALITY_ISSUES_TABLE, quality_schema),
    ]:
        table_id = f"{PROJECT_ID}.{ERROR_DATASET_ID}.{table_name}"
        client.create_table(bigquery.Table(table_id, schema=schema), exists_ok=True)


def initialize_error_zone() -> None:
    """Khởi tạo cấu trúc Error/DQ Zone ngay đầu pipeline, kể cả khi 0 lỗi."""
    create_error_directory()
    client = create_bigquery_client()
    ensure_bigquery_error_zone(client)
    logger.info(
        "ERROR/DQ ZONE READY - %s.%s (%s, %s, %s)",
        PROJECT_ID,
        ERROR_DATASET_ID,
        VALIDATION_ERRORS_TABLE,
        ERROR_RECORDS_TABLE,
        DATA_QUALITY_ISSUES_TABLE,
    )


# SERIALIZATION

def dataframe_row_to_json(row: pd.Series) -> str:
    payload: dict[str, Any] = {}

    for column_name, value in row.items():
        if pd.isna(value):
            payload[column_name] = None
            continue

        if isinstance(value, (pd.Timestamp, datetime)):
            payload[column_name] = value.isoformat()
            continue

        if hasattr(value, "item"):
            try:
                value = value.item()
            except Exception:
                pass

        payload[column_name] = value

    return json.dumps(payload, ensure_ascii=False, default=str)


def append_dataframe_to_bigquery(
    client: bigquery.Client,
    df: pd.DataFrame,
    table_id: str,
) -> None:
    if df.empty:
        return

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
    )
    job = client.load_table_from_dataframe(
        df,
        table_id,
        job_config=job_config,
        location=LOCATION,
    )
    job.result()


# FATAL VALIDATION ERROR

def save_validation_error(
    validation_stage: str,
    error_message: str,
    table_name: str | None = None,
    check_name: str | None = None,
    failed_rows: pd.DataFrame | None = None,
) -> Path:
    """
    Lưu lỗi validation nghiêm trọng.
    Lỗi này làm pipeline STOP trước khi dữ liệu đi tiếp.
    """
    logger.error("=" * 70)
    logger.error("BẮT ĐẦU QUARANTINE FATAL VALIDATION ERROR")
    logger.error("=" * 70)

    run_id = generate_run_id()
    error_time = datetime.now(timezone.utc)

    create_error_directory()
    error_batch_dir = ERROR_DIR / f"{run_id}_{validation_stage}"
    error_batch_dir.mkdir(parents=True, exist_ok=True)

    failed_row_count = 0

    if failed_rows is not None and not failed_rows.empty:
        failed_row_count = len(failed_rows)
        file_name = f"{table_name or 'failed_rows'}_error.parquet"
        output_path = error_batch_dir / file_name
        failed_rows.to_parquet(output_path, index=True, engine="pyarrow")
        logger.error(
            "LOCAL FATAL ERROR - %s dòng -> %s",
            f"{failed_row_count:,}",
            output_path,
        )

    metadata = {
        "run_id": run_id,
        "error_time": error_time,
        "validation_stage": validation_stage,
        "check_name": check_name,
        "source_table": table_name,
        "error_message": error_message,
        "failed_row_count": failed_row_count,
        "local_error_path": str(error_batch_dir),
    }

    with open(error_batch_dir / "error_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4, default=str)

    try:
        client = create_bigquery_client()
        ensure_bigquery_error_zone(client)

        metadata_df = pd.DataFrame([metadata])
        append_dataframe_to_bigquery(
            client,
            metadata_df,
            f"{PROJECT_ID}.{ERROR_DATASET_ID}.{VALIDATION_ERRORS_TABLE}",
        )

        if failed_rows is not None and not failed_rows.empty:
            records = []
            for source_index, row in failed_rows.iterrows():
                records.append(
                    {
                        "run_id": run_id,
                        "error_time": error_time,
                        "validation_stage": validation_stage,
                        "check_name": check_name,
                        "source_table": table_name,
                        "source_row_index": str(source_index),
                        "error_message": error_message,
                        "row_data": dataframe_row_to_json(row),
                    }
                )

            append_dataframe_to_bigquery(
                client,
                pd.DataFrame(records),
                f"{PROJECT_ID}.{ERROR_DATASET_ID}.{ERROR_RECORDS_TABLE}",
            )

    except Exception:
        logger.exception(
            "Không thể ghi Fatal Error lên BigQuery. Local Error Zone vẫn giữ tại: %s",
            error_batch_dir,
        )

    logger.error(
        "FATAL VALIDATION ERROR QUARANTINED | stage=%s | table=%s | check=%s | rows=%s",
        validation_stage,
        table_name,
        check_name,
        f"{failed_row_count:,}",
    )

    return error_batch_dir


# NON-FATAL DATA QUALITY ISSUES


def save_quality_issues(
    issues: list[dict[str, Any]],
    pipeline_stage: str = "clean_validation",
) -> int:

    if not issues:
        logger.info("DATA QUALITY ISSUES - Không có issue cần ghi.")
        return 0

    run_id = generate_run_id()
    issue_time = datetime.now(timezone.utc)

    create_error_directory()
    issue_dir = ERROR_DIR / f"{run_id}_quality_issues"
    issue_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []

    for issue in issues:
        rows: pd.DataFrame = issue["rows"]
        severity = str(issue["severity"])
        issue_code = str(issue["issue_code"])
        source_table = str(issue["source_table"])
        message = str(issue["message"])
        disposition = str(issue["disposition"])

        safe_code = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in issue_code)
        output_path = issue_dir / f"{source_table}__{safe_code}.parquet"
        rows.to_parquet(output_path, index=True, engine="pyarrow")

        summary.append(
            {
                "severity": severity,
                "issue_code": issue_code,
                "source_table": source_table,
                "row_count": len(rows),
                "message": message,
                "disposition": disposition,
                "local_file": str(output_path),
            }
        )

        for source_index, row in rows.iterrows():
            all_records.append(
                {
                    "run_id": run_id,
                    "issue_time": issue_time,
                    "pipeline_stage": pipeline_stage,
                    "severity": severity,
                    "issue_code": issue_code,
                    "source_table": source_table,
                    "source_row_index": str(source_index),
                    "message": message,
                    "disposition": disposition,
                    "row_data": dataframe_row_to_json(row),
                }
            )

    with open(issue_dir / "quality_metadata.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "run_id": run_id,
                "issue_time": issue_time,
                "pipeline_stage": pipeline_stage,
                "issue_types": summary,
                "total_issue_records": len(all_records),
            },
            f,
            ensure_ascii=False,
            indent=4,
            default=str,
        )

    try:
        client = create_bigquery_client()
        ensure_bigquery_error_zone(client)
        append_dataframe_to_bigquery(
            client,
            pd.DataFrame(all_records),
            f"{PROJECT_ID}.{ERROR_DATASET_ID}.{DATA_QUALITY_ISSUES_TABLE}",
        )
        logger.warning(
            "BIGQUERY DATA QUALITY ISSUES -> %s.%s.%s | %s record-issue",
            PROJECT_ID,
            ERROR_DATASET_ID,
            DATA_QUALITY_ISSUES_TABLE,
            f"{len(all_records):,}",
        )
    except Exception:
        logger.exception(
            "Không thể ghi Data Quality Issues lên BigQuery. Local copy vẫn giữ tại: %s",
            issue_dir,
        )

    return len(all_records)
