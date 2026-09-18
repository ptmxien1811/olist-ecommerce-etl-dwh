from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype


logger = logging.getLogger(__name__)



# CẤU HÌNH DỮ LIỆU NGUỒN


EXPECTED_TABLES = {
    "customers",
    "geolocation",
    "order_items",
    "payments",
    "reviews",
    "orders",
    "products",
    "sellers",
    "category_translation",
}

REQUIRED_COLUMNS = {
    "customers": {
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    },
    "geolocation": {
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    },
    "order_items": {
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    },
    "payments": {
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    },
    "reviews": {
        "review_id",
        "order_id",
        "review_score",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
    },
    "orders": {
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    },
    "products": {
        "product_id",
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    },
    "sellers": {
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    },
    "category_translation": {
        "product_category_name",
        "product_category_name_english",
    },
}

SINGLE_KEYS = {
    "customers": "customer_id",
    "orders": "order_id",
    "products": "product_id",
    "sellers": "seller_id",
    "category_translation": "product_category_name",
}

COMPOSITE_KEYS = {
    "order_items": ["order_id", "order_item_id"],
    "payments": ["order_id", "payment_sequential"],
    "reviews": ["review_id", "order_id"],
}

FOREIGN_KEYS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("payments", "order_id", "orders", "order_id"),
    ("reviews", "order_id", "orders", "order_id"),
]

ORDER_DATETIME_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

REVIEW_DATETIME_COLUMNS = [
    "review_creation_date",
    "review_answer_timestamp",
]

PRODUCT_COUNT_COLUMNS = [
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty",
]

# Tập giá trị payment_type xuất hiện/được chấp nhận trong bộ Olist.
EXPECTED_PAYMENT_TYPES = {
    "credit_card",
    "boleto",
    "voucher",
    "debit_card",
    "not_defined",
}


# EXCEPTION CÓ NGỮ CẢNH LỖI


class ValidationError(Exception):


    def __init__(
        self,
        message: str,
        table_name: str | None = None,
        check_name: str | None = None,
        failed_rows: pd.DataFrame | None = None,
    ) -> None:
        super().__init__(message)
        self.table_name = table_name
        self.check_name = check_name
        self.failed_rows = failed_rows


class RawValidationError(ValidationError):
    pass


class CleanValidationError(ValidationError):
    pass



# HÀM HỖ TRỢ


def raw_fail(
    message: str,
    table_name: str | None = None,
    check_name: str | None = None,
    failed_rows: pd.DataFrame | None = None,
) -> None:
    logger.error(message)
    raise RawValidationError(
        message=message,
        table_name=table_name,
        check_name=check_name,
        failed_rows=failed_rows,
    )


def raw_warn(message: str) -> None:
    logger.warning(message)


def clean_fail(
    message: str,
    table_name: str | None = None,
    check_name: str | None = None,
    failed_rows: pd.DataFrame | None = None,
) -> None:
    logger.error(message)
    raise CleanValidationError(
        message=message,
        table_name=table_name,
        check_name=check_name,
        failed_rows=failed_rows,
    )


def add_quality_issue(
    issues: list[dict[str, Any]],
    *,
    severity: str,
    issue_code: str,
    source_table: str,
    message: str,
    disposition: str,
    rows: pd.DataFrame,
) -> None:
    if rows.empty:
        return

    issues.append(
        {
            "severity": severity,
            "issue_code": issue_code,
            "source_table": source_table,
            "message": message,
            "disposition": disposition,
            "rows": rows.copy(),
        }
    )


# VALIDATE RAW - CỔNG CHẤT LƯỢNG TRƯỚC TRANSFORM


def validate_expected_tables(raw_data: dict[str, pd.DataFrame]) -> None:
    missing_tables = EXPECTED_TABLES - set(raw_data.keys())

    if missing_tables:
        raw_fail(
            "Thiếu bảng dữ liệu nguồn: " + ", ".join(sorted(missing_tables)),
            check_name="missing_source_table",
        )

    logger.info("RAW CHECK - Đủ %s bảng dữ liệu nguồn.", len(EXPECTED_TABLES))


def validate_non_empty(raw_data: dict[str, pd.DataFrame]) -> None:
    for table_name in EXPECTED_TABLES:
        if raw_data[table_name].empty:
            raw_fail(
                f"Bảng {table_name} không chứa dữ liệu.",
                table_name=table_name,
                check_name="empty_source_table",
            )

    logger.info("RAW CHECK - Tất cả bảng đều có dữ liệu.")


