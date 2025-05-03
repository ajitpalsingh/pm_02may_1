import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from streamlit_calendar import calendar

st.set_page_config(page_title="Resource Calendar Editor", layout="wide")
st.title("📅 Resource Monitoring - Editable Calendar")

# Setup
resources = ["Alice", "Bob", "Charlie", "Diana"]
selected_user = st.selectbox("Select Resource", resources)

filename = f"{selected_user}_non_availability.csv"
if os.path.exists(filename):
    df = pd.read_csv(filename)
    df["Start"] = pd.to_datetime(df["Start"])
    df["End"] = pd.to_datetime(df["End"])
else:
    df = pd.DataFrame(columns=["Start", "End", "Reason"])

# Calendar Events Format
events = []
for idx, row in df.iterrows():
    events.append({
        "id": idx,
        "title": row["Reason"],
        "start": row["Start"].strftime("%Y-%m-%dT%H:%M:%S"),
        "end": row["End"].strftime("%Y-%m-%dT%H:%M:%S"),
    })

# Calendar Display with click support
st.subheader("📆 Calendar View")
clicked_date = calendar(events=events, options={"selectable": True, "editable": False, "initialView": "dayGridWeek"}, key="cal")

# Identify clicked event and extract data
clicked_event = st.session_state.get("calendar_date_click", None)
edit_index = None
if clicked_date:
    click_time = pd.to_datetime(clicked_date)
    match = df[(df["Start"].dt.floor("min") == click_time.floor("min"))]
    if not match.empty:
        edit_index = match.index[0]
        st.success(f"Editing entry for: {df.loc[edit_index, 'Reason']}")

# Pre-fill Form
st.subheader("✏️ Log / Edit Non-Availability")
if edit_index is not None:
    sel_start = df.loc[edit_index, "Start"]
    sel_end = df.loc[edit_index, "End"]
    sel_reason = df.loc[edit_index, "Reason"]
else:
    sel_start = datetime.now()
    sel_end = datetime.now() + timedelta(hours=1)
    sel_reason = "Meeting"

with st.form("entry_form"):
    start = st.datetime_input("Start", sel_start)
    end = st.datetime_input("End", sel_end)
    reason = st.selectbox("Reason", ["Meeting", "Leave", "Sick", "Unplanned Leave", "Out of Office"], index=0 if edit_index is None else ["Meeting", "Leave", "Sick", "Unplanned Leave", "Out of Office"].index(sel_reason))
    submitted = st.form_submit_button("💾 Save Entry")

    if submitted:
        if edit_index is not None:
            df.loc[edit_index, "Start"] = start
            df.loc[edit_index, "End"] = end
            df.loc[edit_index, "Reason"] = reason
            st.success("Entry updated successfully!")
        else:
            df = pd.concat([df, pd.DataFrame([{
                "Start": start,
                "End": end,
                "Reason": reason
            }])], ignore_index=True)
            st.success("New entry saved!")

        df.to_csv(filename, index=False)
        st.experimental_rerun()