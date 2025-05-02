import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Resource Monitoring & Insights", layout="wide")
st.title("📊 Resource Monitoring with Non-Availability and GPT Insights")

uploaded_file = st.sidebar.file_uploader("Upload JIRA Excel", type=["xlsx"])
resources = ["Alice", "Bob", "Charlie", "Diana"]
user = st.sidebar.selectbox("Select Resource", resources)

# Log non-availability
st.subheader("🛠️ Log Non-Availability")
start_date = st.date_input("Start Date", datetime.today())
start_time = st.time_input("Start Time", datetime.now().time())
end_date = st.date_input("End Date", datetime.today())
end_time = st.time_input("End Time", (datetime.now() + timedelta(hours=1)).time())
start_dt = datetime.combine(start_date, start_time)
end_dt = datetime.combine(end_date, end_time)

reason = st.selectbox("Reason", ["Meeting", "Leave", "Sick", "Unplanned Leave", "Out of Office"])
log_file = f"{user}_non_availability.csv"

try:
    log_df = pd.read_csv(log_file)
except FileNotFoundError:
    log_df = pd.DataFrame(columns=["Start", "End", "Reason"])

if st.button("💾 Save Non-Availability"):
    log_df = pd.concat([log_df, pd.DataFrame([{
        "Start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "End": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "Reason": reason
    }])], ignore_index=True)
    log_df.to_csv(log_file, index=False)
    st.success("Entry saved!")

st.dataframe(log_df, use_container_width=True)

# Weekly Non-Availability Summary
st.subheader("📅 Non-Availability Summary Across All Resources")
summary_data = []
for r in resources:
    path = f"{r}_non_availability.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        df["Start"] = pd.to_datetime(df["Start"])
        df["End"] = pd.to_datetime(df["End"])
        df["Hours"] = (df["End"] - df["Start"]).dt.total_seconds() / 3600
        df["Resource"] = r
        summary_data.append(df)

if summary_data:
    all_na = pd.concat(summary_data)
    na_summary = all_na.groupby(["Resource", "Reason"]).agg(Total_Hours=("Hours", "sum")).reset_index()
    st.dataframe(na_summary)
    st.bar_chart(na_summary.pivot(index="Resource", columns="Reason", values="Total_Hours").fillna(0))
else:
    st.info("No non-availability data found yet.")

# Main JIRA Data Analysis
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

        availability_map = {}
        for u in df["Assignee"].unique():
            fpath = f"{u}_non_availability.csv"
            if os.path.exists(fpath):
                temp_df = pd.read_csv(fpath)
                temp_df["Start"] = pd.to_datetime(temp_df["Start"])
                temp_df["End"] = pd.to_datetime(temp_df["End"])
                unavailable = (temp_df["End"] - temp_df["Start"]).dt.total_seconds().sum() / 3600
                availability_map[u] = round(80 - unavailable, 2)
            else:
                availability_map[u] = 80

        available_df = pd.DataFrame(list(availability_map.items()), columns=["Assignee", "Available Hours"])
        merged_df = pd.merge(agg_df, available_df, on="Assignee", how="left")
        merged_df["Overallocation Flag"] = merged_df["Original Estimate (hrs)"] > merged_df["Available Hours"]

        st.subheader("📊 Workload vs. Availability")
        st.dataframe(merged_df)

        fig = px.density_heatmap(
            merged_df,
            x="Assignee",
            y="Utilization (%)",
            z="Utilization (%)",
            color_continuous_scale="RdYlGn"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("🧠 GPT-Powered Recommendations (Placeholder)")
        st.markdown("""
        > Based on current utilization and non-availability:
        - Charlie and Alice are over-allocated.
        - Recommend reassigning low-priority tasks to Bob or Diana.
        - Consider pushing non-critical work to next sprint.
        """)

    except Exception as e:
        st.error(f"Processing error: {e}")
else:
    st.info("Upload a JIRA Excel file to proceed.")