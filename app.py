import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
from datetime import datetime
import io
import xlsxwriter

# File uploader
st.sidebar.title("Upload Your JIRA Data")
uploaded_file = st.sidebar.file_uploader("Choose an Excel file", type="xlsx")

# Provide downloadable template
if st.sidebar.button("Download Data Template"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Sheet: Issues
        pd.DataFrame({
            "Issue Key": ["JIRA-001"],
            "Summary": ["Implement login page"],
            "Status": ["To Do"],
            "Assignee": ["Amit"],
            "Role": ["Frontend Dev"],
            "Story Points": [5],
            "Original Estimate (days)": [3],
            "Project": ["Lucid"],
            "Start Date": ["2025-04-01"],
            "Due Date": ["2025-04-10"]
        }).to_excel(writer, sheet_name="Issues", index=False)

        # Sheet: Skills
        pd.DataFrame({
            "Resource": ["Amit"],
            "Skillset": ["Frontend"]
        }).to_excel(writer, sheet_name="Skills", index=False)

        # Sheet: Worklogs
        pd.DataFrame({
            "Issue Key": ["JIRA-001"],
            "Resource": ["Amit"],
            "Date": ["2025-04-03"],
            "Time Spent (hrs)": [6]
        }).to_excel(writer, sheet_name="Worklogs", index=False)

        # Sheet: Non_Availability
        pd.DataFrame({
            "Date": ["2025-04-05"],
            "Resource": ["Amit"],
            "Reason": ["Sick Leave"]
        }).to_excel(writer, sheet_name="Non_Availability", index=False)

        # Add helpful comments
        workbook  = writer.book
        worksheet = writer.sheets['Issues']
        worksheet.write_comment('A1', 'Unique identifier for each task')
        worksheet.write_comment('F1', 'Story points: effort estimate (e.g., 3, 5, 8, 13)')
        worksheet.write_comment('G1', 'Estimated number of working days')
        worksheet.write_comment('H1', 'Project name (e.g., Lucid, Snowflake)')

    buffer.seek(0)
    st.sidebar.download_button(
        label="📥 Download Template Excel File",
        data=buffer,
        file_name="jira_data_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Load data from uploaded file or default
@st.cache_data
def load_data(file):
    required_sheets = {"Issues", "Skills", "Worklogs", "Non_Availability"}
    try:
        if file is not None:
            xls = pd.ExcelFile(file)
            available_sheets = set(xls.sheet_names)
            missing = required_sheets - available_sheets
            if missing:
                st.error(f"Missing required sheets: {', '.join(missing)}")
                return None, None, None, None
        else:
            xls = pd.ExcelFile("enriched_jira_project_data.xlsx")

        issues = xls.parse("Issues")
        skills = xls.parse("Skills")
        worklogs = xls.parse("Worklogs")
        leaves = xls.parse("Non_Availability")
        return issues, skills, worklogs, leaves
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None, None

# Load data
issues_df, skills_df, worklogs_df, leaves_df = load_data(uploaded_file)

# Navigation
view = st.sidebar.radio("Go to", [
    "PM Daily Brief",
    "Resource Utilization",
    "Skill Distribution",
    "Sprint Burnup",
    "Work Calendar"
])

# --- PM Daily Brief ---
if view == "PM Daily Brief" and issues_df is not None:
    st.title("📝 Project Manager Daily Brief")

    today = pd.to_datetime("today").normalize()

    # To-Do Items
    st.subheader("🔧 Action Required")
    unassigned = issues_df[issues_df['Assignee'].isna()]
    due_soon = issues_df[pd.to_datetime(issues_df['Due Date'], errors='coerce').between(today, today + pd.Timedelta(days=7))]
    stuck = issues_df[(issues_df['Status'] == 'In Progress') &
                      (pd.to_datetime(today - pd.to_datetime(issues_df['Start Date'], errors='coerce')).dt.days > 7)]
    if not unassigned.empty:
        st.markdown("**🔲 Unassigned Tasks**")
        st.dataframe(unassigned)
    if not due_soon.empty:
        st.markdown("**🗓 Tasks Due This Week**")
        st.dataframe(due_soon)
    if not stuck.empty:
        st.markdown("**🔄 Stuck Tasks (In Progress > 7 days)**")
        st.dataframe(stuck)

    # Alerts
    st.subheader("🚨 Alerts & Notifications")
    missing_est = issues_df[issues_df['Original Estimate (days)'].isna() | issues_df['Story Points'].isna()]
    overdue = issues_df[pd.to_datetime(issues_df['Due Date'], errors='coerce') < today]
    if not missing_est.empty:
        st.markdown("**⚠️ Missing Estimates**")
        st.dataframe(missing_est)
    if not overdue.empty:
        st.markdown("**⏰ Overdue Tasks**")
        st.dataframe(overdue)

    # Recommendations (simple placeholders)
    st.subheader("🤖 Recommendations")
    st.markdown("- Reassign unassigned or stuck tasks.")
    st.markdown("- Alert assignees with overdue items.")
    st.markdown("- Review items due this week.")

    # Downloadable Brief
    brief = f"""
    === PROJECT MANAGER DAILY BRIEF ===
    - {len(unassigned)} unassigned tasks
    - {len(due_soon)} tasks due this week
    - {len(stuck)} tasks in progress > 7 days
    - {len(missing_est)} tasks missing estimates
    - {len(overdue)} overdue tasks
    """
    st.download_button("📄 Download Brief as TXT", brief, file_name="PM_Daily_Brief.txt")