def validate_required_columns(raw_data: dict[str, pd.DataFrame]) -> None:
    for table_name, expected_columns in REQUIRED_COLUMNS.items():
        missing_columns = expected_columns - set(raw_data[table_name].columns)

        if missing_columns:
            raw_fail(
                f"Bảng {table_name} thiếu cột: " + ", ".join(sorted(missing_columns)),
                table_name=table_name,
                check_name="missing_required_columns",
            )

    logger.info("RAW CHECK - Schema các bảng đầy đủ.")


def validate_single_keys(raw_data: dict[str, pd.DataFrame]) -> None:
    for table_name, key_column in SINGLE_KEYS.items():
        df = raw_data[table_name]

        null_mask = df[key_column].isna()
        if null_mask.any():
            failed_rows = df.loc[null_mask].copy()
            raw_fail(
                f"{table_name}.{key_column} có {len(failed_rows)} giá trị NULL.",
                table_name=table_name,
                check_name=f"{key_column}_null",
                failed_rows=failed_rows,
            )

        duplicate_mask = df[key_column].duplicated(keep=False)
        if duplicate_mask.any():
            failed_rows = df.loc[duplicate_mask].copy()
            raw_fail(
                f"{table_name}.{key_column} có {len(failed_rows)} dòng thuộc khóa bị lặp.",
                table_name=table_name,
                check_name=f"{key_column}_duplicate",
                failed_rows=failed_rows,
            )

        logger.info("RAW CHECK - %s.%s: khóa hợp lệ.", table_name, key_column)


def validate_composite_keys(raw_data: dict[str, pd.DataFrame]) -> None:
    for table_name, key_columns in COMPOSITE_KEYS.items():
        df = raw_data[table_name]

        null_mask = df[key_columns].isna().any(axis=1)
        if null_mask.any():
            failed_rows = df.loc[null_mask].copy()
            raw_fail(
                f"Bảng {table_name} có {len(failed_rows)} dòng thiếu thành phần khóa ghép {key_columns}.",
                table_name=table_name,
                check_name="composite_key_null",
                failed_rows=failed_rows,
            )

        duplicate_mask = df.duplicated(subset=key_columns, keep=False)
        if duplicate_mask.any():
            failed_rows = df.loc[duplicate_mask].copy()
            raw_fail(
                f"Bảng {table_name} có {len(failed_rows)} dòng thuộc khóa ghép trùng {key_columns}.",
                table_name=table_name,
                check_name="composite_key_duplicate",
                failed_rows=failed_rows,
            )

        logger.info("RAW CHECK - %s: khóa ghép %s hợp lệ.", table_name, key_columns)


def validate_foreign_keys(raw_data: dict[str, pd.DataFrame]) -> None:
    for child_table, child_column, parent_table, parent_column in FOREIGN_KEYS:
        child_df = raw_data[child_table]
        parent_df = raw_data[parent_table]

        null_mask = child_df[child_column].isna()
        if null_mask.any():
            failed_rows = child_df.loc[null_mask].copy()
            raw_fail(
                f"{child_table}.{child_column} có {len(failed_rows)} giá trị NULL.",
                table_name=child_table,
                check_name=f"fk_{child_column}_null",
                failed_rows=failed_rows,
            )

        parent_values = set(parent_df[parent_column].dropna())
        unmatched_mask = ~child_df[child_column].isin(parent_values)

        if unmatched_mask.any():
            failed_rows = child_df.loc[unmatched_mask].copy()
            raw_fail(
                f"{child_table}.{child_column} có {len(failed_rows)} dòng không tìm thấy "
                f"trong {parent_table}.{parent_column}.",
                table_name=child_table,
                check_name=f"fk_{child_column}_to_{parent_table}_{parent_column}",
                failed_rows=failed_rows,
            )

        logger.info(
            "RAW CHECK - FK %s.%s -> %s.%s: hợp lệ.",
            child_table,
            child_column,
            parent_table,
            parent_column,
        )


