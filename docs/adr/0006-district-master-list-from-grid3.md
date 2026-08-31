---
status: accepted
---

# District master list sourced live from GRID3's ArcGIS FeatureServer

We need an authoritative list of Zambia's 116 districts (names, codes, provinces, boundaries) to validate Excel/CSV indicator uploads against and to render the dashboard's map. We decided to query GRID3's `NSDI_Zambia_Districts_2022` layer directly via its public ArcGIS REST FeatureServer, rather than committing a downloaded shapefile/GeoJSON to the repo:

```
https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/Zambia_Administrative_Boundaries_Districts_2020/FeatureServer/0/query?where=1=1&outFields=*&f=geojson
```

This dataset is the government-endorsed source — produced collaboratively by Zambia's Survey Department, Electoral Commission, Central Statistical Office, Ministry of Local Government and Housing, and the University of Zambia — and its 116-district count matches the CCA's scope exactly. Fields include `DISTRICT`, `DIST_CODE`, `PROVINCE`, `PROV_CODE`, and polygon geometry.

Querying live avoids the repo silently drifting out of sync if GRID3 revises boundaries (e.g. a district split), at the cost of a runtime dependency on GRID3's service availability.

**Consequence**: fetch and cache a copy at each data refresh/ingest cycle (not on every dashboard page load), so a GRID3 outage doesn't take the dashboard down, and re-validate district names/counts against the live layer whenever it's revised.
