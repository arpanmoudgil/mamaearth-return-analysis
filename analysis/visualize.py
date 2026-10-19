"""
Part 2, Task 11: two charts, built from the same cleaning code as clean_and_eda.py.
Writes visualizations/return_rate_by_payment.png and visualizations/monthly_revenue.png.

Usage:  python analysis/visualize.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # no window; identical PNGs on every run
import matplotlib.pyplot as plt

from clean_and_eda import clean, monthly_revenue, return_rate_by_payment

OUT = Path(__file__).resolve().parent.parent / "visualizations"


def return_rate_chart(merged):
    by_pay = return_rate_by_payment(merged)
    rates = by_pay["rate"] * 100
    overall = merged["returned"].mean() * 100

    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = ["#c0392b" if m == "COD" else "#2e7d5b" for m in rates.index]
    bars = ax.bar(rates.index, rates.values, color=colors)
    ax.axhline(overall, color="#555", linestyle="--", linewidth=1)
    ax.text(len(rates) - 0.5, overall + 0.6, f"overall {overall:.1f}%", ha="right", fontsize=9, color="#555")
    for bar, (rate, n) in zip(bars, zip(rates.values, by_pay["orders"])):
        ax.text(bar.get_x() + bar.get_width() / 2, rate + 0.6, f"{rate:.1f}%\n(n={n})",
                ha="center", va="bottom", fontsize=9)
    ax.set_title("Return rate by payment method (cleaned orders)")
    ax.set_ylabel("Orders returned (%)")
    ax.set_ylim(0, rates.max() * 1.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = OUT / "return_rate_by_payment.png"
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)
    return path


def monthly_revenue_chart(merged):
    monthly = monthly_revenue(merged)
    labels = [p.strftime("%b %y") for p in monthly.index]
    peak = monthly["without_outliers"].values.argmax()

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(labels, monthly["with_outliers"] / 1000, color="#bbb", linestyle="--",
            marker="o", markersize=4, label="With bulk outliers")
    ax.plot(labels, monthly["without_outliers"] / 1000, color="#2e7d5b", linewidth=2.2,
            marker="o", label="Corrected (outliers removed)")
    ax.annotate(f"True peak: {labels[peak]}", xy=(peak, monthly["without_outliers"].iloc[peak] / 1000),
                xytext=(0, 14), textcoords="offset points", ha="center", fontsize=9, color="#2e7d5b")
    ax.set_title("Monthly revenue, with and without outlier orders")
    ax.set_ylabel("Revenue (INR thousand)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = OUT / "monthly_revenue.png"
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)
    return path


def main():
    OUT.mkdir(exist_ok=True)
    _, _, merged, _ = clean(verbose=False)
    for path in (return_rate_chart(merged), monthly_revenue_chart(merged)):
        print(f"Saved {path.relative_to(OUT.parent)}")


if __name__ == "__main__":
    main()
