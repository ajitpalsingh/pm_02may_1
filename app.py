import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Resource Monitor", layout="wide")
st.title("📊 Resource Monitoring and Control App")

st.sidebar.header("Upload JIRA Excel File")
uploaded_file = st.sidebar.file_uploader("Choose an Excel file", type=["xlsx"])
availability_dir = "."

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ Data loaded successfully!")

        df["Original Estimate (hrs)"] = df["Original Estimate (sec)"] / 3600
        df["Time Spent (hrs)"] = df["Time Spent (sec)"] / 3600

        agg_df = df.groupby("Assignee").agg({
            "Original Estimate (hrs)": "sum",
            "Time Spent (hrs)": "sum"
        }).reset_index()
        agg_df["Utilization (%)"] = (agg_df["Time Spent (hrs)"] / agg_df["Original Estimate (hrs)"]) * 100
        agg_df["Utilization (%)"] = agg_df["Utilization (%)"].round(1)

        # Load manual availability if available
        st.subheader("📅 Resource Availability (Imported)")
        availability_data = {}
        for user in df["Assignee"].unique():
            file_path = os.path.join(availability_dir, f"{user}_availability.csv")
            if os.path.exists(file_path):
                avail_df = pd.read_csv(file_path)
                daily_avail = avail_df.drop("Date", axis=1).sum(axis=1).sum() / 2  # Assume each check = 0.5h
                availability_data[user] = round(daily_avail, 2)

        if availability_data:
            avail_df = pd.DataFrame(list(availability_data.items()), columns=["Assignee", "Available Hours"])
            merged = pd.merge(agg_df, avail_df, on="Assignee", how="left")
            merged["Available Hours"].fillna(80, inplace=True)  # Default 2-week sprint
            merged["Overallocation Flag"] = merged["Original Estimate (hrs)"] > merged["Available Hours"]
            st.dataframe(merged)
        else:
            st.info("Manual availability files not found. Using default 80h per sprint.")

        # KPIs
        avg_util = agg_df["Utilization (%)"].mean().round(1)
        overload_count = (agg_df["Utilization (%)"] > 100).sum()
        underutilized_count = (agg_df["Utilization (%)"] < 60).sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("📈 Avg. Utilization", f"{avg_util}%")
        col2.metric("🔥 Over-allocated", overload_count)
        col3.metric("🧊 Under-utilized", underutilized_count)

        fig = px.density_heatmap(
            agg_df,
            x="Assignee",
            y="Utilization (%)",
            z="Utilization (%)",
            color_continuous_scale="RdYlGn",
            title="Resource Utilization Heatmap"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Raw Data Preview")
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
else:
    st.info("📥 Please upload a JIRA Excel file to begin.")