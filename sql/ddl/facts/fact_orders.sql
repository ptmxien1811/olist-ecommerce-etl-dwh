-- =========================================================
-- FACT_ORDERS
--
-- Grain:
--     1 dòng / order_id
--
-- Loại Fact:
--     Accumulating Snapshot Fact
--
-- Mục đích:
--     - trạng thái đơn hàng
--     - thời gian xử lý đơn
--     - thời gian giao
--     - giao trễ
-- =========================================================

CREATE OR REPLACE TABLE
`olist-ecommerce-dwh.olist_dwh.fact_orders`
AS

SELECT
    -- -----------------------------------------------------
    -- BUSINESS KEY
    -- -----------------------------------------------------

    o.order_id,


    -- -----------------------------------------------------
    -- CUSTOMER FOREIGN KEY
    -- -----------------------------------------------------

    dc.customer_sk,


    -- -----------------------------------------------------
    -- ROLE-PLAYING DATE KEYS
    -- -----------------------------------------------------

    CASE
        WHEN o.order_purchase_timestamp IS NULL
        THEN NULL

        ELSE CAST(
            FORMAT_DATE(
                '%Y%m%d',
                DATE(
                    o.order_purchase_timestamp
                )
            )
            AS INT64
        )
    END AS purchase_date_sk,


    CASE
        WHEN o.order_approved_at IS NULL
        THEN NULL

        ELSE CAST(
            FORMAT_DATE(
                '%Y%m%d',
                DATE(
                    o.order_approved_at
                )
            )
            AS INT64
        )
    END AS approved_date_sk,


    CASE
        WHEN o.order_delivered_carrier_date IS NULL
        THEN NULL

        ELSE CAST(
            FORMAT_DATE(
                '%Y%m%d',
                DATE(
                    o.order_delivered_carrier_date
                )
            )
            AS INT64
        )
    END AS carrier_date_sk,


    CASE
        WHEN o.order_delivered_customer_date IS NULL
        THEN NULL

        ELSE CAST(
            FORMAT_DATE(
                '%Y%m%d',
                DATE(
                    o.order_delivered_customer_date
                )
            )
            AS INT64
        )
    END AS delivered_date_sk,


    CASE
        WHEN o.order_estimated_delivery_date IS NULL
        THEN NULL

        ELSE CAST(
            FORMAT_DATE(
                '%Y%m%d',
                DATE(
                    o.order_estimated_delivery_date
                )
            )
            AS INT64
        )
    END AS estimated_delivery_date_sk,


    -- -----------------------------------------------------
    -- NATURAL KEY ĐƯỢC GIỮ LẠI ĐỂ ĐỐI CHIẾU
    -- -----------------------------------------------------

    o.customer_id,


    -- -----------------------------------------------------
    -- ORDER STATUS
    -- -----------------------------------------------------

    o.order_status,


    -- -----------------------------------------------------
    -- TIMESTAMP GỐC
    -- -----------------------------------------------------

    o.order_purchase_timestamp,

    o.order_approved_at,

    o.order_delivered_carrier_date,

    o.order_delivered_customer_date,

    o.order_estimated_delivery_date,


    -- -----------------------------------------------------
    -- DERIVED MEASURES
    -- -----------------------------------------------------

    CASE
        WHEN o.order_delivered_customer_date IS NULL
          OR o.order_purchase_timestamp IS NULL

        THEN NULL

        ELSE DATE_DIFF(
            DATE(
                o.order_delivered_customer_date
            ),
            DATE(
                o.order_purchase_timestamp
            ),
            DAY
        )
    END AS delivery_days,


    CASE
        WHEN o.order_estimated_delivery_date IS NULL
          OR o.order_purchase_timestamp IS NULL

        THEN NULL

        ELSE DATE_DIFF(
            DATE(
                o.order_estimated_delivery_date
            ),
            DATE(
                o.order_purchase_timestamp
            ),
            DAY
        )
    END AS estimated_delivery_days,


    CASE
        WHEN o.order_delivered_customer_date IS NULL
          OR o.order_estimated_delivery_date IS NULL

        THEN NULL

        ELSE DATE_DIFF(
            DATE(
                o.order_delivered_customer_date
            ),
            DATE(
                o.order_estimated_delivery_date
            ),
            DAY
        )
    END AS delivery_delay_days,


    CASE
        WHEN o.order_delivered_customer_date IS NULL
          OR o.order_estimated_delivery_date IS NULL

        THEN NULL

        ELSE
            DATE(
                o.order_delivered_customer_date
            )
            >
            DATE(
                o.order_estimated_delivery_date
            )

    END AS is_late_delivery


FROM
    `olist-ecommerce-dwh.olist_staging.orders`
    AS o


LEFT JOIN
    `olist-ecommerce-dwh.olist_dwh.dim_customers`
    AS dc

ON
    o.customer_id
    =
    dc.customer_id;