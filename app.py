# Cleaned version of the provided Streamlit app

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import xlsxwriter
from openai import OpenAI
from datetime import datetime
import os

# ---------- File Upload ----------
fallback_file = "enriched_jira_project_data.xlsx"
uploaded_file = st.sidebar.file_uploader("Upload your JIRA Excel file", type="xlsx")

if st.sidebar.button("📂 Load Sample Project Data"):
    if os.path.exists(fallback_file):
        uploaded_file = open(fallback_file, "rb")
        st.sidebar.success("Loaded default file: enriched_jira_project_data.xlsx")

# ---------- Load Data ----------
@st.cache_data
def load_data(file):
    if file is not None:
        xls = pd.ExcelFile(file)
        issues = xls.parse("Issues")
        skills = xls.parse("Skills")
        worklogs = xls.parse("Worklogs")
        leaves = xls.parse("Non_Availability")
        return issues, skills, worklogs, leaves
    return None, None, None, None

issues_df, skills_df, worklogs_df, leaves_df = load_data(uploaded_file)

# ---------- Gantt Chart ----------
def gantt_chart():
    st.title("📅 Gantt Chart - Timeline by Assignee")
    if issues_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return
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

# ---------- Traffic Light Matrix ----------
def traffic_light_matrix():
    st.title("🚦 Traffic Light Matrix - Task Monitoring")
    if issues_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return
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

# ---------- Sprint Burnup ----------
def sprint_burnup():
    st.title("📈 Sprint Burnup Chart")
    if issues_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return
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

# ---------- Radar Chart ----------
def radar_chart():
    st.title("📡 Radar Chart - Resource Load by Skill")
    if issues_df is None or skills_df is None or worklogs_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return
    if 'Resource' not in worklogs_df.columns or 'Resource' not in skills_df.columns:
        st.error("Missing 'Resource' column in worklogs or skills data.")
        return
    combined = pd.merge(worklogs_df, skills_df, on='Resource', how='inner')
    if 'Time Spent (hrs)' not in combined.columns or 'Skillset' not in combined.columns:
        st.error("Missing required columns in merged dataset.")
        return
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

# ---------- GPT Assistant ----------
def gpt_insight_widget():
    st.title("🤖 AI-Powered Insights")
    if issues_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return
    client = OpenAI(api_key=st.secrets["openai_api_key"])
    sample_prompt = "What are the key risks in current sprint and how can they be mitigated?"
    user_query = st.text_area("Ask GPT a project-related question:", value=sample_prompt)
    if st.button("Generate Insight"):
        with st.spinner("Generating response from GPT..."):
            try:
                context_summary = issues_df[['Summary', 'Status', 'Assignee', 'Due Date']].dropna().head(10).to_string()
                prompt = f"""Project data:
{context_summary}

User query: {user_query}
Answer:"""
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

# ---------- PM Daily Brief ----------
def pm_daily_brief():
    st.title("📝 Project Manager Daily Brief")
    if issues_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return

    today = pd.to_datetime("today").normalize()
    issues_df['Start Date'] = pd.to_datetime(issues_df['Start Date'], errors='coerce')
    issues_df['Due Date'] = pd.to_datetime(issues_df['Due Date'], errors='coerce')

    unassigned = issues_df[issues_df['Assignee'].isna()]
    due_soon = issues_df[issues_df['Due Date'].between(today, today + pd.Timedelta(days=7), inclusive='both')]
    stuck = issues_df[(issues_df['Status'] == 'In Progress') & ((today - issues_df['Start Date']).dt.days > 7)]
    missing_est = issues_df[issues_df['Original Estimate (days)'].isna() | issues_df['Story Points'].isna()]
    overdue = issues_df[issues_df['Due Date'] < today]

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

