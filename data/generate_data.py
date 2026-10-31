"""
ProcureBench Synthetic Database Generator
Generates a reproducible, synthetic SQLite procurement database conforming to schemas.sql.
"""

import argparse
import datetime
import pathlib
import random
import sqlite3
import sys

# Fixed random seed for complete reproducibility
RANDOM_SEED = 42

# Target record counts
TARGET_SUPPLIERS = 30
TARGET_EMPLOYEES = 15
TARGET_PURCHASE_ORDERS = 100
TARGET_PO_ITEMS = 200
TARGET_GOODS_RECEIPTS = 120
TARGET_INVOICES = 100


def get_connection(db_path: pathlib.Path) -> sqlite3.Connection:
    """Creates a connection with foreign key constraints enforced."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_schema(conn: sqlite3.Connection, schema_path: pathlib.Path) -> None:
    """Executes the DDL statements from schemas.sql."""
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)


def generate_suppliers(conn: sqlite3.Connection, count: int = TARGET_SUPPLIERS) -> list[int]:
    """Generates fictional supplier records."""
    name_prefixes = [
        "Apex", "Vanguard", "Nexus", "Horizon", "Quantum", "Cascade", "Titan",
        "Pinnacle", "Starlight", "Beacon", "Crest", "Zenith", "Summit", "Atlas",
        "Omega", "Matrix", "Solstice", "Polaris", "Aura", "Prime", "Synapse",
        "Vector", "Echo", "Lumina", "Forge", "Dynamo", "Cobalt", "Sterling",
        "Kore", "Aero"
    ]
    name_suffixes = [
        "Logistics", "Supplies", "Technologies", "Manufacturing", "Components",
        "Industries", "Solutions", "Materials", "Systems", "Enterprises"
    ]
    countries = ["US", "DE", "JP", "GB", "CA", "FR", "NL", "IT", "KR", "AU"]

    suppliers_data = []
    supplier_ids = []

    for i in range(1, count + 1):
        prefix = name_prefixes[(i - 1) % len(name_prefixes)]
        suffix = name_suffixes[(i - 1) % len(name_suffixes)]
        name = f"{prefix} {suffix}"
        # Maintain ~80% ACTIVE, ~20% INACTIVE suppliers deterministically
        status = "ACTIVE" if (i % 5 != 0) else "INACTIVE"
        country = countries[(i - 1) % len(countries)]

        suppliers_data.append((i, name, status, country))
        supplier_ids.append(i)

    conn.executemany(
        "INSERT INTO suppliers (supplier_id, supplier_name, status, country) VALUES (?, ?, ?, ?)",
        suppliers_data,
    )
    return supplier_ids


def generate_employees(conn: sqlite3.Connection, count: int = TARGET_EMPLOYEES) -> list[int]:
    """Generates fictional employee records with approval limits."""
    fictional_staff = [
        ("Eleanor Vance", "Procurement Officer", 15000.0),
        ("Marcus Chen", "Senior Procurement Officer", 35000.0),
        ("Sarah Jenkins", "Procurement Manager", 75000.0),
        ("David Patel", "Procurement Officer", 15000.0),
        ("Elena Rostova", "Finance Officer", 50000.0),
        ("Arthur Pendelton", "Procurement Director", 120000.0),
        ("Chloe Bennett", "Procurement Officer", 15000.0),
        ("James Wilson", "Finance Manager", 80000.0),
        ("Sofia Alvarez", "Senior Procurement Officer", 35000.0),
        ("Liam O'Connor", "Administrator", 200000.0),
        ("Maya Lin", "Procurement Officer", 15000.0),
        ("Alexander Wright", "Finance Director", 150000.0),
        ("Grace Kim", "Procurement Manager", 75000.0),
        ("Lucas Morales", "Procurement Officer", 15000.0),
        ("Hannah Schmidt", "Finance Officer", 50000.0),
    ]

    employees_data = []
    employee_ids = []

    for i in range(1, count + 1):
        name, role, limit = fictional_staff[(i - 1) % len(fictional_staff)]
        employees_data.append((i, name, role, limit))
        employee_ids.append(i)

    conn.executemany(
        "INSERT INTO employees (employee_id, name, role, approval_limit) VALUES (?, ?, ?, ?)",
        employees_data,
    )
    return employee_ids


def generate_purchase_orders_and_items(
    conn: sqlite3.Connection,
    supplier_ids: list[int],
    po_count: int = TARGET_PURCHASE_ORDERS,
    item_count: int = TARGET_PO_ITEMS,
) -> dict[int, dict]:
    """
    Generates purchase orders and order items.
    Ensures every PO has at least 1 item and PO total_amount matches the sum of item amounts.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT supplier_id FROM suppliers WHERE status = 'ACTIVE'")
    active_suppliers = [row[0] for row in cursor.fetchall()]

    # Distribute 200 items across 100 POs:
    # Every PO gets 1 item first (100 items). Remaining 100 items distributed among POs.
    items_per_po = {po_id: 1 for po_id in range(1, po_count + 1)}
    extra_items = item_count - po_count
    for _ in range(extra_items):
        chosen_po = random.randint(1, po_count)
        items_per_po[chosen_po] += 1

    base_date = datetime.date(2026, 1, 1)
    po_records = []
    item_records = []
    po_summary = {}

    current_item_id = 1
    for po_id in range(1, po_count + 1):
        supplier_id = random.choice(active_suppliers)
        date_offset = random.randint(0, 200)
        order_date = (base_date + datetime.timedelta(days=date_offset)).isoformat()
        po_status = "APPROVED"

        po_items_total = 0.0
        po_total_ordered_qty = 0

        num_items = items_per_po[po_id]
        for _ in range(num_items):
            product_id = f"PRD-{random.randint(100, 999)}"
            quantity = random.randint(5, 100)
            unit_price = round(random.uniform(10.0, 250.0), 2)
            line_total = round(quantity * unit_price, 2)

            item_records.append((current_item_id, po_id, product_id, quantity, unit_price))
            po_items_total = round(po_items_total + line_total, 2)
            po_total_ordered_qty += quantity
            current_item_id += 1

        po_records.append((po_id, supplier_id, order_date, po_items_total, po_status))
        po_summary[po_id] = {
            "supplier_id": supplier_id,
            "order_date": order_date,
            "total_amount": po_items_total,
            "total_ordered_qty": po_total_ordered_qty,
        }

    conn.executemany(
        "INSERT INTO purchase_orders (po_id, supplier_id, order_date, total_amount, status) "
        "VALUES (?, ?, ?, ?, ?)",
        po_records,
    )

    conn.executemany(
        "INSERT INTO purchase_order_items (item_id, po_id, product_id, quantity, unit_price) "
        "VALUES (?, ?, ?, ?, ?)",
        item_records,
    )

    return po_summary


