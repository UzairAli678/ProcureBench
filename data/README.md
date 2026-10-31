# ProcureBench Database

## Purpose of the Database

The ProcureBench database serves as the relational data layer for evaluating the reliability and policy-compliance decision-making of Large Language Models (LLMs) across enterprise procurement workflows. It models standard Procure-to-Pay (P2P) records against which LLM agents evaluate commercial transactions, 3-way matching rules, and business discrepancy scenarios.

> [!IMPORTANT]
> **Synthetic Data Notice**: This database is designed to contain **synthetic procurement data only**. No real company, proprietary, or confidential internship data is used or stored.

---

## Table Definitions

The schema consists of exactly six relational tables defined in `schemas.sql`:

1. **`suppliers`**
   - **Purpose**: Stores vendor master records, including supplier name, operating status (`ACTIVE` or `INACTIVE`), and country of origin.
   - **Primary Key**: `supplier_id`

2. **`employees`**
   - **Purpose**: Tracks personnel authorized to participate in procurement and approval workflows, along with their maximum financial delegation limit (`approval_limit`).
   - **Primary Key**: `employee_id`

3. **`purchase_orders`**
   - **Purpose**: Captures formal commercial commitments issued to suppliers, recording the order date, aggregate monetary value (`total_amount`), and order status.
   - **Primary Key**: `po_id`
   - **Foreign Keys**: `supplier_id` references `suppliers(supplier_id)`

4. **`purchase_order_items`**
   - **Purpose**: Contains line-item breakdowns for purchase orders, specifying ordered products, line quantities, and agreed unit pricing.
   - **Primary Key**: `item_id`
   - **Foreign Keys**: `po_id` references `purchase_orders(po_id)`

5. **`goods_receipts`**
   - **Purpose**: Documents the receipt of physical goods delivered against an authorized purchase order (Goods Receipt Note / GRN), including quantity delivered and receipt date.
   - **Primary Key**: `grn_id`
   - **Foreign Keys**: `po_id` references `purchase_orders(po_id)`

6. **`invoices`**
   - **Purpose**: Stores billing requests submitted by vendors against purchase orders, used in 3-way reconciliation (PO vs. GRN vs. Invoice) and payment authorizations.
   - **Primary Key**: `invoice_id`
   - **Foreign Keys**:
     - `supplier_id` references `suppliers(supplier_id)`
     - `po_id` references `purchase_orders(po_id)`
   - **Constraints**: Enforces uniqueness on `(supplier_id, invoice_number)` to prevent duplicate billing from the same supplier.

---

## Entity Relationships

```
suppliers (supplier_id)
  ▲
  ├── purchase_orders (supplier_id)
  │     ▲
  │     ├── purchase_order_items (po_id)
  │     ├── goods_receipts (po_id)
  │     └── invoices (po_id)
  │
  └── invoices (supplier_id)
```

- Each **purchase order** belongs to one **supplier**.
- Each **purchase order item** belongs to one **purchase order**.
- Each **goods receipt** references one **purchase order**.
- Each **invoice** references both a **supplier** and a **purchase order**.
- **Employees** maintain approval thresholds used to validate authorization rights against purchase order totals.

---

## Foreign Key Enforcement

SQLite does not enforce foreign keys by default. When connecting via Python or any database client, foreign key enforcement must be explicitly activated on every connection:

```python
conn.execute("PRAGMA foreign_keys = ON;")
```

