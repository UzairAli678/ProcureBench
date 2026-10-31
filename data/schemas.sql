-- Enable foreign key enforcement
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Table 1: suppliers
-- Purpose: Stores vendor master records including operating status,
-- banking credentials, and country of operation.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
    bank_account TEXT NOT NULL,
    country TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- Table 2: employees
-- Purpose: Stores authorized staff details and designated financial
-- approval thresholds for procurement actions.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    employee_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    approval_limit REAL NOT NULL CHECK (approval_limit >= 0)
);

-- ---------------------------------------------------------------------
-- Table 3: purchase_orders
-- Purpose: Represents commercial purchase commitments issued to suppliers,
-- tracked by approving employee, order total, and workflow status.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id INTEGER PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    total_amount REAL NOT NULL CHECK (total_amount >= 0),
    currency TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('DRAFT', 'APPROVED', 'CANCELLED')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id),
    FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
);

-- ---------------------------------------------------------------------
-- Table 4: purchase_order_items
-- Purpose: Captures individual line items, product identifiers, ordered
-- quantities, and unit pricing associated with a purchase order.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_order_items (
    item_id INTEGER PRIMARY KEY,
    po_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (po_id) REFERENCES purchase_orders (po_id)
);

-- ---------------------------------------------------------------------
-- Table 5: goods_receipts
-- Purpose: Records physical or verified delivery of ordered line items
-- (Goods Receipt Note / GRN) against purchase order items.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS goods_receipts (
    grn_id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    received_quantity INTEGER NOT NULL CHECK (received_quantity > 0),
    receipt_date TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES purchase_order_items (item_id)
);

-- ---------------------------------------------------------------------
-- Table 6: invoices
-- Purpose: Stores vendor billing claims referencing a purchase order,
-- supporting 3-way matching and payment authorization workflows.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id INTEGER PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    po_id INTEGER NOT NULL,
    invoice_number TEXT NOT NULL,
    invoice_amount REAL NOT NULL CHECK (invoice_amount >= 0),
    invoice_quantity INTEGER NOT NULL CHECK (invoice_quantity > 0),
    currency TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'PAID', 'REJECTED')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders (po_id),
    UNIQUE (supplier_id, invoice_number)
);

