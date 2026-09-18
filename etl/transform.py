from __future__ import annotations

import logging

import pandas as pd


logger = logging.getLogger(__name__)



# CẤU HÌNH CÁC CỘT CẦN TRANSFORM


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



# HÀM DÙNG CHUNG


def normalize_zip_code(series: pd.Series) -> pd.Series:

    normalized = (
        series
        .astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )

    return normalized.str.zfill(5)


def convert_datetime_columns(
    df: pd.DataFrame,
    columns: list[str]
) -> pd.DataFrame:

    for column in columns:
        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )

    return df



# CUSTOMERS


def transform_customers(
    customers_df: pd.DataFrame
) -> pd.DataFrame:


    df = customers_df.copy()

    df["customer_zip_code_prefix"] = normalize_zip_code(
        df["customer_zip_code_prefix"]
    )

    logger.info(
        "Transform customers hoàn tất: %s dòng.",
        len(df)
    )

    return df


# SELLERS


def transform_sellers(
    sellers_df: pd.DataFrame
) -> pd.DataFrame:

    df = sellers_df.copy()

    df["seller_zip_code_prefix"] = normalize_zip_code(
        df["seller_zip_code_prefix"]
    )

    logger.info(
        "Transform sellers hoàn tất: %s dòng.",
        len(df)
    )

    return df



# GEOLOCATION

def transform_geolocation(
    geolocation_df: pd.DataFrame
) -> pd.DataFrame:

    df = geolocation_df.copy()

    # 1. Chuẩn hóa ZIP
    df["geolocation_zip_code_prefix"] = normalize_zip_code(
        df["geolocation_zip_code_prefix"]
    )

    # 2. Loại exact duplicate
    before_rows = len(df)

    df = (
        df
        .drop_duplicates()
        .reset_index(drop=True)
    )

    removed_rows = before_rows - len(df)

    logger.info(
        "Geolocation: đã loại %s exact duplicate.",
        f"{removed_rows:,}"
    )

    logger.info(
        "Transform geolocation hoàn tất: %s dòng.",
        f"{len(df):,}"
    )

    return df


def build_geolocation_lookup(
    geolocation_df: pd.DataFrame
) -> pd.DataFrame:

    df = geolocation_df.copy()

    geo_lookup = (
        df
        .groupby(
            "geolocation_zip_code_prefix",
            as_index=False
        )
        .agg(
            geolocation_lat=(
                "geolocation_lat",
                "median"
            ),
            geolocation_lng=(
                "geolocation_lng",
                "median"
            ),
            geolocation_city=(
                "geolocation_city",
                lambda s: (
                    s.mode().iloc[0]
                    if not s.mode().empty
                    else pd.NA
                )
            ),
            geolocation_state=(
                "geolocation_state",
                lambda s: (
                    s.mode().iloc[0]
                    if not s.mode().empty
                    else pd.NA
                )
            ),
        )
    )

    logger.info(
        "Geolocation lookup: %s ZIP đại diện.",
        f"{len(geo_lookup):,}"
    )

    return geo_lookup



# ORDERS


def transform_orders(
    orders_df: pd.DataFrame
) -> pd.DataFrame:

    df = orders_df.copy()

    df = convert_datetime_columns(
        df,
        ORDER_DATETIME_COLUMNS
    )

    logger.info(
        "Transform orders hoàn tất: %s dòng.",
        len(df)
    )

    return df



# ORDER ITEMS


def transform_order_items(
    order_items_df: pd.DataFrame
) -> pd.DataFrame:

    df = order_items_df.copy()

    df["shipping_limit_date"] = pd.to_datetime(
        df["shipping_limit_date"],
        errors="coerce"
    )

    logger.info(
        "Transform order_items hoàn tất: %s dòng.",
        len(df)
    )

    return df



# PAYMENTS


def transform_payments(
    payments_df: pd.DataFrame
) -> pd.DataFrame:

    df = payments_df.copy()

    logger.info(
        "Transform payments hoàn tất: %s dòng.",
        len(df)
    )

    return df



# REVIEWS


def transform_reviews(
    reviews_df: pd.DataFrame
) -> pd.DataFrame:


    df = reviews_df.copy()

    df = convert_datetime_columns(
        df,
        REVIEW_DATETIME_COLUMNS
    )

    logger.info(
        "Transform reviews hoàn tất: %s dòng.",
        len(df)
    )

    return df



# PRODUCTS


def transform_products(
    products_df: pd.DataFrame
) -> pd.DataFrame:


    df = products_df.copy()


    # 1. Chuyển các trường số đếm sang nullable Int64


    for column in PRODUCT_COUNT_COLUMNS:

        df[column] = (
            pd.to_numeric(
                df[column],
                errors="coerce"
            )
            .astype("Int64")
        )


    # 2. product_weight_g = 0 -> NULL


    zero_weight_mask = (
        df["product_weight_g"]
        .eq(0)
        .fillna(False)
    )

    zero_weight_count = int(
        zero_weight_mask.sum()
    )

    df.loc[
        zero_weight_mask,
        "product_weight_g"
    ] = pd.NA

    logger.info(
        "Products: chuyển %s product_weight_g = 0 thành NULL.",
        zero_weight_count
    )

    logger.info(
        "Transform products hoàn tất: %s dòng.",
        len(df)
    )

    return df



# CATEGORY TRANSLATION


def transform_category_translation(
    category_translation_df: pd.DataFrame
) -> pd.DataFrame:


    df = category_translation_df.copy()

    logger.info(
        "Transform category_translation hoàn tất: %s dòng.",
        len(df)
    )

    return df



# TRANSFORM TOÀN BỘ DATASET


def transform_all(
    raw_data: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:

    logger.info("=" * 70)
    logger.info("BẮT ĐẦU TRANSFORM")
    logger.info("=" * 70)

    transformed_data = {
        "customers": transform_customers(
            raw_data["customers"]
        ),

        "geolocation": transform_geolocation(
            raw_data["geolocation"]
        ),

        "order_items": transform_order_items(
            raw_data["order_items"]
        ),

        "payments": transform_payments(
            raw_data["payments"]
        ),

        "reviews": transform_reviews(
            raw_data["reviews"]
        ),

        "orders": transform_orders(
            raw_data["orders"]
        ),

        "products": transform_products(
            raw_data["products"]
        ),

        "sellers": transform_sellers(
            raw_data["sellers"]
        ),

        "category_translation": (
            transform_category_translation(
                raw_data["category_translation"]
            )
        ),
    }


    # GEOLOCATION LOOKUP

    transformed_data["geolocation_lookup"] = (
        build_geolocation_lookup(
            transformed_data["geolocation"]
        )
    )

    logger.info("=" * 70)
    logger.info("TRANSFORM HOÀN TẤT")
    logger.info("=" * 70)

    return transformed_data



# TEST RIÊNG transform.py


if __name__ == "__main__":

    from extract import extract_all
    from validate import validate_all_raw

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S"
    )


    #  EXTRACT


    raw_data = extract_all()


    # VALIDATE RAW


    validate_all_raw(
        raw_data
    )


    # TRANSFORM


    clean_data = transform_all(
        raw_data
    )

    # HIỂN THỊ KẾT QUẢ


    print("\n" + "=" * 75)
    print("KẾT QUẢ TRANSFORM")
    print("=" * 75)

    for table_name, df in clean_data.items():

        print(
            f"{table_name:<25}"
            f"{df.shape[0]:>12,} dòng   "
            f"{df.shape[1]:>2} cột"
        )

    print("=" * 75)