def validate_known_raw_quality(raw_data: dict[str, pd.DataFrame]) -> None:

    geolocation_df = raw_data["geolocation"]
    products_df = raw_data["products"]
    payments_df = raw_data["payments"]

    geo_duplicate_count = int(geolocation_df.duplicated().sum())
    if geo_duplicate_count > 0:
        raw_warn(
            f"geolocation có {geo_duplicate_count:,} exact duplicate. "
            "Transform sẽ loại các dòng trùng hoàn toàn."
        )

    zero_weight_count = int(products_df["product_weight_g"].eq(0).sum())
    if zero_weight_count > 0:
        raw_warn(
            f"products có {zero_weight_count} product_weight_g = 0. "
            "Transform sẽ chuyển giá trị thuộc tính không hợp lệ thành NULL."
        )

    not_defined_count = int(payments_df["payment_type"].eq("not_defined").sum())
    if not_defined_count > 0:
        raw_warn(
            f"payments có {not_defined_count} payment_type = not_defined. "
            "Giữ bản ghi và theo dõi như thiếu thông tin nghiệp vụ."
        )

    zero_payment_count = int(payments_df["payment_value"].eq(0).sum())
    if zero_payment_count > 0:
        raw_warn(
            f"payments có {zero_payment_count} payment_value = 0. "
            "Chưa đủ cơ sở kết luận sai; giữ lại để đối chiếu."
        )

    invalid_credit_installment_count = int(
        (
            payments_df["payment_type"].eq("credit_card")
            & payments_df["payment_installments"].le(0)
        ).sum()
    )
    if invalid_credit_installment_count > 0:
        raw_warn(
            f"payments có {invalid_credit_installment_count} credit_card với "
            "payment_installments <= 0. Không tự gán số kỳ; sẽ ghi nhận "
            "thành Data Quality Issue sau Transform."
        )

    logger.info("RAW CHECK - Hoàn tất kiểm tra các vấn đề chất lượng đã biết.")


def validate_lookup_coverage(raw_data: dict[str, pd.DataFrame]) -> None:
    products_df = raw_data["products"]
    category_df = raw_data["category_translation"]

    category_mask = (
        products_df["product_category_name"].notna()
        & ~products_df["product_category_name"].isin(category_df["product_category_name"])
    )
    if category_mask.any():
        raw_warn(
            f"products có {int(category_mask.sum())} dòng category có giá trị nhưng không tìm thấy "
            "trong category_translation. Không loại product; dùng Unknown/giữ tên gốc khi xây Dimension."
        )

    geo_zip_values = set(raw_data["geolocation"]["geolocation_zip_code_prefix"].dropna())

    customer_mask = ~raw_data["customers"]["customer_zip_code_prefix"].isin(geo_zip_values)
    if customer_mask.any():
        raw_warn(
            f"customers có {int(customer_mask.sum())} dòng không tìm thấy ZIP trong geolocation. "
            "Không loại customer; vị trí bổ sung sẽ để chưa xác định."
        )

    seller_mask = ~raw_data["sellers"]["seller_zip_code_prefix"].isin(geo_zip_values)
    if seller_mask.any():
        raw_warn(
            f"sellers có {int(seller_mask.sum())} dòng không tìm thấy ZIP trong geolocation. "
            "Không loại seller; vị trí bổ sung sẽ để chưa xác định."
        )

    logger.info("RAW CHECK - Hoàn tất kiểm tra lookup coverage.")


def validate_all_raw(raw_data: dict[str, pd.DataFrame]) -> bool:
    logger.info("=" * 70)
    logger.info("BẮT ĐẦU VALIDATE RAW")
    logger.info("=" * 70)

    validate_expected_tables(raw_data)
    validate_non_empty(raw_data)
    validate_required_columns(raw_data)
    validate_single_keys(raw_data)
    validate_composite_keys(raw_data)
    validate_foreign_keys(raw_data)
    validate_known_raw_quality(raw_data)
    validate_lookup_coverage(raw_data)

    logger.info("=" * 70)
    logger.info("VALIDATE RAW: PASS")
    logger.info("Dữ liệu đủ điều kiện chuyển sang Transform.")
    logger.info("=" * 70)
    return True


# =========================================================
# VALIDATE CLEAN - HARD RULES SAU TRANSFORM
# =========================================================

def validate_clean_row_counts(
    raw_data: dict[str, pd.DataFrame],
    clean_data: dict[str, pd.DataFrame],
) -> None:
    unchanged_tables = [
        "customers",
        "order_items",
        "payments",
        "reviews",
        "orders",
        "products",
        "sellers",
        "category_translation",
    ]

    for table_name in unchanged_tables:
        raw_rows = len(raw_data[table_name])
        clean_rows = len(clean_data[table_name])
        if raw_rows != clean_rows:
            clean_fail(
                f"{table_name}: số dòng thay đổi ngoài dự kiến. Raw={raw_rows:,}, Clean={clean_rows:,}.",
                table_name=table_name,
                check_name="unexpected_row_count_change",
            )

    expected_geo_rows = raw_data["geolocation"].drop_duplicates().shape[0]
    actual_geo_rows = len(clean_data["geolocation"])
    if actual_geo_rows != expected_geo_rows:
        clean_fail(
            "geolocation: số dòng sau Transform không đúng. "
            f"Kỳ vọng {expected_geo_rows:,}, thực tế {actual_geo_rows:,}.",
            table_name="geolocation",
            check_name="geolocation_row_count_after_dedup",
        )

    logger.info("CLEAN CHECK - Số dòng sau Transform hợp lệ.")


