-- ============================================================
-- DE Interview Prep — Practice Schema
-- Postgres-flavored SQL. If you're using SQLite in VSCode instead,
-- swap `CURRENT_DATE - INTERVAL 'n days'` for `date('now','-n days')`
-- and drop the `SERIAL` keyword in favor of `INTEGER PRIMARY KEY`.
-- ============================================================

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

-- ------------------------------------------------------------
-- CUSTOMERS
-- ------------------------------------------------------------
CREATE TABLE customers (
    customer_id   SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    signup_date   DATE NOT NULL,
    region        TEXT NOT NULL  -- 'US-East', 'US-West', 'EU', 'APAC'
);

INSERT INTO customers (customer_id, name, signup_date, region) VALUES
(1,  'Alice Chen',      '2024-01-15', 'US-East'),
(2,  'Bruno Silva',     '2024-02-20', 'EU'),
(3,  'Carla Mendes',    '2024-03-05', 'US-West'),
(4,  'David Kim',       '2024-01-30', 'APAC'),
(5,  'Elena Petrova',   '2024-04-11', 'EU'),
(6,  'Farhan Ali',      '2024-05-02', 'APAC'),
(7,  'Grace Lee',       '2024-02-14', 'US-East'),
(8,  'Hassan Iqbal',    '2024-06-18', 'US-West'),
(9,  'Ivy Zhang',       '2024-03-22', 'EU'),
(10, 'Jamal Brooks',    '2024-07-01', 'US-East'),
-- customer with zero orders on purpose — tests LEFT JOIN handling
(11, 'Karen Novak',     '2024-07-20', 'US-West'),
-- two customers who signed up but haven't ordered in a while
(12, 'Liam O''Connor',  '2023-11-01', 'EU');

-- ------------------------------------------------------------
-- PRODUCTS
-- ------------------------------------------------------------
CREATE TABLE products (
    product_id    SERIAL PRIMARY KEY,
    product_name  TEXT NOT NULL,
    category      TEXT NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL
);

INSERT INTO products (product_id, product_name, category, unit_price) VALUES
(1, 'Wireless Mouse',      'Electronics', 19.99),
(2, 'Mechanical Keyboard', 'Electronics', 79.99),
(3, 'USB-C Hub',           'Electronics', 34.50),
(4, 'Notebook (A5)',       'Stationery',  4.99),
(5, 'Standing Desk',       'Furniture',   249.00),
(6, 'Office Chair',        'Furniture',   189.99),
(7, 'Water Bottle',        'Lifestyle',   14.00),
(8, 'Desk Lamp',           'Furniture',   29.99);

-- ------------------------------------------------------------
-- ORDERS
-- Dates are relative to CURRENT_DATE at insert time so "last 30 days"
-- filters actually have meaningful hits/misses when you run this.
-- status: 'completed', 'pending', 'cancelled', 'refunded'
-- ------------------------------------------------------------
CREATE TABLE orders (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date    DATE NOT NULL,
    amount        NUMERIC(10,2) NOT NULL,
    status        TEXT NOT NULL
);

INSERT INTO orders (order_id, customer_id, order_date, amount, status) VALUES
-- Alice: repeat customer, mix of old + recent, one cancelled
(1,  1, CURRENT_DATE - INTERVAL '45 days', 120.50, 'completed'),
(2,  1, CURRENT_DATE - INTERVAL '20 days', 75.00,  'completed'),
(3,  1, CURRENT_DATE - INTERVAL '3 days',  200.00, 'completed'),
(4,  1, CURRENT_DATE - INTERVAL '10 days', 45.00,  'cancelled'),

-- Bruno: one big old order, nothing recent
(5,  2, CURRENT_DATE - INTERVAL '90 days', 500.00, 'completed'),

-- Carla: recent + pending
(6,  3, CURRENT_DATE - INTERVAL '5 days',  89.99,  'completed'),
(7,  3, CURRENT_DATE - INTERVAL '1 days',  15.00,  'pending'),

-- David: refunded order (test status filtering)
(8,  4, CURRENT_DATE - INTERVAL '15 days', 300.00, 'refunded'),
(9,  4, CURRENT_DATE - INTERVAL '2 days',  60.00,  'completed'),

-- Elena: heavy spender, several completed
(10, 5, CURRENT_DATE - INTERVAL '60 days', 150.00, 'completed'),
(11, 5, CURRENT_DATE - INTERVAL '25 days', 220.00, 'completed'),
(12, 5, CURRENT_DATE - INTERVAL '4 days',  310.00, 'completed'),

-- Farhan: single small order
(13, 6, CURRENT_DATE - INTERVAL '8 days',  25.00,  'completed'),

-- Grace: nothing in last 30 days (tests "inactive customer" queries)
(14, 7, CURRENT_DATE - INTERVAL '50 days', 99.00,  'completed'),
(15, 7, CURRENT_DATE - INTERVAL '70 days', 60.00,  'completed'),

-- Hassan: recent big order
(16, 8, CURRENT_DATE - INTERVAL '6 days',  410.00, 'completed'),

-- Ivy: mix
(17, 9, CURRENT_DATE - INTERVAL '12 days', 55.00,  'completed'),
(18, 9, CURRENT_DATE - INTERVAL '2 days',  95.00,  'pending'),

-- Jamal: brand-new customer, one order same day
(19, 10, CURRENT_DATE,                     40.00,  'completed'),

-- Karen (customer_id 11) has NO orders — intentional
-- Liam: signed up long ago, one very old order only
(20, 12, CURRENT_DATE - INTERVAL '200 days', 130.00, 'completed');

-- ------------------------------------------------------------
-- ORDER_ITEMS
-- Line-item detail — lets you practice multi-level joins,
-- fact/dim thinking, and "top product" style aggregations.
-- ------------------------------------------------------------
CREATE TABLE order_items (
    order_item_id  SERIAL PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES orders(order_id),
    product_id     INTEGER NOT NULL REFERENCES products(product_id),
    quantity       INTEGER NOT NULL,
    line_amount    NUMERIC(10,2) NOT NULL
);

INSERT INTO order_items (order_item_id, order_id, product_id, quantity, line_amount) VALUES
(1,  1, 2, 1, 79.99),
(2,  1, 1, 2, 39.98),
(3,  2, 4, 3, 14.97),
(4,  2, 7, 4, 56.00),
(5,  3, 5, 1, 200.00),
(6,  4, 3, 1, 34.50),
(7,  5, 6, 2, 379.98),
(8,  5, 8, 4, 119.96),
(9,  6, 1, 1, 19.99),
(10, 6, 3, 2, 69.00),
(11, 7, 4, 3, 14.97),
(12, 8, 5, 1, 249.00),
(13, 8, 8, 1, 29.99),
(14, 9, 7, 4, 56.00),
(15, 10, 6, 1, 189.99),
(16, 11, 5, 1, 249.00),
(17, 12, 2, 3, 239.97),
(18, 13, 7, 1, 14.00),
(19, 14, 1, 5, 99.95),
(20, 16, 5, 1, 249.00),
(21, 16, 6, 1, 189.99),
(22, 17, 3, 1, 34.50),
(23, 19, 4, 2, 9.98);

-- ============================================================
-- Sanity check queries — run these first to confirm the load worked
-- ============================================================
-- SELECT COUNT(*) FROM customers;   -- expect 12
-- SELECT COUNT(*) FROM orders;      -- expect 20
-- SELECT COUNT(*) FROM order_items; -- expect 23
