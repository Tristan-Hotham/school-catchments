"""Step 3. Official catchment polygons from the councils that publish them openly.

Picks one layer per council, phase and denomination from work/inventory.csv (the list below was checked
by hand against each layer's fields), dissolves polygons by school name, clips them to the council's land
(ONS LAD Dec 2024 BGC boundary), measures land area in km2 (British National Grid), and links each
catchment to a school in data/schools_uk.csv: a school of the same phase (and Roman Catholic for
denominational layers) inside the polygon, preferring the closest name; else the nearest such school
within 3 km whose name matches.
Outputs: data/catchments.csv, work/catchments_bng.pkl (for step 4), data/catchment_sources.csv
Run: python3 code/03_catchments.py
"""
import os, re, pickle, difflib
import numpy as np
import shapely
import pandas as pd
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from common import fix, to_bng
from common import DATA, WORK, load_gz, TO_BNG

I = pd.read_csv(os.path.join(WORK, "inventory.csv")).fillna("")
B = load_gz("sc_catchments_bundle_20261028.json.gz")
LAYER = {}
ITEM = {}
for src in ("ckan", "agol", "extra"):
    for it in B[src]:
        for l in it.get("layers", []):
            if l.get("feats"):
                LAYER.setdefault(l["url"], l); ITEM.setdefault(l["url"], it)

