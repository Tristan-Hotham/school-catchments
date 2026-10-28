"""Step 4. Nearest-school zones, distances and every headline number.

Nearest-school zones: for each nation and phase, a Voronoi cell around every open mainstream state school
(special schools excluded), clipped to the nation's land (ONS LAD Dec 2024 BGC). A cell is the land that is
closer, in a straight line, to that school than to any other school of the same phase in the same nation.
These are NOT catchments: they ignore roads, admissions rules, faith schools' wider areas and parental choice.
Agreement: for every official catchment linked to a school, points on a 200 m grid inside it are tested:
is the linked school the nearest school of its kind (Roman Catholic schools for denominational catchments,
otherwise all mainstream schools of the phase except Roman Catholic ones in Scotland)?
Distance: a 1 km grid over all UK land and every OS Open Names village and hamlet in Great Britain, with
the straight-line distance to the nearest mainstream primary and secondary school (any nation).
Outputs: data/schools_uk.csv (zone columns added), data/zones_summary.csv, data/settlements_distance.csv,
data/la_summary.csv, work/zones.pkl, data/results.json
Run: python3 code/04_analyse.py
"""
import os, json, pickle
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape, MultiPoint, Point
from shapely.strtree import STRtree
from scipy.spatial import cKDTree
from common import DATA, WORK, OSN, load_gz, to_bng, fix, TO_BNG, TO_ITM

S = pd.read_csv(os.path.join(DATA, "schools_uk.csv"))
S["rc"] = S.religious.fillna("").str.contains("Catholic")
B = load_gz("sc_catchments_bundle_20261028.json.gz")
NAT = {"E": "England", "W": "Wales", "S": "Scotland", "N": "Northern Ireland"}
LADS = []
for f in B["lad"]["features"]:
    cd = f["properties"]["LAD24CD"]; nat = NAT[cd[0]]
    g = shape(f["geometry"])
    LADS.append(dict(code=cd, name=f["properties"]["LAD24NM"], nation=nat, g=fix(to_bng(g, TO_ITM if nat == "Northern Ireland" else TO_BNG))))
LAND = {n: shapely.union_all([l["g"] for l in LADS if l["nation"] == n]) for n in NAT.values()}
R = {"meta": {"retrieved": "2026-10-28"}}
R.update(json.load(open(os.path.join(WORK, "schools_meta.json"))))


def xy(df):
    return df[["x", "y"]].to_numpy(float)


# ---------- nearest-school zones ----------
zones = {}
for nat in NAT.values():
    parts = [l for l in LADS if l["nation"] == nat]
    tree = STRtree([l["g"] for l in parts])
    for ph in ("primary", "secondary"):
        sub = S[(S.nation == nat) & (S[ph] == 1)].copy()
        P = xy(sub).copy()
        # separate schools that share a site by a metre so each gets a cell
        seen = {}
        for i, (a, b) in enumerate(P):
            k = (round(a), round(b)); n = seen.get(k, 0); seen[k] = n + 1
            if n: P[i] += [n * 1.0, 0]
        vor = shapely.voronoi_polygons(MultiPoint(P), extend_to=LAND[nat].envelope.buffer(50000), ordered=True)
        cells = list(vor.geoms)
        area, far, gl = [], [], []
        for i, c in enumerate(cells):
            hits = tree.query(c)
            g = shapely.union_all([c.intersection(parts[j]["g"]) for j in hits]) if len(hits) else shapely.Polygon()
            g = fix(g) if not g.is_empty else g
            gl.append(g)
            area.append(g.area / 1e6)
            if g.is_empty: far.append(0.0)
            else:
                co = shapely.get_coordinates(g)
                far.append(float(np.hypot(co[:, 0] - P[i, 0], co[:, 1] - P[i, 1]).max() / 1000))
        S.loc[sub.index, f"zone_{ph}_km2"] = np.round(area, 3)
        S.loc[sub.index, f"zone_{ph}_far_km"] = np.round(far, 2)
        zones[(nat, ph)] = (list(sub.id), gl)
        print(nat, ph, len(sub), "land km2", round(LAND[nat].area / 1e6), "zones km2", round(sum(area)))
