import pandas as pd
import plotly.express as px
import streamlit as st

import analysis as an

# --- Page Config ---
st.set_page_config(page_title="ChurnLens — Customer Churn Analyzer", layout="wide")

# --- Light Minimal CSS ---
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2563EB;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0F172A;
    }
    .welcome-box {
        text-align: center;
        padding: 5rem 2rem 3rem 2rem;
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
        margin-top: 3rem;
    }
    .welcome-title {
        font-size: 3rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.5rem;
    }
    .welcome-sub {
        font-size: 1.15rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Init DB & Session State ---
an.init_db()
if "page" not in st.session_state:
    st.session_state.page = "welcome"

df = an.load_data()


# --- Pop-up Modal for Editing from Analysis Page ---
@st.dialog("Add / Edit Customer Record")
def manual_entry_modal(current_df: pd.DataFrame):
    existing_ids = sorted(current_df["customer_id"].tolist()) if not current_df.empty else []
    selection = st.selectbox("Choose an action", options=["+ Add New Customer"] + existing_ids)

    if selection != "+ Add New Customer":
        row = current_df[current_df["customer_id"] == selection].iloc[0]
        d_id, d_tenure, d_spend = str(row["customer_id"]), int(row["tenure_months"]), float(row["monthly_spend"])
        d_tickets, d_inactive = int(row["support_tickets"]), int(row["days_since_last_activity"])
        contract_val = str(row["contract_type"])
        d_contract_idx = an.CONTRACT_OPTIONS.index(contract_val) if contract_val in an.CONTRACT_OPTIONS else 0
        d_churned_idx = 1 if int(row["churned"]) == 1 else 0
        id_disabled = True
    else:
        d_id, d_tenure, d_spend, d_tickets, d_inactive = "", 12, 2000.0, 1, 15
        d_contract_idx, d_churned_idx, id_disabled = 0, 0, False

    with st.form("modal_form"):
        c1, c2 = st.columns(2)
        m_id = c1.text_input("Customer ID", value=d_id, placeholder="e.g., CUST-2050", disabled=id_disabled)
        m_contract = c2.selectbox("Contract Type", an.CONTRACT_OPTIONS, index=d_contract_idx)
        m_tenure = c1.number_input("Tenure (Months)", min_value=0, value=d_tenure)
        m_spend = c2.number_input("Monthly Spend (₹)", min_value=0.0, value=d_spend)
        m_tickets = c1.number_input("Support Tickets", min_value=0, value=d_tickets)
        m_inactive = c2.number_input("Days Since Last Activity", min_value=0, value=d_inactive)
        m_churned = st.selectbox(
            "Status",
            [0, 1],
            index=d_churned_idx,
            format_func=lambda x: "Active (0)" if x == 0 else "Churned (1)",
        )
        if st.form_submit_button("Save Record", type="primary", width="stretch"):
            final_id = d_id if id_disabled else m_id.strip()
            if not final_id:
                st.error("Customer ID is required.")
            else:
                new_df = pd.DataFrame(
                    [[final_id, m_tenure, m_spend, m_tickets, m_contract, m_inactive, m_churned]],
                    columns=an.REQUIRED_COLUMNS,
                )
                an.save_data(new_df, mode="append")
                st.rerun()


# =========================================================
# STEP 1: WELCOME / NAME PAGE
# =========================================================
if st.session_state.page == "welcome":
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown(
            """
            <div class="welcome-box">
                <div class="welcome-title">ChurnLens</div>
                <div class="welcome-sub">Simple, light, and actionable customer churn analysis.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("Get Started →", type="primary", width="stretch"):
            st.session_state.page = "input"
            st.rerun()


# =========================================================
# STEP 2: DATA INPUT PAGE (UPLOAD OR MANUAL)
# =========================================================
elif st.session_state.page == "input":
    top_l, top_r = st.columns([4, 1])
    top_l.title("Provide Customer Data")
    if top_r.button("← Home", width="stretch"):
        st.session_state.page = "welcome"
        st.rerun()

    st.write("Choose how you would like to add your data before viewing the analysis.")
    method = st.radio(
        "Input Method",
        ["Upload Dataset (CSV / Excel)", "Enter Data Manually"],
        horizontal=True,
    )
    st.divider()

    if method == "Upload Dataset (CSV / Excel)":
        col_up, col_help = st.columns([2, 1])

        with col_up:
            upload_mode = st.radio(
                "Upload behavior", ["Replace All Data", "Append / Update"], horizontal=True
            )
            uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

            if uploaded_file is not None:
                try:
                    raw_df = (
                        pd.read_csv(uploaded_file)
                        if uploaded_file.name.lower().endswith(".csv")
                        else pd.read_excel(uploaded_file, engine="openpyxl")
                    )
                    valid_df, error = an.validate_dataframe(raw_df)
                    if error:
                        st.error(error)
                    else:
                        st.success(f"Validated {len(valid_df)} records successfully.")
                        if st.button("Save & View Analysis →", type="primary", width="stretch"):
                            mode = "replace" if upload_mode == "Replace All Data" else "append"
                            an.save_data(valid_df, mode=mode)
                            st.session_state.page = "analysis"
                            st.rerun()
                except Exception as e:
                    st.error(f"Could not read file: {e}")

        with col_help:
            st.subheader("Quick Start")
            sample_df = an.generate_sample_data()
            st.download_button(
                label="Download Sample Excel Template",
                data=an.to_excel_bytes(sample_df.head(10)),
                file_name="churn_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
            if st.button("Load Demo Dataset (120 rows)", width="stretch"):
                an.save_data(sample_df, mode="replace")
                st.session_state.page = "analysis"
                st.rerun()

    else:
        with st.form("manual_input_page_form"):
            st.subheader("Add Customer Record")
            c1, c2, c3 = st.columns(3)
            m_id = c1.text_input("Customer ID", placeholder="e.g., CUST-1001")
            m_tenure = c2.number_input("Tenure (Months)", min_value=0, value=12)
            m_spend = c3.number_input("Monthly Spend (₹)", min_value=0.0, value=2500.0)
            m_tickets = c1.number_input("Support Tickets", min_value=0, value=1)
            m_contract = c2.selectbox("Contract Type", an.CONTRACT_OPTIONS)
            m_inactive = c3.number_input("Days Since Last Activity", min_value=0, value=10)
            m_churned = st.selectbox(
                "Status", [0, 1], format_func=lambda x: "Active (0)" if x == 0 else "Churned (1)"
            )

            if st.form_submit_button("Add Record to Database", type="primary"):
                if not m_id.strip():
                    st.error("Customer ID is required.")
                else:
                    new_row = pd.DataFrame(
                        [[m_id.strip(), m_tenure, m_spend, m_tickets, m_contract, m_inactive, m_churned]],
                        columns=an.REQUIRED_COLUMNS,
                    )
                    an.save_data(new_row, mode="append")
                    st.success(f"Added {m_id.strip()}.")
                    st.rerun()

        if not df.empty:
            st.write(f"**{len(df)}** record(s) currently saved.")
            st.dataframe(df.tail(5), width="stretch", hide_index=True)

    # Only allow moving to Analysis once data is saved in SQLite
    if not df.empty:
        st.divider()
        if st.button(f"Proceed to Analysis ({len(df)} records) →", type="primary"):
            st.session_state.page = "analysis"
            st.rerun()


# =========================================================
# STEP 3: ANALYSIS PAGE
# =========================================================
elif st.session_state.page == "analysis":
    if df.empty:
        st.session_state.page = "input"
        st.rerun()

    # Sidebar controls
    st.sidebar.title("ChurnLens")
    if st.sidebar.button("Add / Edit Customer", type="primary", width="stretch"):
        manual_entry_modal(df)
    if st.sidebar.button("← Change / Upload Data", width="stretch"):
        st.session_state.page = "input"
        st.rerun()

    st.sidebar.divider()
    st.sidebar.download_button(
        label="Export Database to Excel",
        data=an.to_excel_bytes(df),
        file_name="customer_churn_database.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    if st.sidebar.button("Clear All Data", width="stretch"):
        an.clear_db()
        st.session_state.page = "input"
        st.rerun()

    # Run analytics
    model, feature_cols, importances, accuracy = an.train_model(df)
    active_df = an.score_active_customers(df, model, feature_cols)
    kpis = an.compute_kpis(df, active_df, model_ready=(model is not None))

    st.title("Customer Churn Analysis")
    if accuracy is not None:
        st.caption(f"Model trained & tested on your dataset (80/20 split accuracy: **{accuracy:.1f}%**)")

    tab_dash, tab_risk, tab_sim = st.tabs(
        ["Analytics Dashboard", "High-Risk Customers", "What-If Simulator"]
    )

    with tab_dash:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Customers", f"{kpis['total_customers']:,}")
        k2.metric("Overall Churn Rate", f"{kpis['churn_rate']:.1f}%")
        k3.metric("Monthly Revenue at Risk", f"₹{kpis['revenue_at_risk']:,.0f}")
        k4.metric("Avg. Tenure", f"{kpis['avg_tenure']:.1f} mos")

        st.divider()
        col_l, col_r = st.columns(2)

        contract_churn = an.get_contract_churn_summary(df)
        fig_contract = px.bar(
            contract_churn,
            x="contract_type",
            y="churn_pct",
            text="churn_pct",
            title="Churn Rate (%) by Contract Type",
            labels={"contract_type": "Contract Type", "churn_pct": "Churn Rate (%)"},
            color="churn_pct",
            color_continuous_scale="Reds",
        )
        fig_contract.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_contract.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        col_l.plotly_chart(fig_contract, width="stretch")

        if importances is not None:
            fig_imp = px.bar(
                importances,
                x="Importance",
                y="Feature",
                orientation="h",
                title="Top Churn Drivers",
                color="Importance",
                color_continuous_scale="Blues",
            )
            fig_imp.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            col_r.plotly_chart(fig_imp, width="stretch")
        else:
            col_r.info("Add at least 10 records with both Active and Churned customers to see churn drivers.")

        df_plot = df.copy()
        df_plot["Status"] = df_plot["churned"].map({0: "Active", 1: "Churned"})
        fig_scatter = px.scatter(
            df_plot,
            x="tenure_months",
            y="monthly_spend",
            color="Status",
            size="support_tickets",
            hover_data=["customer_id", "contract_type", "days_since_last_activity"],
            title="Tenure vs. Monthly Spend (Bubble Size = Support Tickets)",
            labels={"tenure_months": "Tenure (Months)", "monthly_spend": "Monthly Spend (₹)"},
            color_discrete_map={"Active": "#2ecc71", "Churned": "#e74c3c"},
        )
        fig_scatter.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_scatter, width="stretch")

    with tab_risk:
        st.subheader("High-Risk Active Customers")
        if model is None:
            st.info("Need at least 10 records with both Active and Churned customers to score risk.")
        elif active_df.empty:
            st.info("No active customers available to score.")
        else:
            f1, f2 = st.columns([1, 2])
            min_prob = f1.slider("Minimum Churn Risk (%)", 0, 95, 50, step=5)
            selected_contracts = f2.multiselect(
                "Filter by Contract Type",
                options=active_df["contract_type"].unique().tolist(),
                default=active_df["contract_type"].unique().tolist(),
            )
            filtered = active_df[
                (active_df["churn_probability"] >= min_prob)
                & (active_df["contract_type"].isin(selected_contracts))
            ].sort_values("churn_probability", ascending=False)

            cols = [
                "customer_id",
                "churn_probability",
                "risk_tier",
                "monthly_spend",
                "contract_type",
                "tenure_months",
                "support_tickets",
                "days_since_last_activity",
            ]
            st.dataframe(
                filtered[cols],
                width="stretch",
                hide_index=True,
                column_config={
                    "customer_id": "Customer ID",
                    "churn_probability": st.column_config.ProgressColumn(
                        "Churn Risk (%)", min_value=0, max_value=100, format="%.1f%%"
                    ),
                    "risk_tier": "Risk Tier",
                    "monthly_spend": st.column_config.NumberColumn("Monthly Spend", format="₹%.0f"),
                    "contract_type": "Contract",
                    "tenure_months": "Tenure (Mos)",
                    "support_tickets": "Tickets",
                    "days_since_last_activity": "Inactive Days",
                },
            )
            e1, e2 = st.columns(2)
            e1.download_button(
                "Export High-Risk (Excel)",
                data=an.to_excel_bytes(filtered[cols]),
                file_name="high_risk_customers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
            e2.download_button(
                "Export High-Risk (CSV)",
                data=filtered[cols].to_csv(index=False).encode("utf-8"),
                file_name="high_risk_customers.csv",
                mime="text/csv",
                width="stretch",
            )

    with tab_sim:
        st.subheader("What-If Churn Risk Simulator")
        if model is None:
            st.info("Need at least 10 records with both Active and Churned customers to simulate.")
        else:
            c1, c2, c3 = st.columns(3)
            s_tenure = c1.slider("Tenure (Months)", 0, 60, 6)
            s_spend = c2.slider("Monthly Spend (₹)", 500, 15000, 3000, step=250)
            s_tickets = c3.slider("Support Tickets", 0, 10, 3)
            s_inactive = c1.slider("Days Since Last Activity", 0, 120, 45)
            s_contract = c2.selectbox("Contract Type", an.CONTRACT_OPTIONS)

            prob = an.predict_single_customer(
                model, feature_cols, s_tenure, s_spend, s_tickets, s_inactive, s_contract
            )
            st.divider()
            m_col, a_col = st.columns([1, 2])
            m_col.metric("Predicted Churn Probability", f"{prob:.1f}%")
            if prob >= 70:
                a_col.error("High Risk: Immediate retention outreach recommended.")
            elif prob >= 40:
                a_col.warning("Medium Risk: Monitor engagement or offer a plan upgrade.")
            else:
                a_col.success("Low Risk: Customer looks healthy.")
