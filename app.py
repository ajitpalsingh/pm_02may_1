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
    "Work Calendar",
    "Gantt Chart",
    "Traffic Light Matrix",
    "Sankey Diagram",
    "Radar Chart"
])

# --- PM Daily Brief ---
if view == "PM Daily Brief" and issues_df is not None:
    st.title("📝 Project Manager Daily Brief")

    today = pd.to_datetime("today").normalize()

    # To-Do Items
    st.subheader("🔧 Action Required")
    unassigned = issues_df[issues_df['Assignee'].isna()]
    due_soon = issues_df[pd.to_datetime(issues_df['Due Date'], errors='coerce').between(today, today + pd.Timedelta(days=7))]
    start_dates = pd.to_datetime(issues_df['Start Date'], errors='coerce')
    duration = (today - start_dates).dt.days
    stuck = issues_df[(issues_df['Status'] == 'In Progress') & (duration > 7)]
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

# --- Resource Utilization ---
if view == "Resource Utilization" and worklogs_df is not None:
    st.title("📊 Resource Utilization by Week")
    worklogs_df['Date'] = pd.to_datetime(worklogs_df['Date'], errors='coerce')
    worklogs_df['Week'] = worklogs_df['Date'].dt.strftime('%Y-W%U')

    grouped = worklogs_df.groupby(['Week', 'Resource'])['Time Spent (hrs)'].sum().reset_index()
    pivot = grouped.pivot(index='Week', columns='Resource', values='Time Spent (hrs)').fillna(0)

    fig = px.bar(
        pivot,
        x=pivot.index,
        y=pivot.columns,
        title="Weekly Resource Utilization (hrs)",
        labels={'value': 'Hours Worked', 'Week': 'Week'},
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Skill Distribution ---
if view == "Skill Distribution" and skills_df is not None:
    st.title("🧠 Skill Distribution by Team")
    skill_counts = skills_df['Skillset'].value_counts().reset_index()
    skill_counts.columns = ['Skillset', 'Count']

    fig = px.pie(
        skill_counts,
        names='Skillset',
        values='Count',
        title="Skill Distribution",
        hole=0.4
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Sprint Burnup ---
if view == "Sprint Burnup" and issues_df is not None:
    st.title("📈 Sprint Burnup Chart")
    issues_df['Start Date'] = pd.to_datetime(issues_df['Start Date'], errors='coerce')
    issues_df['Due Date'] = pd.to_datetime(issues_df['Due Date'], errors='coerce')

    date_range = pd.date_range(start=issues_df['Start Date'].min(), end=issues_df['Due Date'].max())
    burnup_data = pd.DataFrame({'Date': date_range})

    burnup_data['Completed'] = burnup_data['Date'].apply(
        lambda d: issues_df[(issues_df['Status'] == 'Done') & (issues_df['Due Date'] <= d)]['Story Points'].sum()
    )
    burnup_data['Total Scope'] = issues_df['Story Points'].sum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=burnup_data['Date'], y=burnup_data['Completed'], mode='lines+markers', name='Completed'))
    fig.add_trace(go.Scatter(x=burnup_data['Date'], y=[burnup_data['Total Scope'].iloc[0]]*len(burnup_data),
                             mode='lines', name='Total Scope', line=dict(dash='dash')))

    fig.update_layout(title='Sprint Burnup Chart', xaxis_title='Date', yaxis_title='Story Points')
    st.plotly_chart(fig, use_container_width=True)

# --- Work Calendar ---
if view == "Work Calendar" and leaves_df is not None:
    st.title("📆 Resource Non-Availability Calendar")
    leaves_df['Date'] = pd.to_datetime(leaves_df['Date'], errors='coerce')
    calendar_data = leaves_df.groupby(['Date', 'Resource']).size().reset_index(name='Count')

    heatmap_data = calendar_data.pivot(index='Resource', columns='Date', values='Count').fillna(0)
    st.dataframe(heatmap_data.style.background_gradient(axis=1, cmap='YlOrRd'))

# --- Gantt Chart ---
if view == "Gantt Chart" and issues_df is not None:
    st.title("📅 Gantt Chart with Resource Coloring")
    issues_df['Start Date'] = pd.to_datetime(issues_df['Start Date'], errors='coerce')
    issues_df['Due Date'] = pd.to_datetime(issues_df['Due Date'], errors='coerce')

    gantt_data = issues_df.dropna(subset=['Start Date', 'Due Date'])
    fig = px.timeline(
        gantt_data,
        x_start="Start Date",
        x_end="Due Date",
        y="Assignee",
        color="Project",
        hover_name="Summary",
        title="Gantt Chart by Assignee"
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# --- Traffic Light Matrix ---
if view == "Traffic Light Matrix" and issues_df is not None:
    st.title("🚦 Resource Health Status Matrix")
    today = pd.to_datetime("today").normalize()
    issues_df['Due Date'] = pd.to_datetime(issues_df['Due Date'], errors='coerce')
    summary = issues_df.groupby('Assignee').agg(
        total_tasks=('Issue Key', 'count'),
        overdue_tasks=('Due Date', lambda d: (d < today).sum())
    ).reset_index()

    def status_color(row):
        if row['overdue_tasks'] == 0:
            return '🟢'
        elif row['overdue_tasks'] < row['total_tasks'] * 0.5:
            return '🟠'
        else:
            return '🔴'

    summary['Status'] = summary.apply(status_color, axis=1)
    st.dataframe(summary)

# --- Sankey Diagram ---
if view == "Sankey Diagram" and issues_df is not None:
    st.title("🔀 Task Flow Across Statuses")
    flow = issues_df.groupby(['Status', 'Project']).size().reset_index(name='Count')

    labels = list(pd.concat([flow['Status'], flow['Project']]).unique())
    label_to_index = {label: i for i, label in enumerate(labels)}

    source = flow['Status'].map(label_to_index)
    target = flow['Project'].map(label_to_index)
    value = flow['Count']

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=labels
        ),
        link=dict(
            source=source,
            target=target,
            value=value
        ))])

    fig.update_layout(title_text="Task Flow from Status to Project", font_size=10)
    st.plotly_chart(fig, use_container_width=True)

# --- Radar Chart ---
if view == "Radar Chart" and worklogs_df is not None and skills_df is not None:
    st.title("📡 Skill Load Balance Radar Chart")
    combined = pd.merge(worklogs_df, skills_df, left_on='Resource', right_on='Resource', how='inner')
    radar_data = combined.groupby(['Skillset', 'Resource'])['Time Spent (hrs)'].sum().reset_index()

    for skill in radar_data['Skillset'].unique():
        df = radar_data[radar_data['Skillset'] == skill]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=df['Time Spent (hrs)'],
            theta=df['Resource'],
            fill='toself',
            name=skill
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            showlegend=True,
            title=f"Load Balance for Skill: {skill}"
        )
        st.plotly_chart(fig, use_container_width=True)
