-- =========================================================
-- FACT_PAYMENTS
--
-- Grain:
--     1 dòng /
--     order_id + payment_sequential
--
-- Mục đích:
--     - payment type
--     - installments
--     - payment value
-- =========================================================

CREATE OR REPLACE TABLE
`olist-ecommerce-dwh.olist_dwh.fact_payments`
AS

SELECT
    -- -----------------------------------------------------
    -- COMPOSITE BUSINESS KEY
    -- -----------------------------------------------------

    p.order_id,

    p.payment_sequential,


    -- -----------------------------------------------------
    -- CUSTOMER FK
    -- -----------------------------------------------------

    dc.customer_sk,


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
    -- PAYMENT INFORMATION
    -- -----------------------------------------------------

    p.payment_type,

    p.payment_installments,

    p.payment_value


FROM
    `olist-ecommerce-dwh.olist_staging.payments`
    AS p


-- =========================================================
-- Lấy customer và purchase date từ orders.
-- =========================================================

LEFT JOIN
    `olist-ecommerce-dwh.olist_staging.orders`
    AS o

ON
    p.order_id
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
    dc.customer_id;