def validate_clean_zip_codes(clean_data: dict[str, pd.DataFrame]) -> None:
    zip_columns = {
        "customers": "customer_zip_code_prefix",
        "sellers": "seller_zip_code_prefix",
        "geolocation": "geolocation_zip_code_prefix",
    }

    for table_name, column_name in zip_columns.items():
        df = clean_data[table_name]
        series = df[column_name]

        if str(series.dtype) != "string":
            clean_fail(
                f"{table_name}.{column_name}: dtype hiện tại là {series.dtype}, kỳ vọng string.",
                table_name=table_name,
                check_name=f"{column_name}_dtype",
            )

        invalid_mask = series.notna() & ~series.str.fullmatch(r"\d{5}")
        if invalid_mask.any():
            failed_rows = df.loc[invalid_mask].copy()
            clean_fail(
                f"{table_name}.{column_name}: có {len(failed_rows)} ZIP không đúng định dạng 5 chữ số.",
                table_name=table_name,
                check_name=f"{column_name}_invalid_format",
                failed_rows=failed_rows,
            )

        logger.info("CLEAN CHECK - %s.%s: ZIP hợp lệ.", table_name, column_name)


def validate_clean_datetime(
    raw_data: dict[str, pd.DataFrame],
    clean_data: dict[str, pd.DataFrame],
) -> None:
    datetime_columns = {
        "orders": ORDER_DATETIME_COLUMNS,
        "order_items": ["shipping_limit_date"],
        "reviews": REVIEW_DATETIME_COLUMNS,
    }

    for table_name, columns in datetime_columns.items():
        for column in columns:
            raw_series = raw_data[table_name][column]
            clean_series = clean_data[table_name][column]

            if not is_datetime64_any_dtype(clean_series):
                clean_fail(
                    f"{table_name}.{column}: dtype hiện tại là {clean_series.dtype}, kỳ vọng datetime.",
                    table_name=table_name,
                    check_name=f"{column}_datetime_dtype",
                )

            parse_failure_mask = raw_series.notna() & clean_series.isna()
            if parse_failure_mask.any():
                failed_rows = clean_data[table_name].loc[parse_failure_mask].copy()
                # Lưu thêm giá trị nguồn để truy vết lỗi parse.
                failed_rows[f"_raw_{column}"] = raw_series.loc[parse_failure_mask].astype("string")
                clean_fail(
                    f"{table_name}.{column}: phát sinh {len(failed_rows)} NaT từ dữ liệu nguồn có giá trị.",
                    table_name=table_name,
                    check_name=f"{column}_datetime_parse_failure",
                    failed_rows=failed_rows,
                )

            logger.info("CLEAN CHECK - %s.%s: datetime hợp lệ.", table_name, column)


def validate_clean_product_dtypes(clean_data: dict[str, pd.DataFrame]) -> None:
    products_df = clean_data["products"]
    for column in PRODUCT_COUNT_COLUMNS:
        if str(products_df[column].dtype) != "Int64":
            clean_fail(
                f"products.{column}: dtype hiện tại là {products_df[column].dtype}, kỳ vọng Int64 nullable.",
                table_name="products",
                check_name=f"{column}_dtype",
            )
        logger.info("CLEAN CHECK - products.%s: Int64 hợp lệ.", column)


def validate_clean_product_physical_values(clean_data: dict[str, pd.DataFrame]) -> None:
    products_df = clean_data["products"]

    for column in [
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]:
        invalid_mask = products_df[column].notna() & products_df[column].le(0)
        if invalid_mask.any():
            failed_rows = products_df.loc[invalid_mask].copy()
            clean_fail(
                f"products.{column}: còn {len(failed_rows)} giá trị <= 0 sau Transform.",
                table_name="products",
                check_name=f"{column}_non_positive",
                failed_rows=failed_rows,
            )

    logger.info("CLEAN CHECK - Các thuộc tính vật lý sản phẩm hợp lệ (> 0 hoặc NULL).")


