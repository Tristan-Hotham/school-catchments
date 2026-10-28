# School catchments: how much of the UK does one school serve?

Every open state school in the UK, the official catchment areas of the councils that publish them as open data, and straight-line nearest-school zones everywhere else, clearly marked as not catchments. The page lets you switch between primary and secondary, colour by the land each school serves, the size of the school or whether the nearest school is the catchment school, click anywhere to see the nearest schools and the catchment you are in, and search for a place or postcode.

**Interactive version:** https://maps.tristanhotham.com/school-catchments/

**Paper and archived release:** https://doi.org/10.5281/zenodo.23748248

A data study by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

**Not an admissions tool.** Nearest-school zones are not catchments, and distances are straight lines. Real admissions depend on each school's rules, faith criteria, selection, siblings and capacity. Always check with your council.

## Headline results

- 27,024 open state schools (26,991 distinct establishments, since Scotland lists departments of combined schools separately): 20,823 primary, 4,174 secondary and 2,220 special, with 9,741,266 pupils on roll.
- 2,992 official catchments from 33 councils that publish open map services: 21 in Scotland, 11 in England and 1 in Wales; 98% linked to their school. Northern Ireland has no catchments.
- The biggest official catchment found is Golspie High School's in Highland, 2,215 km² for 264 pupils, bigger than Herefordshire (2,180 km²). Next: Lochaber High (2,048 km²) and Ullapool High (2,031 km²). The biggest primary catchment is Ullapool Primary's, 986 km².
- Median nearest-school zone: primary 2.4 km² in England, 5.6 in Wales, 8.2 in Scotland and 12.9 in Northern Ireland; secondary 11.7, 37.0, 50.2 and 38.2 km². The biggest zones are Tongue Primary (841 km²) and Ullapool High (2,390 km²); in England, Kielder Primary School and Nursery (298 km², 10 pupils).
- 53% of Scotland's land is more than 5 km in a straight line from a primary school, against 6% of England's, 23% of Wales's and 13% of Northern Ireland's.
- Of 28,055 villages and hamlets in Great Britain, 17% of Scottish ones are more than 5 km from a primary school (2% in England, 7% in Wales), and 34% of Scottish ones are more than 10 km from a secondary. The furthest from a secondary is Da Hametoon in Shetland (42.2 km, across the sea); on the mainland, Braemar (37.5 km).
- Where councils publish catchments, 66% of catchment land (by area) is nearest to the catchment's own school (Scotland 69%, England 55%); in 22% of catchments less than half the land is. Nearest-school zones are a fair first guess, not a substitute.
- The biggest state schools: Brampton Manor Academy, Newham (2,987 pupils) and Claycots School, Slough (1,605, primary).

Every number is in `data/results.json`, from which the page, paper, blog and collage are built.

## Files

| Path | What it is |
|---|---|
| `index.html` | The interactive page. |
| `header.png` | Social card (1200 by 630). |
| `data/schools_uk.csv` | Every school: id (E + URN, W + school code, S + seed code + P/S/X department, N + DE reference), nation, name, council, phase flags, type, religious character, pupils, capacity (England), location, nearest-school zone area and furthest point for its phase(s). |
| `data/catchments.csv` | Every official catchment used: council, nation, phase, denominational, name, land area (km²), linked school, how it was linked, and the share of its land nearest to its own school. |
| `data/catchment_sources.csv` | The council layer used for each council, phase and denomination, with its service address and licence note. |
| `data/zones_summary.csv`, `data/la_summary.csv` | Zone statistics by nation and phase, and school counts and median zones by council. |
| `data/settlements_distance.csv` | Every OS Open Names city, town, village and hamlet in Great Britain with the straight-line distance to the nearest primary and secondary school. |
| `data/page_*.json`, `data/hills.png`, `data/hills.json` | Compact files for the page (catchment polygons simplified to about 25 m and delta-coded; land and council borders; places; hill shading). |
| `data/results.json` | Every number used. |
| `code/` | The analysis, in order (see below). |
| `release/` | Paper PDF and LaTeX source, blog figures and post, Zenodo files. |
| `reddit/` | Collage and post text. |