# (inventory row, authority, nation, phase, denominational, name field, optional (field, regex) filter)
SEL = [
    (51, "Highland", "Scotland", "primary", 0, "NAME", None), (52, "Highland", "Scotland", "secondary", 0, "SECONDARY", None),
    (149, "North Ayrshire", "Scotland", "primary", 0, "NAME", None), (148, "North Ayrshire", "Scotland", "secondary", 0, "NAME", None),
    (154, "North Ayrshire", "Scotland", "primary", 1, "NAME", None), (155, "North Ayrshire", "Scotland", "secondary", 1, "NAME", None),
    (131, "Perth and Kinross", "Scotland", "primary", 0, "NAME", None), (47, "Perth and Kinross", "Scotland", "secondary", 0, "NAME", None),
    (57, "Perth and Kinross", "Scotland", "primary", 1, "NAME", None), (55, "Perth and Kinross", "Scotland", "secondary", 1, "NAME", None),
    (24, "Dundee City", "Scotland", "primary", 0, "School", None), (22, "Dundee City", "Scotland", "secondary", 0, "School", None),
    (23, "Dundee City", "Scotland", "primary", 1, "School", None), (21, "Dundee City", "Scotland", "secondary", 1, "School", None),
    (26, "Stirling", "Scotland", "primary", 0, "School_Name", None), (25, "Stirling", "Scotland", "secondary", 0, "School_Name", None),
    (32, "Fife", "Scotland", "primary", 0, "SCHOOL_NAM", None), (34, "Fife", "Scotland", "secondary", 0, "SCHOOL_NAM", None),
    (36, "Fife", "Scotland", "primary", 1, "SCHOOL_NAM", None), (35, "Fife", "Scotland", "secondary", 1, "SCHOOL_NAM", None),
    (37, "Aberdeen City", "Scotland", "primary", 0, "NAME", None), (43, "Aberdeen City", "Scotland", "secondary", 0, "NAME", None),
    (48, "North Lanarkshire", "Scotland", "primary", 0, "name", None), (67, "North Lanarkshire", "Scotland", "secondary", 0, "name", None),
    (44, "North Lanarkshire", "Scotland", "primary", 1, "name", None), (61, "North Lanarkshire", "Scotland", "secondary", 1, "name", None),
    (88, "Moray", "Scotland", "primary", 0, "SCHOOL", None), (91, "Moray", "Scotland", "secondary", 0, "SCHOOL", None),
    (129, "Moray", "Scotland", "primary", 1, "SCHOOL", None),
    (75, "City of Edinburgh", "Scotland", "primary", 0, "SCHOOL_NAM", None), (70, "City of Edinburgh", "Scotland", "secondary", 0, "SCHOOL", None),
    (128, "City of Edinburgh", "Scotland", "primary", 1, "SCHOOL_NAM", None), (73, "City of Edinburgh", "Scotland", "secondary", 1, "SCH_NAME", None),
    (74, "East Lothian", "Scotland", "primary", 0, "PRIMARY_", None), (76, "East Lothian", "Scotland", "secondary", 0, "SECONDARY", None),
    (77, "South Ayrshire", "Scotland", "primary", 0, "ndprimary", None), (145, "South Ayrshire", "Scotland", "secondary", 0, "ndsecondar", None),
    (146, "South Ayrshire", "Scotland", "primary", 1, "rcprimary", None), (147, "South Ayrshire", "Scotland", "secondary", 1, "schoolname", None),
    (167, "Falkirk", "Scotland", "primary", 0, "name_", None), (169, "Falkirk", "Scotland", "secondary", 0, "name_", None),
    (165, "Falkirk", "Scotland", "primary", 1, "name_", None), (164, "Falkirk", "Scotland", "secondary", 1, "name_", None),
    (40, "Renfrewshire", "Scotland", "primary", 0, "Name", ("Type", r"^Non Denominational Primar")),
    (40, "Renfrewshire", "Scotland", "secondary", 0, "Name", ("Type", r"^Non Denominational Second")),
    (40, "Renfrewshire", "Scotland", "primary", 1, "Name", ("Type", r"^Denominational Primar")),
    (40, "Renfrewshire", "Scotland", "secondary", 1, "Name", ("Type", r"^Denominational Second")),
    (56, "Aberdeenshire", "Scotland", "primary", 0, "school_name", None), (58, "Aberdeenshire", "Scotland", "secondary", 0, "school_name", None),
    (60, "Dumfries and Galloway", "Scotland", "primary", 0, "name", None),
    (87, "Argyll and Bute", "Scotland", "primary", 0, "NM", ("DENOM", r"^Non Denominational")),
    (87, "Argyll and Bute", "Scotland", "primary", 1, "NM", ("DENOM", r"^Roman Catholic")),
    (89, "Argyll and Bute", "Scotland", "secondary", 0, "SEC", None),
    (127, "West Dunbartonshire", "Scotland", "primary", 0, "sch_name", None), (126, "West Dunbartonshire", "Scotland", "secondary", 0, "sch_name", None),
    (125, "West Dunbartonshire", "Scotland", "primary", 1, "school_nam", None), (124, "West Dunbartonshire", "Scotland", "secondary", 1, "school_nam", None),
    (151, "East Dunbartonshire", "Scotland", "primary", 0, "ND_SCHOOLS", None), (153, "East Dunbartonshire", "Scotland", "secondary", 0, "SCHOOLS", None),
    (152, "East Dunbartonshire", "Scotland", "primary", 1, "SCHOOLS", None),
    (181, "Midlothian", "Scotland", "primary", 0, "SchoolName", ("Type", r"^ND_PS$")), (181, "Midlothian", "Scotland", "secondary", 0, "SchoolName", ("Type", r"^ND_HS$")),
    (181, "Midlothian", "Scotland", "primary", 1, "SchoolName", ("Type", r"^D_PS$")), (181, "Midlothian", "Scotland", "secondary", 1, "SchoolName", ("Type", r"^D_HS$")),
    (191, "West Lothian", "Scotland", "primary", 0, "schoolname", None), (192, "West Lothian", "Scotland", "secondary", 0, "school", None),
    (190, "West Lothian", "Scotland", "primary", 1, "schoolname", None), (189, "West Lothian", "Scotland", "secondary", 1, "school", None),
    # England
    (31, "Northumberland", "England", "primary", 0, "SCHOOL_NAME", None), (28, "Northumberland", "England", "secondary", 0, "SCHOOL_NAME", None),
    (141, "Sheffield", "England", "primary", 0, "catchment", None), (69, "Sheffield", "England", "secondary", 0, "catchment", None),
    (176, "Hampshire", "England", "primary", 0, "School", None), (175, "Hampshire", "England", "secondary", 0, "School", None),
    (54, "Southend-on-Sea", "England", "primary", 0, "Catchment", None), (53, "Southend-on-Sea", "England", "secondary", 0, "Catchment", None),
    (227, "Wiltshire", "England", "primary", 0, "NAME", None), (226, "Wiltshire", "England", "secondary", 0, "Establishment_Name", None),
    (96, "Telford and Wrekin", "England", "primary", 0, "NAME", None), (95, "Telford and Wrekin", "England", "secondary", 0, "NAME", None),
    (93, "Nottingham", "England", "primary", 0, "Name", None), (92, "Nottingham", "England", "secondary", 0, "Name", None),
    (123, "North Tyneside", "England", "primary", 0, "NAME", None), (94, "North Tyneside", "England", "secondary", 0, "CATCH_NAME", None),
    (166, "East Riding of Yorkshire", "England", "primary", 0, None, None),
    (170, "Cornwall", "England", "primary", 0, "School_Nam", None),
    (38, "Bracknell Forest", "England", "primary", 0, "School_1", None),
    # Wales
    (204, "Merthyr Tydfil", "Wales", "primary", 0, "Name", ("Type", r"^(English|Welsh) Medium Primary")),
    (204, "Merthyr Tydfil", "Wales", "primary", 1, "Name", ("Type", r"^Roman Catholic Primary")),
    (204, "Merthyr Tydfil", "Wales", "secondary", 0, "Name", ("Type", r"^Secondary")),
]
# polygons that are not a school's catchment: county-wide or "no catchment" areas, interim zones, out-of-area slivers
NOT_CATCH = re.compile(r"no school catchment|no catchment|not applicable|undesignated|tyneside district|^northtyneside$|interim provision|-x$|\(EAC\)|^X ", re.I)
COUNTY = {"Hampshire": ["Basingstoke and Deane", "East Hampshire", "Eastleigh", "Fareham", "Gosport", "Hart", "Havant", "New Forest", "Rushmoor", "Test Valley", "Winchester"]}

