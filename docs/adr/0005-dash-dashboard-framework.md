---
status: accepted
---

# Dash (Python/Plotly) as the dashboard framework

Considered Streamlit, Dash, R/Shiny, and a React/Next.js web app. Chose Dash. It keeps the dashboard in the same language as any ETL/scoring code (Python), and offers more layout and callback flexibility than Streamlit for the map-click → radar-chart drill-down interaction the dashboard needs, without the added build and maintenance cost of a separate React frontend plus API backend.