## Sources and licences

- England: Department for Education, Get Information About Schools, all establishments download of 28 October 2026 (https://get-information-schools.service.gov.uk/Downloads). Open Government Licence v3.0. Only open state-funded schools and the fields above were kept; no personal data (head teacher names were dropped in the browser).
- Wales: Welsh Government, address list of schools, maintained schools layer on DataMapWales (https://datamap.gov.wales/). Open Government Licence v3.0.
- Scotland: Scottish Government, Scottish School Roll and Locations (https://maps.gov.scot/server/rest/services/ScotGov/UtilityGovernmental/MapServer/0). Open Government Licence v3.0.
- Northern Ireland: Department of Education, school enrolment, school level data 2025/26 (https://www.education-ni.gov.uk/publications/school-enrolment-school-level-data-20252026). Open Government Licence v3.0. Locations are postcode centroids from postcodes.io (ONS Postcode Directory; Northern Ireland postcode locations are Crown copyright, Land and Property Services, under ONSPD terms). Two schools whose postcodes were not found are omitted.
- Official catchments: open ArcGIS services of 33 councils, found through data.gov.uk and ArcGIS Online; see `data/catchment_sources.csv`. Most are published under the Open Government Licence and contain Ordnance Survey data © Crown copyright and database right. The Improvement Service's national Scottish layer (https://data.spatialhub.scot/dataset/school_catchments-is) requires accepting terms in a web form and was not used.
- Boundaries: ONS Open Geography Portal, Local Authority Districts (December 2024) Boundaries UK BGC. Open Government Licence v3.0; contains OS data © Crown copyright and database right 2024.
- Places: Ordnance Survey, OS Open Names (Open Government Licence v3.0); GeoNames cities15000 for Northern Ireland towns (CC BY 4.0). Hill shading: AWS Terrain Tiles (Mapzen and Tilezen).
- Page libraries: Leaflet 1.9.4, d3-delaunay 6.0.4. Base map tiles © Esri when they load.

Derived data, text and figures: CC BY 4.0. Code: MIT (see `LICENSE`).

## How to rerun

The source bundles were fetched in a web browser (the analysis machine has no general web access) and saved as gzipped JSON: `sc_gias_20261028.json.gz`, `sc_ni_schools_202526.json.gz` and `sc_catchments_bundle_20261028.json.gz` (council catchment layers, Scottish and Welsh school lists, ONS boundaries). Set `SC_RAW` to their folder, `OSNAMES` to an OS Open Names extract (tab-separated) and `FONT_DIR` to Fraunces, Source Serif 4 and IBM Plex Mono, then run in order:

```
python3 code/01_schools.py      # schools table
python3 code/02_inventory.py    # inventory of harvested catchment layers
python3 code/03_catchments.py   # chosen layers, clipped, measured and linked to schools
python3 code/04_analyse.py      # nearest-school zones, agreement, distances, results.json
python3 code/05_page_data.py    # compact page files and hill shading
python3 code/06_build_site.py   # index.html
python3 code/07_header.py       # header.png
python3 code/08_figures.py      # paper and blog figures
python3 code/09_paper.py        # paper PDF (xelatex)
python3 code/10_release.py      # blog post, meta files, Zenodo folder
```

Python 3 with pandas, numpy, scipy, shapely 2, pyproj, matplotlib and Pillow.

## Caveats

Coverage of official catchments is partial and uneven, and some council layers are dated or marked as working copies by their publishers. Wokingham, Lancashire and Bristol publish overlapping priority areas and were left out. Nearest-school zones ignore roads, ferries, faith, selection and capacity, and stop at national borders; faith and non-faith schools are mixed. The map recomputes zones in the browser in Web Mercator, which can differ slightly from the figures computed in British National Grid. Rolls are a single census day.

## Citation

Hotham, T. (2026) How Much Land Does One School Serve? Official Catchments and Nearest-School Zones Across the United Kingdom. Zenodo. https://doi.org/10.5281/zenodo.23748248

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
