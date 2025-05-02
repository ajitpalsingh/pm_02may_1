import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Resource Monitor", layout="wide")
st.title("📊 Resource Monitoring and Control App")

st.sidebar.header("Upload JIRA Excel File")
uploaded_file = st.sidebar.file_uploader("Choose an Excel file", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ Data loaded successfully!")

        # Convert seconds to hours
        df["Original Estimate (hrs)"] = df["Original Estimate (sec)"] / 3600
        df["Time Spent (hrs)"] = df["Time Spent (sec)"] / 3600

        # Group by Assignee to calculate utilization
        agg_df = df.groupby("Assignee").agg({
            "Original Estimate (hrs)": "sum",
            "Time Spent (hrs)": "sum"
        }).reset_index()

        agg_df["Utilization (%)"] = (agg_df["Time Spent (hrs)"] / agg_df["Original Estimate (hrs)"]) * 100
        agg_df["Utilization (%)"] = agg_df["Utilization (%)"].round(1)

        # KPIs
        avg_util = agg_df["Utilization (%)"].mean().round(1)
        overload_count = (agg_df["Utilization (%)"] > 100).sum()
        underutilized_count = (agg_df["Utilization (%)"] < 60).sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("📈 Avg. Utilization", f"{avg_util}%")
        col2.metric("🔥 Over-allocated", overload_count)
        col3.metric("🧊 Under-utilized", underutilized_count)

        # Resource Utilization Heatmap
        fig = px.density_heatmap(
            agg_df,
            x="Assignee",
            y="Utilization (%)",
            z="Utilization (%)",
            color_continuous_scale="RdYlGn",
            title="Resource Utilization Heatmap"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("⚠️ Resource Conflict Detection")
        conflict_df = df.groupby(["Assignee", "Sprint"]).agg({
            "Original Estimate (hrs)": "sum"
        }).reset_index()
        conflict_df["Conflict Flag"] = conflict_df["Original Estimate (hrs)"] > 40
        conflicts = conflict_df[conflict_df["Conflict Flag"]]

        if not conflicts.empty:
            st.warning("The following resource(s) are over-allocated within a sprint:")
            st.dataframe(conflicts[["Assignee", "Sprint", "Original Estimate (hrs)"]])
        else:
            st.success("✅ No sprint-level over-allocations detected.")

        st.subheader("💡 Reassignment Suggestions")
        overloaded = agg_df[agg_df["Utilization (%)"] > 100]
        underused = agg_df[agg_df["Utilization (%)"] < 60]

        suggestions = []
        for _, row in overloaded.iterrows():
            assignee = row["Assignee"]
            tasks = df[df["Assignee"] == assignee].sort_values(by="Original Estimate (hrs)", ascending=False)
            if not underused.empty:
                target = underused.sample(1).iloc[0]["Assignee"]
                suggestions.append({
                    "From": assignee,
                    "Task to Reassign": tasks.iloc[0]["Summary"],
                    "Hours": tasks.iloc[0]["Original Estimate (hrs)"],
                    "To": target
                })

        if suggestions:
            st.table(pd.DataFrame(suggestions))
        else:
            st.info("No reassignment needed at this time.")

        st.subheader("📋 Raw Data Preview")
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
else:
    st.info("📥 Please upload a JIRA Excel file to begin.")