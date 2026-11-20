"""Regenerate every practice dataset in this folder (deterministic, seed=42).

    python datasets/generate_datasets.py

The data is intentionally messy: duplicates, missing values, malformed rows,
mixed date formats, inconsistent casing, unknown foreign keys, re-delivered files.
Exercises and tests do not depend on exact random values; tests build their own
small fixtures. The large files exist so you feel real data-processing concerns.
"""
from __future__ import annotations

import csv
import json
import random
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = random.Random(42)

FIRST = ["Aarav", "Diya", "Kalyan", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Arjun", "Meera",
         "John", "Emma", "Liam", "Olivia", "Noah", "Sofia", "Lukas", "Mia", "Elias", "Aino",
         "Wei", "Mei", "Hiro", "Yuki", "Omar", "Layla", "Carlos", "Lucia", "Erik", "Freya"]
LAST = ["Sharma", "Reddy", "Iyer", "Patel", "Nair", "Gupta", "Rao", "Kumar", "Singh", "Das",
        "Smith", "Brown", "Wilson", "Taylor", "Müller", "Schmidt", "Virtanen", "Korhonen", "Tan", "Lee",
        "Garcia", "Lopez", "Johansson", "Nielsen", "Khan", "Ali", "Sato", "Chen", "Ivanova", "Rossi"]
COUNTRIES = {"IN": ["Hyderabad", "Bengaluru", "Mumbai", "Chennai", "Pune"], "US": ["Austin", "Seattle", "Boston"],
             "GB": ["London", "Manchester"], "DE": ["Berlin", "Munich"], "FI": ["Helsinki", "Espoo"],
             "SE": ["Stockholm"], "SG": ["Singapore"]}
