"""Step 6. Build index.html from code/page_template.html.

Every number in the text is a {{path|format}} token filled from data/results.json. A few values derived here
(the "d" block) are written back into results.json so that every number used anywhere is in that file.
Facts the template states in words are checked with asserts. Map data are fetched from data/ by the page.
Run: python3 code/06_build_site.py
"""
import json, os, re
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import MultiPoint, Point
from common import DATA, ROOT, HERE

R = json.load(open(os.path.join(DATA, "results.json"), encoding="utf-8"))
C = pd.read_csv(os.path.join(DATA, "catchments.csv"))
S = pd.read_csv(os.path.join(DATA, "schools_uk.csv"))

d = {}
LD = R["land_distance"]
d["scot_prim_gt5"] = LD["Scotland"]["prim_gt5"]; d["eng_prim_gt5"] = LD["England"]["prim_gt5"]
big = R["biggest_catchments_secondary"][0]
# a well-known council area a little smaller than the biggest catchment, for scale
lad = R["lad_km2"]
cands = [(n, a) for n, a in lad.items() if n in ("Herefordshire, County of", "Shropshire", "Somerset", "Cornwall", "Wiltshire", "Isle of Wight", "Rutland", "Cheshire East", "Fife", "Pembrokeshire", "Anglesey")]
cands = sorted([c for c in cands if c[1] < big["km2"]], key=lambda c: -c[1])
d["scale_name"], d["scale_km2"] = cands[0][0].replace(", County of", ""), cands[0][1]
e = C[(C.nation == "England") & (C.denominational == 0)].sort_values("area_km2", ascending=False).iloc[0]
d["eng_big_name"], d["eng_big_auth"], d["eng_big_km2"] = e.catchment.title() if e.catchment.isupper() else e.catchment, e.authority, float(e.area_km2)
d["eng_zone_prim_med"] = R["zones"]["England|primary"]["median_km2"]
d["scot_zone_prim_med"] = R["zones"]["Scotland|primary"]["median_km2"]; d["scot_zone_sec_med"] = R["zones"]["Scotland|secondary"]["median_km2"]
d["golspie_per_pupil"] = big["km2"] / big["pupils"]
g = S[S.id == big["school_id"]].iloc[0]; d["golspie_fly"] = f"{g.lat:.3f},{g.lon:.3f},8"
k = R["biggest_zones_primary_by_nation"]["England"]; d["kielder_fly"] = f"{k['lat']:.3f},{k['lon']:.3f},10"
b = R["biggest_secondary"][0]; d["bigschool_fly"] = f"{b['lat']:.3f},{b['lon']:.3f},13"
fs = R["settlements"]["farthest_secondary"][0]; d["island_fly"] = f"{fs['lat']:.3f},{fs['lon']:.3f},9"
d["far_county"] = fs["county"]
ag = R["agreement"]["by_authority"]
d["ag_min_name"], d["ag_min"] = min(ag.items(), key=lambda t: t[1]); d["ag_max_name"], d["ag_max"] = max(ag.items(), key=lambda t: t[1])
m = C[(C.school_id.fillna("") != "") & C.nearest_agreement.notna()]
for nat, key in (("Scotland", "ag_scot"), ("England", "ag_eng")):
    t = m[m.nation == nat]; d[key] = float(np.average(t.nearest_agreement, weights=t.area_km2))
R["d"] = d

# facts stated in words
assert R["biggest_catchments_secondary"][0]["authority"] == "Highland" and all(c["authority"] in ("Highland", "Argyll and Bute") for c in R["biggest_catchments_secondary"][:3])
assert R["biggest_catchments_secondary"][0]["catchment"].startswith("Golspie")   # story card text is about Sutherland
assert R["biggest_zones_primary_by_nation"]["England"]["name"].startswith("Kielder") and R["biggest_zones_primary_by_nation"]["England"]["la"] == "Northumberland"
assert R["biggest_secondary"][0]["la"] == "Newham"     # "in east London"
assert fs["county"] == "Shetland Islands" and fs["island"] == 1
assert R["median_pupils_primary"]["Scotland"] < R["median_pupils_primary"]["England"]
assert 0.6 < R["agreement"]["all"] < 0.72      # "two thirds", "a third of the time"
assert R["zones"]["Scotland|primary"]["median_km2"] > 3 * R["zones"]["England|primary"]["median_km2"]   # "several times"
assert d["scale_km2"] < big["km2"]
assert R["catchments"]["by_nation"]["Wales"]["authorities"] == 1
assert R["ni_unplaced"] == 2


def get(path):
    v = R
    for kk in path.split("."):
        v = v[int(kk)] if isinstance(v, list) else v[kk]
    return v


def fmt(v, f):
    if f is None or f == "raw": return str(v)
    if f == "title": return " ".join(w.capitalize() if len(w) > 2 else w.lower() for w in str(v).split()) if str(v).isupper() else str(v)
    if f == "int": return f"{round(v):,}"
    if f == "pct": return f"{round(v * 100)}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f1": return f"{v:.1f}"
    raise ValueError(f)


def sub(m):
    return fmt(get(m.group(1)), m.group(3))


# hero mark: Voronoi cells of a few points in a circle (fixed seed)
rng = np.random.default_rng(7)
pts = [(60, 60)] + [(60 + r * np.cos(a), 60 + r * np.sin(a)) for r, a in zip(rng.uniform(26, 52, 11), np.linspace(0, 2 * np.pi, 12)[:-1] + rng.uniform(-.2, .2, 11))]
disc = Point(60, 60).buffer(57, 64)
vor = shapely.voronoi_polygons(MultiPoint(pts), extend_to=disc.buffer(40), ordered=True)
cells = []
for c in vor.geoms:
    q = c.intersection(disc)
    xy = np.asarray(q.exterior.coords)
    cells.append("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in xy) + " Z")
HERO = {"cells": cells, "pts": [[round(x, 1), round(y, 1)] for x, y in pts], "mid": 0}


def slim():
    keep = ["schools", "zones", "agreement", "catchments", "coverage", "settlements", "distance_bins", "distance_bin_edges", "land_distance",
            "biggest_catchments_primary", "biggest_catchments_secondary", "biggest_primary", "biggest_secondary", "biggest_zones_primary", "biggest_zones_secondary"]
    return {kk: R[kk] for kk in keep}


tpl = open(os.path.join(HERE, "page_template.html"), encoding="utf-8").read()
html = re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", sub, tpl)
assert "{{" not in html
html = html.replace("/*RESULTS*/", json.dumps(slim(), ensure_ascii=False, separators=(",", ":")))
html = html.replace("/*HERO*/", json.dumps(HERO)).replace("/*HILLS*/", open(os.path.join(DATA, "hills.json")).read())
vis = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", html, flags=re.S)
for bad in ("—", "–", "--"):
    assert bad not in vis, (bad, vis[vis.find(bad) - 80: vis.find(bad) + 80])
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
json.dump(R, open(os.path.join(DATA, "results.json"), "w"), indent=1, ensure_ascii=False)
print("index.html", round(len(html) / 1024), "KB")
