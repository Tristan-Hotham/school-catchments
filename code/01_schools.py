"""Step 1. One table of every open state-funded mainstream and special school in the UK, with its location and roll.

Inputs (gzipped JSON bundles fetched in the browser, see README):
  sc_gias_20261028.json.gz            England: Get Information About Schools, open establishments (DfE, OGL v3)
  sc_catchments_bundle_20261028.json.gz  Wales: Welsh Government maintained schools (DataMapWales, OGL v3);
                                      Scotland: Scottish School Roll and Locations (Scottish Government, OGL v3)
  sc_ni_schools_202526.json.gz        Northern Ireland: DE school level enrolment data 2025/26 (OGL v3),
                                      located by postcode centroid via postcodes.io (ONS Postcode Directory)
Output: data/schools_uk.csv
Run: python3 code/01_schools.py
"""
import os, json
import numpy as np
import pandas as pd
from common import DATA, WORK, load_gz, TO_BNG, TO_ITM, FROM_BNG

rows = []


def add(**k):
    rows.append(k)


# ---------- England (GIAS) ----------
G = load_gz("sc_gias_20261028.json.gz")
g = pd.DataFrame(G["rows"], columns=G["fields"])
STATE = {"Local authority maintained schools", "Academies", "Free Schools", "Special schools"}
g = g[g.EstablishmentTypeGroup.isin(STATE) & (g.Country.fillna("") != "Wales")]
for c in ("NumberOfPupils", "SchoolCapacity", "Easting", "Northing", "StatutoryLowAge", "StatutoryHighAge"):
    g[c] = pd.to_numeric(g[c], errors="coerce")
g = g[g.Easting > 0]
for r in g.itertuples():
    ph = r.PhaseOfEducation
    special = r.EstablishmentTypeGroup == "Special schools" or "special" in str(r.TypeOfEstablishment).lower()
    prim = ph in ("Primary", "Middle deemed primary", "All-through")
    sec = ph in ("Secondary", "Middle deemed secondary", "All-through")
    if ph == "Nursery" or ph == "16 plus":
        continue
    if not (prim or sec or special):
        continue
    lon, lat = FROM_BNG.transform(r.Easting, r.Northing)
    rel = r.ReligiousCharacter if r.ReligiousCharacter not in ("None", "Does not apply", "", None) else ""
    add(id=f"E{r.URN}", nation="England", name=r.EstablishmentName, la=r.LA, phase=ph if not special else "Special",
        primary=int(prim and not special), secondary=int(sec and not special), special=int(special),
        type=r.TypeOfEstablishment, religious=rel, gender=r.Gender, pupils=r.NumberOfPupils, capacity=r.SchoolCapacity,
        age_low=r.StatutoryLowAge, age_high=r.StatutoryHighAge, urban_rural=r.UrbanRural, postcode=r.Postcode,
        lat=round(lat, 6), lon=round(lon, 6), x=round(r.Easting), y=round(r.Northing), source="GIAS 28 Oct 2026")

# ---------- Wales ----------
B = load_gz("sc_catchments_bundle_20261028.json.gz")
for r in B["wales_schools"]["rows"]:
    if r["lon"] is None:
        continue
    sec_ = r["sector"]
    prim = sec_ in ("Cynradd", "Canol")
    sec = sec_ in ("Uwchradd", "Canol")
    special = sec_ == "Arbennig"
    if sec_ == "Meithrin":
        continue
    x, y = TO_BNG.transform(r["lon"], r["lat"])
    rel = r["rel"] if r["rel"] not in ("---", "Not available", None) else ""
    add(id=f"W{r['code']}", nation="Wales", name=r["name"], la=r["la"],
        phase={"Cynradd": "Primary", "Uwchradd": "Secondary", "Canol": "Middle (all-through)", "Arbennig": "Special"}[sec_],
        primary=int(prim), secondary=int(sec), special=int(special), type=r["type"], religious=rel, gender="",
        pupils=pd.to_numeric(r["pupils"], errors="coerce"), capacity=np.nan, age_low=np.nan, age_high=np.nan,
        urban_rural="", postcode=r["pc"], lat=round(r["lat"], 6), lon=round(r["lon"], 6), x=round(x), y=round(y),
        source="Welsh Government address list of schools (DataMapWales)")

