# ChurnLens — Customer Churn Analysis Dashboard

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?logo=streamlit&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-Random%20Forest-F7931E?logo=scikit-learn&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)

**ChurnLens** is a lightweight, interactive Customer Churn Analysis web application built with Python and Streamlit. It enables businesses and analysts to upload customer datasets (CSV/Excel) or enter records manually, store them in a local SQLite database, and automatically train a machine learning model to uncover churn drivers, score active customers by risk, and run live "What-If" retention simulations.

---

## Key Features

* **3-Step Guided Workflow:** Clean progression from a **Welcome Screen** → **Data Input Page** (upload or manual entry) → **Analytics Dashboard**. Analytics remain gated until valid data is loaded.
* **Flexible Data Ingestion & Validation:**
  * Upload `.csv` or `.xlsx` files with automatic schema validation (checks for required columns, numeric integrity, and valid churn labels).
  * Choose between **Replace All Data** or **Append / Update** modes.
  * Download a pre-formatted 10-row Excel template or load a built-in **120-row Demo Dataset** for instant testing.
* **Live Record Management (`@st.dialog` Modal):** Add new customers or select an existing `customer_id` from the sidebar pop-up modal to auto-fill and update records in place—automatically refreshing all charts and predictions.
* **Interactive Analytics Dashboard:**
  * **KPI Cards:** Total Customers, Overall Churn Rate (%), Monthly Revenue at Risk (₹), and Average Tenure.
  * **Visualizations:** Churn Rate by Contract Type (bar chart), Top Churn Drivers (horizontal feature importance chart), and Tenure vs. Monthly Spend (interactive bubble scatter plot sized by support tickets).
* **Actionable High-Risk Customers Table:** Scores only **Active (`churned = 0`)** customers, assigns risk tiers (`Low`, `Medium`, `High`), displays visual churn probability progress bars, and supports filtering by minimum risk % and contract type with one-click **Excel/CSV export**.
* **What-If Churn Risk Simulator:** Adjust sliders for tenure, monthly spend, support tickets, inactivity, and contract type to see real-time churn probability predictions and retention recommendations.
* **Clean Architecture:** Strict separation between the pure-Python backend/ML engine (`analysis.py`) and the Streamlit UI (`app.py`).

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend & UI** | Streamlit, Custom CSS, `.streamlit/config.toml` (Light Theme) |
| **Visualizations** | Plotly Express |
| **Data Processing** | Pandas, NumPy, OpenPyXL |
| **Machine Learning** | Scikit-learn (`RandomForestClassifier`) |
| **Database** | SQLite (`churn_data.db`) |

---

## Project Structure

```text
churn-lens/
├── .devcontainer/          # Dev container configuration
├── .streamlit/
│   └── config.toml         # Global light-theme styling
├── analysis.py             # Pure Python backend: SQLite, validation, KPIs & ML model
├── app.py                  # Streamlit UI, @st.dialog modal & Plotly charts
├── requirements.txt        # Python dependencies
└── README.md
