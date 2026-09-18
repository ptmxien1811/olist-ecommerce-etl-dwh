CREATE OR REPLACE TABLE
`olist-ecommerce-dwh.olist_dwh.dim_customers`
AS

SELECT
    ROW_NUMBER() OVER (
        ORDER BY c.customer_id
    ) AS customer_sk,

    c.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,

    g.geolocation_lat AS customer_lat,
    g.geolocation_lng AS customer_lng

FROM
    `olist-ecommerce-dwh.olist_staging.customers` AS c

LEFT JOIN
    `olist-ecommerce-dwh.olist_staging.geolocation_lookup` AS g

ON
    c.customer_zip_code_prefix
    =
    g.geolocation_zip_code_prefix;