# ---------- Scotland ----------
for r in B["scot_schools"]["rows"]:
    if r["centretype"] != "Local Authority" or r["longitude"] is None:
        continue
    t = r["schooltype"]
    rel = r["denomination"] if r["denomination"] != "Non-denominational" else ""
    add(id=f"S{r['seedcode']}" + {"Primary": "P", "Secondary": "S", "Special": "X"}[t], nation="Scotland", name=r["schoolname"], la=r["laname"], phase=t,
        primary=int(t == "Primary"), secondary=int(t == "Secondary"), special=int(t == "Special"), type=t + " (local authority)",
        religious=rel, gender="", pupils=r["pupilroll"], capacity=np.nan, age_low=np.nan, age_high=np.nan,
        urban_rural=r["addrur6desc"] or "", postcode=r["postcode"], lat=round(r["latitude"], 6), lon=round(r["longitude"], 6),
        x=round(r["gridrefeasting"]), y=round(r["gridrefnorthing"]), source="Scottish School Roll and Locations (maps.gov.scot)")

# ---------- Northern Ireland ----------
N = load_gz("sc_ni_schools_202526.json.gz")
PC = N["postcodes"]


def sheet(kind, name):
    rr = N["sheets"][kind][name]
    hi = next(i for i, r in enumerate(rr) if r and r[0] == "DENI ref")
    h = rr[hi]
    return pd.DataFrame([r for r in rr[hi + 1:] if r and r[0] and str(r[0]).strip().isdigit()], columns=h)


UNPLACED = []
for kind, phase in (("primary", "Primary"), ("post", "Post-primary"), ("special", "Special")):
    ref = sheet(kind, "Reference Data")
    en = sheet(kind, "Enrolments" if kind != "special" else "Sex")
    tot = dict(zip(en["DENI ref"].astype(str), pd.to_numeric(en["Total enrolment"], errors="coerce")))
    for r in ref.itertuples(index=False):
        d = dict(zip(ref.columns, r))
        pc = str(d["Postcode"]).strip().upper()
        if pc not in PC:
            print("NI no postcode", d["School name"], pc); UNPLACED.append(d["School name"]); continue
        lon, lat = PC[pc]
        x, y = TO_ITM.transform(lon, lat)
        st = str(d["School Type"])
        add(id=f"N{d['DENI ref']}", nation="Northern Ireland", name=d["School name"], la=d["District Council (2014)"], phase=phase if kind != "post" else st,
            primary=int(kind == "primary"), secondary=int(kind == "post"), special=int(kind == "special"),
            type=f"{st} ({d['Management Type']})", religious="", gender="", pupils=tot.get(str(d["DENI ref"])), capacity=np.nan,
            age_low=np.nan, age_high=np.nan, urban_rural=d["Urban/ Rural"], postcode=pc, lat=round(lat, 6), lon=round(lon, 6),
            x=round(x), y=round(y), source="DE NI school level enrolment data 2025/26; location = postcode centroid")

json.dump({"ni_unplaced": len(UNPLACED), "ni_unplaced_names": UNPLACED}, open(os.path.join(WORK, "schools_meta.json"), "w"))
S = pd.DataFrame(rows)
S["pupils"] = pd.to_numeric(S.pupils, errors="coerce")
for c in ("name", "type", "la"):
    S[c] = S[c].fillna("").astype(str).str.replace("\\s*[\u2013\u2014]\\s*|\\s*--\\s*", " - ", regex=True)
assert S.id.is_unique
S.to_csv(os.path.join(DATA, "schools_uk.csv"), index=False)
print(S.groupby("nation")[["primary", "secondary", "special"]].sum())
print(S.groupby("nation").pupils.agg(["count", "sum"]))
