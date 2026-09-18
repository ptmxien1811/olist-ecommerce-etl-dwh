from __future__ import annotations

import logging
import os

from google.cloud import bigquery


# CẤU HÌNH BIGQUERY


PROJECT_ID = "olist-ecommerce-dwh"

STAGING_DATASET = "olist_staging"

DWH_DATASET = "olist_dwh"

LOCATION = "US"


# GOOGLE CLOUD PROJECT ENVIRONMENT

os.environ.setdefault(
    "GOOGLE_CLOUD_PROJECT",
    PROJECT_ID,
)


# LOGGER


logger = logging.getLogger(__name__)



# CUSTOM EXCEPTION


class DWHReconciliationError(Exception):

    pass



# BIGQUERY CLIENT


def create_bigquery_client() -> bigquery.Client:


    return bigquery.Client(
        project=PROJECT_ID,
        location=LOCATION,
    )



# HÀM CHẠY QUERY VÀ LẤY 1 DÒNG KẾT QUẢ


def query_one_row(
    client: bigquery.Client,
    sql: str,
):


    query_job = client.query(
        sql,
        location=LOCATION,
    )

    rows = list(
        query_job.result()
    )

    if not rows:

        raise DWHReconciliationError(
            "Query Reconciliation không trả về kết quả."
        )

    return rows[0]


# 1. RECONCILIATION ROW COUNT


def reconcile_fact_row_counts(
    client: bigquery.Client,
) -> None:

    logger.info(
        "RECONCILIATION - "
        "Kiểm tra row count Staging <-> Fact."
    )

    mappings = {
        "orders": "fact_orders",
        "order_items": "fact_order_items",
        "payments": "fact_payments",
        "reviews": "fact_reviews",
    }

    for staging_table, fact_table in mappings.items():

        sql = f"""
        SELECT

            (
                SELECT COUNT(*)
                FROM
                    `{PROJECT_ID}.{STAGING_DATASET}.{staging_table}`
            ) AS staging_rows,

            (
                SELECT COUNT(*)
                FROM
                    `{PROJECT_ID}.{DWH_DATASET}.{fact_table}`
            ) AS dwh_rows
        """

        row = query_one_row(
            client=client,
            sql=sql,
        )

        staging_rows = row["staging_rows"]
        dwh_rows = row["dwh_rows"]

        if staging_rows != dwh_rows:

            raise DWHReconciliationError(
                f"{staging_table} -> {fact_table}: "
                f"row count không khớp. "
                f"Staging={staging_rows:,}, "
                f"DWH={dwh_rows:,}."
            )

        logger.info(
            "ROW COUNT PASS - %-15s -> %-20s | %s dòng",
            staging_table,
            fact_table,
            f"{staging_rows:,}",
        )



# 2. VALIDATE DIMENSION KEYS

