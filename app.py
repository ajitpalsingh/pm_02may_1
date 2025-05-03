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
        pd.DataFrame({
            "Resource": ["Amit"],
            "Skillset": ["Frontend"]
        }).to_excel(writer, sheet_name="Skills", index=False)
        pd.DataFrame({
            "Issue Key": ["JIRA-001"],
            "Resource": ["Amit"],
            "Date": ["2025-04-03"],
            "Time Spent (hrs)": [6]
        }).to_excel(writer, sheet_name="Worklogs", index=False)
        pd.DataFrame({
            "Date": ["2025-04-05"],
            "Resource": ["Amit"],
            "Reason": ["Sick Leave"]
        }).to_excel(writer, sheet_name="Non_Availability", index=False)

        workbook = writer.book
        worksheet = writer.sheets['Issues']
        worksheet.write_comment('A1', 'Unique identifier for each task')
        worksheet.write_comment('F1', 'Story points: effort estimate (e.g., 3, 5, 8, 13)')
        worksheet.write_comment('G1', 'Estimated number of working days')
        worksheet.write_comment('H1', 'Project name (e.g., Lucid, Snowflake)')

    buffer.seek(0)
    st.sidebar.download_button("📥 Download Template Excel File", data=buffer,
                               file_name="jira_data_template.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
