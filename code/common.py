"""Shared paths and helpers for the school-catchments project."""
import gzip, json, os
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
RAW = os.environ.get("SC_RAW", "/home/claude/hist/_data18/school-catchments")
DATA = os.path.join(ROOT, "data")
WORK = os.environ.get("SC_WORK", os.path.join(RAW, "work"))
OSN = os.environ.get("OSNAMES", "/home/claude/hist/osnames_gb.tsv")
os.makedirs(DATA, exist_ok=True); os.makedirs(WORK, exist_ok=True)

DOI = "10.5281/zenodo.23748248"
SLUG = "school-catchments"
PAGE = f"https://maps.tristanhotham.com/{SLUG}/"
REPO = f"https://github.com/Tristan-Hotham/{SLUG}"
BLOG = f"https://blog.tristanhotham.com/2026/10/28/{SLUG}/"

# British National Grid for areas and distances in GB; Irish Transverse Mercator for Northern Ireland
TO_BNG = Transformer.from_crs(4326, 27700, always_xy=True)
TO_ITM = Transformer.from_crs(4326, 2157, always_xy=True)
FROM_BNG = Transformer.from_crs(27700, 4326, always_xy=True)
FROM_ITM = Transformer.from_crs(2157, 4326, always_xy=True)


def proj_for(nation):
    return (TO_ITM, FROM_ITM) if nation == "Northern Ireland" else (TO_BNG, FROM_BNG)


def load_gz(name):
    return json.load(gzip.open(os.path.join(RAW, name), "rt", encoding="utf-8"))


def dump(obj, path, **kw):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), **kw)


def to_bng(g, tr=None):
    """Project a WGS84 shapely geometry to British National Grid (or another transformer)."""
    import numpy as np, shapely
    t = tr or TO_BNG
    return shapely.transform(g, lambda a: np.column_stack(t.transform(a[:, 0], a[:, 1])))


def fix(g):
    """Repair a polygon geometry and keep only its polygon parts."""
    import shapely
    from shapely.geometry import MultiPolygon, Polygon
    h = g.buffer(0)
    if h.is_empty and not g.is_empty:
        h = shapely.make_valid(g)
    if h.geom_type == "GeometryCollection":
        ps = [x for x in h.geoms if x.geom_type in ("Polygon", "MultiPolygon")]
        h = shapely.union_all(ps) if ps else Polygon()
    return h
