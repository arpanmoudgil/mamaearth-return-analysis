-- Part 1, Task 1: relational schema (SQLite)
-- Re-runnable: drops children before parents, then recreates all three tables.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE customers (
    customer_id        TEXT    PRIMARY KEY,
    name               TEXT    NOT NULL,
    city               TEXT    NOT NULL,
    city_tier          INTEGER NOT NULL CHECK (city_tier IN (1, 2, 3)),
    signup_date        DATE    NOT NULL,
    acquisition_source TEXT    NOT NULL
);

CREATE TABLE products (
    product_id TEXT    PRIMARY KEY,
    name       TEXT    NOT NULL,
    category   TEXT    NOT NULL,
    price_inr  REAL    NOT NULL CHECK (price_inr > 0)
);

CREATE TABLE orders (
    order_id       TEXT    PRIMARY KEY,
    customer_id    TEXT    NOT NULL REFERENCES customers (customer_id),
    product_id     TEXT    NOT NULL REFERENCES products (product_id),
    order_date     DATE    NOT NULL,
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    discount_pct   REAL    CHECK (discount_pct BETWEEN 0 AND 100),  -- nullable by design
    payment_method TEXT    NOT NULL,
    rating         INTEGER CHECK (rating BETWEEN 1 AND 5),          -- nullable by design
    returned       INTEGER NOT NULL DEFAULT 0 CHECK (returned IN (0, 1))
);