# ---------- Stacked Bar Chart ----------
def stacked_bar_resource_utilization():
    global worklogs_df
    st.title("📊 Stacked Bar Chart - Resource Utilization by Week")
    if worklogs_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return

    if 'Date' not in worklogs_df.columns or 'Resource' not in worklogs_df.columns:
        st.error("Worklogs must include 'Date' and 'Resource' columns.")
        return

    worklogs_df['Date'] = pd.to_datetime(worklogs_df['Date'], errors='coerce')
    worklogs_df = worklogs_df.dropna(subset=['Date'])
    worklogs_df['Week'] = worklogs_df['Date'].dt.strftime('%Y-%U')
    grouped = worklogs_df.groupby(['Week', 'Resource'])['Time Spent (hrs)'].sum().reset_index()

    if grouped.empty:
        st.warning("No worklog data to display.")
        return

    fig = px.bar(
        grouped,
        x='Week',
        y='Time Spent (hrs)',
        color='Resource',
        title='Resource Utilization by Week',
        text_auto=True
    )
    fig.update_layout(barmode='stack', xaxis_title='Week', yaxis_title='Hours Worked')
    st.plotly_chart(fig, use_container_width=True)

# ---------- Bubble Chart: Overload vs. Velocity ----------
def bubble_chart_overload_velocity():
    st.title("🫧 Bubble Chart - Overload vs. Velocity")
    if worklogs_df is None or issues_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return

    worklogs_df['Date'] = pd.to_datetime(worklogs_df['Date'], errors='coerce')
    worklogs_df['Week'] = worklogs_df['Date'].dt.strftime('%Y-%U')
    actuals = worklogs_df.groupby(['Week', 'Resource'])['Time Spent (hrs)'].sum().reset_index()

    if 'Story Points' not in issues_df.columns or 'Assignee' not in issues_df.columns:
        st.error("Issues sheet must contain 'Assignee' and 'Story Points'.")
        return

    velocity = issues_df.groupby('Assignee')['Story Points'].sum().reset_index()
    velocity.columns = ['Resource', 'Story Points']
    merged = pd.merge(actuals, velocity, on='Resource', how='left')
    merged = merged.dropna()

    if merged.empty:
        st.warning("Insufficient data for bubble chart.")
        return

    fig = px.scatter(
        merged,
        x='Story Points',
        y='Time Spent (hrs)',
        size='Time Spent (hrs)',
        color='Resource',
        hover_name='Resource',
        title='Overload vs. Velocity Bubble Chart',
        labels={'Story Points': 'Velocity', 'Time Spent (hrs)': 'Actual Load'}
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Calendar Heatmap ----------
def calendar_heatmap():
    st.title("🌡 Calendar Heatmap - Resource-wise Utilization")
    if worklogs_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return

    if 'Date' not in worklogs_df.columns or 'Resource' not in worklogs_df.columns:
        st.error("Missing 'Date' or 'Resource' in Worklogs data.")
        return

    worklogs_df['Date'] = pd.to_datetime(worklogs_df['Date'], errors='coerce')
    df = worklogs_df.dropna(subset=['Date'])
    df['Day'] = df['Date'].dt.date

    pivot = df.groupby(['Resource', 'Day'])['Time Spent (hrs)'].sum().reset_index()
    pivot.columns = ['Resource', 'Day', 'Hours']
    heatmap = pivot.pivot(index='Resource', columns='Day', values='Hours').fillna(0)
    heatmap = heatmap[sorted(heatmap.columns)]

    st.subheader("📆 Utilization Heatmap by Resource")
    styled_heatmap = heatmap.style.format('{:.1f}').background_gradient(cmap='viridis', axis=None, gmap=heatmap, vmin=0, vmax=heatmap.values.max())
    st.dataframe(styled_heatmap)

# ---------- Treemap: Team Resource Distribution ----------
def treemap_resource_distribution():
    st.title("🌳 Treemap - Team Resource Distribution")
    if skills_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return

    if 'Resource' not in skills_df.columns or 'Skillset' not in skills_df.columns:
        st.error("Skills data must include 'Resource' and 'Skillset' columns.")
        return

    skills_df['Count'] = 1
    fig = px.treemap(
        skills_df,
        path=['Skillset', 'Resource'],
        values='Count',
        title="Distribution of Resources by Skillset"
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Burnup Chart by Assignee ----------
def burnup_by_assignee():
    st.title("📈 Burnup Chart by Assignee")
    if issues_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return

    issues_df['Due Date'] = pd.to_datetime(issues_df['Due Date'], errors='coerce')
    if issues_df['Due Date'].isna().all():
        st.warning("Due Date missing in all records.")
        return

    assignees = issues_df['Assignee'].dropna().unique()
    for person in assignees:
        df = issues_df[issues_df['Assignee'] == person]
        dates = pd.date_range(start=df['Due Date'].min(), end=df['Due Date'].max())
        burnup = pd.DataFrame({'Date': dates})
        burnup['Completed'] = burnup['Date'].apply(
            lambda d: df[(df['Status'] == 'Done') & (df['Due Date'] <= d)]['Story Points'].sum()
        )
        burnup['Total Scope'] = df['Story Points'].sum()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=burnup['Date'], y=burnup['Completed'], mode='lines+markers', name='Completed'
        ))
        fig.add_trace(go.Scatter(
            x=burnup['Date'], y=[burnup['Total Scope'].iloc[0]]*len(burnup),
            mode='lines', name='Total Scope', line=dict(dash='dash')
        ))
        fig.update_layout(title=f'{person} - Burnup Chart', xaxis_title='Date', yaxis_title='Story Points')
        st.plotly_chart(fig, use_container_width=True)

