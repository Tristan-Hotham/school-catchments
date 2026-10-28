"""Reddit collage (2400 x 3000 px) for the school catchments study. Run from this folder: python3 collage.py"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
from figlib import *

OUT = os.path.dirname(os.path.abspath(__file__))
PAPER = "#F7F3E6"
S = schools()
fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=PAPER)
# faint exercise-book ruling and margin line
for y in np.arange(0.02, 1.0, 0.0125):
    fig.add_artist(plt.Line2D([0, 1], [y, y], color="#C9D8E6", lw=.5, alpha=.55, zorder=0))
fig.add_artist(plt.Line2D([0.025, 0.025], [0, 1], color="#E2A6A0", lw=1.0, alpha=.8, zorder=0))

fig.text(0.045, 0.972, "How much land does one school serve?", fontproperties=DISP, fontsize=40, color=NAVY, va="top")
B = R["biggest_catchments_secondary"][0]
fig.text(0.045, 0.925, f"Every one of the UK's {R['schools']['all_n']:,} state schools and the patch of land nearest to it. Solid areas with dark edges\n"
         f"are official catchments from the {R['catchments']['authorities']} councils that publish them openly; elsewhere, nearest-school zones (not catchments).",
         family=SER, fontsize=14.5, color=FG, va="top", linespacing=1.4)

# hero: secondary zones and catchments
ax = fig.add_axes([0.0, 0.315, 0.6, 0.57])
zone_map(ax, "secondary", lw=.07, simplify=250)
frame(ax, xlim=(-40000, 670000), ylim=(-10000, 1220000))
lg = fig.add_axes([0.04, 0.36, 0.165, 0.05]); lg.axis("off")
area_legend(lg, "secondary", 0, .35, w=1/7, h=.25, fs=10, title="land served by each\nsecondary school, km²", ends=True)
g = S[S.id == B["school_id"]].iloc[0]
ax.annotate(f"{B['catchment']}\n{B['km2']:,.0f} km², {int(B['pupils']):,} pupils", xy=(g.x - 30000, g.y + 20000), xytext=(470000, 1030000),
            family=MONO, fontsize=10.5, color=FG, arrowprops=dict(arrowstyle="-", color=FG, lw=.9))
k = R["biggest_zones_primary_by_nation"]["England"]
ks = S[S.id == k["id"]].iloc[0]
ax.annotate(f"Kielder: England's biggest\nprimary zone, {k['km2']:,.0f} km²", xy=(ks.x, ks.y), xytext=(470000, 700000),
            family=MONO, fontsize=10.5, color=FG, arrowprops=dict(arrowstyle="-", color=FG, lw=.9))

# right column: big numbers
tx = fig.add_axes([0.62, 0.32, 0.36, 0.545]); tx.axis("off")
LD = R["land_distance"]
notes = [(f"{B['km2']:,.0f} km²", f"the biggest official catchment:\n{B['catchment']}, Highland.\nBigger than {R['d']['scale_name']}."),
         (f"{LD['Scotland']['prim_gt5'] * 100:.0f}% vs {LD['England']['prim_gt5'] * 100:.0f}%", "of the land more than 5 km from a\nprimary school: Scotland against\nEngland (straight lines)."),
         (f"{R['agreement']['all'] * 100:.0f}%", "of official catchment land is nearest\nto its own catchment school. The\nnearest school is a fair first guess."),
         (f"{int(R['biggest_secondary'][0]['pupils']):,}", f"pupils at {R['biggest_secondary'][0]['name']},\nthe UK's biggest state school roll.\nHalf of Scotland's primaries have\n{R['median_pupils_primary']['Scotland']:.0f} pupils or fewer.")]
for (big, small), y in zip(notes, [1.0, 0.75, 0.50, 0.25]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=31, color=PENCIL, va="top", transform=tx.transAxes)
    tx.text(0, y - 0.07, small, family=SER, fontsize=13, color=FG, va="top", transform=tx.transAxes, linespacing=1.3)

# small multiples: the same 40 km square in three places, primary schools
fig.text(0.045, 0.30, "THE SAME 40 KM SQUARE, PRIMARY SCHOOLS", family=MONO, fontsize=12, color=MUT)
W = [("London", 530000, 180000), ("Fife", 330000, 705000), ("Sutherland", 265000, 915000)]
counts = {}
for i, (nm, cx, cy) in enumerate(W):
    ext = (cx - 20000, cx + 20000, cy - 20000, cy + 20000)
    a = fig.add_axes([0.04 + i * 0.32, 0.085, 0.29, 0.19])
    a.add_patch(plt.Rectangle((ext[0], ext[2]), 40000, 40000, facecolor="#DCE5E8", edgecolor="none", zorder=0))
    zone_map(a, "primary", lw=.35, simplify=30, extent=ext)
    t = S[(S.primary == 1) & S.x.between(ext[0], ext[1]) & S.y.between(ext[2], ext[3])]
    a.scatter(t.x, t.y, s=3 if len(t) > 150 else 9, color=FG, zorder=5, lw=0)
    a.set_xlim(ext[0], ext[1]); a.set_ylim(ext[2], ext[3]); a.set_aspect("equal"); a.axis("off")
    counts[nm] = int(len(t))
    a.set_title(f"{nm}: {len(t):,} primary schools", family=MONO, fontsize=12, color=FG, pad=6)
R.setdefault("collage", {})["square_40km_primary_counts"] = counts
json.dump(R, open(os.path.join(DATA, "results.json"), "w"), indent=1, ensure_ascii=False)

fig.text(0.045, 0.018, "Data: DfE Get Information About Schools; Welsh Government; Scottish Government; Department of Education NI (all OGL v3);\n"
         "open catchment services of 33 councils; ONS boundaries; OS Open Names. Contains OS data © Crown copyright and database\n"
         "right 2026. Zones: Voronoi cells clipped to land, straight lines; not admissions advice.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib. Interactive: maps.tristanhotham.com/school-catchments",
         family=MONO, fontsize=9, color=MUT, linespacing=1.45)
fig.savefig(os.path.join(OUT, "school_catchments.png"), facecolor=PAPER, dpi=200)
print("ok", counts)
