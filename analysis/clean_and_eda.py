"""
Part 2: Python wrangling & EDA, run on the RAW CSVs (not the SQL database).
Prints every intermediate result and writes narrator/findings.json.

Usage:  python analysis/clean_and_eda.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FINDINGS_PATH = ROOT / "narrator" / "findings.json"

NATURAL_KEY = ["customer_id", "product_id", "order_date", "quantity"]
PAYMENT_MAP = {"COD": "COD", "CARD": "Card", "UPI": "UPI"}


def order_value(df):
    """quantity * price * (1 - discount/100); a missing discount counts as 0%."""
    return df["quantity"] * df["price_inr"] * (1 - df["discount_pct"].fillna(0) / 100)


def strength(r):
    a = abs(r)
    if a < 0.1:
        return "negligible"
    if a < 0.3:
        return "weak"
    if a < 0.5:
        return "moderate"
    return "strong"


def section(title, verbose):
    if verbose:
        print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def load_raw():
    customers = pd.read_csv(DATA / "customers.csv")
    products = pd.read_csv(DATA / "products.csv")
    orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_date"])
    return customers, products, orders


def clean(verbose=True):
    """Tasks 1-6. Returns (raw orders, dropped duplicates, clean merged table, extras)."""
    say = print if verbose else (lambda *a, **k: None)

    # ---- Task 1: load and inspect ----
    section("Task 1: Load and inspect", verbose)
    customers, products, raw = load_raw()
    for name, df in [("customers", customers), ("products", products), ("orders", raw)]:
        say(f"{name:<10} shape = {df.shape}")
    say("\nRaw orders dtypes:\n" + raw.dtypes.to_string())
    say("\nMissing values per column (raw orders):\n" + raw.isna().sum().to_string())
    orders = raw.copy()

    # ---- Task 2: standardise payment_method casing ----
    section("Task 2: Standardise casing", verbose)
    raw_values = sorted(orders["payment_method"].unique())
    say(f"Raw payment_method values ({len(raw_values)}): {raw_values}")
    orders["payment_method"] = orders["payment_method"].str.strip().str.upper().map(PAYMENT_MAP)
    assert orders["payment_method"].notna().all(), "unmapped payment method"
    say(f"Clean values ({orders['payment_method'].nunique()}):")
    say(orders["payment_method"].value_counts().to_string())

    # ---- Task 3: remove double-submitted orders ----
    section("Task 3: Remove duplicates", verbose)
    say(f"Natural key: {NATURAL_KEY}")
    is_dupe = orders.duplicated(subset=NATURAL_KEY, keep="first")
    dropped = orders[is_dupe]
    say(f"Duplicates found: {len(dropped)}")
    say(f"Dropped order IDs: {dropped['order_id'].tolist()}")
    orders = orders[~is_dupe].reset_index(drop=True)
    say(f"Orders after de-duplication: {len(orders)}")

    # ---- Task 4: impute missing values ----
    section("Task 4: Impute missing values", verbose)
    n_disc, n_rate = orders["discount_pct"].isna().sum(), orders["rating"].isna().sum()
    rating_median = orders["rating"].median()
    say(f"Missing discount_pct: {n_disc} -> filled with 0")
    say(f"Missing rating:       {n_rate} -> filled with median {rating_median}")
    orders["discount_pct"] = orders["discount_pct"].fillna(0)
    orders["rating"] = orders["rating"].fillna(rating_median)
    say("Missing values after imputation:\n" + orders.isna().sum().to_string())

    # ---- Task 5: merge and reconcile with Part 1 ----
    section("Task 5: Merge and reconcile", verbose)
    merged = (orders.merge(customers, on="customer_id", how="left")
                    .merge(products[["product_id", "category", "price_inr"]], on="product_id", how="left"))
    assert merged["city"].notna().all() and merged["price_inr"].notna().all(), "orphan keys"
    merged["order_value"] = order_value(merged)

    raw_priced = raw.merge(products[["product_id", "price_inr"]], on="product_id")
    raw_total = order_value(raw_priced).sum()
    dropped_total = order_value(dropped.merge(products[["product_id", "price_inr"]], on="product_id")).sum()
    clean_total = merged["order_value"].sum()
    say(f"Merged shape: {merged.shape}")
    say(f"Raw total (same rule as SQL report a): INR {raw_total:,.2f}  over {len(raw)} orders")
    say(f"Value of {len(dropped)} dropped duplicates:  INR {dropped_total:,.2f}")
    say(f"Clean total:                           INR {clean_total:,.2f}  over {len(merged)} orders")
    say(f"Check: raw - duplicates = {raw_total - dropped_total:,.2f} (matches clean total: "
        f"{round(raw_total - dropped_total, 2) == round(clean_total, 2)})")
    say("Why they differ: Part 1 ran on raw data, so the 5 double-submitted orders were counted\n"
        "twice. Filling missing discounts with 0 changes nothing, because SQL already treated\n"
        "NULL discount as 0%. So the whole gap is the duplicates.")

    # ---- Task 6: IQR outliers on quantity (flag, never drop) ----
    section("Task 6: IQR outliers (quantity)", verbose)
    q1, q3 = merged["quantity"].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    merged["is_outlier"] = ~merged["quantity"].between(lower, upper)
    say(f"Q1 = {q1}, Q3 = {q3}, IQR = {iqr}, fences = [{lower}, {upper}]")
    say(f"Flagged {merged['is_outlier'].sum()} outlier rows (kept in the data):")
    say(merged.loc[merged["is_outlier"], ["order_id", "customer_id", "product_id",
                                          "order_date", "quantity", "order_value"]].to_string(index=False))

    extras = dict(raw_total=raw_total, dropped_total=dropped_total, clean_total=clean_total,
                  rating_median=rating_median, iqr_fences=(lower, upper),
                  raw_payment_values=len(raw_values))
    return raw, dropped, merged, extras


def return_rate_by_payment(df):
    return (df.groupby("payment_method")["returned"].agg(orders="count", returns="sum", rate="mean")
              .sort_values("rate", ascending=False))


def monthly_revenue(df):
    month = df["order_date"].dt.to_period("M")
    return pd.DataFrame({
        "with_outliers": df.groupby(month)["order_value"].sum(),
        "without_outliers": df[~df["is_outlier"]].groupby(month)["order_value"].sum(),
    }).fillna(0)


def analyse(merged, verbose=True):
    """Tasks 7-10. Returns a dict of results."""
    say = print if verbose else (lambda *a, **k: None)

    # ---- Task 7: COD return hypothesis ----
    section("Task 7: COD return hypothesis", verbose)
    say("H1: Cash-on-delivery orders are returned more often than prepaid (Card/UPI) orders.")
    by_pay = return_rate_by_payment(merged)
    say(by_pay.assign(rate=lambda d: (d["rate"] * 100).round(1)).rename(columns={"rate": "rate_%"}).to_string())
    cod_rate = merged.loc[merged["payment_method"] == "COD", "returned"].mean()
    prepaid_rate = merged.loc[merged["payment_method"] != "COD", "returned"].mean()
    supported = cod_rate > prepaid_rate
    verdict = "SUPPORTED" if supported else "NOT SUPPORTED"
    say(f"COD return rate {cod_rate:.1%} vs prepaid {prepaid_rate:.1%} "
        f"({cod_rate / prepaid_rate:.1f}x). Verdict: {verdict}")

    # ---- Task 8: payment method x city tier ----
    section("Task 8: Multi-level segmentation", verbose)
    seg = (merged.groupby(["payment_method", "city_tier"])["returned"]
                 .agg(orders="count", returns="sum", rate="mean").reset_index())
    say(seg.assign(rate=lambda d: (d["rate"] * 100).round(1)).rename(columns={"rate": "rate_%"})
           .to_string(index=False))
    worst = seg.sort_values(["rate", "orders"], ascending=False).iloc[0]
    say(f"Highest-risk segment: {worst['payment_method']} in tier "
        f"{worst['city_tier']} cities, {worst['rate']:.1%} returned "
        f"({int(worst['returns'])} of {int(worst['orders'])})")

    # ---- Task 9: correlation matrix ----
    section("Task 9: Correlation analysis", verbose)
    cols = ["quantity", "price_inr", "discount_pct", "rating", "returned", "order_value", "city_tier"]
    corr = merged[cols].corr()
    say(corr.round(2).to_string())
    pairs = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            r = corr.loc[a, b]
            pairs.append({"pair": f"{a} ~ {b}", "r": round(r, 2), "strength": strength(r)})
    pairs.sort(key=lambda p: -abs(p["r"]))
    say("\nPair labels (|r| <0.1 negligible, <0.3 weak, <0.5 moderate, else strong):")
    for p in pairs:
        say(f"  {p['pair']:<28} r = {p['r']:+.2f}  {p['strength']}")

    # ---- Task 10: outlier-corrected monthly trend ----
    section("Task 10: Outlier-corrected trend", verbose)
    monthly = monthly_revenue(merged)
    say(monthly.round(2).to_string())
    peak_raw = monthly["with_outliers"].idxmax()
    peak_true = monthly["without_outliers"].idxmax()
    say(f"Peak month WITH outliers:    {peak_raw} (INR {monthly.loc[peak_raw, 'with_outliers']:,.2f})")
    say(f"Peak month WITHOUT outliers: {peak_true} (INR {monthly.loc[peak_true, 'without_outliers']:,.2f})"
        "  <- true peak")

    return dict(by_pay=by_pay, cod_rate=cod_rate, prepaid_rate=prepaid_rate, verdict=verdict,
                worst=worst, pairs=pairs, monthly=monthly, peak_raw=peak_raw, peak_true=peak_true)


def write_findings(raw, dropped, merged, extras, res):
    """Every figure here is computed above. Nothing is typed by hand."""
    worst = res["worst"]
    findings = {
        "dataset": {
            "raw_orders": int(len(raw)),
            "duplicates_dropped": int(len(dropped)),
            "dropped_order_ids": dropped["order_id"].tolist(),
            "clean_orders": int(len(merged)),
            "customers_with_orders": int(merged["customer_id"].nunique()),
        },
        "revenue": {
            "raw_total_inr": round(float(extras["raw_total"]), 2),
            "clean_total_inr": round(float(extras["clean_total"]), 2),
            "duplicate_value_inr": round(float(extras["dropped_total"]), 2),
            "avg_order_value_inr": round(float(merged["order_value"].mean()), 2),
        },
        "returns": {
            "overall_return_rate_pct": round(float(merged["returned"].mean() * 100), 1),
            "by_payment_method_pct": {k: round(float(v * 100), 1) for k, v in res["by_pay"]["rate"].items()},
            "cod_return_rate_pct": round(float(res["cod_rate"] * 100), 1),
            "prepaid_return_rate_pct": round(float(res["prepaid_rate"] * 100), 1),
            "cod_hypothesis_verdict": res["verdict"],
            "highest_risk_segment": {
                "payment_method": worst["payment_method"],
                "city_tier": int(worst["city_tier"]),
                "return_rate_pct": round(float(worst["rate"] * 100), 1),
                "orders": int(worst["orders"]),
            },
        },
        "outliers": {
            "rule": "IQR on quantity, flagged not dropped",
            "count": int(merged["is_outlier"].sum()),
            "order_ids": merged.loc[merged["is_outlier"], "order_id"].tolist(),
            "value_inr": round(float(merged.loc[merged["is_outlier"], "order_value"].sum()), 2),
        },
        "trend": {
            "peak_month_with_outliers": str(res["peak_raw"]),
            "true_peak_month": str(res["peak_true"]),
            "true_peak_revenue_inr": round(float(res["monthly"].loc[res["peak_true"], "without_outliers"]), 2),
        },
        "strongest_correlations": [p for p in res["pairs"] if p["strength"] in ("moderate", "strong")],
    }
    FINDINGS_PATH.parent.mkdir(exist_ok=True)
    FINDINGS_PATH.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"\nWrote {FINDINGS_PATH.relative_to(ROOT)}")


def main():
    raw, dropped, merged, extras = clean(verbose=True)
    res = analyse(merged, verbose=True)
    write_findings(raw, dropped, merged, extras, res)


if __name__ == "__main__":
    main()