def validate_dimension_keys(
    client: bigquery.Client,
) -> None:

    logger.info(
        "RECONCILIATION - Kiểm tra Dimension Keys."
    )

    dimensions = {

        "dim_customers": (
            "customer_sk",
            "customer_id",
        ),

        "dim_products": (
            "product_sk",
            "product_id",
        ),

        "dim_sellers": (
            "seller_sk",
            "seller_id",
        ),

        "dim_date": (
            "date_sk",
            "full_date",
        ),
    }

    for (
        table_name,
        (
            surrogate_key,
            natural_key,
        ),
    ) in dimensions.items():

        sql = f"""
        SELECT

            COUNT(*) AS total_rows,

            COUNT(
                DISTINCT {surrogate_key}
            ) AS distinct_surrogate_key,

            COUNT(
                DISTINCT {natural_key}
            ) AS distinct_natural_key,

            COUNTIF(
                {surrogate_key} IS NULL
            ) AS null_surrogate_key

        FROM
            `{PROJECT_ID}.{DWH_DATASET}.{table_name}`
        """

        row = query_one_row(
            client=client,
            sql=sql,
        )

        total_rows = row["total_rows"]

        distinct_surrogate_key = (
            row["distinct_surrogate_key"]
        )

        distinct_natural_key = (
            row["distinct_natural_key"]
        )

        null_surrogate_key = (
            row["null_surrogate_key"]
        )


        # Surrogate Key không được NULL


        if null_surrogate_key > 0:

            raise DWHReconciliationError(
                f"{table_name}.{surrogate_key} "
                f"có {null_surrogate_key:,} giá trị NULL."
            )


        # Surrogate Key phải UNIQUE

        if (
            total_rows
            != distinct_surrogate_key
        ):

            raise DWHReconciliationError(
                f"{table_name}.{surrogate_key} "
                "không unique. "
                f"Rows={total_rows:,}, "
                f"Distinct={distinct_surrogate_key:,}."
            )


        # Natural Key phải UNIQUE theo grain hiện tại


        if (
            total_rows
            != distinct_natural_key
        ):

            raise DWHReconciliationError(
                f"{table_name}.{natural_key} "
                "không unique theo grain hiện tại. "
                f"Rows={total_rows:,}, "
                f"Distinct={distinct_natural_key:,}."
            )

        logger.info(
            "DIMENSION KEY PASS - %-20s | %s dòng",
            table_name,
            f"{total_rows:,}",
        )



# 3. VALIDATE FACT GRAIN

def validate_fact_grains(
    client: bigquery.Client,
) -> None:

    logger.info(
        "RECONCILIATION - Kiểm tra Fact Grain."
    )


    # FACT ORDERS


    sql = f"""
    SELECT

        COUNT(*) AS total_rows,

        COUNT(
            DISTINCT order_id
        ) AS distinct_grain

    FROM
        `{PROJECT_ID}.{DWH_DATASET}.fact_orders`
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    if (
        row["total_rows"]
        != row["distinct_grain"]
    ):

        raise DWHReconciliationError(
            "fact_orders vi phạm grain "
            "1 dòng / order_id. "
            f"Rows={row['total_rows']:,}, "
            f"Distinct={row['distinct_grain']:,}."
        )

    logger.info(
        "FACT GRAIN PASS - fact_orders | %s dòng",
        f"{row['total_rows']:,}",
    )

    # FACT ORDER ITEMS
    sql = f"""
    SELECT

        COUNT(*) AS total_rows,

        COUNT(
            DISTINCT CONCAT(
                order_id,
                '|',
                CAST(
                    order_item_id
                    AS STRING
                )
            )
        ) AS distinct_grain

    FROM
        `{PROJECT_ID}.{DWH_DATASET}.fact_order_items`
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    if (
        row["total_rows"]
        != row["distinct_grain"]
    ):

        raise DWHReconciliationError(
            "fact_order_items vi phạm grain "
            "order_id + order_item_id. "
            f"Rows={row['total_rows']:,}, "
            f"Distinct={row['distinct_grain']:,}."
        )

    logger.info(
        "FACT GRAIN PASS - fact_order_items | %s dòng",
        f"{row['total_rows']:,}",
    )

    # FACT PAYMENTS

    sql = f"""
    SELECT

        COUNT(*) AS total_rows,

        COUNT(
            DISTINCT CONCAT(
                order_id,
                '|',
                CAST(
                    payment_sequential
                    AS STRING
                )
            )
        ) AS distinct_grain

    FROM
        `{PROJECT_ID}.{DWH_DATASET}.fact_payments`
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    if (
        row["total_rows"]
        != row["distinct_grain"]
    ):

        raise DWHReconciliationError(
            "fact_payments vi phạm grain "
            "order_id + payment_sequential. "
            f"Rows={row['total_rows']:,}, "
            f"Distinct={row['distinct_grain']:,}."
        )

    logger.info(
        "FACT GRAIN PASS - fact_payments | %s dòng",
        f"{row['total_rows']:,}",
    )

    sql = f"""
    SELECT

        COUNT(*) AS total_rows,

        COUNT(
            DISTINCT CONCAT(
                review_id,
                '|',
                order_id
            )
        ) AS distinct_grain

    FROM
        `{PROJECT_ID}.{DWH_DATASET}.fact_reviews`
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    if (
        row["total_rows"]
        != row["distinct_grain"]
    ):

        raise DWHReconciliationError(
            "fact_reviews vi phạm grain "
            "review_id + order_id. "
            f"Rows={row['total_rows']:,}, "
            f"Distinct={row['distinct_grain']:,}."
        )

    logger.info(
        "FACT GRAIN PASS - fact_reviews | %s dòng",
        f"{row['total_rows']:,}",
    )