# ---------- Sankey Diagram: Task Flow Across Statuses ----------
def sankey_task_flow():
    st.title("🔀 Sankey Diagram - Task Flow Across Statuses")
    if issues_df is None:
        st.warning("Please upload a valid JIRA Excel file.")
        return

    if 'Status' not in issues_df.columns or 'Project' not in issues_df.columns:
        st.error("Missing 'Status' or 'Project' column in Issues sheet.")
        return

    transitions = issues_df.groupby(['Project', 'Status']).size().reset_index(name='Count')
    transitions = transitions[transitions['Count'] > 0]
    all_labels = list(pd.unique(transitions['Project'].tolist() + transitions['Status'].tolist()))
    label_index = {k: v for v, k in enumerate(all_labels)}

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_labels
        ),
        link=dict(
            source=[label_index[p] for p in transitions['Project']],
            target=[label_index[s] for s in transitions['Status']],
            value=transitions['Count']
        ))])

    fig.update_layout(title_text="Task Flow from Project to Status", font_size=12)
    st.plotly_chart(fig, use_container_width=True)

# ---------- View Dispatcher ----------
view = st.sidebar.selectbox("Select View", [
    "Sankey Diagram",
    "Burnup by Assignee",
    "Treemap",
    "Calendar Heatmap",
    "Bubble Chart",
    "Stacked Bar Chart",
    "PM Daily Brief",
    "GPT Assistant",
    "Gantt Chart",
    "Traffic Light Matrix",
    "Sprint Burnup",
    "Radar Chart"
])

if view == "Gantt Chart":
    gantt_chart()
elif view == "Traffic Light Matrix":
    traffic_light_matrix()
elif view == "Sprint Burnup":
    sprint_burnup()
elif view == "Stacked Bar Chart":
    stacked_bar_resource_utilization()
elif view == "Burnup by Assignee":
    burnup_by_assignee()
elif view == "Radar Chart":
    radar_chart()
elif view == "PM Daily Brief":
    pm_daily_brief()
elif view == "Bubble Chart":
    bubble_chart_overload_velocity()
elif view == "Calendar Heatmap":
    calendar_heatmap()
elif view == "Treemap":
    treemap_resource_distribution()
elif view == "Sankey Diagram":
    sankey_task_flow()
elif view == "GPT Assistant":
    gpt_insight_widget()
