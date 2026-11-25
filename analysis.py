import io
import os
import sqlite3
from contextlib import closing
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "churn_data.db")
REQUIRED_COLUMNS = [
    "customer_id",
    "tenure_months",
    "monthly_spend",
    "support_tickets",
    "contract_type",
    "days_since_last_activity",
    "churned",
]
CONTRACT_OPTIONS = ["Monthly", "Quarterly", "Annual"]
_CONTRACT_MAP = {c.lower(): c for c in CONTRACT_OPTIONS}


def init_db(db_file: str = DB_FILE):
    """Create the SQLite customers table if it does not already exist."""
    with closing(sqlite3.connect(db_file)) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                tenure_months INTEGER,
                monthly_spend REAL,
                support_tickets INTEGER,
                contract_type TEXT,
                days_since_last_activity INTEGER,
                churned INTEGER
            )
            """
        )


def load_data(db_file: str = DB_FILE) -> pd.DataFrame:
    """Load all customer records from SQLite."""
    with closing(sqlite3.connect(db_file)) as conn:
        return pd.read_sql_query("SELECT * FROM customers", conn)


def save_data(df: pd.DataFrame, mode: str = "append", db_file: str = DB_FILE):
    """Persist validated customer records to SQLite using INSERT OR REPLACE."""
    df_clean = df[REQUIRED_COLUMNS].copy()
    with closing(sqlite3.connect(db_file)) as conn, conn:
        if mode == "replace":
            conn.execute("DELETE FROM customers")
        conn.executemany(
            """
            INSERT OR REPLACE INTO customers (
                customer_id, tenure_months, monthly_spend,
                support_tickets, contract_type, days_since_last_activity, churned
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            df_clean.itertuples(index=False, name=None),
        )


def clear_db(db_file: str = DB_FILE):
    """Delete all rows from the customers table."""
    with closing(sqlite3.connect(db_file)) as conn, conn:
        conn.execute("DELETE FROM customers")


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to in-memory XLSX bytes."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="ChurnData")
    return output.getvalue()


def generate_sample_data(n: int = 120) -> pd.DataFrame:
    """Generate a synthetic customer churn dataset."""
    rng = np.random.default_rng(42)
    contracts = rng.choice(CONTRACT_OPTIONS, size=n, p=[0.5, 0.25, 0.25])
    tenure = rng.integers(1, 48, size=n)
    spend = rng.integers(500, 10000, size=n)
    tickets = rng.integers(0, 8, size=n)
    inactive_days = rng.integers(1, 120, size=n)

    risk_score = (
        (contracts == "Monthly").astype(int) * 0.30
        + (tickets >= 4).astype(int) * 0.30
        + (inactive_days > 45).astype(int) * 0.25
        + (tenure < 6).astype(int) * 0.15
    )
    churned = (rng.random(n) < risk_score).astype(int)

    return pd.DataFrame(
        {
            "customer_id": [f"CUST-{1001 + i}" for i in range(n)],
            "tenure_months": tenure,
            "monthly_spend": spend.astype(float),
            "support_tickets": tickets,
            "contract_type": contracts,
            "days_since_last_activity": inactive_days,
            "churned": churned,
        }
    )


