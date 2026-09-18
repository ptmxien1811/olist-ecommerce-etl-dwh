-- =========================================================
-- FACT_REVIEWS
--
-- Grain:
--     1 dòng /
--     review_id + order_id
--
-- Mục đích:
--     - điểm đánh giá
--     - nội dung review
--     - thời gian phản hồi review
-- =========================================================

CREATE OR REPLACE TABLE
`olist-ecommerce-dwh.olist_dwh.fact_reviews`
AS

SELECT
    -- -----------------------------------------------------
    -- COMPOSITE BUSINESS KEY
    -- -----------------------------------------------------

    r.review_id,

    r.order_id,


    -- -----------------------------------------------------
    -- CUSTOMER FK
    -- -----------------------------------------------------

    dc.customer_sk,


    -- -----------------------------------------------------
    -- REVIEW DATE FK
    -- -----------------------------------------------------

    CASE
        WHEN r.review_creation_date IS NULL
        THEN NULL

        ELSE CAST(
            FORMAT_DATE(
                '%Y%m%d',
                DATE(
                    r.review_creation_date
                )
            )
            AS INT64
        )
    END AS review_date_sk,


    -- -----------------------------------------------------
    -- REVIEW DATA
    -- -----------------------------------------------------

    r.review_score,

    r.review_comment_title,

    r.review_comment_message,

    r.review_creation_date,

    r.review_answer_timestamp,


    -- -----------------------------------------------------
    -- DERIVED MEASURE
    -- -----------------------------------------------------

    CASE
        WHEN r.review_answer_timestamp IS NULL
          OR r.review_creation_date IS NULL

        THEN NULL

        ELSE DATE_DIFF(
            DATE(
                r.review_answer_timestamp
            ),
            DATE(
                r.review_creation_date
            ),
            DAY
        )
    END AS review_response_days


FROM
    `olist-ecommerce-dwh.olist_staging.reviews`
    AS r


-- =========================================================
-- Lấy customer_id từ orders.
-- =========================================================

LEFT JOIN
    `olist-ecommerce-dwh.olist_staging.orders`
    AS o

ON
    r.order_id
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