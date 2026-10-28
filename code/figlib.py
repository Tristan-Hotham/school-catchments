"""Shared drawing helpers (matplotlib) for the header, the paper and blog figures, and the Reddit collage.

Fonts: FONT_DIR holding Fraunces, Source Serif 4 and IBM Plex Mono (from github.com/google/fonts);
otherwise matplotlib's defaults are used. Maps are drawn in British National Grid; Northern Ireland,
measured in Irish Transverse Mercator, is re-projected to the same grid for drawing only.
"""
import json, os, pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as MPoly
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import pandas as pd
import shapely
from pyproj import Transformer
from common import DATA, WORK, ROOT

FD = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts")
DISP = None
if os.path.isdir(FD):
    for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
        if os.path.exists(os.path.join(FD, f)): fm.fontManager.addfont(os.path.join(FD, f))
    DISP = fm.FontProperties(fname=os.path.join(FD, "FrauncesVar.ttf"), weight=900)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
BG, FG, MUT, RULE, LAND, SEA = "#F6F3EA", "#1B2430", "#5E6570", "#DCD5C3", "#E9E5DA", "#F6F3EA"
NAVY, PENCIL, RED, GREEN = "#1F3A5F", "#D99A1E", "#B4412F", "#3F7D5A"
AREA_COL = ["#FBF3D6", "#F2DE9C", "#D8C77C", "#9DB38A", "#5E9283", "#3A6A82", "#22406A"]
AREA_BRK = {"primary": [1, 3, 10, 30, 100, 300], "secondary": [5, 15, 50, 150, 500, 1500]}
AG_COL = ["#B4412F", "#E09C72", "#EFE3C4", "#9CC3A6", "#3F7D5A"]
NATS = ["England", "Wales", "Scotland", "Northern Ireland"]
NCOL = {"England": "#B4412F", "Wales": "#3F7D5A", "Scotland": "#1F3A5F", "Northern Ireland": "#D99A1E"}
plt.rcParams.update({"font.family": SER, "font.size": 12, "axes.edgecolor": MUT, "axes.labelcolor": FG, "xtick.color": MUT, "ytick.color": MUT,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.facecolor": BG, "figure.facecolor": BG, "axes.facecolor": BG})
R = json.load(open(os.path.join(DATA, "results.json")))
ITM2BNG = Transformer.from_crs(2157, 27700, always_xy=True)


def cls(v, brk):
    return int(np.searchsorted(brk, v, side="right"))


def to_gb(g, nat):
    if nat != "Northern Ireland": return g
    return shapely.transform(g, lambda a: np.column_stack(ITM2BNG.transform(a[:, 0], a[:, 1])))


def geom_path(g):
    verts, codes = [], []
    polys = [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
    for p in polys:
        for ring in [p.exterior] + list(p.interiors):
            c = np.asarray(ring.coords)
            if len(c) < 3: continue
            verts.append(c); codes.append([Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY])
    if not verts: return None
    return Path(np.vstack(verts), np.concatenate(codes))


def draw(ax, g, **kw):
    p = geom_path(g)
    if p is not None: ax.add_patch(PathPatch(p, **kw))


_Z = _C = _LAND = None


def zones():
    global _Z
    if _Z is None: _Z = pickle.load(open(os.path.join(WORK, "zones.pkl"), "rb"))
    return _Z


def catchments():
    global _C
    if _C is None:
        C, G = pickle.load(open(os.path.join(WORK, "catchments_bng.pkl"), "rb"))
        C = pd.read_csv(os.path.join(DATA, "catchments.csv")).fillna({"school_id": ""})
        _C = (C, G)
    return _C


def land():
    """nation -> land geometry in BNG (from the zones, which tile the land)"""
    global _LAND
    if _LAND is None:
        Z = zones(); _LAND = {}
        for n in NATS:
            _LAND[n] = to_gb(shapely.union_all([g for g in Z[(n, "secondary")][1] if not g.is_empty]).simplify(200), n)
    return _LAND


def schools():
    return pd.read_csv(os.path.join(DATA, "schools_uk.csv"))


def zone_map(ax, phase, official=True, edge=None, lw=0.12, alpha_zone=0.78, extent=None, simplify=150, denom=0):
    """nearest-school zones coloured by area class, with official catchments (non-denominational) solid on top"""
    Z = zones(); S = schools().set_index("id")
    for n in NATS:
        ids, gs = Z[(n, phase)]
        for sid, g in zip(ids, gs):
            if g.is_empty: continue
            if extent is not None:
                b = g.bounds
                if b[2] < extent[0] or b[0] > extent[1] or b[3] < extent[2] or b[1] > extent[3]: continue
            a = S.at[sid, f"zone_{phase}_km2"]
            draw(ax, to_gb(g.simplify(simplify), n), facecolor=AREA_COL[cls(a, AREA_BRK[phase])], edgecolor=edge or "white", lw=lw, alpha=alpha_zone)
    if official:
        C, G = catchments()
        for i, r in C.iterrows():
            if r.phase != phase or r.denominational != denom: continue
            g = G[i]
            if extent is not None:
                b = g.bounds
                if b[2] < extent[0] or b[0] > extent[1] or b[3] < extent[2] or b[1] > extent[3]: continue
            draw(ax, g.simplify(simplify), facecolor=AREA_COL[cls(r.area_km2, AREA_BRK[phase])], edgecolor=FG, lw=lw * 2.2, alpha=1)


def frame(ax, xlim=(-10000, 670000), ylim=(-10000, 1220000)):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.axis("off")


def area_legend(ax, phase, x, y, w=0.05, h=0.018, fs=9, title=None, transform=None, ends=False):
    brk = AREA_BRK[phase]
    labs = [f"<{brk[0]}"] + [f"{brk[i]:,}" for i in range(len(brk))]
    tr = transform or ax.transAxes
    for i, c in enumerate(AREA_COL):
        ax.add_patch(plt.Rectangle((x + i * w, y), w, h, facecolor=c, edgecolor="none", transform=tr, clip_on=False))
    if ends:
        ax.text(x, y - h * .5, f"under {brk[0]:,}", ha="left", va="top", family=MONO, fontsize=fs, color=MUT, transform=tr)
        ax.text(x + len(AREA_COL) * w, y - h * .5, f"{brk[-1]:,} or more", ha="right", va="top", family=MONO, fontsize=fs, color=MUT, transform=tr)
    else:
      for i in range(len(brk)):
        ax.text(x + (i + 1) * w, y - h * .5, f"{brk[i]:,}", ha="center", va="top", family=MONO, fontsize=fs, color=MUT, transform=tr)
    if title: ax.text(x, y + h * 1.6, title, family=MONO, fontsize=fs, color=FG, transform=tr)