CATEGORIES = ["Electronics", "Books", "Home", "Grocery", "Fashion", "Sports"]
PRODUCT_WORDS = {
    "Electronics": ["Laptop", "Mouse", "Keyboard", "Monitor", "Headphones", "Webcam", "SSD", "Router"],
    "Books": ["Python Cookbook", "Data Pipelines", "Clean Code", "SQL Deep Dive", "Spark Guide"],
    "Home": ["Lamp", "Chair", "Desk", "Kettle", "Blender", "Pillow"],
    "Grocery": ["Coffee Beans", "Green Tea", "Basmati Rice", "Olive Oil", "Dark Chocolate"],
    "Fashion": ["T-Shirt", "Sneakers", "Jacket", "Backpack", "Watch"],
    "Sports": ["Yoga Mat", "Dumbbells", "Cricket Bat", "Football", "Cycling Helmet"],
}
STATUSES = ["PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
CHANNELS = ["web", "app", "store"]


def write_csv(path: Path, header: list[str], rows: list[list], delimiter=",", bom=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig" if bom else "utf-8") as f:
        w = csv.writer(f, delimiter=delimiter)
        w.writerow(header)
        w.writerows(rows)


def write_json(path: Path, obj, indent=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=indent, ensure_ascii=False), encoding="utf-8")


def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=rng.randrange((end - start).days + 1))


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- customers
def make_customers(n=1000):
    rows = []
    for i in range(1, n + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        country = rng.choice(list(COUNTRIES))
        signup = rand_date(date(2022, 1, 1), date(2025, 12, 31))
        email = f"{first}.{last}{i}@example.com".lower()
        rows.append({
            "customer_id": f"C{i:05d}", "name": f"{first} {last}", "email": email,
            "country": country, "city": rng.choice(COUNTRIES[country]),
            "signup_date": signup.isoformat(), "segment": rng.choice(["retail", "retail", "smb", "enterprise"]),
            "is_active": rng.choice(["true", "true", "true", "false"]),
        })
    return rows


def messy_customers(clean):
    out = []
    for r in clean:
        r = dict(r)
        roll = rng.random()
        if roll < 0.02:
            r["email"] = ""
        elif roll < 0.03:
            r["email"] = r["email"].replace("@", ".at.")
        elif roll < 0.05:
            r["country"] = r["country"].lower()
        elif roll < 0.06:
            d = date.fromisoformat(r["signup_date"])
            r["signup_date"] = d.strftime("%d/%m/%Y")
        elif roll < 0.07:
            r["name"] = "  " + r["name"].upper() + " "
        out.append(r)
        if rng.random() < 0.015:  # duplicate with cosmetic differences
            dup = dict(r)
            dup["email"] = dup["email"].upper()
            dup["name"] = dup["name"].strip().title() + " "
            out.append(dup)
    return out


# ---------------------------------------------------------------- products
def make_products(n=200):
    rows = []
    for i in range(1, n + 1):
        cat = rng.choice(CATEGORIES)
        base = rng.choice(PRODUCT_WORDS[cat])
        price = {"Electronics": (999, 120000), "Books": (199, 2499), "Home": (299, 25000),
                 "Grocery": (49, 1999), "Fashion": (399, 15000), "Sports": (199, 18000)}[cat]
        rows.append({"product_id": f"P{i:04d}", "name": f"{base} {rng.choice(['Pro', 'Lite', 'Max', 'Basic', 'X'])}",
                     "category": cat if rng.random() > 0.02 else "", "price": round(rng.uniform(*price), 2),
                     "currency": "INR", "active": "true" if rng.random() > 0.08 else "false"})
    return rows


# ---------------------------------------------------------------- orders
def make_orders(customers, products, n=5000, start_id=1, start=datetime(2026, 1, 1), days=60):
    rows = []
    for i in range(start_id, start_id + n):
        c = rng.choice(customers)
        p = rng.choice(products)
        ts = start + timedelta(minutes=rng.randrange(days * 24 * 60))
        upd = ts + timedelta(hours=rng.randrange(0, 72))
        rows.append({
            "order_id": f"O{i:07d}", "customer_id": c["customer_id"], "product_id": p["product_id"],
            "quantity": rng.choice([1, 1, 1, 2, 2, 3, 5]), "unit_price": p["price"],
            "order_ts": iso(ts), "status": rng.choice(STATUSES), "updated_at": iso(upd),
            "channel": rng.choice(CHANNELS), "country": c["country"],
        })
    return rows


ORDER_COLS = ["order_id", "customer_id", "product_id", "quantity", "unit_price", "order_ts",
              "status", "updated_at", "channel", "country"]


def mess_orders(rows, rate=1.0):
    out = []
    for r in rows:
        r = dict(r)
        roll = rng.random() / rate
        if roll < 0.01:
            r["quantity"] = rng.choice([0, -1, -3])
        elif roll < 0.02:
            r["unit_price"] = rng.choice(["N/A", "", "abc"])
        elif roll < 0.03:
            r["customer_id"] = ""
        elif roll < 0.035:
            r["customer_id"] = "C99999"  # unknown customer
        elif roll < 0.045:
            r["order_ts"] = rng.choice(["2026-13-01T10:00:00Z", "yesterday", "01/02/2026 10:00"])
        elif roll < 0.055:
            r["status"] = r["status"].lower()
        out.append(r)
        roll2 = rng.random()
        if roll2 < 0.03:
            out.append(dict(r))  # exact duplicate
        elif roll2 < 0.05:
            upd = dict(r)
            upd["status"] = rng.choice(["SHIPPED", "DELIVERED", "CANCELLED"])
            upd["updated_at"] = iso(datetime.strptime(r["updated_at"], "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=rng.randrange(1, 48)))
            out.append(upd)  # newer version of same order
    rng.shuffle(out)
    return out


def as_row(d, cols):
    return [d.get(c, "") for c in cols]


def nested_orders(customers, products, n=1000):
    out = []
    for i in range(1, n + 1):
        c = rng.choice(customers)
        items = []
        for _ in range(rng.choice([1, 1, 2, 3, 4])):
            p = rng.choice(products)
            items.append({"product_id": p["product_id"], "name": p["name"], "category": p["category"] or None,
                          "qty": rng.choice([1, 1, 2, 3]), "price": p["price"]})
        ts = datetime(2026, 1, 1) + timedelta(minutes=rng.randrange(60 * 24 * 60))
        order = {
            "id": 100000 + i, "created_at": iso(ts), "status": rng.choice(STATUSES),
            "customer": {"id": c["customer_id"], "name": c["name"], "country": c["country"],
                         "contact": {"email": c["email"] or None, "phone": None if rng.random() < 0.3 else f"+91-9{rng.randrange(10**8, 10**9)}"}},
            "items": items,
            "payment": {"method": rng.choice(["card", "upi", "netbanking", "cod"]),
                        "status": rng.choice(["captured", "captured", "captured", "failed", "refunded"])},
            "shipping": {"address": {"city": c["city"], "country": c["country"], "pincode": str(rng.randrange(100000, 999999))},
                         "method": rng.choice(["standard", "express"])},
            "tags": rng.sample(["gift", "prime", "first_order", "bulk", "festive"], rng.randrange(0, 3)),
        }
        if rng.random() < 0.03:
            del order["payment"]
        if rng.random() < 0.02:
            order["items"] = []
        out.append(order)
    return out


# ---------------------------------------------------------------- transactions / employees / events
def make_transactions(n=10000):
    rows = []
    merchants = ["Swiggy", "Amazon", "Flipkart", "Uber", "Zomato", "BigBasket", "Netflix", "IRCTC", "Myntra", "Apollo"]
    for i in range(1, n + 1):
        typ = rng.choices(["DEBIT", "CREDIT", "REFUND", "FEE"], [70, 20, 7, 3])[0]
        amt = round(rng.uniform(20, 25000), 2)
        if typ in ("DEBIT", "FEE"):
            amt = -amt
        ts = datetime(2026, 1, 1) + timedelta(seconds=rng.randrange(90 * 86400))
        rows.append([f"T{i:08d}", f"A{rng.randrange(1, 301):04d}", iso(ts), amt,
                     rng.choices(["INR", "USD", "EUR"], [85, 10, 5])[0], typ,
                     rng.choice(merchants) if typ != "CREDIT" else "SALARY/TRANSFER",
                     rng.choices(["SUCCESS", "FAILED", "PENDING"], [92, 5, 3])[0]])
    dups = rng.sample(rows, 150)
    rows.extend(dups)
    rng.shuffle(rows)
    return rows


def make_employees(n=300):
    depts = ["Data Engineering", "Platform", "Analytics", "Finance", "HR", "Sales"]
    rows = []
    for i in range(1, n + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        dept = rng.choice(depts)
        mgr = "" if i <= 6 else f"E{rng.randrange(1, min(i, 60)):04d}"
        title = "Head" if i <= 6 else rng.choice(["Engineer", "Senior Engineer", "Analyst", "Manager", "Associate"])
        salary = rng.randrange(600000, 4500000, 10000) if rng.random() > 0.02 else ""
        rows.append([f"E{i:04d}", f"{first} {last}", f"{first}.{last}.{i}@corp.example".lower(), dept, title, mgr,
                     salary, rand_date(date(2015, 1, 1), date(2026, 6, 30)).isoformat(),
                     rng.choice(["Hyderabad", "Bengaluru", "Helsinki", "London", "Remote"]),
                     rng.choices(["active", "on_leave", "terminated"], [88, 4, 8])[0]])
    return rows


def make_events(n=5000):
    lines = []
    types = ["page_view", "page_view", "page_view", "add_to_cart", "purchase", "login", "logout", "search"]
    for i in range(1, n + 1):
        typ = rng.choice(types)
        ts = datetime(2026, 2, 1) + timedelta(seconds=rng.randrange(14 * 86400))
        props = {"page": rng.choice(["/", "/cart", "/product/P0012", "/search", "/checkout"])}
        if typ == "purchase":
            props = {"order_id": f"O{rng.randrange(1, 5000):07d}", "amount": round(rng.uniform(100, 50000), 2)}
        if typ == "search":
            props = {"query": rng.choice(["laptop", "python book", "coffee", "yoga mat", ""])}
        ev = {"event_id": f"ev-{i:06d}", "user_id": f"C{rng.randrange(1, 1001):05d}" if rng.random() > 0.02 else None,
              "event_type": typ, "ts": iso(ts), "properties": props,
              "device": {"os": rng.choice(["android", "ios", "windows", "macos"]), "app_version": rng.choice(["4.1.0", "4.2.1", "4.3.0"])}}
        line = json.dumps(ev)
        if rng.random() < 0.01:
            line = line[: rng.randrange(10, len(line) - 5)]  # truncated / malformed line
        lines.append(line)
    return lines


# ---------------------------------------------------------------- logs
SERVICES = ["orders-service", "payment-service", "inventory-service", "auth-service", "gateway"]
PATHS = {"orders-service": ["/api/orders", "/api/orders/{id}"], "payment-service": ["/api/payments", "/api/refunds"],
         "inventory-service": ["/api/stock/{id}", "/api/reserve"], "auth-service": ["/api/login", "/api/token/refresh"],
         "gateway": ["/health", "/api/search"]}
ERRORS = {"payment-service": [("PaymentGatewayTimeout", "gateway timed out after 1200ms"), ("CardDeclined", "card declined by issuer")],
          "orders-service": [("OrderValidationError", "missing shipping address"), ("DatabaseError", "deadlock detected")],
          "inventory-service": [("OutOfStock", "sku not available"), ("DatabaseError", "connection pool exhausted")],
          "auth-service": [("InvalidToken", "jwt signature mismatch"), ("RateLimited", "too many login attempts")],
          "gateway": [("UpstreamUnavailable", "orders-service returned 503")]}


def make_app_log(n=20000, start=datetime(2026, 3, 1, tzinfo=timezone.utc)):
    lines = []
    ts = start
    for _ in range(n):
        ts += timedelta(milliseconds=rng.randrange(50, 9000))
        svc = rng.choice(SERVICES)
        level = rng.choices(["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"], [10, 70, 10, 9, 1])[0]
        method = "GET" if rng.random() < 0.6 else "POST"
        path = rng.choice(PATHS[svc]).replace("{id}", str(rng.randrange(1, 9999)))
        req = "%08x" % rng.randrange(16 ** 8)
        stamp = ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"
        if level in ("ERROR", "CRITICAL"):
            etype, emsg = rng.choice(ERRORS[svc])
            status = rng.choice([500, 502, 503, 504]) if etype not in ("CardDeclined", "OrderValidationError", "InvalidToken", "RateLimited") else rng.choice([400, 401, 422, 429])
            lat = rng.randrange(300, 5000)
            lines.append(f'{stamp} {level} [{svc}] req={req} method={method} path={path} status={status} latency_ms={lat} error={etype} msg="{emsg}"')
            if rng.random() < 0.3:
                lines += ["Traceback (most recent call last):",
                          f'  File "/app/{svc.split("-")[0]}/handlers.py", line {rng.randrange(20, 400)}, in handle',
                          "    result = process(request)",
                          f"{etype}: {emsg}"]
        elif level == "WARN":
            lat = rng.randrange(800, 3000)
            lines.append(f'{stamp} WARN [{svc}] req={req} method={method} path={path} status=200 latency_ms={lat} msg="slow request"')
        else:
            lat = rng.randrange(3, 400)
            msg = "request completed" if level == "INFO" else "cache lookup"
            lines.append(f'{stamp} {level} [{svc}] req={req} method={method} path={path} status={rng.choice([200, 200, 200, 201, 204, 304])} latency_ms={lat} msg="{msg}"')
        if rng.random() < 0.004:
            lines.append(rng.choice(["", "%%% corrupted line %%%", stamp + " INFO", "\x00\x00garbage", "2026-03-01 broken [x"]))
    return lines


def make_access_log(n=5000):
    lines = []
    ts = datetime(2026, 3, 1, tzinfo=timezone.utc)
    agents = ["Mozilla/5.0", "curl/8.4.0", "python-requests/2.32", "Googlebot/2.1"]
    for _ in range(n):
        ts += timedelta(seconds=rng.randrange(1, 40))
        ip = f"10.{rng.randrange(0, 4)}.{rng.randrange(0, 255)}.{rng.randrange(1, 255)}"
        path = rng.choice(["/", "/products", "/products/P0012", "/cart", "/checkout", "/api/orders", "/login", "/static/app.js"])
        status = rng.choices([200, 301, 304, 404, 500, 503], [80, 3, 6, 7, 3, 1])[0]
        size = rng.randrange(200, 50000) if status != 304 else 0
        lines.append(f'{ip} - - [{ts.strftime("%d/%b/%Y:%H:%M:%S +0000")}] "{rng.choice(["GET", "GET", "POST"])} {path} HTTP/1.1" {status} {size} "-" "{rng.choice(agents)}"')
    return lines


# ---------------------------------------------------------------- main
def main():
    for sub in ["csv", "json", "logs", "incoming", "daily", "s3", "config"]:
        shutil.rmtree(HERE / sub, ignore_errors=True)

    customers = make_customers()
    products = make_products()
    cust_rows = messy_customers(customers)
    cust_cols = list(customers[0])
    write_csv(HERE / "csv/customers.csv", cust_cols, [as_row(r, cust_cols) for r in cust_rows])
    prod_cols = list(products[0])
    write_csv(HERE / "csv/products.csv", prod_cols, [as_row(r, prod_cols) for r in products])
    orders = make_orders(customers, products)
    write_csv(HERE / "csv/orders.csv", ORDER_COLS, [as_row(r, ORDER_COLS) for r in mess_orders(orders)])
    write_csv(HERE / "csv/transactions.csv", ["txn_id", "account_id", "ts", "amount", "currency", "type", "merchant", "status"], make_transactions())
    write_csv(HERE / "csv/employees.csv", ["emp_id", "name", "email", "department", "title", "manager_id", "salary", "hire_date", "location", "status"], make_employees())

    write_json(HERE / "json/customers.json", customers[:300])
    write_json(HERE / "json/products.json", products)
    write_json(HERE / "json/orders_nested.json", nested_orders(customers, products))
    (HERE / "json/events.jsonl").write_text("\n".join(make_events()) + "\n", encoding="utf-8")

    # mock API backing data
    api_customers = [dict(c, is_active=c["is_active"] == "true") for c in customers[:237]]
    api_orders = [dict(o, quantity=int(o["quantity"])) for o in make_orders(customers, products, n=523, start_id=700001)]
    for o in rng.sample(api_orders, 15):  # duplicates across pages, like real APIs during writes
        api_orders.insert(rng.randrange(len(api_orders)), dict(o))
    for o in rng.sample(api_orders, 10):
        o["unit_price"] = None
    api_events = []
    for i, o in enumerate(api_orders[:400]):
        api_events.append({"event_id": f"evt-{i:05d}", "order_id": o["order_id"], "status": o["status"],
                           "updated_at": o["updated_at"]})
    write_json(HERE / "json/api/customers.json", api_customers)
    write_json(HERE / "json/api/orders.json", api_orders)
    write_json(HERE / "json/api/products.json", [dict(p, price=float(p["price"]), active=p["active"] == "true") for p in products])
    write_json(HERE / "json/api/events.json", api_events)

    # logs
    (HERE / "logs/app.log").parent.mkdir(parents=True, exist_ok=True)
    app_lines = make_app_log()
    (HERE / "logs/app.log").write_text("\n".join(app_lines) + "\n", encoding="utf-8")
    (HERE / "logs/app_small.log").write_text("\n".join(app_lines[:250]) + "\n", encoding="utf-8")
    (HERE / "logs/access.log").write_text("\n".join(make_access_log()) + "\n", encoding="utf-8")

    # incoming/ landing zone (files + junk to ignore)
    inc = HERE / "incoming"
    batch = make_orders(customers, products, n=1200, start_id=200001, start=datetime(2026, 2, 1), days=10)
    o1, o2, o3 = batch[:400], batch[400:800], batch[800:]
    late = []
    for r in rng.sample(o1, 20):
        u = dict(r, status="DELIVERED")
        u["updated_at"] = iso(datetime.strptime(r["updated_at"], "%Y-%m-%dT%H:%M:%SZ") + timedelta(days=2))
        late.append(u)
    write_csv(inc / "orders_01.csv", ORDER_COLS, [as_row(r, ORDER_COLS) for r in mess_orders(o1, 0.6)])
    write_csv(inc / "orders_02.csv", ORDER_COLS, [as_row(r, ORDER_COLS) for r in mess_orders(o2 + late, 0.6)])
    cols3 = ["order_ts", "order_id", "status", "customer_id", "product_id", "unit_price", "quantity", "updated_at", "channel", "country", "coupon_code"]
    rows3 = [as_row(dict(r, coupon_code=rng.choice(["", "", "NEW10", "FEST20"])), cols3) for r in mess_orders(o3, 0.6)]
    write_csv(inc / "orders_03.csv", cols3, rows3, bom=True)
    (inc / "corrupt.csv").write_text(
        "order_id,customer_id,product_id,quantity,unit_price,order_ts,status,updated_at,channel,country\n"
        "O0299001,C00010,P0001,1,999.0,2026-02-03T10:00:00Z,PLACED,2026-02-03T10:00:00Z,web,IN\n"
        "O0299002,C00011,P0002\n"
        "\n"
        "O0299003,C00012,P0003,two,abc,not-a-date,???,,web,IN,EXTRA,COLS\n"
        "\"O0299004,C00013,P0004,1,10.0,2026-02-03T11:00:00Z,PLACED\n"
        "this is not csv at all\n", encoding="utf-8")
    write_json(inc / "customers.json", customers[:400])
    (inc / "orders_04.csv.tmp").write_text("order_id,customer_id\nO1,C1\n", encoding="utf-8")
    (inc / "_SUCCESS").write_text("", encoding="utf-8")

    # daily/ partitions for incremental processing
    daily = HERE / "daily"
    prev = None
    next_id = 300001
    for d in range(1, 8):
        day = date(2026, 1, d)
        part_dir = daily / f"dt={day.isoformat()}"
        part_dir.mkdir(parents=True, exist_ok=True)
        if d == 7:
            write_csv(part_dir / f"orders_{day:%Y%m%d}_part1.csv", ORDER_COLS, [])
            continue
        rows = make_orders(customers, products, n=rng.randrange(150, 260), start_id=next_id,
                           start=datetime(2026, 1, d), days=1)
        next_id += 1000
        if d == 3 and prev:
            rows += rng.sample(prev, 15)  # late-arriving duplicates from day 2
        rate = 3.0 if d == 5 else 0.5
        messy = mess_orders(rows, rate)
        half = len(messy) // 2
        write_csv(part_dir / f"orders_{day:%Y%m%d}_part1.csv", ORDER_COLS, [as_row(r, ORDER_COLS) for r in messy[:half]])
        write_csv(part_dir / f"orders_{day:%Y%m%d}_part2.csv", ORDER_COLS, [as_row(r, ORDER_COLS) for r in messy[half:]])
        prev = rows
    shutil.copy(daily / "dt=2026-01-05/orders_20260105_part1.csv", daily / "dt=2026-01-06/orders_20260105_part1_redelivered.csv")

    # s3/ simulated buckets
    s3 = HERE / "s3"
    sales = make_orders(customers, products, n=900, start_id=400001, start=datetime(2026, 1, 10), days=3)
    for i in range(3):
        day = date(2026, 1, 10 + i)
        chunk = [r for r in sales if r["order_ts"].startswith(day.isoformat())]
        for p in range(2):
            write_csv(s3 / f"lab-raw-bucket/sales/ingest_date={day.isoformat()}/part-{p:05d}.csv", ORDER_COLS,
                      [as_row(r, ORDER_COLS) for r in mess_orders(chunk[p::2], 0.5)])
    write_json(s3 / "lab-raw-bucket/customers/customers.json", customers[:500])
    (s3 / "lab-processed-bucket").mkdir(parents=True, exist_ok=True)
    (s3 / "lab-processed-bucket/.keep").write_text("", encoding="utf-8")
    write_json(s3 / "lab-config-bucket/jobs/daily_sales.json", {
        "job_name": "daily_sales", "source": "s3://lab-raw-bucket/sales/", "target": "s3://lab-processed-bucket/sales_daily/",
        "rejected": "s3://lab-processed-bucket/rejected/sales/", "partition_key": "ingest_date",
        "min_quantity": 1, "allowed_status": STATUSES, "max_retries": 3})

    # config/
    write_json(HERE / "config/pipeline.json", {
        "pipeline": "orders_daily", "input_dir": "datasets/incoming", "output_dir": "output/orders",
        "file_pattern": "orders_*.csv", "dedupe_key": ["order_id"], "order_by": "updated_at",
        "log_level": "INFO", "batch_size": 500, "fail_on_reject_ratio": 0.2})
    (HERE / "config/.env.example").write_text("LAB_ENV=dev\nLAB_LOG_LEVEL=DEBUG\nLAB_BATCH_SIZE=250\nLAB_INPUT_DIR=datasets/incoming\n", encoding="utf-8")
    print("datasets generated in", HERE)


if __name__ == "__main__":
    main()