def validate_clean_geolocation(clean_data: dict[str, pd.DataFrame]) -> None:
    geolocation_df = clean_data["geolocation"]

    duplicate_mask = geolocation_df.duplicated(keep=False)
    if duplicate_mask.any():
        failed_rows = geolocation_df.loc[duplicate_mask].copy()
        clean_fail(
            f"geolocation vẫn còn {len(failed_rows):,} dòng thuộc exact duplicate.",
            table_name="geolocation",
            check_name="exact_duplicate_after_transform",
            failed_rows=failed_rows,
        )

    invalid_lat_mask = geolocation_df["geolocation_lat"].notna() & ~geolocation_df["geolocation_lat"].between(-90, 90)
    if invalid_lat_mask.any():
        failed_rows = geolocation_df.loc[invalid_lat_mask].copy()
        clean_fail(
            f"geolocation có {len(failed_rows)} latitude ngoài [-90, 90].",
            table_name="geolocation",
            check_name="invalid_latitude",
            failed_rows=failed_rows,
        )

    invalid_lng_mask = geolocation_df["geolocation_lng"].notna() & ~geolocation_df["geolocation_lng"].between(-180, 180)
    if invalid_lng_mask.any():
        failed_rows = geolocation_df.loc[invalid_lng_mask].copy()
        clean_fail(
            f"geolocation có {len(failed_rows)} longitude ngoài [-180, 180].",
            table_name="geolocation",
            check_name="invalid_longitude",
            failed_rows=failed_rows,
        )

    logger.info("CLEAN CHECK - geolocation hợp lệ và không còn exact duplicate.")


def validate_geolocation_lookup(clean_data: dict[str, pd.DataFrame]) -> None:
    if "geolocation_lookup" not in clean_data:
        clean_fail(
            "Không tìm thấy geolocation_lookup sau Transform.",
            table_name="geolocation_lookup",
            check_name="missing_derived_table",
        )

    geo_df = clean_data["geolocation"]
    lookup_df = clean_data["geolocation_lookup"]
    zip_column = "geolocation_zip_code_prefix"

    duplicate_zip_mask = lookup_df[zip_column].duplicated(keep=False)
    if duplicate_zip_mask.any():
        failed_rows = lookup_df.loc[duplicate_zip_mask].copy()
        clean_fail(
            f"geolocation_lookup có {len(failed_rows)} dòng thuộc ZIP bị lặp.",
            table_name="geolocation_lookup",
            check_name="duplicate_zip",
            failed_rows=failed_rows,
        )

    expected_zip_count = int(geo_df[zip_column].nunique())
    if len(lookup_df) != expected_zip_count:
        clean_fail(
            "geolocation_lookup không đúng mức một dòng/ZIP. "
            f"Kỳ vọng {expected_zip_count:,}, thực tế {len(lookup_df):,}.",
            table_name="geolocation_lookup",
            check_name="lookup_grain",
        )

    invalid_zip_mask = lookup_df[zip_column].notna() & ~lookup_df[zip_column].str.fullmatch(r"\d{5}")
    if invalid_zip_mask.any():
        failed_rows = lookup_df.loc[invalid_zip_mask].copy()
        clean_fail(
            f"geolocation_lookup có {len(failed_rows)} ZIP sai định dạng.",
            table_name="geolocation_lookup",
            check_name="invalid_zip_format",
            failed_rows=failed_rows,
        )

    for column, lower, upper, check_name in [
        ("geolocation_lat", -90, 90, "invalid_latitude"),
        ("geolocation_lng", -180, 180, "invalid_longitude"),
    ]:
        invalid_mask = lookup_df[column].notna() & ~lookup_df[column].between(lower, upper)
        if invalid_mask.any():
            failed_rows = lookup_df.loc[invalid_mask].copy()
            clean_fail(
                f"geolocation_lookup có {len(failed_rows)} {column} không hợp lệ.",
                table_name="geolocation_lookup",
                check_name=check_name,
                failed_rows=failed_rows,
            )

    logger.info("CLEAN CHECK - geolocation_lookup đúng một dòng/ZIP.")


