# Lending Club Loan Analysis & Default Prediction

## 📌 Project Overview
This project analyses historical Lending Club loan data to explore borrower characteristics, loan performance, and factors associated with loan default. The goal is to demonstrate an end-to-end data science workflow, from data cleaning and exploratory analysis to machine learning modelling and evaluation.

The dataset used is a cleaned and reduced version of the original Lending Club dataset (2007–2018), prepared to enable efficient analysis on a local machine.

---

## 🎯 Objectives
- Load and explore Lending Club loan data
- Clean and preprocess the dataset
- Perform exploratory data analysis (EDA)
- Visualise key trends and relationships
- Build a machine learning model to predict loan default
- Summarise findings, insights, and limitations

---

## 📂 Dataset
- **Source:** Lending Club Loan Data (via Kaggle)
- **Original file:** `accepted_2007_to_2018q4.csv` (~1.6 GB)
- **Used file:** `lending_club_cleaned.csv` (reduced and cleaned for analysis)

> Due to the size of the original dataset, only relevant columns were retained to improve performance and usability.

---

## 🛠 Tools & Technologies
- Python
- Jupyter Notebook
- pandas, NumPy
- matplotlib, seaborn
- scikit-learn

---

## 🔍 Exploratory Data Analysis
Key analyses and visualisations include:
- Loan status distribution
- Interest rate comparison between defaulted and non-defaulted loans
- Annual income distribution by default status
- Debt-to-income (DTI) patterns

These visualisations help highlight financial characteristics associated with higher default risk.

---

## 🤖 Machine Learning
- **Model used:** Logistic Regression  
- **Problem type:** Binary classification (Default vs No Default)
- **Target variable:** Loan default status
- **Key features:** Loan amount, interest rate, installment, annual income, DTI, and account metrics
- **Class imbalance handling:** Stratified train-test split and balanced class weights

Model performance is evaluated using classification metrics and a confusion matrix.

---

## 📈 Key Findings
- Higher interest rates are strongly associated with loan default
- Borrowers with lower annual income show a higher likelihood of default
- Debt-to-income ratio is a meaningful predictor of loan performance
- A simple, interpretable model can capture important default risk patterns

---

## ⚠️ Limitations & Future Improvements
- The dataset is imbalanced, which limits recall for defaulted loans
- Only a subset of available Lending Club features was used
- More advanced models (e.g. Random Forest, Gradient Boosting) could improve performance
- Feature engineering and additional credit history variables may enhance predictions

---

## ▶️ How to Run
1. Clone this repository
2. Open `Lending_Club_Loan_Project.ipynb` in Jupyter Notebook
3. Ensure required libraries are installed
4. Run all cells from top to bottom

---

## 📬 Author
This project was created to showcase skills in data analysis, visualisation, and machine learning for entry-level data science and Python-focused roles.
