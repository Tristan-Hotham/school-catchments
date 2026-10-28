"""Step 5. Compact files for the interactive page.

  data/page_schools.json     every school: id, name, council, nation, flags, pupils, lat, lon, zone areas
  data/page_catchments.json  official catchments, simplified to about 25 m, coordinates as delta-coded integers (1e-5 degrees)
  data/page_land.json        land of each nation (for clipping the nearest-school zones) and council borders, simplified
  data/page_places.json      OS Open Names cities, towns and villages (GB) and GeoNames towns (Northern Ireland), for search and labels
  data/hills.png             hill shading for the UK in Web Mercator (alpha = shadow), from AWS Terrain Tiles zoom 7
  data/hills.json            where hills.png sits
Run: python3 code/05_page_data.py
"""
import gzip, io, base64, json, math, os, pickle, zipfile
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape
from PIL import Image
from common import DATA, WORK, OSN, load_gz, to_bng, fix, FROM_BNG, FROM_ITM, TO_ITM, TO_BNG, dump

S = pd.read_csv(os.path.join(DATA, "schools_uk.csv"))
NATS = ["England", "Wales", "Scotland", "Northern Ireland"]
rows = []
for r in S.itertuples():
    rc = "Catholic" in str(r.religious)
    flags = r.primary | (r.secondary << 1) | (r.special << 2) | (int(rc) << 3)
    f = lambda v, d=2: None if pd.isna(v) else round(float(v), d)
    rows.append([r.id, r.name, r.la, NATS.index(r.nation), flags, None if pd.isna(r.pupils) else int(r.pupils), round(r.lat, 5), round(r.lon, 5),
                 f(r.zone_primary_km2), f(r.zone_secondary_km2), f(r.zone_primary_far_km, 1), f(r.zone_secondary_far_km, 1),
                 r.type if isinstance(r.type, str) else "", r.religious if isinstance(r.religious, str) else ""])
dump({"cols": ["id", "name", "la", "nation", "flags(1 primary,2 secondary,4 special,8 Roman Catholic)", "pupils", "lat", "lon",
               "zone_p_km2", "zone_s_km2", "far_p_km", "far_s_km", "type", "religious"], "nations": NATS, "rows": rows},
     os.path.join(DATA, "page_schools.json"))


def enc(g, tr):
    """polygon or multipolygon in projected metres -> list of rings, each [x0,y0,dx,dy,...] in 1e-5 degrees"""
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    out = []
    for p in polys:
        rings = []
        for ring in [p.exterior] + list(p.interiors):
            c = np.asarray(ring.coords)
            lon, lat = tr.transform(c[:, 0], c[:, 1])
            q = np.round(np.column_stack([lon, lat]) * 1e5).astype(np.int64)
            keep = np.ones(len(q), bool); keep[1:] = np.any(np.diff(q, axis=0) != 0, axis=1)
            q = q[keep]
            if len(q) < 4: continue
            d = np.vstack([q[:1], np.diff(q, axis=0)])
            rings.append(d.ravel().tolist())
        if rings: out.append(rings)
    return out


C, CG = pickle.load(open(os.path.join(WORK, "catchments_bng.pkl"), "rb"))
C = pd.read_csv(os.path.join(DATA, "catchments.csv")).fillna({"school_id": "", "school_name": ""})
feats = []
for i, r in C.iterrows():
    g = CG[i].simplify(25, preserve_topology=True)
    if g.is_empty: continue
    feats.append([r.cid, r.authority, ["primary", "secondary"].index(r.phase), int(r.denominational), (r.catchment.title().replace("Ce ", "CE ").replace("Rc ", "RC ").replace("'S ", "'s ") if r.catchment.isupper() else r.catchment)[:90], round(r.area_km2, 2),
                  r.school_id, None if pd.isna(r.nearest_agreement) else round(float(r.nearest_agreement), 2), enc(g, FROM_BNG)])
dump({"cols": ["cid", "authority", "phase(0 primary,1 secondary)", "denominational", "name", "km2", "school_id", "nearest_agreement", "polygons"], "rows": feats},
     os.path.join(DATA, "page_catchments.json"))

B = load_gz("sc_catchments_bundle_20261028.json.gz")
land, borders = {}, []
for f in B["lad"]["features"]:
    cd = f["properties"]["LAD24CD"]; nat = {"E": "England", "W": "Wales", "S": "Scotland", "N": "Northern Ireland"}[cd[0]]
    tr = TO_ITM if nat == "Northern Ireland" else TO_BNG
    g = fix(to_bng(shape(f["geometry"]), tr))
    land.setdefault(nat, []).append(g)
    borders.append((f["properties"]["LAD24NM"], nat, g))
L = {}
for nat, gs in land.items():
    u = shapely.union_all(gs).simplify(120, preserve_topology=True)
    u = shapely.union_all([p for p in (u.geoms if u.geom_type == "MultiPolygon" else [u]) if p.area > 2e5])  # drop specks under 0.2 km2
    L[nat] = enc(u, FROM_ITM if nat == "Northern Ireland" else FROM_BNG)
BL = []
for nm, nat, g in borders:
    s = g.simplify(150, preserve_topology=True)
    s = shapely.union_all([p for p in (s.geoms if s.geom_type == "MultiPolygon" else [s]) if p.area > 5e5])
    if s.is_empty: continue
    BL.append([nm, NATS.index(nat), enc(s, FROM_ITM if nat == "Northern Ireland" else FROM_BNG)])
