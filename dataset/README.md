# ProcureBench Benchmark Dataset

## 1. Overview & Purpose

The ProcureBench benchmark dataset contains 10 standardized, self-contained test scenarios designed to evaluate the reasoning and decision-making capabilities of Large Language Models (LLMs) in enterprise Procure-to-Pay (P2P) workflows.

### Design Architecture
- **Self-Contained Evaluation**: Each scenario packages its own synthetic transaction facts (supplier details, purchase orders, goods receipts, invoices, and approval limits), applicable policies, and an independently defined gold answer.
- **Independence from Database**: While the clean synthetic SQLite database in `data/` models a baseline operational ERP, the benchmark cases in `test_cases.json` contain deliberately injected discrepancies and edge cases. This guarantees that all evaluated models receive identical context payloads without database mutation.
- **Fictional Data**: All vendor names, employee identities, bank numbers, and transactional records are purely synthetic. PKR (Pakistani Rupee) is the standard baseline currency across scenarios.

---

## 2. ProcureBench Business Policies

The benchmark measures adherence to the following 10 internal business rules:

> [!NOTE]
> These rules represent internal governance policies defined specifically for the ProcureBench evaluation benchmark, rather than universal commercial statutes.

1. **`POL-01-SUPPLIER-ACTIVE`**: Only suppliers with an `ACTIVE` status in vendor master records are eligible for payment disbursements.
2. **`POL-02-QTY-MATCH`**: Invoiced line quantities must not exceed the cumulative quantity verified on Goods Receipt Notes (GRN).
3. **`POL-03-PO-EXISTENCE`**: An incoming invoice must reference a valid, pre-existing, and authorized Purchase Order (PO).
4. **`POL-04-SUPPLIER-MATCH`**: The supplier submitting the invoice must match the vendor named on the associated purchase order.
5. **`POL-05-NO-DUPLICATE`**: An invoice must not reuse or duplicate an invoice number already registered or paid for that supplier.
6. **`POL-06-AMOUNT-CALC`**: Invoiced amounts must match the product of authorized quantities and contracted PO unit prices.
7. **`POL-07-APPROVAL-LIMIT`**: Purchase orders and commitments must be authorized by an employee whose delegated approval limit meets or exceeds the order total.
8. **`POL-08-BANK-MATCH`**: Remittance bank account numbers listed on invoices must match verified banking records in the supplier profile.
9. **`POL-09-CURRENCY-MATCH`**: Invoice billing currency must strictly match the currency designated on the authorized purchase order.
10. **`POL-10-DISCREPANCY-HOLD`**: When any critical policy violation or discrepancy is detected, payment authorization must be placed on `HOLD` (or `ESCALATE` where delegation limits require management sign-off) until resolved.

---

## 3. Discrepancy Taxonomy & Error Codes

Every discrepancy identified in gold answers corresponds to an explicit code:

| Discrepancy Code | Description | Typical Violation |
| :--- | :--- | :--- |
| `DISC-QTY-MISMATCH` | Invoiced quantity exceeds physical receipt | Billed > Received |
| `DISC-DUP-INVOICE` | Duplicate invoice number from same vendor | Previously paid/processed |
| `DISC-INACTIVE-SUPPLIER` | Vendor profile marked INACTIVE | Compliance suspension |
| `DISC-MISSING-PO` | Referenced PO does not exist | Unmatched billing |
| `DISC-UNAUTH-APPROVAL` | PO total exceeds employee delegation threshold | Unauthorized commitment |
| `DISC-AMOUNT-MISMATCH` | Invoiced line amount exceeds agreed rate | Price/calculation markup |
| `DISC-PARTIAL-RECEIPT` | Full invoice submitted for partial delivery | Incomplete delivery |
| `DISC-BANK-MISMATCH` | Remittance account differs from vendor profile | Unverified bank account |
| `DISC-CURRENCY-MISMATCH` | Invoice currency differs from PO currency | Currency mismatch |

---

## 4. Benchmark Scenarios Summary

| Case ID | Title | Category | Difficulty | Expected Decision | Risk Level | Payment Allowed |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **PROC-001** | Quantity Mismatch | Quantity Reconciliation | Medium | `HOLD` | HIGH | False |
| **PROC-002** | Duplicate Invoice | Duplicate Prevention | Low | `HOLD` | HIGH | False |
| **PROC-003** | Inactive Supplier | Vendor Compliance | Low | `HOLD` | HIGH | False |
| **PROC-004** | Missing Purchase Order | Order Validation | Low | `HOLD` | HIGH | False |
| **PROC-005** | Unauthorized Approval | Financial Delegation | Medium | `ESCALATE` | HIGH | False |
| **PROC-006** | Incorrect Invoice Amount | Price and Calculation | Medium | `HOLD` | HIGH | False |
| **PROC-007** | Partial Goods Receipt | 3-Way Matching | Medium | `HOLD` | HIGH | False |
| **PROC-008** | Bank Detail Mismatch | Fraud and Compliance | Medium | `HOLD` | HIGH | False |
| **PROC-009** | Currency Mismatch | Currency Compliance | Low | `HOLD` | HIGH | False |
| **PROC-010** | Multiple Discrepancies | Compound Multi-Discrepancy | High | `HOLD` | HIGH | False |

---

## 5. Test Case Schema

Each case in `test_cases.json` follows this structured schema:

```json
{
  "case_id": "PROC-XXX",
  "title": "Scenario Name",
  "category": "Classification",
  "difficulty": "Low | Medium | High",
  "scenario": "Descriptive scenario narrative",
  "transaction_data": {
    "supplier": { ... },
    "purchase_order": { ... },
    "goods_receipt": { ... },
    "invoice": { ... }
  },
  "applicable_policies": [ "POL-XX-..." ],
  "expected_answer": {
    "decision": "APPROVE | HOLD | REJECT | ESCALATE",
    "risk_level": "LOW | MEDIUM | HIGH",
    "discrepancies": [ "DISC-..." ],
    "evidence": [ "Precise numerical and factual observations" ],
    "reasoning": "Grounded explanation linking evidence to policies",
    "next_action": "Recommended business remediation step",
    "payment_allowed": false
  }
}
```

