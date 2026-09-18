from __future__ import annotations

import logging

from extract import extract_all
from transform import transform_all
from load import load_staging

from validate import (
    validate_all_raw,
    validate_all_clean,
    RawValidationError,
    CleanValidationError,
)

from error_handler import (
    initialize_error_zone,
    save_validation_error,
    save_quality_issues,
)

from load_bigquery import load_all_staging_to_bigquery
from build_dwh import build_dwh
from reconcile_dwh import reconcile_dwh, DWHReconciliationError


logger = logging.getLogger(__name__)


def quarantine_validation_error(
    error: Exception,
    validation_stage: str,
) -> None:
    error_path = save_validation_error(
        validation_stage=validation_stage,
        error_message=str(error),
        table_name=getattr(error, "table_name", None),
        check_name=getattr(error, "check_name", None),
        failed_rows=getattr(error, "failed_rows", None),
    )

    logger.error(
        "Fatal Validation Error đã được quarantine tại: %s",
        error_path,
    )


def run_pipeline() -> bool:
    logger.info("=" * 70)
    logger.info("BẮT ĐẦU OLIST ETL + DWH PIPELINE")
    logger.info("=" * 70)

    try:
        initialize_error_zone()
    except Exception:
        logger.exception("Không thể khởi tạo Error/DQ Zone.")
        raise


    # EXTRACT

    logger.info("STEP 1/8 - EXTRACT")

    try:
        raw_data = extract_all()
    except Exception:
        logger.exception("PIPELINE FAILED tại STEP 1 - EXTRACT.")
        raise

    logger.info("STEP 1/8 - EXTRACT: SUCCESS")


    # VALIDATE RAW

    logger.info("STEP 2/8 - VALIDATE RAW")

    try:
        validate_all_raw(raw_data)
    except RawValidationError as error:
        logger.error("STEP 2/8 - VALIDATE RAW: FAILED")
        logger.error("Lý do: %s", error)
        quarantine_validation_error(error, "raw_validation")
        logger.error("Pipeline dừng trước Transform.")
        raise

    logger.info("STEP 2/8 - VALIDATE RAW: SUCCESS")

    # TRANSFORM

    logger.info("STEP 3/8 - TRANSFORM")

    try:
        clean_data = transform_all(raw_data)
    except Exception:
        logger.exception("PIPELINE FAILED tại STEP 3 - TRANSFORM.")
        raise

    logger.info("STEP 3/8 - TRANSFORM: SUCCESS")


    # VALIDATE CLEAN

    logger.info("STEP 4/8 - VALIDATE CLEAN")

    try:
        quality_issues = validate_all_clean(raw_data, clean_data)
    except CleanValidationError as error:
        logger.error("STEP 4/8 - VALIDATE CLEAN: FAILED")
        logger.error("Lý do: %s", error)
        quarantine_validation_error(error, "clean_validation")
        logger.error("Pipeline dừng trước Load Staging.")
        raise

    logger.info("STEP 4/8 - VALIDATE CLEAN: SUCCESS")
    quality_issue_record_count = save_quality_issues(
        quality_issues,
        pipeline_stage="clean_validation",
    )

    logger.info(
        "DATA QUALITY ISSUE RECORDS ĐÃ GHI: %s",
        f"{quality_issue_record_count:,}",
    )


    # LOAD LOCAL STAGING

    logger.info("STEP 5/8 - LOAD LOCAL STAGING")

    try:
        load_staging(clean_data)
    except Exception:
        logger.exception("PIPELINE FAILED tại STEP 5 - LOAD LOCAL STAGING.")
        raise

    logger.info("STEP 5/8 - LOAD LOCAL STAGING: SUCCESS")


    # LOAD BIGQUERY STAGING

    logger.info("STEP 6/8 - LOAD BIGQUERY STAGING")

    try:
        load_all_staging_to_bigquery()
    except Exception:
        logger.exception("PIPELINE FAILED tại STEP 6 - LOAD BIGQUERY STAGING.")
        raise

    logger.info("STEP 6/8 - LOAD BIGQUERY STAGING: SUCCESS")


    # BUILD DATA WAREHOUSE

    logger.info("STEP 7/8 - BUILD DATA WAREHOUSE")

    try:
        build_dwh()
    except Exception:
        logger.exception("PIPELINE FAILED tại STEP 7 - BUILD DATA WAREHOUSE.")
        raise

    logger.info("STEP 7/8 - BUILD DATA WAREHOUSE: SUCCESS")

    # DWH RECONCILIATION
    logger.info("STEP 8/8 - DWH RECONCILIATION")

    try:
        reconcile_dwh()
    except DWHReconciliationError as error:
        logger.error("STEP 8/8 - DWH RECONCILIATION: FAILED")
        logger.error("Lý do: %s", error)
        logger.error("DWH không đủ điều kiện chuyển sang BI / Analytics.")
        raise
    except Exception:
        logger.exception("PIPELINE FAILED tại STEP 8 - DWH RECONCILIATION.")
        raise

    logger.info("STEP 8/8 - DWH RECONCILIATION: SUCCESS")


    # SUCCESS SUMMARY
    logger.info("")
    logger.info("=" * 70)
    logger.info("OLIST ETL + DWH PIPELINE: SUCCESS")
    logger.info("=" * 70)
    logger.info("Extract                  : PASS")
    logger.info("Validate Raw             : PASS")
    logger.info("Transform                : PASS")
    logger.info("Validate Clean           : PASS")
    logger.info("DQ Issues Recorded       : %s", f"{quality_issue_record_count:,}")
    logger.info("Load Local Staging       : PASS")
    logger.info("Load BigQuery Staging    : PASS")
    logger.info("Build Data Warehouse     : PASS")
    logger.info("DWH Reconciliation       : PASS")
    logger.info("-" * 70)
    logger.info("Dữ liệu đã sẵn sàng cho BI / Analytics.")
    logger.info("=" * 70)

    return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    run_pipeline()
