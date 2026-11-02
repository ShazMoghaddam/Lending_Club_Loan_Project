# Changelog

All notable changes to this project are listed here. Versions are dated by month, like `v2026.11`.

## v2026.11 · November 2026

A full rebuild, from a single notebook into a tested, reproducible analysis.

### Fixed

- The first version counted loans still being repaid as "no default" and late loans as defaults. Default rates now use
  loans that had time to finish, and tests guard the labels
- The model used a random split, so it could learn from loans issued after the ones it was tested on. It now trains on
  earlier loans and is tested on later ones
- The data wasn't in the repo, so the notebook couldn't run. The repo now holds exact summaries and a fixed sample
- Insights read from box plots are replaced with figures calculated from every loan

### Added

- A findings report with seven findings, including what lenders actually got back by grade
- Nine charts and three headline tiles, all drawn with [bezel-charts](https://pypi.org/project/bezel-charts/)
- A fair comparison of four methods against the lender's own sub-grade
- `data/prepare.py` to rebuild the data from the full Kaggle download
- Tests, an automatic check on every pull request, Dependabot and a security policy
- Social preview image in `assets/social-preview.png`

### Changed

- New folder structure: `data/`, `findings/`, `notebooks/`, `charts/` and `tests/`
- README rewritten around the findings
- Notebook rewritten and moved to `notebooks/lending_club_analysis.ipynb`

## February 2026

- First version: one notebook and a README
