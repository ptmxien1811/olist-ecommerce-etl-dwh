-- =========================================================
-- DIM_DATE
--
-- Grain:
--     1 dòng / ngày
--
-- Date Dimension dùng chung cho:
--
-- fact_orders
-- fact_order_items
-- fact_payments
-- fact_reviews
--
-- date_sk:
--     YYYYMMDD
--
-- Ví dụ:
--     2018-08-28 -> 20180828
-- =========================================================

CREATE OR REPLACE TABLE
`olist-ecommerce-dwh.olist_dwh.dim_date`
AS


-- =========================================================
-- STEP 1
-- Thu thập tất cả ngày có trong dữ liệu nghiệp vụ.
-- =========================================================

WITH all_dates AS (

    -- -----------------------------------------------------
    -- ORDERS
    -- -----------------------------------------------------

    SELECT
        DATE(order_purchase_timestamp)
            AS full_date

    FROM
        `olist-ecommerce-dwh.olist_staging.orders`

    WHERE
        order_purchase_timestamp IS NOT NULL


    UNION ALL


    SELECT
        DATE(order_approved_at)

    FROM
        `olist-ecommerce-dwh.olist_staging.orders`

    WHERE
        order_approved_at IS NOT NULL


    UNION ALL


    SELECT
        DATE(order_delivered_carrier_date)

    FROM
        `olist-ecommerce-dwh.olist_staging.orders`

    WHERE
        order_delivered_carrier_date IS NOT NULL


    UNION ALL


    SELECT
        DATE(order_delivered_customer_date)

    FROM
        `olist-ecommerce-dwh.olist_staging.orders`

    WHERE
        order_delivered_customer_date IS NOT NULL


    UNION ALL


    SELECT
        DATE(order_estimated_delivery_date)

    FROM
        `olist-ecommerce-dwh.olist_staging.orders`

    WHERE
        order_estimated_delivery_date IS NOT NULL


    -- -----------------------------------------------------
    -- ORDER ITEMS
    -- -----------------------------------------------------

    UNION ALL


    SELECT
        DATE(shipping_limit_date)

    FROM
        `olist-ecommerce-dwh.olist_staging.order_items`

    WHERE
        shipping_limit_date IS NOT NULL


    -- -----------------------------------------------------
    -- REVIEWS
    -- -----------------------------------------------------

    UNION ALL


    SELECT
        DATE(review_creation_date)

    FROM
        `olist-ecommerce-dwh.olist_staging.reviews`

    WHERE
        review_creation_date IS NOT NULL


    UNION ALL


    SELECT
        DATE(review_answer_timestamp)

    FROM
        `olist-ecommerce-dwh.olist_staging.reviews`

    WHERE
        review_answer_timestamp IS NOT NULL
),


-- =========================================================
-- STEP 2
-- Xác định ngày nhỏ nhất và lớn nhất.
-- =========================================================

date_bounds AS (

    SELECT
        MIN(full_date)
            AS min_date,

        MAX(full_date)
            AS max_date

    FROM
        all_dates
),


-- =========================================================
-- STEP 3
-- Sinh liên tục tất cả ngày trong khoảng.
-- =========================================================

calendar AS (

    SELECT
        full_date

    FROM
        date_bounds,

        UNNEST(
            GENERATE_DATE_ARRAY(
                min_date,
                max_date
            )
        ) AS full_date
)


-- =========================================================
-- STEP 4
-- Tạo các thuộc tính của Date Dimension.
-- =========================================================

SELECT

    CAST(
        FORMAT_DATE(
            '%Y%m%d',
            full_date
        )
        AS INT64
    ) AS date_sk,


    full_date,


    EXTRACT(
        DAY
        FROM full_date
    ) AS day,


    EXTRACT(
        DAYOFWEEK
        FROM full_date
    ) AS day_of_week,


    FORMAT_DATE(
        '%A',
        full_date
    ) AS day_name,


    EXTRACT(
        WEEK
        FROM full_date
    ) AS week_of_year,


    EXTRACT(
        MONTH
        FROM full_date
    ) AS month,


    FORMAT_DATE(
        '%B',
        full_date
    ) AS month_name,


    EXTRACT(
        QUARTER
        FROM full_date
    ) AS quarter,


    EXTRACT(
        YEAR
        FROM full_date
    ) AS year,


    CASE
        WHEN EXTRACT(
            DAYOFWEEK
            FROM full_date
        ) IN (1, 7)

        THEN TRUE

        ELSE FALSE
    END AS is_weekend


FROM
    calendar


ORDER BY
    full_date;