# 4. VALIDATE DIMENSION KEYS TRONG FACT


def validate_fact_dimension_keys(
    client: bigquery.Client,
) -> None:

    logger.info(
        "RECONCILIATION - "
        "Kiểm tra Dimension Key trong Fact."
    )

    # FACT ORDERS

    sql = f"""
    SELECT

        COUNTIF(
            customer_sk IS NULL
        ) AS missing_customer_sk

    FROM
        `{PROJECT_ID}.{DWH_DATASET}.fact_orders`
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    if row["missing_customer_sk"] > 0:

        raise DWHReconciliationError(
            "fact_orders có "
            f"{row['missing_customer_sk']:,} "
            "customer_sk NULL."
        )

    logger.info(
        "FACT DIMENSION KEY PASS - fact_orders"
    )


    # FACT ORDER ITEMS

    sql = f"""
    SELECT

        COUNTIF(
            customer_sk IS NULL
        ) AS missing_customer_sk,

        COUNTIF(
            product_sk IS NULL
        ) AS missing_product_sk,

        COUNTIF(
            seller_sk IS NULL
        ) AS missing_seller_sk

    FROM
        `{PROJECT_ID}.{DWH_DATASET}.fact_order_items`
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    missing_customer_sk = (
        row["missing_customer_sk"]
    )

    missing_product_sk = (
        row["missing_product_sk"]
    )

    missing_seller_sk = (
        row["missing_seller_sk"]
    )

    if (
        missing_customer_sk > 0
        or missing_product_sk > 0
        or missing_seller_sk > 0
    ):

        raise DWHReconciliationError(
            "fact_order_items có missing Dimension Key: "
            f"customer_sk={missing_customer_sk:,}, "
            f"product_sk={missing_product_sk:,}, "
            f"seller_sk={missing_seller_sk:,}."
        )

    logger.info(
        "FACT DIMENSION KEY PASS - fact_order_items"
    )


    # FACT PAYMENTS

    sql = f"""
    SELECT

        COUNTIF(
            customer_sk IS NULL
        ) AS missing_customer_sk

    FROM
        `{PROJECT_ID}.{DWH_DATASET}.fact_payments`
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    if row["missing_customer_sk"] > 0:

        raise DWHReconciliationError(
            "fact_payments có "
            f"{row['missing_customer_sk']:,} "
            "customer_sk NULL."
        )

    logger.info(
        "FACT DIMENSION KEY PASS - fact_payments"
    )

    # FACT REVIEWS


    sql = f"""
    SELECT

        COUNTIF(
            customer_sk IS NULL
        ) AS missing_customer_sk

    FROM
        `{PROJECT_ID}.{DWH_DATASET}.fact_reviews`
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    if row["missing_customer_sk"] > 0:

        raise DWHReconciliationError(
            "fact_reviews có "
            f"{row['missing_customer_sk']:,} "
            "customer_sk NULL."
        )

    logger.info(
        "FACT DIMENSION KEY PASS - fact_reviews"
    )



# 5. RECONCILIATION ORDER ITEM MEASURES

