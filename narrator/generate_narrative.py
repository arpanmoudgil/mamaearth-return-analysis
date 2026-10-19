"""
Part 3: GenAI-powered insight narrator.

Reads findings.json (written by analysis/clean_and_eda.py), turns it into a
Situation-Complication-Resolution (SCR) business narrative with Gemini, and
falls back to a template when there is no API key or no network. Every narrative
is checked for the five key figures before it is accepted.

Usage:
    python narrator/generate_narrative.py              # Gemini if GEMINI_API_KEY is set, else offline
    python narrator/generate_narrative.py --offline    # force the template path

The key is read from the GEMINI_API_KEY environment variable only (free Google
AI Studio key). It is never written to any file.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINDINGS_PATH = HERE / "findings.json"
OUTPUT_PATH = HERE / "sample_output.txt"

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")  # free-tier model
TEMPERATURE = 0
MAX_OUTPUT_TOKENS = 700
TIMEOUT_MS = 30_000

SYSTEM_INSTRUCTION = (
    "You are a business analyst writing for an e-commerce leadership team. "
    "Write a short narrative in three labelled parts: Situation, Complication, Resolution. "
    "Use ONLY the figures provided by the user. Never invent, round or recalculate a number. "
    "Copy every figure exactly as written, including decimals. "
    "Plain English, no bullet lists, under 250 words."
)


def load_findings(path=FINDINGS_PATH):
    return json.loads(path.read_text(encoding="utf-8"))


def key_figures(f):
    """The five figures every narrative must contain, as display strings."""
    seg = f["returns"]["highest_risk_segment"]
    return {
        "clean revenue (INR)": f"{f['revenue']['clean_total_inr']:,.2f}",
        "COD return rate (%)": f"{f['returns']['cod_return_rate_pct']:.1f}",
        "prepaid return rate (%)": f"{f['returns']['prepaid_return_rate_pct']:.1f}",
        f"{seg['payment_method']} tier-{seg['city_tier']} return rate (%)": f"{seg['return_rate_pct']:.1f}",
        "bulk outlier value (INR)": f"{f['outliers']['value_inr']:,.2f}",
    }


def build_prompt(f):
    """Built entirely from findings.json; no number is typed here."""
    k = key_figures(f)
    seg = f["returns"]["highest_risk_segment"]
    lines = [
        "Write the SCR narrative from these verified figures.",
        "",
        f"- Orders analysed after cleaning: {f['dataset']['clean_orders']} "
        f"({f['dataset']['duplicates_dropped']} double-submitted orders removed)",
        f"- Clean revenue: INR {k['clean revenue (INR)']}",
        f"- Average order value: INR {f['revenue']['avg_order_value_inr']:,.2f}",
        f"- Overall return rate: {f['returns']['overall_return_rate_pct']:.1f}%",
        f"- Cash-on-delivery (COD) return rate: {k['COD return rate (%)']}%",
        f"- Prepaid (Card + UPI) return rate: {k['prepaid return rate (%)']}%",
        f"- Hypothesis 'COD orders are returned more': {f['returns']['cod_hypothesis_verdict']}",
        f"- Highest-risk segment: {seg['payment_method']} orders in tier-{seg['city_tier']} cities, "
        f"{seg['return_rate_pct']:.1f}% returned ({seg['orders']} orders)",
        f"- {f['outliers']['count']} bulk outlier orders worth INR {k['bulk outlier value (INR)']} "
        f"inflate {f['trend']['peak_month_with_outliers']}; the true peak month is "
        f"{f['trend']['true_peak_month']} (INR {f['trend']['true_peak_revenue_inr']:,.2f})",
        "",
        "These five figures must appear exactly as written: "
        + "; ".join(f"{name} = {value}" for name, value in k.items()),
    ]
    return "\n".join(lines)


def generate_with_gemini(prompt):
    """Calls Gemini. Always returns a dict, never raises."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"ok": False, "source": "gemini", "text": None, "error": "GEMINI_API_KEY is not set"}
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=TEMPERATURE,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                thinking_config=types.ThinkingConfig(thinking_budget=0),  # all tokens go to the answer
            ),
        )
        text = (response.text or "").strip()
        if not text:
            return {"ok": False, "source": "gemini", "text": None, "error": "empty response"}
        return {"ok": True, "source": "gemini", "text": text, "error": None}
    except Exception as exc:  # network, quota, bad key, timeout, missing package
        return {"ok": False, "source": "gemini", "text": None, "error": f"{type(exc).__name__}: {exc}"}


