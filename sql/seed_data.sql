-- Part 1, Task 2: load the three CSVs (run after schema.sql, from the repo root)
--   sqlite3 sql/shop.db < sql/seed_data.sql
--
-- Re-runnable: staging tables are rebuilt and the real tables emptied each time.
-- Each CSV is imported as raw text into a staging table, then copied across.
-- Blank cells become NULL via NULLIF(x, ''), never empty strings.
-- No cleaning happens here (casing, duplicates etc. are fixed in Python).

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS stg_customers;
DROP TABLE IF EXISTS stg_products;
DROP TABLE IF EXISTS stg_orders;

CREATE TABLE stg_customers (customer_id TEXT, name TEXT, city TEXT, city_tier TEXT,
                            signup_date TEXT, acquisition_source TEXT);
CREATE TABLE stg_products  (product_id TEXT, name TEXT, category TEXT, price_inr TEXT);
CREATE TABLE stg_orders    (order_id TEXT, customer_id TEXT, product_id TEXT, order_date TEXT,
                            quantity TEXT, discount_pct TEXT, payment_method TEXT,
                            rating TEXT, returned TEXT);

.import --csv --skip 1 data/customers.csv stg_customers
.import --csv --skip 1 data/products.csv stg_products
.import --csv --skip 1 data/orders.csv stg_orders

DELETE FROM orders;
DELETE FROM customers;
DELETE FROM products;

INSERT INTO customers (customer_id, name, city, city_tier, signup_date, acquisition_source)
SELECT customer_id, name, city, CAST(city_tier AS INTEGER), signup_date, acquisition_source
FROM stg_customers;

INSERT INTO products (product_id, name, category, price_inr)
SELECT product_id, name, category, CAST(price_inr AS REAL)
FROM stg_products;

INSERT INTO orders (order_id, customer_id, product_id, order_date, quantity,
                    discount_pct, payment_method, rating, returned)
SELECT order_id,
       customer_id,
       product_id,
       order_date,
       CAST(quantity AS INTEGER),
       CAST(NULLIF(discount_pct, '') AS REAL),
       payment_method,  -- raw casing kept on purpose; Python cleans it
       CAST(NULLIF(rating, '') AS INTEGER),
       CAST(returned AS INTEGER)
FROM stg_orders;

DROP TABLE stg_customers;
DROP TABLE stg_products;
DROP TABLE stg_orders;

-- Verify: expected 45 / 16 / 180
SELECT 'customers' AS tbl, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'orders',   COUNT(*) FROM orders;

-- Verify blanks loaded as NULL, not ''
SELECT SUM(discount_pct IS NULL) AS null_discounts,
       SUM(rating IS NULL)       AS null_ratings,
       SUM(discount_pct = '' OR rating = '') AS empty_strings
FROM orders;