def generate_goods_receipts(
    conn: sqlite3.Connection,
    po_summary: dict[int, dict],
    receipt_count: int = TARGET_GOODS_RECEIPTS,
) -> None:
    """
    Generates goods receipt records.
    Allows partial receipts and ensures total received quantity does not exceed ordered quantity.
    """
    po_ids = sorted(list(po_summary.keys()))
    # To get exactly 120 receipts from 100 POs:
    # 80 POs get 1 receipt each = 80 receipts
    # 20 POs get 2 receipts each = 40 receipts (80 + 40 = 120 receipts)
    two_receipt_pos = set(po_ids[:20])

    receipt_records = []
    grn_id = 1

    for po_id in po_ids:
        po_info = po_summary[po_id]
        order_date = datetime.date.fromisoformat(po_info["order_date"])
        ordered_qty = po_info["total_ordered_qty"]

        if po_id in two_receipt_pos:
            # 2 partial receipts
            qty_1 = max(1, int(ordered_qty * 0.4))
            qty_2 = max(1, int(ordered_qty * 0.5))
            if qty_1 + qty_2 > ordered_qty:
                qty_2 = max(1, ordered_qty - qty_1)

            receipt_date_1 = (order_date + datetime.timedelta(days=random.randint(2, 6))).isoformat()
            receipt_date_2 = (order_date + datetime.timedelta(days=random.randint(7, 14))).isoformat()

            receipt_records.append((grn_id, po_id, qty_1, receipt_date_1))
            grn_id += 1
            receipt_records.append((grn_id, po_id, qty_2, receipt_date_2))
            grn_id += 1
        else:
            # 1 receipt (full or near-full receipt)
            receipt_date = (order_date + datetime.timedelta(days=random.randint(2, 10))).isoformat()
            received_qty = ordered_qty  # Clean baseline: full receipt
            receipt_records.append((grn_id, po_id, received_qty, receipt_date))
            grn_id += 1

    conn.executemany(
        "INSERT INTO goods_receipts (grn_id, po_id, received_quantity, receipt_date) "
        "VALUES (?, ?, ?, ?)",
        receipt_records,
    )


