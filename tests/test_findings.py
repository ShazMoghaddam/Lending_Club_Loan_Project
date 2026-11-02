"""Checks that the data is sound and the findings hold up. Run from the repository root with `pytest`."""

import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "findings"), str(ROOT / "data")]

import analysis as an  # noqa: E402
import prepare  # noqa: E402


def test_summaries_agree_with_each_other():
    total = an.statuses().sum()
    assert total == 2_260_668
    assert an.vintages()["loans"].sum() == total
    table = pd.read_csv(an.DATA / "by_band.csv")
    assert table[table["dimension"] == "purpose"]["loans"].sum() == total


def test_sample_looks_like_the_full_data():
    loans = an.sample()
    assert len(loans) == 200_000
    finished = loans[loans["mature"] & (loans["outcome"] != "open")]
    assert (finished["outcome"] == "charged_off").mean() == pytest.approx(an.three_answers()["mature"], abs=0.005)


def test_loans_are_labelled_correctly():
    raw = pd.DataFrame(
        {
            "issue_d": ["Dec-2015", "Jan-2016", "Dec-2013", "Jan-2014", "Jun-2015"],
            "term": [" 36 months", " 36 months", " 60 months", " 60 months", " 36 months"],
            "loan_status": ["Current", "Fully Paid", "Charged Off", "Late (31-120 days)", "Does not meet the credit policy. Status:Charged Off"],
            "fico_range_low": [700] * 5, "fico_range_high": [704] * 5, "emp_length": [None] * 5,
        }
    )
    tidy = prepare.tidy(raw)
    assert tidy["mature"].tolist() == [True, False, True, False, True]
    assert tidy["outcome"].tolist() == ["open", "paid", "charged_off", "open", "charged_off"]
    assert tidy["fico"].iloc[0] == 702
    assert tidy["emp_length"].iloc[0] == "Not given"


def test_loans_still_running_never_count_as_defaults_or_repayments():
    rows = pd.DataFrame({"outcome": ["paid", "charged_off", "open"], "loans": [80, 20, 1000]})
    assert an.default_rate(rows) == 0.2


def test_the_fair_rate_sits_between_the_two_biased_ones():
    answers = an.three_answers()
    assert answers["original"] < answers["mature"] < answers["finished"]


def test_grades_rise_in_order():
    assert an.by_grade()["default_rate"].is_monotonic_increasing


def test_model_trains_only_on_the_past():
    train, test = an.split(an.sample())
    assert train["issue_year"].max() <= 2013 < test["issue_year"].min()
    assert (test["term"] == 36).all()
    assert (train["outcome"] != "open").all() and (test["outcome"] != "open").all()


def test_model_never_sees_the_outcome_or_repayments():
    for column in ("outcome", "loan_status", "total_pymnt", "int_rate", "grade", "sub_grade"):
        assert column not in an.NUMBERS + an.CATEGORIES


def test_writing_has_no_broken_values():
    for path in (ROOT / "README.md", ROOT / "findings" / "README.md"):
        text = path.read_text(encoding="utf-8")
        assert not re.findall(r"\bnan\b", text)
        assert "Filled in by" not in text


def test_every_chart_in_the_writing_exists():
    for path in (ROOT / "README.md", ROOT / "findings" / "README.md"):
        for link in re.findall(r"!\[[^\]]*\]\(([^)]+\.svg)\)", path.read_text(encoding="utf-8")):
            if not link.startswith("http"):
                assert (path.parent / link).resolve().exists(), link


def test_readme_text_written_by_hand_matches_the_data():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    table, grade = an.vintages(), an.by_grade()
    assert f"{table['loans'].sum():,} Lending Club loans worth ${table['funded'].sum() / 1e9:.1f}bn" in text
    assert f"{an.three_answers()['mature'] * 100:.1f} percent of loans defaulted" in text
    assert f"{grade.loc['A', 'default_rate'] * 100:.1f} percent for grade A" in text
    assert f"{grade.loc['G', 'default_rate'] * 100:.1f} percent for grade G" in text
    assert f"reaching {an.yearly_funded()[2018] / 1e9:.1f} billion dollars" in text
