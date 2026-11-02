"""Draw every chart and write the findings report.

Run from the repository root:

    python findings/build.py

Charts go into charts/ as SVG files. The report is written to findings/README.md, and the key findings in the
main README are rewritten between their marker comments. Every number is worked out from the data. Nothing in
them is typed in by hand.
"""

from __future__ import annotations

import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "findings"))

import analysis as an  # noqa: E402
import charts  # noqa: E402

CHARTS = ROOT / "charts"
REPORT = ROOT / "findings" / "README.md"
README = ROOT / "README.md"


def facts() -> dict:
    """Every number the writing uses, in one place."""
    answers = an.three_answers()
    counts = an.statuses()
    table = an.vintages()
    grade = an.by_grade()
    before, after = an.three_year_by_grade(2013), an.three_year_by_grade(2015)
    funded = an.yearly_funded()
    income = an.rate_by_band("income")
    income_c = an.rate_by_band_and_grade("income")["C"]
    fico = an.rate_by_band("fico")
    fico_c = an.rate_by_band_and_grade("fico")["C"]
    dti = an.rate_by_band("dti")
    purpose = an.purposes()
    job = an.employment()
    stated = job.drop("Not given")
    model = an.models()
    auc = model["auc"]
    old = an.first_version()
    best = grade["earned_3y"].idxmax()
    return {
        "loans": f"{counts.sum():,}", "funded": f"${table['funded'].sum() / 1e9:.1f}bn", "current": f"{old['current']:,}",
        "mature_loans": f"{table[table['mature']]['loans'].sum():,}",
        "original": answers["original"], "finished": answers["finished"], "mature": answers["mature"],
        "open_share": counts[["Current", "In Grace Period", "Late (16-30 days)", "Late (31-120 days)"]].sum() / counts.sum(),
        "a": grade.loc["A", "default_rate"], "g": grade.loc["G", "default_rate"],
        "a_rate": grade.loc["A", "interest"], "g_rate": grade.loc["G", "interest"], "g_loans": f"{grade.loc['G', 'loans']:,}",
        "best": best, "best_3y": grade.loc[best, "earned_3y"], "a_3y": grade.loc["A", "earned_3y"], "g_3y": grade.loc["G", "earned_3y"],
        "c_5y": grade.loc["C", "earned_5y"], "g_5y": grade.loc["G", "earned_5y"], "a_5y": grade.loc["A", "earned_5y"],
        "c13": before.loc["C", "default_rate"], "c15": after.loc["C", "default_rate"], "c13r": before.loc["C", "interest"],
        "c15r": after.loc["C", "interest"], "e13": before.loc["E", "default_rate"], "e15": after.loc["E", "default_rate"],
        "funded13": f"${funded[2013] / 1e9:.1f}bn", "funded15": f"${funded[2015] / 1e9:.1f}bn",
        "earn13": an.three_year_earned(2013), "earn15": an.three_year_earned(2015),
        "inc_low": income["Under $40k"], "inc_high": income["Over $120k"], "inc_low_c": income_c["Under $40k"], "inc_high_c": income_c["Over $120k"],
        "fico_low": fico["Under 680"], "fico_high": fico["750 or more"], "fico_low_c": fico_c["Under 680"], "fico_high_c": fico_c["750 or more"],
        "dti_low": dti["Under 10"], "dti_high": dti["Over 30"],
        "biz": purpose["small_business"], "car": purpose["car"], "job_low": stated.min(), "job_high": stated.max(), "job_none": job["Not given"],
        "auc_grade": auc["Lender's sub-grade alone"], "auc_app": auc["Applicant data, logistic regression"],
        "auc_gb": auc["Applicant data, gradient boosting"], "auc_rate": auc["Applicant data plus interest rate"],
        "gap_low": model["gap_low"], "gap_high": model["gap_high"], "train": f"{model['train_size']:,}", "test": f"{model['test_size']:,}",
        "dec_low": model["deciles"].iloc[0], "dec_high": model["deciles"].iloc[-1], "old_auc": old["auc"],
    }


