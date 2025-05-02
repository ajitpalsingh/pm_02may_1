import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Resource Monitor with Availability", layout="wide")
st.title("📊 Resource Monitoring and Control App with Integrated Availability")

# Sidebar: Upload JIRA Excel
uploaded_file = st.sidebar.file_uploader("Upload JIRA Excel", type=["xlsx"])
resources = ["Alice", "Bob", "Charlie", "Diana"]
user = st.sidebar.selectbox("Select Resource", resources)

# === Manual Non-Availability Logging ===
st.subheader("🛠️ Log Non-Availability for Selected Resource")
start_dt = st.datetime_input("Start Date and Time", datetime.now())
end_dt = st.datetime_input("End Date and Time", datetime.now() + timedelta(hours=1))
reason = st.selectbox("Reason for Non-Availability", [
    "Meeting", "Leave", "Sick", "Unplanned Leave", "Out of Office"
])

log_file = f"{user}_non_availability.csv"
try:
    log_df = pd.read_csv(log_file)
except FileNotFoundError:
    log_df = pd.DataFrame(columns=["Start", "End", "Reason"])

if st.button("💾 Log Non-Availability"):
    new_row = {"Start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
               "End": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
               "Reason": reason}
    log_df = pd.concat([log_df, pd.DataFrame([new_row])], ignore_index=True)
    log_df.to_csv(log_file, index=False)
    st.success(f"{user} non-availability logged.")

st.dataframe(log_df, use_container_width=True)

# === JIRA Workload Analysis ===
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df["Original Estimate (hrs)"] = df["Original Estimate (sec)"] / 3600
        df["Time Spent (hrs)"] = df["Time Spent (sec)"] / 3600

        agg_df = df.groupby("Assignee").agg({
            "Original Estimate (hrs)": "sum",
            "Time Spent (hrs)": "sum"
        }).reset_index()
        agg_df["Utilization (%)"] = (agg_df["Time Spent (hrs)"] / agg_df["Original Estimate (hrs)"]) * 100
        agg_df["Utilization (%)"] = agg_df["Utilization (%)"].round(1)

        # Incorporate non-availability into availability analysis
        availability_map = {}
        for u in df["Assignee"].unique():
            fpath = f"{u}_non_availability.csv"
            if os.path.exists(fpath):
                temp_df = pd.read_csv(fpath)
                temp_df["Start"] = pd.to_datetime(temp_df["Start"])
                temp_df["End"] = pd.to_datetime(temp_df["End"])
                total_unavailable = (temp_df["End"] - temp_df["Start"]).dt.total_seconds().sum() / 3600
                availability_map[u] = round(80 - total_unavailable, 2)
            else:
                availability_map[u] = 80  # default for 2-week sprint

        available_df = pd.DataFrame(list(availability_map.items()), columns=["Assignee", "Available Hours"])
        merged_df = pd.merge(agg_df, available_df, on="Assignee", how="left")
        merged_df["Overallocation Flag"] = merged_df["Original Estimate (hrs)"] > merged_df["Available Hours"]

        st.subheader("📊 Utilization vs. Adjusted Availability")
        st.dataframe(merged_df)

        col1, col2, col3 = st.columns(3)
        col1.metric("Avg. Utilization", f"{agg_df['Utilization (%)'].mean().round(1)}%")
        col2.metric("Over-allocated", (agg_df["Utilization (%)"] > 100).sum())
        col3.metric("Under-utilized", (agg_df["Utilization (%)"] < 60).sum())

        fig = px.density_heatmap(
            agg_df,
            x="Assignee",
            y="Utilization (%)",
            z="Utilization (%)",
            color_continuous_scale="RdYlGn"
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Upload a JIRA Excel file to begin.")