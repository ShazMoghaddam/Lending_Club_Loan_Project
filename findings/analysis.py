"""The analysis behind every finding. Plain functions, no charts and no files written.

The summaries in data/ are exact totals across every loan. A loan counts as "mature" when its full term fits before
the data ends in December 2018: 3-year loans issued up to 2015 and 5-year loans issued up to 2013. Default rates use
mature loans unless a function says otherwise, because recent loans haven't had time to go wrong.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA = Path(__file__).resolve().parent.parent / "data"
GRADES = list("ABCDEFG")
EMPLOYMENT = {
    "Under 1 year": ["< 1 year"],
    "1 to 4 years": ["1 year", "2 years", "3 years", "4 years"],
    "5 to 9 years": ["5 years", "6 years", "7 years", "8 years", "9 years"],
    "10 years or more": ["10+ years"],
    "Not given": ["Not given"],
}
ORIGINAL_DEFAULTS = ["Charged Off", "Default", "Late (31-120 days)"]
MIN_LOANS = 7_000  # Purposes with fewer mature loans than this are left off the chart

NUMBERS = ["loan_amnt", "term", "annual_inc", "dti", "fico", "open_acc", "revol_bal", "total_acc"]
CATEGORIES = ["emp_length", "home_ownership", "purpose"]


def statuses() -> pd.Series:
    return pd.read_csv(DATA / "status_counts.csv").set_index("loan_status")["loans"]


def vintages() -> pd.DataFrame:
    table = pd.read_csv(DATA / "by_vintage.csv")
    table["mature"] = table["issue_year"] + table["term"] // 12 <= 2018
    return table


def bands(dimension: str) -> pd.DataFrame:
    """Mature loans split by one characteristic, such as income or purpose."""
    table = pd.read_csv(DATA / "by_band.csv")
    return table[(table["dimension"] == dimension) & table["mature"]]


def sample() -> pd.DataFrame:
    return pd.read_csv(DATA / "loan_sample.csv.gz")


def default_rate(rows: pd.DataFrame) -> float:
    """Charged-off loans as a share of finished loans."""
    finished = rows.loc[rows["outcome"] != "open", "loans"].sum()
    return rows.loc[rows["outcome"] == "charged_off", "loans"].sum() / finished


def earned(rows: pd.DataFrame) -> float:
    """Cents paid back above each dollar lent, before fees and not adjusted for how long the money was tied up."""
    return (rows["repaid"].sum() / rows["funded"].sum() - 1) * 100


def mean_rate(rows: pd.DataFrame) -> float:
    return rows["rate_sum"].sum() / rows["loans"].sum()


def by_each(rows: pd.DataFrame, keys, measure) -> pd.Series:
    return pd.Series({key: measure(group) for key, group in rows.groupby(keys)})


# Finding 1: how often do loans default? -------------------------------------------------------------

def three_answers() -> dict[str, float]:
    """The same question answered three ways."""
    counts, table = statuses(), vintages()
    return {
        "original": counts[ORIGINAL_DEFAULTS].sum() / counts.sum(),
        "finished": default_rate(table),
        "mature": default_rate(table[table["mature"]]),
    }


# Finding 2 and 3: grades and what they earned ---------------------------------------------------------

def by_grade() -> pd.DataFrame:
    table = vintages()
    rows = table[table["mature"]]
    three, five = rows[rows["term"] == 36], rows[rows["term"] == 60]
    return pd.DataFrame(
        {
            "loans": rows.groupby("grade")["loans"].sum(),
            "default_rate": by_each(rows, "grade", default_rate),
            "interest": by_each(rows, "grade", mean_rate),
            "earned_3y": by_each(three, "grade", earned),
            "earned_5y": by_each(five, "grade", earned),
        }
    ).loc[GRADES]


# Finding 4: same grade, worse outcome ------------------------------------------------------------------

def three_year_by_grade(year: int) -> pd.DataFrame:
    table = vintages()
    rows = table[(table["term"] == 36) & (table["issue_year"] == year)]
    return pd.DataFrame(
        {
            "loans": rows.groupby("grade")["loans"].sum(),
            "default_rate": by_each(rows, "grade", default_rate),
            "interest": by_each(rows, "grade", mean_rate),
        }
    ).loc[GRADES]


def yearly_funded() -> pd.Series:
    return vintages().groupby("issue_year")["funded"].sum()


def three_year_earned(year: int) -> float:
    table = vintages()
    return earned(table[(table["term"] == 36) & (table["issue_year"] == year)])


# Finding 5 and 6: what else tells you something --------------------------------------------------------

def rate_by_band(dimension: str) -> pd.Series:
    return by_each(bands(dimension), "band", default_rate)


def rate_by_band_and_grade(dimension: str) -> pd.DataFrame:
    return by_each(bands(dimension), ["band", "grade"], default_rate).unstack()[GRADES]


def purposes() -> pd.Series:
    rows = bands("purpose")
    counts = rows.groupby("band")["loans"].sum()
    rates = rate_by_band("purpose")
    return rates[counts[counts >= MIN_LOANS].index].sort_values(ascending=False)


def employment() -> pd.Series:
    rows = bands("emp_length")
    return pd.Series({name: default_rate(rows[rows["band"].isin(group)]) for name, group in EMPLOYMENT.items()})


# Finding 7: can a model beat the grade? -----------------------------------------------------------------

def _pipeline(numbers: list[str], categories: list[str], model):
    parts = [(make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), numbers)]
    if categories:
        encoder = OneHotEncoder(handle_unknown="ignore", min_frequency=50, sparse_output=False)
        parts.append((encoder, categories))
    return make_pipeline(make_column_transformer(*parts), model)


def split(loans: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on loans issued up to 2013 and test on 3-year loans issued in 2014 and 2015, as a lender would have to."""
    rows = loans[loans["mature"] & (loans["outcome"] != "open")].copy()
    rows["defaulted"] = (rows["outcome"] == "charged_off").astype(int)
    rows["sub_grade_rank"] = rows["sub_grade"].map(lambda s: GRADES.index(s[0]) * 5 + int(s[1]))
    return rows[rows["issue_year"] <= 2013], rows[(rows["issue_year"] >= 2014) & (rows["term"] == 36)]