def validate_clean_keys(clean_data: dict[str, pd.DataFrame]) -> None:
    for table_name, key_column in SINGLE_KEYS.items():
        df = clean_data[table_name]

        null_mask = df[key_column].isna()
        if null_mask.any():
            failed_rows = df.loc[null_mask].copy()
            clean_fail(
                f"{table_name}.{key_column} có {len(failed_rows)} NULL.",
                table_name=table_name,
                check_name=f"{key_column}_null_after_transform",
                failed_rows=failed_rows,
            )

        duplicate_mask = df[key_column].duplicated(keep=False)
        if duplicate_mask.any():
            failed_rows = df.loc[duplicate_mask].copy()
            clean_fail(
                f"{table_name}.{key_column} có {len(failed_rows)} dòng thuộc duplicate.",
                table_name=table_name,
                check_name=f"{key_column}_duplicate_after_transform",
                failed_rows=failed_rows,
            )

    for table_name, key_columns in COMPOSITE_KEYS.items():
        df = clean_data[table_name]

        null_mask = df[key_columns].isna().any(axis=1)
        if null_mask.any():
            failed_rows = df.loc[null_mask].copy()
            clean_fail(
                f"{table_name}: khóa ghép {key_columns} có {len(failed_rows)} dòng NULL.",
                table_name=table_name,
                check_name="composite_key_null_after_transform",
                failed_rows=failed_rows,
            )

        duplicate_mask = df.duplicated(subset=key_columns, keep=False)
        if duplicate_mask.any():
            failed_rows = df.loc[duplicate_mask].copy()
            clean_fail(
                f"{table_name}: khóa ghép {key_columns} có {len(failed_rows)} dòng thuộc duplicate.",
                table_name=table_name,
                check_name="composite_key_duplicate_after_transform",
                failed_rows=failed_rows,
            )

    logger.info("CLEAN CHECK - Cấu trúc khóa vẫn hợp lệ.")


def validate_clean_foreign_keys(clean_data: dict[str, pd.DataFrame]) -> None:
    for child_table, child_column, parent_table, parent_column in FOREIGN_KEYS:
        child_df = clean_data[child_table]
        parent_df = clean_data[parent_table]
        unmatched_mask = ~child_df[child_column].isin(parent_df[parent_column])

        if unmatched_mask.any():
            failed_rows = child_df.loc[unmatched_mask].copy()
            clean_fail(
                f"FK {child_table}.{child_column} -> {parent_table}.{parent_column}: "
                f"có {len(failed_rows)} dòng không match.",
                table_name=child_table,
                check_name=f"fk_{child_column}_after_transform",
                failed_rows=failed_rows,
            )

    logger.info("CLEAN CHECK - 6 quan hệ FK chính vẫn hợp lệ.")


def validate_clean_business_domains(clean_data: dict[str, pd.DataFrame]) -> None:
    """Các rule miền giá trị chắc chắn theo kết quả EDA."""
    order_items = clean_data["order_items"]
    payments = clean_data["payments"]
    reviews = clean_data["reviews"]

    checks = [
        (
            "order_items",
            order_items["order_item_id"].isna() | order_items["order_item_id"].lt(1),
            "order_item_id_invalid",
            "order_item_id phải >= 1.",
            order_items,
        ),
        (
            "order_items",
            order_items["price"].isna() | order_items["price"].lt(0),
            "price_negative_or_null",
            "price phải >= 0 và không NULL.",
            order_items,
        ),
        (
            "order_items",
            order_items["freight_value"].isna() | order_items["freight_value"].lt(0),
            "freight_value_negative_or_null",
            "freight_value phải >= 0 và không NULL.",
            order_items,
        ),
        (
            "payments",
            payments["payment_sequential"].isna() | payments["payment_sequential"].lt(1),
            "payment_sequential_invalid",
            "payment_sequential phải >= 1.",
            payments,
        ),
        (
            "payments",
            payments["payment_installments"].isna() | payments["payment_installments"].lt(0),
            "payment_installments_negative_or_null",
            "payment_installments phải >= 0 và không NULL.",
            payments,
        ),
        (
            "payments",
            payments["payment_value"].isna() | payments["payment_value"].lt(0),
            "payment_value_negative_or_null",
            "payment_value phải >= 0 và không NULL.",
            payments,
        ),
        (
            "payments",
            ~payments["payment_type"].isin(EXPECTED_PAYMENT_TYPES),
            "payment_type_out_of_domain",
            "payment_type nằm ngoài tập giá trị dự kiến.",
            payments,
        ),
        (
            "reviews",
            reviews["review_score"].isna()
            | reviews["review_score"].lt(1)
            | reviews["review_score"].gt(5)
            | (reviews["review_score"] % 1 != 0),
            "review_score_invalid",
            "review_score phải là số nguyên từ 1 đến 5.",
            reviews,
        ),
    ]

    for table_name, mask, check_name, message, df in checks:
        if mask.any():
            failed_rows = df.loc[mask].copy()
            clean_fail(
                f"{table_name}: {len(failed_rows)} dòng vi phạm rule: {message}",
                table_name=table_name,
                check_name=check_name,
                failed_rows=failed_rows,
            )

    review_order_mask = (
        reviews["review_creation_date"].notna()
        & reviews["review_answer_timestamp"].notna()
        & (reviews["review_answer_timestamp"] < reviews["review_creation_date"])
    )
    if review_order_mask.any():
        failed_rows = reviews.loc[review_order_mask].copy()
        clean_fail(
            f"reviews có {len(failed_rows)} dòng review_answer_timestamp < review_creation_date.",
            table_name="reviews",
            check_name="review_temporal_order",
            failed_rows=failed_rows,
        )

    logger.info("CLEAN CHECK - Các rule miền giá trị bắt buộc hợp lệ.")