def generate_invoices(
    conn: sqlite3.Connection,
    po_summary: dict[int, dict],
    invoice_count: int = TARGET_INVOICES,
) -> None:
    """
    Generates invoice records matching POs and suppliers.
    Guarantees unique invoice numbers and matching supplier IDs.
    """
    statuses = ["PENDING", "APPROVED", "PAID"]
    invoice_records = []

    for i in range(1, invoice_count + 1):
        po_id = i
        po_info = po_summary[po_id]
        supplier_id = po_info["supplier_id"]
        invoice_number = f"INV-2026-{1000 + i}"
        amount = po_info["total_amount"]
        status = statuses[(i - 1) % len(statuses)]

        invoice_records.append((i, supplier_id, po_id, invoice_number, amount, status))

    conn.executemany(
        "INSERT INTO invoices (invoice_id, supplier_id, po_id, invoice_number, amount, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        invoice_records,
    )


def verify_database(conn: sqlite3.Connection) -> dict:
    """
    Verifies all data integrity rules and returns a structured verification report.
    """
    cursor = conn.cursor()
    report = {"errors": [], "checks": []}

    # 1. Exact record counts
    expected_counts = {
        "suppliers": TARGET_SUPPLIERS,
        "employees": TARGET_EMPLOYEES,
        "purchase_orders": TARGET_PURCHASE_ORDERS,
        "purchase_order_items": TARGET_PO_ITEMS,
        "goods_receipts": TARGET_GOODS_RECEIPTS,
        "invoices": TARGET_INVOICES,
    }

    actual_counts = {}
    for table, expected in expected_counts.items():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        actual_counts[table] = count
        if count != expected:
            report["errors"].append(
                f"Record count mismatch in '{table}': expected {expected}, got {count}"
            )
    report["counts"] = actual_counts
    report["checks"].append(("Table Record Counts", len(report["errors"]) == 0))

    # 2. Foreign-key check
    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()
    if fk_violations:
        report["errors"].append(f"Foreign-key violations detected: {fk_violations}")
    report["checks"].append(("Foreign-Key Integrity", len(fk_violations) == 0))

    # 3. PO items without valid purchase order
    cursor.execute(
        "SELECT COUNT(*) FROM purchase_order_items WHERE po_id NOT IN (SELECT po_id FROM purchase_orders)"
    )
    orphan_items = cursor.fetchone()[0]
    if orphan_items > 0:
        report["errors"].append(f"Orphan purchase_order_items detected: {orphan_items}")
    report["checks"].append(("No Orphan Purchase Order Items", orphan_items == 0))

    # 4. Invoices whose supplier differs from their PO supplier
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM invoices i
        JOIN purchase_orders po ON i.po_id = po.po_id
        WHERE i.supplier_id != po.supplier_id
        """
    )
    mismatched_invoice_suppliers = cursor.fetchone()[0]
    if mismatched_invoice_suppliers > 0:
        report["errors"].append(
            f"Mismatched invoice-PO suppliers detected: {mismatched_invoice_suppliers}"
        )
    report["checks"].append(("Invoice Supplier Matches PO Supplier", mismatched_invoice_suppliers == 0))

    # 5. Duplicate invoice numbers for the same supplier
    cursor.execute(
        """
        SELECT supplier_id, invoice_number, COUNT(*)
        FROM invoices
        GROUP BY supplier_id, invoice_number
        HAVING COUNT(*) > 1
        """
    )
    duplicate_invoices = cursor.fetchall()
    if duplicate_invoices:
        report["errors"].append(f"Duplicate invoices detected: {duplicate_invoices}")
    report["checks"].append(("No Duplicate Invoices per Supplier", len(duplicate_invoices) == 0))

    # 6. Purchase order totals equal the sum of their item totals
    cursor.execute(
        """
        SELECT po.po_id, po.total_amount, ROUND(SUM(poi.quantity * poi.unit_price), 2) AS item_total
        FROM purchase_orders po
        JOIN purchase_order_items poi ON po.po_id = poi.po_id
        GROUP BY po.po_id
        HAVING ABS(po.total_amount - item_total) > 0.001
        """
    )
    mismatched_totals = cursor.fetchall()
    if mismatched_totals:
        report["errors"].append(f"PO total mismatches detected: {mismatched_totals}")
    report["checks"].append(("PO Totals Equal Sum of Items", len(mismatched_totals) == 0))

    # 7. No negative amounts or invalid quantities
    cursor.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM purchase_orders WHERE total_amount < 0) +
            (SELECT COUNT(*) FROM purchase_order_items WHERE quantity <= 0 OR unit_price < 0) +
            (SELECT COUNT(*) FROM goods_receipts WHERE received_quantity <= 0) +
            (SELECT COUNT(*) FROM invoices WHERE amount < 0) +
            (SELECT COUNT(*) FROM employees WHERE approval_limit < 0)
        """
    )
    invalid_numerical_values = cursor.fetchone()[0]
    if invalid_numerical_values > 0:
        report["errors"].append(f"Invalid negative or zero values: {invalid_numerical_values}")
    report["checks"].append(("No Negative Amounts or Invalid Quantities", invalid_numerical_values == 0))

    # 8. Total received quantity does not exceed ordered quantity
    cursor.execute(
        """
        SELECT gr.po_id, SUM(gr.received_quantity) AS total_rcv, ord.total_ordered
        FROM goods_receipts gr
        JOIN (
            SELECT po_id, SUM(quantity) AS total_ordered
            FROM purchase_order_items
            GROUP BY po_id
        ) ord ON gr.po_id = ord.po_id
        GROUP BY gr.po_id
        HAVING SUM(gr.received_quantity) > ord.total_ordered
        """
    )
    excess_receipts = cursor.fetchall()
    if excess_receipts:
        report["errors"].append(f"Receipt quantity exceeds ordered quantity: {excess_receipts}")
    report["checks"].append(("Received Quantities <= Ordered Quantities", len(excess_receipts) == 0))

    return report


