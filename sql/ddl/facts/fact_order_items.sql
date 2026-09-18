-- =========================================================
-- FACT_ORDER_ITEMS
--
-- Grain:
--     1 dòng /
--     order_id + order_item_id
--
-- Đây là Fact chi tiết nhất của nghiệp vụ bán hàng.
--
-- Measures:
--     price
--     freight_value
--     total_item_value
-- =========================================================

CREATE OR REPLACE TABLE
`olist-ecommerce-dwh.olist_dwh.fact_order_items`
AS

SELECT
    -- -----------------------------------------------------
    -- COMPOSITE BUSINESS KEY
    -- -----------------------------------------------------

    oi.order_id,

    oi.order_item_id,


    -- -----------------------------------------------------
    -- CUSTOMER FK
    -- -----------------------------------------------------

    dc.customer_sk,


    -- -----------------------------------------------------
    -- PRODUCT FK
    -- -----------------------------------------------------

    dp.product_sk,


    -- -----------------------------------------------------
    -- SELLER FK
    -- -----------------------------------------------------

    ds.seller_sk,


    -- -----------------------------------------------------
    -- PURCHASE DATE FK
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


    -- -----------------------------------------------------
    -- SHIPPING LIMIT DATE FK
    -- -----------------------------------------------------

    CASE
        WHEN oi.shipping_limit_date IS NULL
        THEN NULL

        ELSE CAST(
            FORMAT_DATE(
                '%Y%m%d',
                DATE(
                    oi.shipping_limit_date
                )
            )
            AS INT64
        )
    END AS shipping_limit_date_sk,


    -- -----------------------------------------------------
    -- NATURAL KEYS
    --
    -- Giữ lại để dễ debug / reconciliation.
    -- -----------------------------------------------------

    oi.product_id,

    oi.seller_id,


    -- -----------------------------------------------------
    -- DATETIME GỐC
    -- -----------------------------------------------------

    oi.shipping_limit_date,


    -- -----------------------------------------------------
    -- MEASURES
    -- -----------------------------------------------------

    oi.price,

    oi.freight_value,


    (
        oi.price
        +
        oi.freight_value
    ) AS total_item_value


FROM
    `olist-ecommerce-dwh.olist_staging.order_items`
    AS oi


-- =========================================================
-- Lấy customer + purchase timestamp của order.
-- =========================================================

LEFT JOIN
    `olist-ecommerce-dwh.olist_staging.orders`
    AS o

ON
    oi.order_id
    =
    o.order_id


-- =========================================================
-- CUSTOMER DIMENSION
-- =========================================================

LEFT JOIN
    `olist-ecommerce-dwh.olist_dwh.dim_customers`
    AS dc

ON
    o.customer_id
    =
    dc.customer_id


-- =========================================================
-- PRODUCT DIMENSION
-- =========================================================

LEFT JOIN
    `olist-ecommerce-dwh.olist_dwh.dim_products`
    AS dp

ON
    oi.product_id
    =
    dp.product_id


-- =========================================================
-- SELLER DIMENSION
-- =========================================================

LEFT JOIN
    `olist-ecommerce-dwh.olist_dwh.dim_sellers`
    AS ds

ON
    oi.seller_id
    =
    ds.seller_id;