dump({"land": L, "councils": BL}, os.path.join(DATA, "page_land.json"))

# places: OS Open Names (GB) and GeoNames (Northern Ireland)
osn = pd.read_csv(OSN, sep="\t", dtype=str, keep_default_na=False, quoting=3)
osn = osn[(osn.type == "populatedPlace") & osn.local_type.isin(["City", "Town", "Village"])]
rank = {"City": 3, "Town": 2, "Village": 1}
P = [[r.name1, r.county or r.district, round(float(r.lat), 4), round(float(r.lon), 4), rank[r.local_type]] for r in osn.itertuples()]
with zipfile.ZipFile("/home/claude/hist/_data13/cities15000.zip") as z:
    gn = pd.read_csv(io.BytesIO(z.read("cities15000.txt")), sep="\t", header=None, dtype=str, keep_default_na=False, quoting=3)
gn.columns = ["id", "name", "ascii", "alt", "lat", "lon", "fcl", "fcode", "cc", "cc2", "a1", "a2", "a3", "a4", "pop", "elev", "dem", "tz", "mod"]
for r in gn[(gn.cc == "GB") & (gn.a1 == "NIR") & (gn.fcode != "PPLX")].itertuples():
    P.append([r.name, "Northern Ireland", round(float(r.lat), 4), round(float(r.lon), 4), 3 if int(r.pop) > 60000 else 2])
dump({"cols": ["name", "county", "lat", "lon", "rank(3 city,2 town,1 village)"], "rows": P}, os.path.join(DATA, "page_places.json"))

# hill shade (Web Mercator image over the UK), alpha = depth of shadow
T = json.load(gzip.open("/home/claude/hist/_data13/terrarium_tiles.json.gz"))
x0, x1, y0, y1 = 58, 69, 34, 45
dem = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.float32)
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        k = f"7/{x}/{y}"
        if k in T["tiles"]:
            a = np.asarray(Image.open(io.BytesIO(base64.b64decode(T["tiles"][k]))).convert("RGB")).astype(np.float32)
            dem[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
del T
n7 = 256 * 2 ** 7
cell = 2 * math.pi * 6371008.8 / n7 * 0.58
z = np.maximum(dem, 0)
gy, gx = np.gradient(z, cell)
slope = np.arctan(np.hypot(gx, gy) * 3.2); aspect = np.arctan2(-gx, gy)
az, alt = np.radians(315), np.radians(45)
sh = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
shade = np.clip(1 - sh / np.sin(alt), 0, 1)          # 0 flat or lit, 1 deep shadow
light = np.clip(sh / np.sin(alt) - 1, 0, 1)            # sunlit slopes
# crop to the UK and upsample 2x for a smoother look
lon_px = lambda lon: (lon + 180) / 360 * n7 - x0 * 256
lat_px = lambda lat: (1 - math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) / math.pi) / 2 * n7 - y0 * 256
LON0, LON1, LAT0, LAT1 = -8.8, 2.0, 49.8, 61.0
c0, c1 = int(lon_px(LON0)), int(math.ceil(lon_px(LON1))); r0, r1 = int(lat_px(LAT1)), int(math.ceil(lat_px(LAT0)))
sd = shade[r0:r1, c0:c1]; li = light[r0:r1, c0:c1]
img = np.zeros(sd.shape + (4,), np.uint8)
img[..., 3] = np.clip(sd * 255 * 1.4 + li * 60, 0, 255).astype(np.uint8)
img[..., 0:3] = np.where((li > sd)[..., None], 255, 0).astype(np.uint8)   # white for lit, black for shadow
# keep the shading to UK land: rasterise the nations' land onto the image grid
from PIL import ImageDraw
Hh, Ww = img.shape[:2]
msk = Image.new("L", (Ww, Hh), 0); dr = ImageDraw.Draw(msk)
lon_of = lambda px: (px + x0 * 256) / n7 * 360 - 180
def topx(lon, lat):
    return lon_px(lon) - c0, lat_px(lat) - r0
for nat, gs in land.items():
    u = shapely.union_all(gs).buffer(2000).simplify(500)
    tr = FROM_ITM if nat == "Northern Ireland" else FROM_BNG
    for p in (u.geoms if u.geom_type == "MultiPolygon" else [u]):
        c = np.asarray(p.exterior.coords); lo, la_ = tr.transform(c[:, 0], c[:, 1])
        dr.polygon([topx(a, b) for a, b in zip(lo, la_)], fill=255)
img[..., 3] = (img[..., 3].astype(np.uint16) * (np.asarray(msk) > 0)).astype(np.uint8)
la = np.dstack([img[..., 0], (img[..., 3] // 8) * 8])   # grey (0 shadow, 255 light) and alpha, alpha in 32 steps to compress
Image.fromarray(la, "LA").save(os.path.join(DATA, "hills.png"), optimize=True)
inv_lon = lambda px: (px + x0 * 256) / n7 * 360 - 180
inv_lat = lambda py: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (py + y0 * 256) / n7))))
json.dump({"north": inv_lat(r0), "south": inv_lat(r1), "west": inv_lon(c0), "east": inv_lon(c1)}, open(os.path.join(DATA, "hills.json"), "w"))
for f in ("page_schools.json", "page_catchments.json", "page_land.json", "page_places.json", "hills.png"):
    print(f, round(os.path.getsize(os.path.join(DATA, f)) / 1e6, 2), "MB")
