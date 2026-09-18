-- =========================================================
-- DIM_SELLERS
--
-- Grain:
--     1 dòng / seller_id
--
-- Nguồn:
--     olist_staging.sellers
--     olist_staging.geolocation_lookup
--
-- seller_sk:
--     Surrogate Key của DWH
-- =========================================================

CREATE OR REPLACE TABLE
`olist-ecommerce-dwh.olist_dwh.dim_sellers`
AS

SELECT
    -- -----------------------------------------------------
    -- SURROGATE KEY
    -- -----------------------------------------------------

    ROW_NUMBER() OVER (
        ORDER BY s.seller_id
    ) AS seller_sk,


    -- -----------------------------------------------------
    -- NATURAL KEY
    -- -----------------------------------------------------

    s.seller_id,


    -- -----------------------------------------------------
    -- THÔNG TIN SELLER
    -- -----------------------------------------------------

    s.seller_zip_code_prefix,

    s.seller_city,

    s.seller_state,


    -- -----------------------------------------------------
    -- THÔNG TIN ĐỊA LÝ
    -- -----------------------------------------------------

    g.geolocation_lat
        AS seller_lat,

    g.geolocation_lng
        AS seller_lng


FROM
    `olist-ecommerce-dwh.olist_staging.sellers`
    AS s


LEFT JOIN
    `olist-ecommerce-dwh.olist_staging.geolocation_lookup`
    AS g

ON
    s.seller_zip_code_prefix
    =
    g.geolocation_zip_code_prefix;