def generate_offline(f):
    """Template narrative: no API key, no network, same verified figures."""
    k = key_figures(f)
    seg = f["returns"]["highest_risk_segment"]
    t = f["trend"]
    text = (
        f"Situation: After removing {f['dataset']['duplicates_dropped']} double-submitted orders, "
        f"the store has {f['dataset']['clean_orders']} clean orders worth INR {k['clean revenue (INR)']}, "
        f"an average of INR {f['revenue']['avg_order_value_inr']:,.2f} per order. "
        f"Overall, {f['returns']['overall_return_rate_pct']:.1f}% of orders come back.\n\n"
        f"Complication: Returns are concentrated in cash on delivery. COD orders are returned at "
        f"{k['COD return rate (%)']}%, against {k['prepaid return rate (%)']}% for prepaid Card and UPI "
        f"orders, so the hypothesis is {f['returns']['cod_hypothesis_verdict'].lower()}. The worst segment "
        f"is {seg['payment_method']} in tier-{seg['city_tier']} cities at {seg['return_rate_pct']:.1f}%. "
        f"Headline trends are also misleading: {f['outliers']['count']} bulk orders worth INR "
        f"{k['bulk outlier value (INR)']} make {t['peak_month_with_outliers']} look like the best month, "
        f"when the true peak is {t['true_peak_month']} at INR {t['true_peak_revenue_inr']:,.2f}.\n\n"
        f"Resolution: Nudge COD buyers toward prepaid payment, starting with tier-{seg['city_tier']} cities, "
        f"for example with a small prepaid incentive or COD confirmation calls. Report monthly revenue "
        f"with bulk orders separated, and plan stock and staffing around {t['true_peak_month']}, "
        f"not {t['peak_month_with_outliers']}."
    )
    return {"ok": True, "source": "offline", "text": text, "error": None}


def check_figures(text, f):
    """Confirms each key figure appears in the narrative (commas and currency ignored)."""
    normalised = text.replace(",", "")
    results = {}
    for name, value in key_figures(f).items():
        results[name] = (value, value.replace(",", "") in normalised)
    return results


def main():
    findings = load_findings()
    prompt = build_prompt(findings)
    force_offline = "--offline" in sys.argv

    result = None
    if not force_offline:
        result = generate_with_gemini(prompt)
        if result["ok"]:
            checks = check_figures(result["text"], findings)
            if not all(ok for _, ok in checks.values()):
                missing = [n for n, (_, ok) in checks.items() if not ok]
                print(f"Gemini narrative failed the figure check (missing: {missing}); using offline fallback.")
                result = None
        else:
            print(f"Gemini unavailable ({result['error']}); using offline fallback.")
            result = None
    if result is None:
        result = generate_offline(findings)

    checks = check_figures(result["text"], findings)
    report = [f"Source: {result['source']}" + (f" ({MODEL})" if result["source"] == "gemini" else ""), "",
              result["text"], "", "Numeric accuracy check:"]
    for name, (value, ok) in checks.items():
        report.append(f"  [{'PASS' if ok else 'FAIL'}] {name}: {value}")
    passed = sum(ok for _, ok in checks.values())
    report.append(f"  {passed}/{len(checks)} key figures present")

    output = "\n".join(report)
    print(output)
    OUTPUT_PATH.write_text(output + "\n", encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH.name}")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
