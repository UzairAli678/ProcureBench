# ProcureBench
### Evaluating LLM Reliability in Enterprise Procurement Workflows

ProcureBench is a lightweight evaluation benchmark designed to measure how reliably Large Language Models handle enterprise procurement scenarios.

It uses synthetically generated procurement records, predefined business policies, and test cases containing both valid transactions and deliberately introduced discrepancies.

The same scenarios will be presented to multiple LLMs and their responses will be evaluated using a consistent scoring framework.

---

## 1. Problem Statement

Enterprise procurement workflows (such as 3-way matching across purchase orders, goods receipts, and vendor invoices) require strict adherence to business policies and zero tolerance for costly financial errors. While Large Language Models (LLMs) are increasingly deployed as autonomous agents or co-pilots in enterprise resource planning (ERP) environments, their reliability in spotting discrepancies, enforcing policy rules, and preventing fraudulent or erroneous payouts remains poorly measured and benchmarked.

## 2. Project Objectives

- **Standardized Evaluation**: Create a transparent, reproducible benchmark to assess LLM decision-making in procurement workflows.
- **Discrepancy Detection**: Evaluate the ability of models to identify subtle anomalies (e.g., price deviations, quantity mismatches, duplicate billings, unauthorized approvals).
- **Auditability and Reasoning**: Measure whether models provide grounded reasoning and cite explicit policy rules rather than generating hallucinations or unsupported decisions.
- **Multi-Model Comparison**: Compare closed and open-source models using a normalized scoring framework.

## 3. Scope — Procure-to-Pay Workflow

ProcureBench focuses on the operational core of the Procure-to-Pay (P2P) cycle:
- Purchase Requisition and Purchase Order (PO) creation and approval
- Goods Receipt Note (GRN) verification and quantity matching
- Supplier Invoice intake and 3-way matching (PO vs. GRN vs. Invoice)
- Business policy enforcement (e.g., approval thresholds, active vendor validation, banking details consistency)
- Payment authorization decision (Approve, Reject, or Escalate for Manual Review)

*Note: All data within this project is purely synthetic. No real company or proprietary corporate data is used.*

## 4. Technology Stack

- **Core Language**: Python
- **Data Storage**: SQLite
- **Data Processing**: Pandas, Faker
- **Evaluation & Testing**: pytest
- **LLM Integrations (Planned)**: Gemini API, Groq API (optional)
- **Reporting & Visualization (Planned)**: Streamlit, Plotly

## 5. Planned Benchmark Scenarios

> [!NOTE]
> The following scenarios represent planned test cases subject to implementation and validation in subsequent development phases.

1. **Quantity Mismatch**: Invoiced quantity exceeds the received goods quantity or PO quantity.
2. **Duplicate Invoice**: Resubmission of an already processed or paid invoice with identical or slightly modified metadata.
3. **Inactive Supplier**: Invoices or orders associated with a vendor marked inactive, suspended, or de-listed in vendor master records.
4. **Missing Purchase Order**: Invoices submitted without a corresponding approved PO.
5. **Unauthorized Approval**: Purchase orders approved by an individual exceeding their designated financial delegation limits.
6. **Incorrect Invoice Amount**: Unit price, tax calculation, or total balance differing from negotiated PO rates.
7. **Partial Goods Receipt**: Invoicing for full delivery when only a partial delivery has been received and verified.
8. **Supplier Bank-Detail Mismatch**: Remittance bank account numbers on the invoice differing from verified vendor master profiles.
9. **Currency Mismatch**: Discrepancies between PO currency and invoice billing currency without valid exchange terms.
10. **Multiple Discrepancies**: Complex compound cases combining multiple overlapping policy violations and mismatches.

## 6. Evaluation Methodology

> [!NOTE]
> Scoring parameters and weight allocations are planned and subject to experimental tuning during implementation.

Model responses will be scored on a 100-point rubric per scenario based on the following planned scoring weights:

| Evaluation Criterion | Planned Weight | Description |
| :--- | :---: | :--- |
| **Correct Business Decision** | 40 | Proper final disposition (Approve, Reject, or Escalate) |
| **Discrepancy Identification** | 25 | Precise detection of the specific issue(s) present |
| **Evidence and Reasoning** | 20 | Grounded explanation citing specific line items, IDs, and policies |
| **Recommended Next Action** | 10 | Actionable remediation guidance (e.g., contact vendor, request revised invoice) |
| **Valid Structured Output** | 5 | Adherence to requested JSON/structured response schema |
| **Total** | **100** | |

## 7. Installation (Planned)

*The benchmark is currently in the initial configuration phase and is not yet functional.*

Planned setup instructions:

```bash
git clone https://github.com/your-username/ProcureBench.git
cd ProcureBench
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## 8. Running the Benchmark (Planned)

*Execution modules are under development and not yet available.*

Planned execution command:

```bash
python run_benchmark.py
```

## 9. Experimental Results

*Results will be added only after actual benchmark experiments are conducted.*

No experimental or synthetic benchmark scores have been generated at this stage.

## 10. Limitations

- Relies solely on synthetic data structures which may simplify nuances found in real-world messy ERP extracts.
- Focuses primarily on structured tabular and document data rather than unstructured email negotiation threads.
- Initial scenarios assume English-language transaction documents and standard enterprise policy guidelines.

## 11. Hackathon Submission

This project is created as a structured benchmark submission exploring generative AI reliability, enterprise compliance, and deterministic policy enforcement in mission-critical business workflows.

