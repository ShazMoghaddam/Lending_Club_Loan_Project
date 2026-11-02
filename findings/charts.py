"""Every chart in the project, drawn with bezel-charts (https://pypi.org/project/bezel-charts/).

Each function returns a chart, which shows up in a notebook and saves as an SVG.
"""

from __future__ import annotations

import pandas as pd

import bezel_charts as bc

try:
    from . import analysis as an
except ImportError:
    import analysis as an

WIDE = {"theme": "light", "width": 760}
TILE = {"theme": "light", "width": 270}

# The library's default order puts pink next to green, which look alike with red-green colour blindness.
PAIR = ["#6E70F0", "#D99A0E"]
MUTED, STRONG = "#B7B8F7", "#6E70F0"
FIVE_GRADES = list("ABCDE")  # Grades F and G have too few loans in a single year to compare reliably

PURPOSE_NAMES = {
    "small_business": "Small business", "medical": "Medical", "other": "Other", "debt_consolidation": "Debt consolidation",
    "major_purchase": "Major purchase", "home_improvement": "Home improvement", "credit_card": "Credit card", "car": "Car",
}


def three_answers():
    answers = an.three_answers()
    return bc.bars(
        pd.Series(
            {
                "First version's label": round(answers["original"] * 100, 1),
                "Finished loans only": round(answers["finished"] * 100, 1),
                "Loans with time to finish": round(answers["mature"] * 100, 1),
            }
        ),
        heading="Share of loans that defaulted, measured three ways",
        horizontal=True, stat="none", show_values=True, suffix="%", decimals=1, color=[MUTED, MUTED, STRONG],
        highlight="none", **WIDE,
    )


def default_by_grade():
    return bc.bars(
        (an.by_grade()["default_rate"] * 100).round(1),
        heading="Share of loans that defaulted, by grade, loans with time to finish",
        stat="none", show_values=True, suffix="%", decimals=1, height=210, **WIDE,
    )


def earned_by_grade():
    table = an.by_grade()
    return bc.bars(
        pd.DataFrame({"3-year loans": table["earned_3y"].round(1), "5-year loans": table["earned_5y"].round(1)}),
        heading="Cents repaid above each $1 lent, by grade, before fees",
        stat="none", show_values=True, suffix="¢", decimals=1, height=230, color=PAIR, **WIDE,
    )


def same_grade_worse():
    before, after = an.three_year_by_grade(2013), an.three_year_by_grade(2015)
    return bc.bars(
        pd.DataFrame(
            {
                "Issued 2013": (before["default_rate"] * 100).round(1),
                "Issued 2015": (after["default_rate"] * 100).round(1),
            }
        ).loc[FIVE_GRADES],
        heading="Share of 3-year loans that defaulted, same grade, two years apart",
        stat="none", show_values=True, suffix="%", decimals=1, height=230, color=PAIR, **WIDE,
    )


def income_within_grade():
    table = an.rate_by_band_and_grade("income") * 100
    return bc.bars(
        pd.DataFrame(
            {"Income under $40k": table.loc["Under $40k"].round(1), "Income over $120k": table.loc["Over $120k"].round(1)}
        ).loc[FIVE_GRADES],
        heading="Share of loans that defaulted, by grade, lowest and highest incomes",
        stat="none", show_values=True, suffix="%", decimals=1, height=230, color=PAIR, **WIDE,
    )


def purposes():
    rates = (an.purposes() * 100).round(1)
    rates.index = [PURPOSE_NAMES[name] for name in rates.index]
    return bc.bars(
        rates,
        heading="Share of loans that defaulted, by stated purpose",
        horizontal=True, stat="none", show_values=True, suffix="%", decimals=1, **WIDE,
    )


def employment():
    return bc.bars(
        (an.employment() * 100).round(1),
        heading="Share of loans that defaulted, by time in current job",
        stat="none", show_values=True, suffix="%", decimals=1, height=200, **WIDE,
    )


def model_scores():
    return bc.bars(
        an.models()["auc"].round(2),
        heading="How well each method ranks risk on later loans. 0.5 is a coin flip, 1 is perfect",
        horizontal=True, stat="none", show_values=True, decimals=2, **WIDE,
    )


def risk_deciles():
    rates = (an.models()["deciles"] * 100).round(1)
    rates.index = [str(n) for n in rates.index]
    return bc.bars(
        rates,
        heading="Share defaulting, later loans sorted into ten groups by predicted risk, 1 is safest",
        stat="none", show_values=True, suffix="%", decimals=0, height=210, **WIDE,
    )


# Headline tiles ------------------------------------------------------------------------------------

def tile_default():
    rate = an.three_answers()["mature"] * 100
    return bc.gauge(round(rate, 1), label="of loans defaulted", heading="Default rate", suffix="%", **TILE)


def tile_funded():
    funded = an.yearly_funded() / 1e9
    funded.index = funded.index.astype(str)
    return bc.spark(funded, heading="Lent in 2018", delta="none", straight=True, height=86, prefix="$", suffix="bn", decimals=1, **TILE)


def tile_grade_g():
    return bc.ring(
        {"A": round(an.by_grade().loc["A", "default_rate"] * 100, 1), "G": round(an.by_grade().loc["G", "default_rate"] * 100, 1)},
        heading="Defaults, grade A and G", suffix="%", max=100, **TILE,
    )


ALL = {
    "three-answers": three_answers,
    "default-by-grade": default_by_grade,
    "earned-by-grade": earned_by_grade,
    "same-grade-worse": same_grade_worse,
    "income-within-grade": income_within_grade,
    "purposes": purposes,
    "employment": employment,
    "model-scores": model_scores,
    "risk-deciles": risk_deciles,
    "tile-default": tile_default,
    "tile-funded": tile_funded,
    "tile-grades": tile_grade_g,
}