def key_findings(f: dict) -> str:
    return f"""### The first answer to "how many default?" was wrong

Counting {f['current']} loans still being repaid as "no default" gives {f['original']:.1%}. Using only finished loans swings too far,
to {f['finished']:.1%}. Among loans that had time to finish, the answer is **{f['mature']:.1%}**.

![Three measures of the default rate](charts/three-answers.svg)

### The riskiest 3-year loans earned the least

Grade G borrowers paid {f['g_rate']:.1f}% interest against {f['a_rate']:.1f}% for grade A, but {f['g']:.0%} of them defaulted. On 3-year loans, lenders
got back **{f['g_3y']:.1f} cents** above each dollar on grade G and **{f['best_3y']:.1f} cents** on grade {f['best']}, before fees.

![Cents repaid above each dollar lent, by grade](charts/earned-by-grade.svg)

### The same grade got riskier

Between 2013 and 2015, 3-year grade C loans went from {f['c13']:.1%} defaulting to **{f['c15']:.1%}**, while their average interest rate
fell from {f['c13r']:.1f}% to {f['c15r']:.1f}%.

![Default rates by grade, 2013 and 2015](charts/same-grade-worse.svg)

### My models couldn't beat the lender's own grade

Tested fairly on later loans, the lender's sub-grade alone scored **{f['auc_grade']:.2f}**. Models built on the applicant data here scored
**{f['auc_app']:.2f}**.

![How well each method ranks risk](charts/model-scores.svg)"""