def reconcile_order_item_measures(
    client: bigquery.Client,
) -> None:

    logger.info(
        "RECONCILIATION - "
        "Kiểm tra price và freight_value."
    )

    sql = f"""
    SELECT

        ROUND(
            (
                SELECT SUM(price)
                FROM
                    `{PROJECT_ID}.{STAGING_DATASET}.order_items`
            ),
            2
        ) AS staging_price,

        ROUND(
            (
                SELECT SUM(price)
                FROM
                    `{PROJECT_ID}.{DWH_DATASET}.fact_order_items`
            ),
            2
        ) AS dwh_price,

        ROUND(
            (
                SELECT SUM(freight_value)
                FROM
                    `{PROJECT_ID}.{STAGING_DATASET}.order_items`
            ),
            2
        ) AS staging_freight,

        ROUND(
            (
                SELECT SUM(freight_value)
                FROM
                    `{PROJECT_ID}.{DWH_DATASET}.fact_order_items`
            ),
            2
        ) AS dwh_freight
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    staging_price = row["staging_price"]
    dwh_price = row["dwh_price"]

    staging_freight = row["staging_freight"]
    dwh_freight = row["dwh_freight"]


    if staging_price != dwh_price:

        raise DWHReconciliationError(
            "SUM(price) không khớp. "
            f"Staging={staging_price}, "
            f"DWH={dwh_price}."
        )


    if staging_freight != dwh_freight:

        raise DWHReconciliationError(
            "SUM(freight_value) không khớp. "
            f"Staging={staging_freight}, "
            f"DWH={dwh_freight}."
        )


    logger.info(
        "MEASURE PASS - price | "
        "Staging=%s | DWH=%s",
        staging_price,
        dwh_price,
    )

    logger.info(
        "MEASURE PASS - freight_value | "
        "Staging=%s | DWH=%s",
        staging_freight,
        dwh_freight,
    )


# 6. RECONCILIATION PAYMENT VALUE


def reconcile_payment_value(
    client: bigquery.Client,
) -> None:

    logger.info(
        "RECONCILIATION - Kiểm tra payment_value."
    )

    sql = f"""
    SELECT

        ROUND(
            (
                SELECT SUM(payment_value)
                FROM
                    `{PROJECT_ID}.{STAGING_DATASET}.payments`
            ),
            2
        ) AS staging_payment,

        ROUND(
            (
                SELECT SUM(payment_value)
                FROM
                    `{PROJECT_ID}.{DWH_DATASET}.fact_payments`
            ),
            2
        ) AS dwh_payment
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    staging_payment = (
        row["staging_payment"]
    )

    dwh_payment = (
        row["dwh_payment"]
    )

    if staging_payment != dwh_payment:

        raise DWHReconciliationError(
            "SUM(payment_value) không khớp. "
            f"Staging={staging_payment}, "
            f"DWH={dwh_payment}."
        )

    logger.info(
        "MEASURE PASS - payment_value | "
        "Staging=%s | DWH=%s",
        staging_payment,
        dwh_payment,
    )


# 7. VALIDATE DIM_DATE

def validate_dim_date(
    client: bigquery.Client,
) -> None:

    logger.info(
        "RECONCILIATION - Kiểm tra dim_date."
    )

    sql = f"""
    SELECT

        COUNT(*) AS total_rows,

        COUNT(
            DISTINCT date_sk
        ) AS distinct_date_sk,

        COUNT(
            DISTINCT full_date
        ) AS distinct_full_date,

        COUNTIF(
            date_sk IS NULL
        ) AS null_date_sk,

        COUNTIF(
            full_date IS NULL
        ) AS null_full_date,

        MIN(full_date)
            AS min_date,

        MAX(full_date)
            AS max_date

    FROM
        `{PROJECT_ID}.{DWH_DATASET}.dim_date`
    """

    row = query_one_row(
        client=client,
        sql=sql,
    )

    total_rows = row["total_rows"]

    distinct_date_sk = (
        row["distinct_date_sk"]
    )

    distinct_full_date = (
        row["distinct_full_date"]
    )

    null_date_sk = row["null_date_sk"]

    null_full_date = row["null_full_date"]


    if null_date_sk > 0:

        raise DWHReconciliationError(
            "dim_date.date_sk có "
            f"{null_date_sk:,} giá trị NULL."
        )


    if null_full_date > 0:

        raise DWHReconciliationError(
            "dim_date.full_date có "
            f"{null_full_date:,} giá trị NULL."
        )


    if total_rows != distinct_date_sk:

        raise DWHReconciliationError(
            "dim_date.date_sk không unique."
        )


    if total_rows != distinct_full_date:

        raise DWHReconciliationError(
            "dim_date.full_date không unique."
        )


    logger.info(
        "DIM_DATE PASS - %s -> %s | %s ngày",
        row["min_date"],
        row["max_date"],
        f"{total_rows:,}",
    )



