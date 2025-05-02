import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
from streamlit_calendar import calendar

st.set_page_config(page_title="Resource Monitor with Calendar", layout="wide")
st.title("📊 Resource Monitoring and Control App")

# Sidebar: Upload JIRA Excel
st.sidebar.header("Upload JIRA Excel File")
uploaded_file = st.sidebar.file_uploader("Choose an Excel file", type=["xlsx"])

# Sidebar: Select user for calendar availability
resources = ["Alice", "Bob", "Charlie", "Diana"]
user = st.sidebar.selectbox("Select Resource for Availability", resources)

# === Embedded Calendar UI ===
st.subheader("📅 Calendar-Based Manual Availability")
start_date = datetime.today()
dates = [start_date + timedelta(days=i) for i in range(14)]
working_days = [d for d in dates if d.weekday() < 5]  # Weekdays only

calendar_events = [{
    "title": f"{user} Available",
    "start": d.strftime("%Y-%m-%dT09:00:00"),
    "end": d.strftime("%Y-%m-%dT17:30:00")
} for d in working_days]

calendar(events=calendar_events, options={"editable": False})
availability_df = pd.DataFrame({
    "Date": [d.strftime("%Y-%m-%d") for d in working_days],
    "Available Hours": [8.5] * len(working_days)
})

if st.button("💾 Save Calendar Availability"):
    availability_df.to_csv(f"{user}_availability.csv", index=False)
    st.success(f"{user}_availability.csv saved successfully.")

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

        # Load availability if present
        availability_data = {}
        for u in df["Assignee"].unique():
            file_path = f"{u}_availability.csv"
            if os.path.exists(file_path):
                a_df = pd.read_csv(file_path)
                total_available = a_df["Available Hours"].sum()
                availability_data[u] = total_available

        if availability_data:
            st.subheader("📊 Utilization vs. Availability")
            a_df = pd.DataFrame(list(availability_data.items()), columns=["Assignee", "Available Hours"])
            merged_df = pd.merge(agg_df, a_df, on="Assignee", how="left")
            merged_df["Available Hours"].fillna(80, inplace=True)
            merged_df["Overallocation Flag"] = merged_df["Original Estimate (hrs)"] > merged_df["Available Hours"]
            st.dataframe(merged_df)
        else:
            st.warning("No availability data found. Using default 80 hours.")

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
        st.error(f"Error reading data: {e}")
else:
    st.info("Please upload a JIRA Excel file to begin.")