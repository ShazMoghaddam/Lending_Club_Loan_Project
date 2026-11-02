"""Turn the full Lending Club download into small files that can live in this repo.

The original file is far too big for GitHub, so it isn't committed. Download it from Kaggle, then run:

    python data/prepare.py path/to/accepted_2007_to_2018Q4.csv.gz

This writes, into data/:

    status_counts.csv     Every loan status, exact counts across all loans
    by_vintage.csv        Exact totals by year issued, term, grade and outcome
    by_band.csv           Exact totals by income, debt, credit score, purpose and more
    loan_sample.csv.gz    A fixed random sample of loans, used to train and test the model
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent
SAMPLE_SIZE = 200_000
SEED = 42

COLUMNS = [
    "issue_d", "term", "grade", "sub_grade", "int_rate", "loan_amnt", "funded_amnt", "installment", "annual_inc",
    "dti", "fico_range_low", "fico_range_high", "emp_length", "home_ownership", "purpose", "addr_state", "open_acc",
    "revol_bal", "total_acc", "loan_status", "total_pymnt",
]

PAID = {"Fully Paid", "Does not meet the credit policy. Status:Fully Paid"}
CHARGED_OFF = {"Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off"}

INCOME_BINS = [-1, 40_000, 60_000, 80_000, 120_000, float("inf")]
INCOME_LABELS = ["Under $40k", "$40k to $60k", "$60k to $80k", "$80k to $120k", "Over $120k"]
DTI_BINS = [-2, 10, 20, 30, float("inf")]
DTI_LABELS = ["Under 10", "10 to 20", "20 to 30", "Over 30"]
FICO_BINS = [0, 679, 699, 719, 749, float("inf")]
FICO_LABELS = ["Under 680", "680 to 699", "700 to 719", "720 to 749", "750 or more"]


def load(path: Path) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns
    missing = [column for column in COLUMNS if column not in header]
    if missing:
        raise SystemExit(
            f"This file is missing {missing}.\n"
            "Please use the original Kaggle download (accepted_2007_to_2018Q4.csv.gz), not a cleaned copy."
        )
    print(f"Reading {path.name}. This takes a few minutes...")
    df = pd.read_csv(path, usecols=COLUMNS, low_memory=False)
    # The file ends with summary lines that aren't loans, so they have no status.
    return df.dropna(subset=["loan_status", "issue_d", "funded_amnt"]).reset_index(drop=True)


def tidy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["issue_year"] = pd.to_datetime(df["issue_d"], format="%b-%Y").dt.year
    df["term"] = df["term"].str.strip().str.extract(r"(\d+)", expand=False).astype(int)
    df["fico"] = (df["fico_range_low"] + df["fico_range_high"]) / 2
    df["outcome"] = "open"
    df.loc[df["loan_status"].isin(PAID), "outcome"] = "paid"
    df.loc[df["loan_status"].isin(CHARGED_OFF), "outcome"] = "charged_off"
    # The data ends in December 2018, so a loan has had time to finish only if its full term fits before then.
    df["mature"] = df["issue_year"] + df["term"] // 12 <= 2018
    df["emp_length"] = df["emp_length"].fillna("Not given")
    return df


def bands(df: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "income": pd.cut(df["annual_inc"], INCOME_BINS, labels=INCOME_LABELS),
        "dti": pd.cut(df["dti"], DTI_BINS, labels=DTI_LABELS),
        "fico": pd.cut(df["fico"], FICO_BINS, labels=FICO_LABELS),
        "purpose": df["purpose"],
        "home_ownership": df["home_ownership"],
        "emp_length": df["emp_length"],
        "state": df["addr_state"],
    }


def totals(group) -> pd.DataFrame:
    return group.agg(
        loans=("funded_amnt", "size"),
        funded=("funded_amnt", "sum"),
        repaid=("total_pymnt", "sum"),
        rate_sum=("int_rate", "sum"),
    ).reset_index()


def write_summaries(df: pd.DataFrame) -> None:
    df["loan_status"].value_counts().rename_axis("loan_status").reset_index(name="loans").to_csv(
        DATA / "status_counts.csv", index=False
    )
    keys = ["issue_year", "term", "grade", "outcome"]
    totals(df.groupby(keys, observed=True)).round(2).to_csv(DATA / "by_vintage.csv", index=False)

    tables = []
    for name, band in bands(df).items():
        rows = df.assign(band=band).dropna(subset=["band"])
        table = totals(rows.groupby(["band", "grade", "term", "mature", "outcome"], observed=True))
        table.insert(0, "dimension", name)
        tables.append(table)
    pd.concat(tables).round(2).to_csv(DATA / "by_band.csv", index=False)


def write_sample(df: pd.DataFrame) -> None:
    columns = [
        "issue_d", "issue_year", "term", "grade", "sub_grade", "int_rate", "loan_amnt", "funded_amnt", "installment",
        "annual_inc", "dti", "fico", "emp_length", "home_ownership", "purpose", "addr_state", "open_acc", "revol_bal",
        "total_acc", "loan_status", "outcome", "mature", "total_pymnt",
    ]
    sample = df.sample(n=min(SAMPLE_SIZE, len(df)), random_state=SEED).sort_values(["issue_year", "issue_d"])
    sample[columns].round(2).to_csv(DATA / "loan_sample.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="the Kaggle file, accepted_2007_to_2018Q4.csv.gz")
    parser.add_argument("--zip", type=Path, help="also bundle the outputs into this zip file")
    args = parser.parse_args()

    df = tidy(load(args.source))
    write_summaries(df)
    write_sample(df)
    print(f"{len(df):,} loans, issued {df['issue_year'].min()} to {df['issue_year'].max()}")
    print(df["outcome"].value_counts().to_string())

    names = ["status_counts.csv", "by_vintage.csv", "by_band.csv", "loan_sample.csv.gz"]
    for name in names:
        print(f"{name}: {(DATA / name).stat().st_size / 1e6:.1f} MB")
    if args.zip:
        with zipfile.ZipFile(args.zip, "w") as bundle:
            for name in names:
                bundle.write(DATA / name, name)
        print(f"Bundled into {args.zip} ({args.zip.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