# 8. VALIDATE DATE KEYS TRONG FACT


def validate_fact_date_keys(
    client: bigquery.Client,
) -> None:

    logger.info(
        "RECONCILIATION - "
        "Kiểm tra Date Keys trong Fact."
    )

    checks = [

        (
            "fact_orders",
            "purchase_date_sk",
        ),

        (
            "fact_orders",
            "approved_date_sk",
        ),

        (
            "fact_orders",
            "carrier_date_sk",
        ),

        (
            "fact_orders",
            "delivered_date_sk",
        ),

        (
            "fact_orders",
            "estimated_delivery_date_sk",
        ),

        (
            "fact_order_items",
            "purchase_date_sk",
        ),

        (
            "fact_order_items",
            "shipping_limit_date_sk",
        ),

        (
            "fact_payments",
            "purchase_date_sk",
        ),

        (
            "fact_reviews",
            "review_date_sk",
        ),
    ]

    for table_name, date_key in checks:

        sql = f"""
        SELECT

            COUNT(*) AS orphan_count

        FROM
            `{PROJECT_ID}.{DWH_DATASET}.{table_name}`
            AS f

        LEFT JOIN
            `{PROJECT_ID}.{DWH_DATASET}.dim_date`
            AS d

        ON
            f.{date_key}
            =
            d.date_sk

        WHERE
            f.{date_key} IS NOT NULL

            AND d.date_sk IS NULL
        """

        row = query_one_row(
            client=client,
            sql=sql,
        )

        orphan_count = (
            row["orphan_count"]
        )

        if orphan_count > 0:

            raise DWHReconciliationError(
                f"{table_name}.{date_key} có "
                f"{orphan_count:,} Date Key "
                "không tồn tại trong dim_date."
            )

        logger.info(
            "DATE KEY PASS - %s.%s",
            table_name,
            date_key,
        )



# HÀM RECONCILIATION TOÀN BỘ DWH


def reconcile_dwh() -> bool:


    logger.info("=" * 70)
    logger.info(
        "BẮT ĐẦU DWH RECONCILIATION"
    )
    logger.info("=" * 70)



    # BIGQUERY CONNECTION


    client = create_bigquery_client()

    logger.info(
        "BIGQUERY CONNECTION - Project: %s",
        PROJECT_ID,
    )

    logger.info(
        "BIGQUERY CONNECTION - Staging: %s",
        STAGING_DATASET,
    )

    logger.info(
        "BIGQUERY CONNECTION - DWH: %s",
        DWH_DATASET,
    )

    logger.info(
        "BIGQUERY CONNECTION - Location: %s",
        LOCATION,
    )



    # STAGING <-> FACT ROW COUNT


    reconcile_fact_row_counts(
        client
    )



    # DIMENSION KEYS


    validate_dimension_keys(
        client
    )


    # FACT GRAIN


    validate_fact_grains(
        client
    )



    # FACT DIMENSION KEYS


    validate_fact_dimension_keys(
        client
    )



    # ORDER ITEM MEASURES


    reconcile_order_item_measures(
        client
    )


    # PAYMENT VALUE


    reconcile_payment_value(
        client
    )


    # DIM_DATE

    validate_dim_date(
        client
    )



    # FACT DATE KEYS


    validate_fact_date_keys(
        client
    )


    # SUCCESS


    logger.info("=" * 70)
    logger.info(
        "DWH RECONCILIATION: PASS"
    )

    logger.info(
        "Data Warehouse đủ điều kiện "
        "chuyển sang BI / Analytics."
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

    reconcile_dwh()