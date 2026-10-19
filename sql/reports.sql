-- Part 1, Task 3: nine business reports on the RAW data
-- (duplicates and mixed casing still present; cleaning happens in Python).
-- Order value = quantity * price * (1 - discount/100), NULL discount = 0%.

-- (a) Order totals: total orders, revenue, average order value
-- Output:
-- total_orders | revenue_inr | avg_order_value_inr
-- 180          | 869202.0    | 4828.9
SELECT COUNT(*)                                                                    AS total_orders,
       ROUND(SUM(o.quantity * p.price_inr * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS revenue_inr,
       ROUND(AVG(o.quantity * p.price_inr * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS avg_order_value_inr
FROM orders o
JOIN products p ON p.product_id = o.product_id;

-- (b) COUNT(*) vs COUNT(col): COUNT(rating) skips NULLs, so the gap = unrated orders
-- Output:
-- all_orders | rated_orders | orders_without_rating
-- 180        | 164          | 16
SELECT COUNT(*)                 AS all_orders,
       COUNT(rating)            AS rated_orders,
       COUNT(*) - COUNT(rating) AS orders_without_rating
FROM orders;

-- (c1) Customers with zero orders, way 1: LEFT JOIN, keep rows with no match
-- Output:
-- customer_id | name
-- C007        | Priya Gupta
-- C019        | Divya Nair
-- C027        | Simran Khan
-- C031        | Bhavna Verma
-- C042        | Uday Das
SELECT c.customer_id, c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_id;

-- (c2) Same question, way 2: NOT IN
-- Safe here because orders.customer_id is NOT NULL (a NULL in the subquery
-- would make NOT IN return no rows at all).
-- Output (matches c1 exactly):
-- customer_id | name
-- C007        | Priya Gupta
-- C019        | Divya Nair
-- C027        | Simran Khan
-- C031        | Bhavna Verma
-- C042        | Uday Das
SELECT customer_id, name
FROM customers
WHERE customer_id NOT IN (SELECT customer_id FROM orders)
ORDER BY customer_id;

-- (d) Return rate by city, only cities above 20%
-- Output:
-- city    | orders | returns | return_rate_pct
-- Udaipur | 33     | 11      | 33.3
-- Mumbai  | 8      | 2       | 25.0
-- Nashik  | 12     | 3       | 25.0
-- Delhi   | 28     | 6       | 21.4
-- Chennai | 19     | 4       | 21.1
SELECT c.city,
       COUNT(*)                            AS orders,
       SUM(o.returned)                     AS returns,
       ROUND(100.0 * AVG(o.returned), 1)   AS return_rate_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.city
HAVING AVG(o.returned) > 0.20
ORDER BY return_rate_pct DESC, c.city;

-- (e1) Top 5 customers by spend
-- Output:
-- customer_id | name           | spend_inr
-- C036        | Mohit Rao      | 202350.75
-- C033        | Farah Malhotra | 101974.5
-- C032        | Deepak Iyer    | 44743.7
-- C012        | Rahul Sharma   | 27826.15
-- C021        | Kavya Malhotra | 27577.7
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price_inr * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS spend_inr
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products  p ON p.product_id  = o.product_id
GROUP BY c.customer_id, c.name
ORDER BY spend_inr DESC, c.customer_id
LIMIT 5;

-- (e2) Ranks 3-5 only, via OFFSET (skip the top 2, take the next 3)
-- Output (rows 3-5 of e1):
-- customer_id | name           | spend_inr
-- C032        | Deepak Iyer    | 44743.7
-- C012        | Rahul Sharma   | 27826.15
-- C021        | Kavya Malhotra | 27577.7
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price_inr * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS spend_inr
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products  p ON p.product_id  = o.product_id
GROUP BY c.customer_id, c.name
ORDER BY spend_inr DESC, c.customer_id
LIMIT 3 OFFSET 2;

-- (f) Three-table JOIN: order count and revenue by product category
-- (the customers join keeps only orders that belong to a known customer)
-- Output:
-- category    | order_count | revenue_inr
-- Electronics | 51          | 436735.85
-- Home        | 52          | 247175.15
-- Beauty      | 42          | 93375.8
-- Fashion     | 35          | 91915.2
SELECT p.category,
       COUNT(*) AS order_count,
       ROUND(SUM(o.quantity * p.price_inr * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS revenue_inr
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products  p ON p.product_id  = o.product_id
GROUP BY p.category
ORDER BY revenue_inr DESC;

-- (g) LIKE: customers whose name starts with "A"
-- Output:
-- customer_id | name
-- C001        | Aarav Sharma
-- C002        | Ananya Verma
-- C003        | Arjun Verma
-- C004        | Aditi Mehta
-- C005        | Amit Singh
SELECT customer_id, name
FROM customers
WHERE name LIKE 'A%'
ORDER BY customer_id;

-- (h) DISTINCT acquisition sources
-- Output:
-- acquisition_source
-- Email
-- Google Ads
-- Instagram
-- Organic
-- Referral
SELECT DISTINCT acquisition_source
FROM customers
ORDER BY acquisition_source;

-- (i) ALTER + UPDATE CASE: loyalty_tier = Gold for tier-1 cities, else Silver
-- Output (of the check query below):
-- loyalty_tier | customers
-- Gold         | 16
-- Silver       | 29
ALTER TABLE customers ADD COLUMN loyalty_tier TEXT;

UPDATE customers
SET loyalty_tier = CASE WHEN city_tier = 1 THEN 'Gold' ELSE 'Silver' END;

SELECT loyalty_tier, COUNT(*) AS customers
FROM customers
GROUP BY loyalty_tier
ORDER BY loyalty_tier;
