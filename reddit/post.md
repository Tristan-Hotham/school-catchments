# Reddit post

## Title

[OC] How much land does one school serve? All 27,024 UK state schools, official catchments where councils publish them and nearest-school zones elsewhere. The biggest catchment, Golspie High in the Highlands, covers 2,215 km²

## Body

There is no UK-wide map of school catchments, so I built one from open data: every state school in the four nations, the official catchments of the 33 councils that publish them as open map services (mostly in Scotland), and Voronoi "nearest-school" zones everywhere else. The same 40 km square holds 1,768 primary schools in London, 114 in Fife and 4 in Sutherland. 53% of Scotland's land is more than 5 km from a primary school, against 6% of England's. Where official catchments exist, the nearest school is the catchment school for 66% of the land. Caveat: nearest-school zones are straight-line geometry, not catchments or admissions advice. Interactive map with search: https://maps.tristanhotham.com/school-catchments/

## Source comment

Source: Department for Education, Get Information About Schools (28 October 2026); Welsh Government address list of schools (DataMapWales); Scottish Government, Scottish School Roll and Locations; Department of Education Northern Ireland, school level enrolment data 2025/26 (located by postcode via postcodes.io); open catchment map services of 33 councils (listed in the data release); ONS Local Authority District boundaries; OS Open Names. All Open Government Licence v3.0; contains OS data © Crown copyright and database right 2026.

Tools: Python (pandas, shapely, pyproj, scipy, matplotlib).

Interactive version: https://maps.tristanhotham.com/school-catchments/
Blog post: https://blog.tristanhotham.com/2026/10/28/school-catchments/
Paper: https://doi.org/10.5281/zenodo.23748248
