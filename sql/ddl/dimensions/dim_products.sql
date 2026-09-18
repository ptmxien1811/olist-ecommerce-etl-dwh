-- =========================================================
-- DIM_PRODUCTS
--
-- Grain:
--     1 dòng / product_id
--
-- Nguồn:
--     olist_staging.products
--     olist_staging.category_translation
--
-- product_sk:
--     Surrogate Key của DWH
-- =========================================================

CREATE OR REPLACE TABLE
`olist-ecommerce-dwh.olist_dwh.dim_products`
AS

SELECT
    -- -----------------------------------------------------
    -- SURROGATE KEY
    -- -----------------------------------------------------

    ROW_NUMBER() OVER (
        ORDER BY p.product_id
    ) AS product_sk,


    -- -----------------------------------------------------
    -- NATURAL KEY
    -- -----------------------------------------------------

    p.product_id,


    -- -----------------------------------------------------
    -- CATEGORY
    -- -----------------------------------------------------

    p.product_category_name,

    ct.product_category_name_english,


    -- -----------------------------------------------------
    -- THÔNG TIN MÔ TẢ SẢN PHẨM
    --
    -- Giữ nguyên tên cột gốc của Olist.
    -- -----------------------------------------------------

    p.product_name_lenght,

    p.product_description_lenght,

    p.product_photos_qty,


    -- -----------------------------------------------------
    -- KÍCH THƯỚC / KHỐI LƯỢNG
    -- -----------------------------------------------------

    p.product_weight_g,

    p.product_length_cm,

    p.product_height_cm,

    p.product_width_cm


FROM
    `olist-ecommerce-dwh.olist_staging.products`
    AS p


LEFT JOIN
    `olist-ecommerce-dwh.olist_staging.category_translation`
    AS ct

ON
    p.product_category_name
    =
    ct.product_category_name;