pickle.dump(zones, open(os.path.join(WORK, "zones.pkl"), "wb"))
S.drop(columns=["rc"]).to_csv(os.path.join(DATA, "schools_uk.csv"), index=False)

# ---------- schools and zones summaries ----------
main = lambda ph: S[(S[ph] == 1)]
R["schools"] = {nat: dict(primary=int(((S.nation == nat) & (S.primary == 1)).sum()), secondary=int(((S.nation == nat) & (S.secondary == 1)).sum()),
                          special=int(((S.nation == nat) & (S.special == 1)).sum()), pupils=int(S[S.nation == nat].pupils.sum()),
                          land_km2=round(LAND[nat].area / 1e6)) for nat in NAT.values()}
R["schools"]["UK"] = {k: sum(R["schools"][n][k] for n in NAT.values()) for k in ("primary", "secondary", "special", "pupils", "land_km2")}
R["schools"]["all_n"] = int(len(S))
R["schools"]["scot_dept_rows"] = int(S[S.nation == "Scotland"].id.str[:-1].duplicated(keep=False).sum())
R["schools"]["distinct_n"] = int(len(S) - S[S.nation == "Scotland"].id.str[:-1].duplicated().sum())
R["schools"]["all_through_e"] = int(((S.primary == 1) & (S.secondary == 1)).sum())
zs = []
for nat in NAT.values():
    for ph in ("primary", "secondary"):
        sub = S[(S.nation == nat) & (S[ph] == 1)]
        a = sub[f"zone_{ph}_km2"]
        zs.append(dict(nation=nat, phase=ph, schools=len(sub), land_km2=round(LAND[nat].area / 1e6), mean_km2=round(a.mean(), 2), median_km2=round(a.median(), 2),
                       max_km2=round(a.max(), 1), p90_km2=round(a.quantile(.9), 1), pupils_median=sub.pupils.median()))
Z = pd.DataFrame(zs); Z.to_csv(os.path.join(DATA, "zones_summary.csv"), index=False)
R["zones"] = {f"{r.nation}|{r.phase}": r._asdict() for r in Z.itertuples(index=False)}
cols = ["id", "name", "la", "nation", "pupils", "lat", "lon"]
for ph in ("primary", "secondary"):
    t = S[S[ph] == 1].sort_values(f"zone_{ph}_km2", ascending=False)
    R[f"biggest_zones_{ph}"] = [dict(**{c: (None if pd.isna(r[c]) else r[c]) for c in cols}, km2=round(r[f"zone_{ph}_km2"], 1), far_km=r[f"zone_{ph}_far_km"]) for _, r in t.head(15).iterrows()]
    R[f"biggest_zones_{ph}_by_nation"] = {nat: dict(**{c: (None if pd.isna(r[c]) else r[c]) for c in cols}, km2=round(r[f"zone_{ph}_km2"], 1), far_km=r[f"zone_{ph}_far_km"])
                                          for nat in NAT.values() for _, r in t[t.nation == nat].head(1).iterrows()}
    R[f"smallest_zone_{ph}"] = {c: (None if pd.isna(v) else v) for c, v in t.iloc[-1][cols + [f"zone_{ph}_km2"]].items()}

# ---------- biggest and smallest schools ----------
for ph in ("primary", "secondary"):
    t = S[(S[ph] == 1) & ~((S.primary == 1) & (S.secondary == 1))].sort_values("pupils", ascending=False)
    R[f"biggest_{ph}"] = [dict(**{c: (None if pd.isna(r[c]) else r[c]) for c in cols + ["type"]}) for _, r in t.head(12).iterrows()]
    R[f"biggest_{ph}_by_nation"] = {nat: {c: (None if pd.isna(v) else v) for c, v in t[t.nation == nat].iloc[0][cols].items()} for nat in NAT.values()}
    R[f"median_pupils_{ph}"] = {nat: float(t[t.nation == nat].pupils.median()) for nat in NAT.values()}
    tt = t[t.pupils > 0]
    R[f"tiny_{ph}"] = {nat: int(((tt.nation == nat) & (tt.pupils < (25 if ph == "primary" else 150))).sum()) for nat in NAT.values()}
    R[f"smallest_{ph}"] = [dict(**{c: (None if pd.isna(r[c]) else r[c]) for c in cols}) for _, r in tt.sort_values("pupils").head(8).iterrows()]
