
import streamlit as st
import streamlit.components.v1 as components
import json
from pathlib import Path

st.set_page_config(page_title="📅 Resource Monitoring Calendar", layout="wide")
st.title("📅 Resource Non-Availability (FullCalendar.js)")

# Load JSON events
json_path = Path("calendar_events.json")
if json_path.exists():
    with open(json_path, "r") as f:
        events = json.load(f)
else:
    events = []

# Generate HTML for FullCalendar
calendar_html = f"""
<!DOCTYPE html>
<html>
<head>
  <link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css' rel='stylesheet' />
  <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js'></script>
  <style>
    #calendar {{
      max-width: 100%;
      margin: 0 auto;
    }}
  </style>
</head>
<body>
  <div id='calendar'></div>
  <script>
    document.addEventListener('DOMContentLoaded', function () {{
      var calendarEl = document.getElementById('calendar');
      var calendar = new FullCalendar.Calendar(calendarEl, {{
        initialView: 'dayGridMonth',
        editable: false,
        events: {json.dumps(events)}
      }});
      calendar.render();
    }});
  </script>
</body>
</html>
"""

# Save the HTML to disk
html_path = "calendar.html"
with open(html_path, "w") as f:
    f.write(calendar_html)

# Render the calendar
components.iframe(src=html_path, height=600, width=1000)
