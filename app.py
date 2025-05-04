# Cleaned version of the provided Streamlit app

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import xlsxwriter
from openai import OpenAI
from datetime import datetime

# ---------- Sidebar: Upload and Template ----------
import os

fallback_file = "enriched_jira_project_data.xlsx"
if uploaded_file is None and os.path.exists(fallback_file):
    uploaded_file = open(fallback_file, "rb")
st.sidebar.title("Upload Your JIRA Data")
if st.sidebar.button("📂 Load Sample Project Data"):
    if os.path.exists(fallback_file):
        uploaded_file = open(fallback_file, "rb")
        st.sidebar.success("Loaded default file: enriched_jira_project_data.xlsx")
uploaded_file = st.sidebar.file_uploader("Choose an Excel file", type="xlsx")

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

        pd.DataFrame({"Resource": ["Amit"], "Skillset": ["Frontend"]}).to_excel(writer, sheet_name="Skills", index=False)
        pd.DataFrame({"Issue Key": ["JIRA-001"], "Resource": ["Amit"], "Date": ["2025-04-03"], "Time Spent (hrs)": [6]}).to_excel(writer, sheet_name="Worklogs", index=False)
        pd.DataFrame({"Date": ["2025-04-05"], "Resource": ["Amit"], "Reason": ["Sick Leave"]}).to_excel(writer, sheet_name="Non_Availability", index=False)

        worksheet = writer.sheets['Issues']
        worksheet.write_comment('A1', 'Unique identifier for each task')
        worksheet.write_comment('F1', 'Story points: effort estimate (e.g., 3, 5, 8, 13)')
        worksheet.write_comment('G1', 'Estimated number of working days')
        worksheet.write_comment('H1', 'Project name (e.g., Lucid, Snowflake)')

    buffer.seek(0)
    st.sidebar.download_button("📥 Download Template Excel File", data=buffer, file_name="jira_data_template.xlsx")

# ---------- GPT Client ----------
client = OpenAI(api_key=st.secrets["openai_api_key"])

# ---------- PM Daily Brief ----------
def pm_daily_brief():
    st.title("📝 Project Manager Daily Brief")
    today = pd.to_datetime("today").normalize()
    unassigned = issues_df[issues_df['Assignee'].isna()]
    due_soon = issues_df[pd.to_datetime(issues_df['Due Date'], errors='coerce').between(today, today + pd.Timedelta(days=7))]
    stuck = issues_df[(issues_df['Status'] == 'In Progress') & ((today - pd.to_datetime(issues_df['Start Date'], errors='coerce')).dt.days > 7)]
    missing_est = issues_df[issues_df['Original Estimate (days)'].isna() | issues_df['Story Points'].isna()]
    overdue = issues_df[pd.to_datetime(issues_df['Due Date'], errors='coerce') < today]

    st.subheader("🔧 Action Required")
    if not unassigned.empty: st.markdown("**🔲 Unassigned Tasks**"); st.dataframe(unassigned)
    if not due_soon.empty: st.markdown("**🗓 Tasks Due This Week**"); st.dataframe(due_soon)
    if not stuck.empty: st.markdown("**🔄 Stuck Tasks (In Progress > 7 days)**"); st.dataframe(stuck)

    st.subheader("🚨 Alerts & Notifications")
    if not missing_est.empty: st.markdown("**⚠️ Missing Estimates**"); st.dataframe(missing_est)
    if not overdue.empty: st.markdown("**⏰ Overdue Tasks**"); st.dataframe(overdue)

    st.subheader("🤖 Recommendations")
    st.markdown("- Reassign unassigned or stuck tasks.")
    st.markdown("- Alert assignees with overdue items.")
    st.markdown("- Review items due this week.")

    brief = f"""
    === PROJECT MANAGER DAILY BRIEF ===
    - {len(unassigned)} unassigned tasks
    - {len(due_soon)} tasks due this week
    - {len(stuck)} tasks in progress > 7 days
    - {len(missing_est)} tasks missing estimates
    - {len(overdue)} overdue tasks
    """
    st.download_button("📄 Download Brief as TXT", brief, file_name="PM_Daily_Brief.txt")

# ---------- Skill Distribution ----------
def skill_distribution():
    st.title("📘 Skill Distribution")
    skill_counts = skills_df['Skillset'].value_counts().reset_index()
    skill_counts.columns = ['Skillset', 'Count']
    fig = px.pie(skill_counts, names='Skillset', values='Count', title="Team Skill Distribution", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

# ---------- Resource Utilization ----------
def resource_utilization():
    st.title("📊 Resource Utilization")
    worklogs_df['Date'] = pd.to_datetime(worklogs_df['Date'], errors='coerce')
    worklogs_df['Week'] = worklogs_df['Date'].dt.strftime('%Y-W%U')
    grouped = worklogs_df.groupby(['Week', 'Resource'])['Time Spent (hrs)'].sum().reset_index()
    pivot = grouped.pivot(index='Week', columns='Resource', values='Time Spent (hrs)').fillna(0)
    fig = px.bar(
        pivot,
        x=pivot.index,
        y=pivot.columns,
        title="Weekly Resource Utilization (hrs)",
        labels={'value': 'Hours Worked', 'Week': 'Week'}
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Sprint Burnup ----------
def sprint_burnup():
    st.title("📈 Sprint Burnup Chart")
    issues_df['Start Date'] = pd.to_datetime(issues_df['Start Date'], errors='coerce')
    issues_df['Due Date'] = pd.to_datetime(issues_df['Due Date'], errors='coerce')

    if issues_df['Start Date'].isna().all() or issues_df['Due Date'].isna().all():
        st.warning("Start Date or Due Date missing in all records. Cannot build burnup chart.")
        return

    date_range = pd.date_range(start=issues_df['Start Date'].min(), end=issues_df['Due Date'].max())
    burnup_data = pd.DataFrame({'Date': date_range})
    burnup_data['Completed'] = burnup_data['Date'].apply(
        lambda d: issues_df[(issues_df['Status'] == 'Done') & (issues_df['Due Date'] <= d)]['Story Points'].sum()
    )
    burnup_data['Total Scope'] = issues_df['Story Points'].sum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=burnup_data['Date'], y=burnup_data['Completed'], mode='lines+markers', name='Completed'
    ))
    fig.add_trace(go.Scatter(
        x=burnup_data['Date'], y=[burnup_data['Total Scope'].iloc[0]]*len(burnup_data),
        mode='lines', name='Total Scope', line=dict(dash='dash')
    ))
    fig.update_layout(title='Sprint Burnup Chart', xaxis_title='Date', yaxis_title='Story Points')
    st.plotly_chart(fig, use_container_width=True)