at = S[(S.primary == 1) & (S.secondary == 1)].sort_values("pupils", ascending=False)
R["biggest_all_through"] = [dict(**{c: (None if pd.isna(r[c]) else r[c]) for c in cols}) for _, r in at.head(5).iterrows()]

# ---------- official catchments: size, coverage, agreement ----------
C, CG = pickle.load(open(os.path.join(WORK, "catchments_bng.pkl"), "rb"))
C["area_km2"] = C.area_km2.astype(float)
rng = np.random.default_rng(1)
agree, npts = [], []
trees = {}
for i, r in C.iterrows():
    if not r.school_id:
        agree.append(np.nan); npts.append(0); continue
    key = (r.nation, r.phase, r.denominational)
    if key not in trees:
        sub = S[(S.nation == r.nation) & (S[r.phase] == 1)]
        if r.denominational: sub = sub[sub.religious.fillna("").str.contains("Catholic")]
        elif r.nation == "Scotland": sub = sub[~sub.religious.fillna("").str.contains("Catholic")]
        trees[key] = (cKDTree(xy(sub)), list(sub.id))
    tr, ids = trees[key]
    g = CG[i]; x0, y0, x1, y1 = g.bounds
    step = max(200, np.sqrt(g.area / 3000))
    gx, gy = np.meshgrid(np.arange(x0 + step / 2, x1, step), np.arange(y0 + step / 2, y1, step))
    gx, gy = gx.ravel(), gy.ravel()
    ins = shapely.contains_xy(g, gx, gy)
    gx, gy = gx[ins], gy[ins]
    if len(gx) == 0:
        c = g.representative_point(); gx, gy = np.array([c.x]), np.array([c.y])
    _, j = tr.query(np.column_stack([gx, gy]))
    agree.append(float(np.mean([ids[k] == r.school_id for k in j]))); npts.append(len(gx))
C["nearest_agreement"] = np.round(agree, 3)
C["grid_points"] = npts
C.to_csv(os.path.join(DATA, "catchments.csv"), index=False)
m = C[C.school_id != ""]
R["catchments"] = dict(n=int(len(C)), authorities=int(C.authority.nunique()), matched=int(len(m)), matched_share=round(len(m) / len(C), 3),
                       by_nation={n: dict(authorities=int(g.authority.nunique()), n=int(len(g)), km2=round(g.area_km2.sum())) for n, g in C.groupby("nation")},
                       authorities_list={n: sorted(g.authority.unique()) for n, g in C.groupby("nation")})
w = lambda g: float(np.average(g.nearest_agreement, weights=g.area_km2))
R["agreement"] = dict(all=round(w(m), 3), primary=round(w(m[m.phase == "primary"]), 3), secondary=round(w(m[m.phase == "secondary"]), 3),
                      nondenom=round(w(m[m.denominational == 0]), 3), denom=round(w(m[m.denominational == 1]), 3),
                      median_catchment=round(float(m.nearest_agreement.median()), 3), share_below_half=round(float((m.nearest_agreement < .5).mean()), 3),
                      by_authority={a: round(w(g), 3) for a, g in m.groupby("authority")})
for ph in ("primary", "secondary"):
    t = C[(C.phase == ph) & (C.denominational == 0)].sort_values("area_km2", ascending=False)
    R[f"biggest_catchments_{ph}"] = [dict(authority=r.authority, nation=r.nation, catchment=r.catchment, km2=round(r.area_km2, 1), school=r.school_name or None,
                                          pupils=None if pd.isna(r.school_pupils) else r.school_pupils, school_id=r.school_id or None) for r in t.head(12).itertuples()]
    R[f"catchment_median_km2_{ph}"] = {n: round(float(g.area_km2.median()), 2) for n, g in t.groupby("nation")}
    R[f"catchment_median_km2_{ph}_by_auth"] = {a: round(float(g.area_km2.median()), 2) for a, g in t.groupby("authority")}
    t2 = C[(C.phase == ph) & (C.denominational == 1)].sort_values("area_km2", ascending=False)
    R[f"biggest_denom_{ph}"] = [dict(authority=r.authority, catchment=r.catchment, km2=round(r.area_km2, 1)) for r in t2.head(5).itertuples()]