@lru_cache(maxsize=1)
def models() -> dict:
    train, test = split(sample())
    logistic = LogisticRegression(max_iter=2000)
    boosted = HistGradientBoostingClassifier(random_state=0, max_depth=4, learning_rate=0.05, max_iter=200)
    candidates = {
        "Lender's sub-grade alone": _pipeline(["sub_grade_rank"], [], logistic),
        "Applicant data, logistic regression": _pipeline(NUMBERS, CATEGORIES, logistic),
        "Applicant data, gradient boosting": _pipeline(NUMBERS, CATEGORIES, boosted),
        "Applicant data plus interest rate": _pipeline(NUMBERS + ["int_rate"], CATEGORIES, logistic),
    }
    scores = {name: model.fit(train, train["defaulted"]).predict_proba(test)[:, 1] for name, model in candidates.items()}
    auc = pd.Series({name: roc_auc_score(test["defaulted"], score) for name, score in scores.items()})

    applicant = scores["Applicant data, logistic regression"]
    deciles = test["defaulted"].groupby(pd.qcut(applicant, 10, labels=range(1, 11)), observed=True).mean()

    # How sure is the gap between the grade and the model? Resample the test loans and measure it each time.
    random = np.random.default_rng(0)
    outcome, grade = test["defaulted"].to_numpy(), scores["Lender's sub-grade alone"]
    gaps = []
    for _ in range(300):
        pick = random.integers(0, len(outcome), len(outcome))
        gaps.append(roc_auc_score(outcome[pick], grade[pick]) - roc_auc_score(outcome[pick], applicant[pick]))
    return {
        "auc": auc.sort_values(ascending=False),
        "deciles": deciles,
        "gap_low": float(np.percentile(gaps, 2.5)),
        "gap_high": float(np.percentile(gaps, 97.5)),
        "train_size": len(train),
        "test_size": len(test),
    }


# The correction to the first version of this project ---------------------------------------------------

def first_version() -> dict:
    """The original notebook's label, split and model, run on the sample.

    It treated loans still being repaid as "no default", counted late loans as defaults, and split at random.
    """
    features = ["loan_amnt", "int_rate", "installment", "annual_inc", "dti", "open_acc", "revol_bal", "total_acc"]
    rows = sample().dropna(subset=features)
    label = rows["loan_status"].isin(ORIGINAL_DEFAULTS).astype(int)
    x_train, x_test, y_train, y_test = train_test_split(rows[features], label, test_size=0.2, random_state=42, stratify=label)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced"))
    model.fit(x_train, y_train)
    return {"auc": roc_auc_score(y_test, model.predict_proba(x_test)[:, 1]), "current": int(statuses()["Current"])}