# ---------- Work Calendar ----------
def work_calendar():
    st.title("📅 Team Non-Availability Calendar")
    leaves_df['Date'] = pd.to_datetime(leaves_df['Date'], errors='coerce')
    calendar_data = leaves_df.groupby(['Date', 'Resource']).size().reset_index(name='Count')
    heatmap_data = calendar_data.pivot(index='Resource', columns='Date', values='Count').fillna(0)

    st.subheader("Team Leave Heatmap")
    if heatmap_data.empty:
        st.warning("No non-availability data available to display.")
    else:
        st.dataframe(heatmap_data.style.background_gradient(axis=1, cmap='YlOrRd'))

# ---------- Gantt Chart ----------
def gantt_chart():
    st.title("📅 Gantt Chart - Timeline by Assignee")
    issues_df['Start Date'] = pd.to_datetime(issues_df['Start Date'], errors='coerce')
    issues_df['Due Date'] = pd.to_datetime(issues_df['Due Date'], errors='coerce')

    gantt_data = issues_df.dropna(subset=['Start Date', 'Due Date'])
    if gantt_data.empty:
        st.warning("No valid start and due dates available for Gantt chart visualization.")
        return

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

# ---------- Sankey Diagram ----------
def sankey_diagram():
    st.title("🔀 Sankey Diagram - Status to Project Flow")
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
        )
    )])
    fig.update_layout(title_text="Task Flow from Status to Project", font_size=10)
    st.plotly_chart(fig, use_container_width=True)

# ---------- Radar Chart ----------
def radar_chart():
    st.title("📡 Radar Chart - Resource Load by Skill")
    combined = pd.merge(worklogs_df, skills_df, on='Resource', how='inner')
    radar_data = combined.groupby(['Skillset', 'Resource'])['Time Spent (hrs)'].sum().reset_index()

    if radar_data.empty:
        st.warning("No merged worklog and skill data available.")
        return

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

# ---------- Traffic Light Matrix ----------
def traffic_light_matrix():
    st.title("🚦 Traffic Light Matrix - Task Monitoring")
    today = pd.to_datetime("today").normalize()
    issues_df['Due Date'] = pd.to_datetime(issues_df['Due Date'], errors='coerce')

    summary = issues_df.groupby('Assignee').agg(
        total_tasks=('Issue Key', 'count'),
        overdue_tasks=('Due Date', lambda d: (d < today).sum())
    ).reset_index()
    summary['Status'] = summary.apply(
        lambda row: '🟢' if row['overdue_tasks'] == 0 else (
            '🟠' if row['overdue_tasks'] < row['total_tasks'] * 0.5 else '🔴'
        ), axis=1
    )
    st.dataframe(summary)

# ---------- View Routing ----------
view = st.sidebar.radio("Choose View", [
    "Radar Chart",
    "Sankey Diagram",
    "Traffic Light Matrix",
    "Gantt Chart",
    "Work Calendar",
    "Sprint Burnup",
    "Skill Distribution",
    "Resource Utilization",
    "PM Daily Brief",
    "GPT Insight Widgets"
])

if 'issues_df' not in globals():
    issues_df, skills_df, worklogs_df, leaves_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if uploaded_file:
    issues_df, skills_df, worklogs_df, leaves_df = pd.read_excel(uploaded_file, sheet_name=None).values()

if view == "PM Daily Brief":
    pm_daily_brief()
elif view == "Resource Utilization":
    resource_utilization()
elif view == "Skill Distribution":
    skill_distribution()
elif view == "Sprint Burnup":
    sprint_burnup()
elif view == "Work Calendar":
    work_calendar()
elif view == "Gantt Chart":
    gantt_chart()
elif view == "Traffic Light Matrix":
    traffic_light_matrix()
elif view == "Sankey Diagram":
    sankey_diagram()
elif view == "Radar Chart":
    radar_chart()
elif view == "GPT Insight Widgets":
    gpt_insight_widget()


# ---------- GPT Insight Widget ----------
def gpt_insight_widget():
    st.title("🤖 AI-Powered Insights")
    st.info("This section uses GPT to analyze your JIRA project data.")
    sample_prompt = "What are the key risks in current sprint and how can they be mitigated?"
    user_query = st.text_area("Ask GPT a project-related question:", value=sample_prompt)

    if st.button("Generate Insight"):
        with st.spinner("Generating response from GPT..."):
            try:
                context_summary = issues_df[['Summary', 'Status', 'Assignee', 'Due Date']].dropna().head(10).to_string()
                prompt = f"""Project data:\n{context_summary}\n\nUser query: {user_query}\nAnswer:"""
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a project management assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )
                st.success("✅ Insight generated")
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"GPT call failed: {e}")