lad = {f["properties"]["LAD24NM"]: fix(to_bng(shape(f["geometry"]))) for f in B["lad"]["features"]}


def land_of(auth):
    names = COUNTY.get(auth, [auth])
    return unary_union([lad[n] for n in names]).buffer(0)


S = pd.read_csv(os.path.join(DATA, "schools_uk.csv"))
S["rc"] = S.religious.fillna("").str.contains("Catholic")
norm = lambda s: re.sub(r"\b(primary|secondary|high|school|academy|community|rc|r\.c\.|c of e|ce|church of england|catholic|the|and|st|saint|infant|junior|nursery|campus|grammar|college|first|middle)\b|[^a-z ]", " ", str(s).lower()).split()


def sim(a, b):
    a, b = " ".join(norm(a)), " ".join(norm(b))
    return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0


rows, geoms, srcs = [], [], []
for k, (idx, auth, nation, phase, denom, nf, flt) in enumerate(SEL):
    r = I.loc[idx]; L = LAYER[r.url]; it = ITEM[r.url]
    land = land_of(auth)
    parts = {}
    for f in L["feats"]:
        p = f["properties"] or {}
        if flt and not re.search(flt[1], str(p.get(flt[0]) or "")):
            continue
        if not f.get("geometry"):
            continue
        g = fix(to_bng(shape(f["geometry"])))
        nm = str(p.get(nf) or "").strip() if nf else ""
        if NOT_CATCH.search(nm):
            continue
        nm = re.sub(r"\s*\(For [PS]1 entry.*$", "", nm, flags=re.S).strip()
        nm = re.sub(r"\s*[\u2013\u2014]\s*|\s*--\s*", " - ", nm)
        if not nm or nm.lower() in ("none", "null"):
            nm = f"Catchment {len(parts) + 1}"
        parts.setdefault(nm, []).append(g)
    sub = S[(S.nation == nation) & (S[phase] == 1)]
    if denom: sub = sub[sub.rc]
    for nm, gs in parts.items():
        g = unary_union(gs).buffer(0).intersection(land)
        if g.is_empty or g.area < 1e4:
            continue
        x0, y0, x1, y1 = g.bounds
        bb = sub[(sub.x >= x0) & (sub.x <= x1) & (sub.y >= y0) & (sub.y <= y1)]
        bb = bb[shapely.contains_xy(g, bb.x.to_numpy(float), bb.y.to_numpy(float))] if len(bb) else bb
        cand = [(sim(nm, s.name), s) for s in bb.itertuples()]
        best = None
        if cand:
            cand.sort(key=lambda t: -t[0]); best = cand[0][1]; how = "inside" if len(cand) == 1 else "inside, best name of %d" % len(cand)
            if len(cand) > 1 and cand[0][0] < 0.5: how += " (weak name)"
        else:
            c = g.representative_point(); d = np.hypot(sub.x - c.x, sub.y - c.y)
            near = sub.assign(d=d)[d < 3000]
            sc = [(sim(nm, s.name), s) for s in near.itertuples()]
            sc = [t for t in sc if t[0] >= 0.6]
            if sc:
                sc.sort(key=lambda t: -t[0]); best = sc[0][1]; how = "named school within 3 km"
        rows.append(dict(cid=f"C{len(rows):04d}", authority=auth, nation=nation, phase=phase, denominational=denom, catchment=nm,
                         area_km2=round(g.area / 1e6, 3), school_id=best.id if best is not None else "", school_name=best.name if best is not None else "",
                         school_pupils=best.pupils if best is not None else np.nan, match=how if best is not None else "none"))
        geoms.append(g)
    srcs.append(dict(authority=auth, nation=nation, phase=phase, denominational=denom, layer=r.layer, item_title=r.title, owner_account=r.owner,
                     service_url=r.url, licence_note=str(it.get("lic") or "")[:200].strip()))
C = pd.DataFrame(rows)
C.to_csv(os.path.join(DATA, "catchments.csv"), index=False)
pd.DataFrame(srcs).drop_duplicates(["authority", "phase", "denominational"]).to_csv(os.path.join(DATA, "catchment_sources.csv"), index=False)
pickle.dump((C, geoms), open(os.path.join(WORK, "catchments_bng.pkl"), "wb"))
print(C.groupby(["nation", "authority", "phase", "denominational"]).agg(n=("cid", "size"), km2=("area_km2", "sum"), matched=("school_id", lambda s: (s != "").mean())).round(2).to_string())
print("total", len(C), "matched", (C.school_id != "").mean())
print(C.sort_values("area_km2", ascending=False).head(15)[["authority", "phase", "catchment", "area_km2", "school_name", "school_pupils"]].to_string())
