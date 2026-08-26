/*markdown
# Day 1 — SQL: CTEs + window function intro

**Schema (e-commerce pipeline):**
- `orders(order_id, customer_id, order_date, amount, status)`
- `customers(customer_id, name, signup_date, region)`
*/  

/*markdown
## Q1 — revenue by region, completed orders, last 30 days
*/

select c.region, sum(o.amount) as total_revenue
from orders o
join customers c on o.customer_id = c.customer_id
where o.status = 'completed'
  and o.order_date >= now() - interval '30 days'
group by c.region;

/*markdown
## Q2 — customers with total spend above average
*/

with customer_totals as (
    select o.customer_id, c.name, sum(o.amount) as total_spend
    from orders o
    join customers c on o.customer_id = c.customer_id
    group by o.customer_id, c.name
),
avg_spend as (
    select avg(total_spend) as avg_total from customer_totals
)
select ct.customer_id, ct.name, ct.total_spend
from customer_totals ct
cross join avg_spend
where ct.total_spend > avg_spend.avg_total;

/*markdown
## Scratch — ROW_NUMBER() per customer demo
*/

select order_id, customer_id, order_date,
row_number() over (PARTITION BY customer_id order by order_date desc) as rn from orders;

/*markdown
## Q — most recent order per customer (CTE + window)
For each customer, find their most recent order. Write it with a CTE
(don't worry if you'd normally use ROW_NUMBER() — use whatever approach comes to mind, I want to see your instinct)
*/

with ranked as (select customer_id, order_id, order_date, amount,row_number()
over (PARTITION BY customer_id order by order_date desc) as rnk from orders)
select customer_id, order_id, order_date, amount from ranked where rnk =1;

/*markdown
## Scratch — RANK() partitioned by order_id
*/

with ranked as (select customer_id, order_id, amount, order_date, rank() over (PARTITION BY order_id order by order_date desc)
as rnk from orders)
select customer_id, order_id, amount, order_date, rnk from ranked where rnk = 2;

/*markdown
## Q6 (CTE + window) — top 2 highest-value orders per customer
Return customer_id, order_id, amount, ranked.
*/

with ranked as (select customer_id, order_id, amount, row_number() over (PARTITION BY customer_id order by order_date desc) as rnk from orders)
select customer_id, order_id, amount from ranked where rnk = 2;

/*markdown
## Scratch — table peeks
*/

select * from orders limit 1;
select * from customers limit 1;


/*markdown
## Q7 — rank customers by total completed-order spend (RANK())
Expected output structure below.
*/

with ranked as (select o.customer_id as customer_id, c.name as customer_name, sum(o.amount)
 as total_spend, rank() over (order by sum(o.amount) desc) as rnk from orders o join customers c
 ON c.customer_id = o.customer_id where o.status = 'completed' group by o.customer_id, c.name, o.status)
 select customer_id, customer_name, total_spend, rnk from ranked;

/*markdown
## Scratch — avg order amount per customer
*/

select customer_id, avg(amount) from orders group by customer_id order by customer_id;

/*markdown
## Bonus — rank customers by average order amount
*/

with cust_avg as (
    select customer_id, avg(amount) as avgamt from orders
    group by customer_id
)
select customer_id, avgamt, row_number() over ( order by avgamt desc) from cust_avg;


SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

select * from order_items limit 1;
select * from products limit 1;

/*markdown
#### Q8 — expected output structure

Best-selling product by revenue, per category, using order_items + products.
*/

with details as (
    select p.category as category, p.product_name, sum(o.line_amount) as total_revenue
    -- ,rank() over (PARTITION BY p.category order by o.line_amount desc) as rnk
    from products p join order_items o on
    p.product_id = o.product_id
    group by p.product_name, p.category
),
ranked as (
    select category, product_name, total_revenue, rank() over (PARTITION BY category order by total_revenue desc) as rankk
    from details
)
select category, product_name, total_revenue from ranked where rankk = 1 ;

