
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="📅 FullCalendar with Editable Events", layout="wide")
st.title("📅 FullCalendar.js in Streamlit")

# Load events from CSV
csv_file = "calendar_events.csv"
try:
    df = pd.read_csv(csv_file)
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
except FileNotFoundError:
    df = pd.DataFrame(columns=["title", "start", "end"])
    df.to_csv(csv_file, index=False)

# Show as editable calendar
events = df.to_dict("records")
events_json = json.dumps(events, default=str)

# Inject FullCalendar with editable features
components.html(f"""
<!DOCTYPE html>
<html>
<head>
  <link href='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.0/main.min.css' rel='stylesheet' />
  <script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.0/main.min.js'></script>
  <style>
    #calendar {{
      max-width: 100%;
      margin: 40px auto;
    }}
  </style>
</head>
<body>
  <div id='calendar'></div>
  <script>
    document.addEventListener('DOMContentLoaded', function() {{
      var calendarEl = document.getElementById('calendar');
      var calendar = new FullCalendar.Calendar(calendarEl, {{
        initialView: 'dayGridMonth',
        editable: true,
        selectable: true,
        events: {events_json},
        eventClick: function(info) {{
          alert('Clicked event: ' + info.event.title);
        }}
      }});
      calendar.render();
    }});
  </script>
</body>
</html>
""", height=600)

# Display table for reference
st.subheader("📋 Event Log")
st.dataframe(df)