def generate_database(db_path: pathlib.Path, schema_path: pathlib.Path) -> dict:
    """Executes full database generation inside a single transaction."""
    random.seed(RANDOM_SEED)

    conn = get_connection(db_path)
    try:
        initialize_schema(conn, schema_path)
        with conn:
            supplier_ids = generate_suppliers(conn)
            generate_employees(conn)
            po_summary = generate_purchase_orders_and_items(conn, supplier_ids)
            generate_goods_receipts(conn, po_summary)
            generate_invoices(conn, po_summary)

        # Verification step
        report = verify_database(conn)
        return report
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic procurement SQLite database for ProcureBench."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Overwrite and regenerate the database if it already exists.",
    )
    args = parser.parse_args()

    data_dir = pathlib.Path(__file__).resolve().parent
    db_path = data_dir / "procurebench.db"
    schema_path = data_dir / "schemas.sql"

    if not schema_path.exists():
        print(f"Error: Schema file not found at {schema_path}", file=sys.stderr)
        sys.exit(1)

    if db_path.exists():
        if not args.reset:
            print(
                f"Notice: Database file '{db_path}' already exists.\n"
                "To safely delete and regenerate the database, run with the '--reset' flag:\n"
                "  python data/generate_data.py --reset"
            )
            return
        else:
            print(f"Reset requested. Removing existing database at: {db_path}")
            db_path.unlink()

    print(f"Generating synthetic database at: {db_path}")
    report = generate_database(db_path, schema_path)

    print("\n" + "=" * 50)
    print("           VERIFICATION REPORT")
    print("=" * 50)
    print("Database Location:", db_path)
    print("\nRecord Counts:")
    for table, count in report["counts"].items():
        print(f"  - {table}: {count}")

    print("\nIntegrity Checks:")
    for check_name, passed in report["checks"]:
        status = "PASSED" if passed else "FAILED"
        print(f"  - {check_name}: {status}")

    if report["errors"]:
        print("\nErrors Encountered:")
        for err in report["errors"]:
            print(f"  [ERROR] {err}")
        sys.exit(1)
    else:
        print("\nAll database constraints and integrity checks verified successfully.")


if __name__ == "__main__":
    main()