# Highland compared with its nearest zones
hz = S[(S.la == "Highland") & (S.primary == 1)]
R["highland"] = dict(primary_schools=int(len(hz)), secondary_schools=int(((S.la == "Highland") & (S.secondary == 1)).sum()),
                     land_km2=round(shapely.union_all([l["g"] for l in LADS if l["name"] == "Highland"]).area / 1e6),
                     catch_primary_n=int(((C.authority == "Highland") & (C.phase == "primary")).sum()),
                     catch_secondary_n=int(((C.authority == "Highland") & (C.phase == "secondary")).sum()))

# ---------- distance to the nearest school ----------
allP = {ph: S[S[ph] == 1] for ph in ("primary", "secondary")}
GB = S.nation != "Northern Ireland"
KD = {}
for ph in ("primary", "secondary"):
    KD[("GB", ph)] = cKDTree(xy(allP[ph][allP[ph].nation != "Northern Ireland"]))
    KD[("NI", ph)] = cKDTree(xy(allP[ph][allP[ph].nation == "Northern Ireland"]))
grid = []
for nat in NAT.values():
    land = LAND[nat]; x0, y0, x1, y1 = land.bounds
    gx, gy = np.meshgrid(np.arange(x0 + 500, x1, 1000), np.arange(y0 + 500, y1, 1000)); gx, gy = gx.ravel(), gy.ravel()
    ins = shapely.contains_xy(land, gx, gy); gx, gy = gx[ins], gy[ins]
    k = "NI" if nat == "Northern Ireland" else "GB"
    dp = KD[(k, "primary")].query(np.column_stack([gx, gy]))[0] / 1000
    ds = KD[(k, "secondary")].query(np.column_stack([gx, gy]))[0] / 1000
    grid.append(dict(nation=nat, cells=int(len(gx)), prim_gt5=round(float((dp > 5).mean()), 3), prim_gt10=round(float((dp > 10).mean()), 3),
                     sec_gt10=round(float((ds > 10).mean()), 3), sec_gt20=round(float((ds > 20).mean()), 3), prim_max=round(float(dp.max()), 1), sec_max=round(float(ds.max()), 1),
                     prim_median=round(float(np.median(dp)), 2), sec_median=round(float(np.median(ds)), 2)))
R["land_distance"] = {g["nation"]: g for g in grid}

osn = pd.read_csv(OSN, sep="\t", dtype=str, keep_default_na=False, quoting=3)
osn = osn[(osn.type == "populatedPlace") & osn.local_type.isin(["City", "Town", "Village", "Hamlet"])].copy()
osn["x"] = osn.x.astype(float); osn["y"] = osn.y.astype(float)
for ph in ("primary", "secondary"):
    d, j = KD[("GB", ph)].query(osn[["x", "y"]].to_numpy())
    osn[f"{ph}_km"] = np.round(d / 1000, 2)
    sub = allP[ph][allP[ph].nation != "Northern Ireland"].reset_index(drop=True)
    osn[f"{ph}_school"] = sub.name.to_numpy()[j]; osn[f"{ph}_school_id"] = sub.id.to_numpy()[j]