# DATA QUALITY ISSUES - LỖI/BẤT THƯỜNG KHÔNG LÀM DỪNG BATCH


def collect_data_quality_issues(clean_data: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    payments = clean_data["payments"]
    orders = clean_data["orders"]
    products = clean_data["products"]
    customers = clean_data["customers"]
    sellers = clean_data["sellers"]
    category = clean_data["category_translation"]
    geo_lookup = clean_data["geolocation_lookup"]


    # PAYMENTS

    mask = payments["payment_type"].eq("not_defined")
    add_quality_issue(
        issues,
        severity="WARNING",
        issue_code="payment_type_not_defined",
        source_table="payments",
        message="Không xác định được phương thức thanh toán thực tế; giữ record để bảo toàn giao dịch.",
        disposition="KEEP_AND_FLAG",
        rows=payments.loc[mask],
    )

    mask = payments["payment_type"].eq("credit_card") & payments["payment_installments"].le(0)
    add_quality_issue(
        issues,
        severity="ERROR",
        issue_code="credit_card_installments_non_positive",
        source_table="payments",
        message="credit_card có payment_installments <= 0, không phù hợp rule nghiệp vụ; không tự gán số kỳ.",
        disposition="KEEP_AND_EXCLUDE_FROM_INSTALLMENT_ANALYSIS",
        rows=payments.loc[mask],
    )

    mask = payments["payment_value"].eq(0)
    add_quality_issue(
        issues,
        severity="WARNING",
        issue_code="payment_value_zero",
        source_table="payments",
        message="payment_value = 0 chưa đủ cơ sở kết luận sai; giữ để đối chiếu quan hệ đơn hàng/thanh toán.",
        disposition="KEEP_AND_RECONCILE",
        rows=payments.loc[mask],
    )


    # ORDERS - TEMPORAL CONSISTENCY

    mask = (
        orders["order_delivered_carrier_date"].notna()
        & orders["order_approved_at"].notna()
        & (orders["order_delivered_carrier_date"] < orders["order_approved_at"])
    )
    add_quality_issue(
        issues,
        severity="ERROR",
        issue_code="carrier_before_approved",
        source_table="orders",
        message="order_delivered_carrier_date xảy ra trước order_approved_at; không tự sửa timestamp.",
        disposition="KEEP_AND_EXCLUDE_FROM_AFFECTED_TIME_KPI",
        rows=orders.loc[mask],
    )

    mask = (
        orders["order_delivered_customer_date"].notna()
        & orders["order_delivered_carrier_date"].notna()
        & (orders["order_delivered_customer_date"] < orders["order_delivered_carrier_date"])
    )
    add_quality_issue(
        issues,
        severity="ERROR",
        issue_code="customer_delivery_before_carrier",
        source_table="orders",
        message="order_delivered_customer_date xảy ra trước order_delivered_carrier_date; không tự sửa timestamp.",
        disposition="KEEP_AND_EXCLUDE_FROM_AFFECTED_TIME_KPI",
        rows=orders.loc[mask],
    )

    delivered = orders["order_status"].eq("delivered")

    for column, issue_code, message in [
        (
            "order_approved_at",
            "delivered_missing_approved_at",
            "Đơn delivered nhưng thiếu order_approved_at.",
        ),
        (
            "order_delivered_carrier_date",
            "delivered_missing_carrier_date",
            "Đơn delivered nhưng thiếu order_delivered_carrier_date.",
        ),
        (
            "order_delivered_customer_date",
            "delivered_missing_customer_date",
            "Đơn delivered nhưng thiếu order_delivered_customer_date.",
        ),
    ]:
        mask = delivered & orders[column].isna()
        add_quality_issue(
            issues,
            severity="ERROR",
            issue_code=issue_code,
            source_table="orders",
            message=message + " Không điền ngày giả và không xóa order.",
            disposition="KEEP_AND_EXCLUDE_FROM_AFFECTED_TIME_KPI",
            rows=orders.loc[mask],
        )

    # LOOKUP COVERAGE

    mask = (
        products["product_category_name"].notna()
        & ~products["product_category_name"].isin(category["product_category_name"])
    )
    add_quality_issue(
        issues,
        severity="WARNING",
        issue_code="category_translation_unmatched",
        source_table="products",
        message="Danh mục sản phẩm không tìm thấy bản dịch; product vẫn hợp lệ.",
        disposition="KEEP_AND_USE_UNKNOWN_TRANSLATION",
        rows=products.loc[mask],
    )

    geo_zip_values = set(geo_lookup["geolocation_zip_code_prefix"].dropna())

    mask = ~customers["customer_zip_code_prefix"].isin(geo_zip_values)
    add_quality_issue(
        issues,
        severity="WARNING",
        issue_code="customer_zip_unmatched_geolocation",
        source_table="customers",
        message="ZIP khách hàng không được geolocation_lookup bao phủ; customer vẫn hợp lệ.",
        disposition="KEEP_WITH_UNKNOWN_GEO",
        rows=customers.loc[mask],
    )

    mask = ~sellers["seller_zip_code_prefix"].isin(geo_zip_values)
    add_quality_issue(
        issues,
        severity="WARNING",
        issue_code="seller_zip_unmatched_geolocation",
        source_table="sellers",
        message="ZIP người bán không được geolocation_lookup bao phủ; seller vẫn hợp lệ.",
        disposition="KEEP_WITH_UNKNOWN_GEO",
        rows=sellers.loc[mask],
    )

    return issues


def log_quality_issues(issues: list[dict[str, Any]]) -> None:
    if not issues:
        logger.info("QUALITY ISSUE CHECK - Không phát hiện issue không-fatal.")
        return

    logger.warning("QUALITY ISSUE CHECK - Phát hiện %s loại issue.", len(issues))
    for issue in issues:
        logger.warning(
            "QUALITY ISSUE - %-7s | %-40s | %-12s | %s dòng | %s",
            issue["severity"],
            issue["issue_code"],
            issue["source_table"],
            f"{len(issue['rows']):,}",
            issue["disposition"],
        )




def validate_all_clean(
    raw_data: dict[str, pd.DataFrame],
    clean_data: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    logger.info("=" * 70)
    logger.info("BẮT ĐẦU VALIDATE CLEAN")
    logger.info("=" * 70)

    validate_clean_row_counts(raw_data, clean_data)
    validate_clean_zip_codes(clean_data)
    validate_clean_datetime(raw_data, clean_data)
    validate_clean_product_dtypes(clean_data)
    validate_clean_product_physical_values(clean_data)
    validate_clean_geolocation(clean_data)
    validate_geolocation_lookup(clean_data)
    validate_clean_keys(clean_data)
    validate_clean_foreign_keys(clean_data)
    validate_clean_business_domains(clean_data)

    quality_issues = collect_data_quality_issues(clean_data)
    log_quality_issues(quality_issues)

    logger.info("=" * 70)
    logger.info("VALIDATE CLEAN: PASS")
    logger.info(
        "Dữ liệu đạt các rule bắt buộc. Các issue không-fatal sẽ được ghi vào Error/DQ Zone "
        "và dữ liệu vẫn được phép chuyển sang Staging."
    )
    logger.info("=" * 70)

    return quality_issues




if __name__ == "__main__":
    from extract import extract_all
    from transform import transform_all

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        raw_data = extract_all()
        validate_all_raw(raw_data)
        clean_data = transform_all(raw_data)
        issues = validate_all_clean(raw_data, clean_data)

        print("\n" + "=" * 70)
        print("PIPELINE VALIDATION: PASS")
        print(f"Số loại Data Quality Issue không-fatal: {len(issues)}")
        print("=" * 70)

    except RawValidationError as error:
        print("\nVALIDATE RAW: FAIL")
        print(f"Lý do: {error}")
        raise

    except CleanValidationError as error:
        print("\nVALIDATE CLEAN: FAIL")
        print(f"Lý do: {error}")
        raise
