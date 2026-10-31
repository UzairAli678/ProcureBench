-- ProcureBench Database Schema
-- Defines six core tables for evaluating procurement workflows.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Table 1: suppliers
-- Vendor records containing name, active status, and country.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'INACTIVE')),
    country TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- Table 2: employees
-- Staff authorized to participate in procurement approval workflows.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    employee_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    approval_limit REAL NOT NULL CHECK (approval_limit >= 0)
);

-- ---------------------------------------------------------------------
-- Table 3: purchase_orders
-- Commercial purchase commitments issued to suppliers.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id INTEGER PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    total_amount REAL NOT NULL CHECK (total_amount >= 0),
    status TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
);

-- ---------------------------------------------------------------------
-- Table 4: purchase_order_items
-- Individual line items and quantities associated with a purchase order.
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
-- Documented receipts of delivered items linked to purchase orders.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS goods_receipts (
    grn_id INTEGER PRIMARY KEY,
    po_id INTEGER NOT NULL,
    received_quantity INTEGER NOT NULL CHECK (received_quantity > 0),
    receipt_date TEXT NOT NULL,
    FOREIGN KEY (po_id) REFERENCES purchase_orders (po_id)
);

-- ---------------------------------------------------------------------
-- Table 6: invoices
-- Vendor payment claims referencing purchase orders.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id INTEGER PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    po_id INTEGER NOT NULL,
    invoice_number TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    status TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders (po_id),
    UNIQUE (supplier_id, invoice_number)
);

-- ---------------------------------------------------------------------
-- Indexes
-- Indexes for foreign key relationships and invoice lookup performance.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_id ON purchase_orders (supplier_id);
CREATE INDEX IF NOT EXISTS idx_purchase_order_items_po_id ON purchase_order_items (po_id);
CREATE INDEX IF NOT EXISTS idx_goods_receipts_po_id ON goods_receipts (po_id);
CREATE INDEX IF NOT EXISTS idx_invoices_supplier_id ON invoices (supplier_id);
CREATE INDEX IF NOT EXISTS idx_invoices_po_id ON invoices (po_id);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices (invoice_number);