def validate_dataframe(df: pd.DataFrame):
    """Validate and normalize an uploaded DataFrame against the required schema."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return None, f"Missing required columns: {', '.join(missing)}"

    df = df[REQUIRED_COLUMNS].copy()
    if df["customer_id"].isna().any():
        return None, "`customer_id` cannot contain empty cells."
    df["customer_id"] = df["customer_id"].astype(str).str.strip()
    if (df["customer_id"] == "").any():
        return None, "`customer_id` cannot be blank."

    numeric_cols = [
        "tenure_months",
        "monthly_spend",
        "support_tickets",
        "days_since_last_activity",
        "churned",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df.isnull().any().any():
        return None, "File contains empty cells or invalid numbers in numeric columns."

    if (
        (df["tenure_months"] < 0).any()
        or (df["monthly_spend"] < 0).any()
        or (df["support_tickets"] < 0).any()
        or (df["days_since_last_activity"] < 0).any()
    ):
        return None, "Numeric metrics (`tenure_months`, `monthly_spend`, `support_tickets`, `days_since_last_activity`) cannot be negative."

    if not set(df["churned"].unique()).issubset({0, 1}):
        return None, "`churned` column must only contain 0 (Active) or 1 (Churned)."

    df["contract_type"] = df["contract_type"].astype(str).str.strip().str.lower().map(_CONTRACT_MAP)
    if df["contract_type"].isna().any():
        return None, f"`contract_type` must be one of: {', '.join(CONTRACT_OPTIONS)}."

    int_cols = ["tenure_months", "support_tickets", "days_since_last_activity", "churned"]
    for col in int_cols:
        df[col] = df[col].astype(int)
    df["monthly_spend"] = df["monthly_spend"].astype(float)

    return df, None


def _prepare_features(df: pd.DataFrame, feature_cols=None) -> pd.DataFrame:
    X = df[
        [
            "tenure_months",
            "monthly_spend",
            "support_tickets",
            "days_since_last_activity",
            "contract_type",
        ]
    ].copy()
    X = pd.get_dummies(X, columns=["contract_type"], dtype=int)
    if feature_cols is not None:
        for col in feature_cols:
            if col not in X.columns:
                X[col] = 0
        X = X[feature_cols]
    return X


def train_model(df: pd.DataFrame):
    """Train a RandomForestClassifier on the dataset and compute optional 80/20 test accuracy."""
    if len(df) < 10 or df["churned"].nunique() < 2:
        return None, None, None, None

    X = _prepare_features(df)
    y = df["churned"]

    # 80/20 stratified split to evaluate accuracy when dataset has >= 20 rows and >= 2 per class
    accuracy = None
    if len(df) >= 20 and y.value_counts().min() >= 2:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        eval_model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
        eval_model.fit(X_train, y_train)
        accuracy = float(accuracy_score(y_test, eval_model.predict(X_test)) * 100)

    # Fit final model on full dataset for scoring active customers
    model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    model.fit(X, y)

    importances = pd.DataFrame(
        {"Feature": X.columns, "Importance": model.feature_importances_}
    ).sort_values("Importance", ascending=True)
    importances["Feature"] = importances["Feature"].str.replace("_", " ").str.title()

    return model, list(X.columns), importances, accuracy


def score_active_customers(df: pd.DataFrame, model, feature_cols) -> pd.DataFrame:
    """Predict churn probabilities and risk tiers for active (churned == 0) customers."""
    active_df = df[df["churned"] == 0].copy()
    if model is not None and not active_df.empty:
        X_active = _prepare_features(active_df, feature_cols)
        active_df["churn_probability"] = (model.predict_proba(X_active)[:, 1] * 100).round(1)
        active_df["risk_tier"] = pd.cut(
            active_df["churn_probability"],
            bins=[-1, 39.9, 69.9, 100],
            labels=["Low", "Medium", "High"],
        ).astype(str)
    else:
        active_df["churn_probability"] = np.nan
        active_df["risk_tier"] = "N/A"
    return active_df


def predict_single_customer(
    model, feature_cols, tenure: int, spend: float, tickets: int, inactive_days: int, contract: str
) -> float:
    """Predict churn probability (%) for a single hypothetical customer profile."""
    sim_input = pd.DataFrame(
        [[tenure, spend, tickets, inactive_days, contract]],
        columns=[
            "tenure_months",
            "monthly_spend",
            "support_tickets",
            "days_since_last_activity",
            "contract_type",
        ],
    )
    X_sim = _prepare_features(sim_input, feature_cols)
    return float(model.predict_proba(X_sim)[0][1] * 100)


def compute_kpis(df: pd.DataFrame, active_df: pd.DataFrame, model_ready: bool) -> dict:
    """Compute top-level KPI summary metrics."""
    if model_ready and not active_df.empty:
        revenue_at_risk = active_df.loc[
            active_df["churn_probability"] >= 50, "monthly_spend"
        ].sum()
    else:
        revenue_at_risk = df.loc[df["churned"] == 1, "monthly_spend"].sum()

    return {
        "total_customers": len(df),
        "churn_rate": float(df["churned"].mean() * 100),
        "revenue_at_risk": float(revenue_at_risk),
        "avg_tenure": float(df["tenure_months"].mean()),
    }


def get_contract_churn_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate churn percentage by contract type."""
    return (
        df.groupby("contract_type", as_index=False)["churned"]
        .mean()
        .assign(churn_pct=lambda x: (x["churned"] * 100).round(1))
    )
