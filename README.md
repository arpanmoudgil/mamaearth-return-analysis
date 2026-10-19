# E-commerce Analytics: SQL → Python → GenAI

One repository, three layers. Each layer feeds the next:

```
data/*.csv ──► sql/ (SQLite schema, load, 9 reports)
           └─► analysis/ (pandas cleaning + EDA) ──► narrator/findings.json ──► narrator/ (SCR narrative)
                         └─► visualizations/*.png
```

**Golden rule:** no layer reports a number it did not compute itself or receive from the layer
before it. `findings.json` and both charts are written by code, never typed by hand.

> **Note on data:** the CSVs in `data/` are sample data matching the brief: 45 customers,
> 16 products, 180 orders, with the same deliberate mess. They are committed exactly as given
> and never edited by hand.

## Repository structure

```
README.md            this file
requirements.txt     pandas, matplotlib, google-genai
sql/                 schema.sql · seed_data.sql · reports.sql
data/                customers.csv · products.csv · orders.csv (never hand-edited)
analysis/            clean_and_eda.py · visualize.py
visualizations/      return_rate_by_payment.png · monthly_revenue.png
narrator/            findings.json · generate_narrative.py · sample_output.txt
```

## Run order (from the repo root)

Requires Python 3.10+ and the `sqlite3` command-line tool (3.32+; preinstalled on macOS and
most Linux, on Windows download "sqlite-tools" from the SQLite website).

```bash
# 0. Setup
python -m venv .venv
.venv/Scripts/activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# 1. SQL layer: builds sql/shop.db, prints the load check (45 / 16 / 180) and all 9 reports
sqlite3 sql/shop.db < sql/schema.sql
sqlite3 -header -column sql/shop.db < sql/seed_data.sql
sqlite3 -header -column sql/shop.db < sql/reports.sql

# 2. Python layer: cleaning + EDA, prints every step, writes narrator/findings.json
python analysis/clean_and_eda.py
python analysis/visualize.py      # writes the two PNGs

# 3. GenAI layer: writes narrator/sample_output.txt
python narrator/generate_narrative.py            # uses Gemini if GEMINI_API_KEY is set
python narrator/generate_narrative.py --offline  # template only, no key or network
```

Every script can be re-run end to end and produces identical numbers and PNGs.

## Layer 1: SQL (`sql/`)

| File | What it does |
|---|---|
| `schema.sql` | 3 tables with types, `NOT NULL`, `DEFAULT`, `PRIMARY KEY`, `FOREIGN KEY` and `CHECK` constraints. `discount_pct` and `rating` stay nullable. Re-runnable (drops and recreates). |
| `seed_data.sql` | Imports each CSV (`.import`) into a text staging table, then copies the rows into the real tables. Blank cells become `NULL` via `NULLIF(x, '')`. Rebuilds staging and empties the tables first, so it is re-runnable. Ends with the row-count check (45 / 16 / 180) and a NULL check. No cleaning happens in SQL. |
| `reports.sql` | The nine reports (a–i), each with its exact output pasted as a comment above it. Runs on the raw data, so duplicates and mixed casing are still present. Run it once after each fresh `schema.sql` + `seed_data.sql`, because report (i) adds a column. |

Revenue rule used everywhere: `quantity × price × (1 − discount/100)`, with a missing discount treated as 0%.

## Layer 2: Python (`analysis/`)

`clean_and_eda.py` runs on the **raw CSVs**, not the database:

1. **Load and inspect:** shapes, dtypes, missing values
2. **Standardise casing:** 7 raw `payment_method` spellings → `COD`, `Card`, `UPI`
3. **Remove duplicates:** natural key `customer_id + product_id + order_date + quantity`; prints the dropped order IDs
4. **Impute:** missing discount → 0, missing rating → median
5. **Merge and reconcile:** joins all three tables and explains the gap from SQL report (a): raw total − value of the duplicates = clean total, checked in code
6. **IQR outliers:** flags bulk quantities with a new `is_outlier` column. Nothing is dropped
7. **COD hypothesis:** COD vs prepaid return rate, with a verdict
8. **Segmentation:** return rate by payment method × city tier, naming the highest-risk segment
9. **Correlation:** matrix plus a label for every pair (negligible / weak / moderate / strong)
10. **Corrected trend:** monthly revenue with and without the outlier orders, and the true peak month

`visualize.py` reuses the same cleaning functions, so the charts can never disagree with the printed numbers.

## Layer 3: GenAI narrator (`narrator/`)

- `findings.json` is written by `clean_and_eda.py`, so every figure is computed.
- `generate_narrative.py` builds the prompt from `findings.json` and asks Gemini for a **Situation – Complication – Resolution** narrative.
  - Settings: temperature 0, token limit 700, 30-second timeout. Errors are caught and returned as a dict (`ok`, `source`, `text`, `error`).
- **Offline fallback:** a template narrative from the same figures. It runs with no API key and no network, so spending money is never required.
- **Numeric accuracy check:** confirms five key figures appear in the narrative: clean revenue, COD return rate, prepaid return rate, highest-risk segment rate, and bulk outlier value. If a Gemini narrative misses any of them, the script uses the offline narrative instead.

### API key

Use a **free** Google AI Studio key, set as an environment variable only:

```bash
set GEMINI_API_KEY=your-key        # Windows cmd
$env:GEMINI_API_KEY="your-key"     # PowerShell
export GEMINI_API_KEY=your-key     # macOS/Linux
```

Keys are never written to a file or committed. The model defaults to `gemini-2.5-flash` and can be changed with `GEMINI_MODEL`.