def report(f: dict) -> str:
    return f"""# Findings

What happened to {f['loans']} Lending Club loans worth {f['funded']}, issued from 2007 to 2018. This page is written by
[`build.py`](build.py), so every number comes straight from the data.

"Defaulted" means charged off or in default. Unless a finding says otherwise, rates use the {f['mature_loans']} loans that
had time to finish by December 2018: 3-year loans issued up to 2015 and 5-year loans issued up to 2013.

## 1. How many loans default? It depends how you count

| How it's counted | Default rate | The problem |
|---|---|---|
| The first version's label | {f['original']:.1%} | Treats {f['current']} loans still being repaid as "no default" |
| Finished loans only | {f['finished']:.1%} | Recent loans that go wrong finish early, while most healthy ones are still running |
| Loans with time to finish | **{f['mature']:.1%}** | Leaves out recent loans, but compares like with like |

![Three measures of the default rate](../charts/three-answers.svg)

{f['open_share']:.0%} of all loans hadn't finished when the data ends, so this choice shapes everything that follows.

## 2. Grades work

Lending Club gave every loan a grade from A to G. Defaults climb at every step, from {f['a']:.1%} at grade A to {f['g']:.1%} at grade G.

![Default rate by grade](../charts/default-by-grade.svg)

## 3. The riskiest 3-year loans earned the least

Higher interest is meant to pay for higher risk. Grade G borrowers paid an average of {f['g_rate']:.1f}% against {f['a_rate']:.1f}% for grade A, yet on 3-year
loans lenders got back {f['g_3y']:.1f} cents above each dollar on grade G, {f['a_3y']:.1f} cents on grade A and {f['best_3y']:.1f} cents on grade {f['best']}, the best of the seven.

![Cents repaid above each dollar lent](../charts/earned-by-grade.svg)

5-year loans look different: {f['a_5y']:.1f} cents at grade A, {f['c_5y']:.1f} at grade C and {f['g_5y']:.1f} at grade G, so the extra risk paid at first and then stopped
adding much. Don't compare the two terms directly. These figures are before fees and don't adjust for time, so 5-year money
was tied up for longer, and only 5-year loans from 2010 to 2013 have finished. Grade G also has just {f['g_loans']} mature loans.

## 4. The same grade got riskier

A grade should mean the same thing from year to year. It didn't. Among 3-year loans, grade C defaults rose from {f['c13']:.1%} for loans
issued in 2013 to {f['c15']:.1%} for 2015, and grade E from {f['e13']:.1%} to {f['e15']:.1%}. Grade C's average interest rate fell from {f['c13r']:.1f}% to {f['c15r']:.1f}% over
the same time.

![Default rates by grade, 2013 and 2015](../charts/same-grade-worse.svg)

Lending grew from {f['funded13']} to {f['funded15']} a year across those two years, and lenders' return on 3-year loans fell from {f['earn13']:.1f} to
{f['earn15']:.1f} cents per dollar. The data shows these happened together, not that one caused another.

## 5. Income still matters inside a grade

Overall, {f['inc_low']:.1%} of borrowers earning under $40k defaulted against {f['inc_high']:.1%} of those over $120k. The gap survives inside a grade: {f['inc_low_c']:.1%}
against {f['inc_high_c']:.1%} at grade C. Credit score, which the grade already leans on, is a stronger signal overall ({f['fico_low']:.1%} under 680 against {f['fico_high']:.1%} at
750 or more), but narrows to {f['fico_low_c']:.1%} against {f['fico_high_c']:.1%} inside grade C. Debt matters too: {f['dti_low']:.1%} with a debt-to-income ratio under 10, {f['dti_high']:.1%} over 30.

![Default rates by grade, lowest and highest incomes](../charts/income-within-grade.svg)

## 6. What borrowers say tells you something

Small business loans defaulted at {f['biz']:.1%}, about double the {f['car']:.1%} for car loans. Purposes with fewer than 7,000 mature loans are left out.

![Default rate by purpose](../charts/purposes.svg)

Time in a job barely matters, with every stated group between {f['job_low']:.1%} and {f['job_high']:.1%}. Leaving it blank does: {f['job_none']:.1%}.

![Default rate by time in job](../charts/employment.svg)

## 7. My models couldn't beat the lender's own grade

Each method trained on loans issued up to 2013 ({f['train']} loans from the sample) and was tested on 3-year loans from 2014 and 2015 ({f['test']} loans),
as a real lender would have to. The score, ROC AUC, measures how well a method ranks risky loans above safe ones.

![How well each method ranks risk](../charts/model-scores.svg)

The sub-grade alone scored {f['auc_grade']:.2f}. A logistic regression on applicant data scored {f['auc_app']:.2f}, and gradient boosting did no better at {f['auc_gb']:.2f}. The grade's lead
over the logistic regression is between {f['gap_low']:.2f} and {f['gap_high']:.2f} when the test loans are resampled, so it isn't luck. Adding the interest rate, which is largely
the grade in another form, lifts the model to {f['auc_rate']:.2f}.

That isn't surprising, as the grade drew on far more than the handful of columns used here. And the applicant-data model still sorts risk usefully:

![Default rate by predicted risk group](../charts/risk-deciles.svg)

The safest tenth of loans defaulted at {f['dec_low']:.1%} and the riskiest tenth at {f['dec_high']:.1%}.

## What this data can't tell you

- **It only covers approved loans.** Nobody knows what rejected applicants would have done, so these patterns may not hold for everyone.
- **It's one lender in one period.** These are US loans during a long recovery, and the mature loans end before the pandemic.
- **Repayments aren't profit.** The cents-per-dollar figures leave out fees and timing, so they aren't a rate of return.
- **It shows what, not why.** Comparisons between groups don't show that income or purpose causes default.

## How it was worked out

1. [`data/prepare.py`](../data/prepare.py) turns the full download into exact summaries and a {200_000:,}-loan sample.
2. [`analysis.py`](analysis.py) holds every calculation as a small, tested function.
3. [`charts.py`](charts.py) draws each chart with [bezel-charts](https://pypi.org/project/bezel-charts/).
4. [`notebooks/lending_club_analysis.ipynb`](../notebooks/lending_club_analysis.ipynb) walks through the same steps with the working shown.

Rates and totals come from every loan. Only the model in finding 7 uses the sample.

## A correction to the first version

The first version labelled {f['current']} loans still being repaid as "no default" and counted late loans as defaults, which produced the
{f['original']:.1%} figure. It also split loans at random, so its model could learn from loans issued after the ones it was tested on. Rebuilt on the
sample, that setup scores {f['old_auc']:.2f}, but on a label and test that aren't comparable with finding 7. Its claims about income and risk were
read from box plots. Everything here replaces that work.
"""


def replace_block(text: str, name: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- {name}:start -->\n).*?(\n<!-- {name}:end -->)", re.S)
    if not pattern.search(text):
        raise ValueError(f"Marker {name} not found")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


def main() -> None:
    # bezel-charts gives each gradient a random id so charts can share a page. A fixed seed keeps the
    # files identical between runs, so a rebuild only shows up in git when something really changed.
    random.seed(2026)
    CHARTS.mkdir(exist_ok=True)
    for name, draw in charts.ALL.items():
        draw().save(CHARTS / f"{name}.svg")
    f = facts()
    REPORT.write_text(report(f), encoding="utf-8")
    README.write_text(replace_block(README.read_text(encoding="utf-8"), "key-findings", key_findings(f)), encoding="utf-8")
    print(f"Wrote {len(charts.ALL)} charts, {REPORT.relative_to(ROOT)} and the README findings")


if __name__ == "__main__":
    main()