osn["name"] = osn.name1
gbl = shapely.union_all([LAND["England"], LAND["Wales"], LAND["Scotland"]])
mainland = max(gbl.geoms, key=lambda q: q.area)
osn["island"] = (~shapely.contains_xy(mainland, osn.x.to_numpy(), osn.y.to_numpy())).astype(int)
osn["nation"] = osn.country
O = osn[["name", "local_type", "county", "nation", "island", "lat", "lon", "x", "y", "primary_km", "primary_school", "primary_school_id", "secondary_km", "secondary_school", "secondary_school_id"]]
O.to_csv(os.path.join(DATA, "settlements_distance.csv"), index=False)
vh = O[O.local_type.isin(["Village", "Hamlet"])]
R["settlements"] = dict(n=int(len(O)), villages_hamlets=int(len(vh)), villages=int((O.local_type == "Village").sum()), hamlets=int((O.local_type == "Hamlet").sum()),
                        by_nation={n: dict(n=int(len(g)), prim_gt5=round(float((g.primary_km > 5).mean()), 3), prim_gt5_n=int((g.primary_km > 5).sum()),
                                           sec_gt10=round(float((g.secondary_km > 10).mean()), 3), sec_gt15_n=int((g.secondary_km > 15).sum()),
                                           prim_median=round(float(g.primary_km.median()), 2), sec_median=round(float(g.secondary_km.median()), 2))
                                   for n, g in vh.groupby("nation")},
                        villages_with_primary_within_2km=round(float((O[O.local_type == "Village"].primary_km <= 2).mean()), 3),
                        farthest_primary=[dict(name=r.name, county=r.county, nation=r.nation, km=r.primary_km, school=r.primary_school) for r in vh.sort_values("primary_km", ascending=False).head(10).itertuples()],
                        farthest_secondary=[dict(name=r.name, county=r.county, nation=r.nation, km=r.secondary_km, school=r.secondary_school, island=r.island, lat=float(r.lat), lon=float(r.lon)) for r in vh.sort_values("secondary_km", ascending=False).head(10).itertuples()],
                        farthest_secondary_mainland=[dict(name=r.name, county=r.county, km=r.secondary_km, school=r.secondary_school, lat=float(r.lat), lon=float(r.lon)) for r in vh[vh.island == 0].sort_values("secondary_km", ascending=False).head(5).itertuples()],
                        farthest_primary_mainland=[dict(name=r.name, county=r.county, km=r.primary_km, school=r.primary_school) for r in vh[vh.island == 0].sort_values("primary_km", ascending=False).head(5).itertuples()],
                        island_share=round(float(vh.island.mean()), 3),
                        town_farthest_secondary=[dict(name=r.name, county=r.county, km=r.secondary_km, school=r.secondary_school) for r in O[O.local_type == "Town"].sort_values("secondary_km", ascending=False).head(5).itertuples()])
R["distance_bins"] = {ph: {n: [int(x) for x in np.histogram(g[f"{ph}_km"], bins=[0, 1, 2, 3, 5, 10, 20, 1000])[0]] for n, g in vh.groupby("nation")} for ph in ("primary", "secondary")}
R["distance_bin_edges"] = [0, 1, 2, 3, 5, 10, 20]

# ---------- by local authority ----------
la = []
for l in LADS:
    pass
S2 = pd.read_csv(os.path.join(DATA, "schools_uk.csv"))
for (nat, a), g in S2.groupby(["nation", "la"]):
    la.append(dict(nation=nat, la=a, primary=int(g.primary.sum()), secondary=int(g.secondary.sum()), pupils=int(g.pupils.sum()),
                   median_primary_pupils=float(g[g.primary == 1].pupils.median()) if g.primary.sum() else np.nan,
                   median_primary_zone_km2=round(float(g[g.primary == 1].zone_primary_km2.median()), 2) if g.primary.sum() else np.nan,
                   median_secondary_zone_km2=round(float(g[g.secondary == 1].zone_secondary_km2.median()), 2) if g.secondary.sum() else np.nan,
                   has_catchments=int(a in set(C.authority))))
LA = pd.DataFrame(la); LA.to_csv(os.path.join(DATA, "la_summary.csv"), index=False)
R["la_n"] = int(len(LA))
cov = []
for a, g in C.groupby("authority"):
    cov.append(dict(authority=a, nation=g.nation.iloc[0], primary=int(((g.phase == "primary") & (g.denominational == 0)).sum()),
                    secondary=int(((g.phase == "secondary") & (g.denominational == 0)).sum()), denom=int((g.denominational == 1).sum()),
                    km2=round(float(g[(g.denominational == 0)].groupby("phase").area_km2.sum().max()))))
R["coverage"] = sorted(cov, key=lambda c: (["Scotland", "England", "Wales"].index(c["nation"]), c["authority"]))
R["lad_km2"] = {l["name"]: round(l["g"].area / 1e6) for l in LADS}


def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating, float)): return None if np.isnan(o) else float(o)
    return o


json.dump(clean(R), open(os.path.join(DATA, "results.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(clean({k: R[k] for k in ("schools", "agreement", "land_distance", "settlements", "catchments")}), indent=1)[:6000])
