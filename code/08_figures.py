"""Step 8. Static figures for the paper (release/paper/fig_*.png) and the blog (release/blog/b_*.png, 1520 px wide).
Run: python3 code/08_figures.py
"""
from figlib import *

PAP = os.path.join(ROOT, "release", "paper"); BLOG = os.path.join(ROOT, "release", "blog")
os.makedirs(PAP, exist_ok=True); os.makedirs(BLOG, exist_ok=True)
S = schools(); C, CG = catchments()


def save(fig, name, blog=True, paper=True):
    if paper: fig.savefig(os.path.join(PAP, f"fig_{name}.png"), dpi=200, bbox_inches="tight", pad_inches=.08)
    if blog: fig.savefig(os.path.join(BLOG, f"b_{name}.png"), dpi=200, bbox_inches="tight", pad_inches=.12)
    plt.close(fig)


# 1. the map: secondary and primary side by side
fig, axs = plt.subplots(1, 2, figsize=(7.6, 6.9))
for ax, ph in zip(axs, ("secondary", "primary")):
    zone_map(ax, ph, lw=.04 if ph == "primary" else .08, simplify=300 if ph == "primary" else 200)
    frame(ax, xlim=(-40000, 670000), ylim=(-10000, 1220000))
    ax.set_title(ph.capitalize() + " schools", family=MONO, fontsize=11, color=FG, loc="left")
    area_legend(ax, ph, .02, .93, w=.075, h=.016, fs=7.5, title="area served, km²")
fig.text(.01, .015, "Solid areas with dark edges: official catchments from councils that publish them. Elsewhere: nearest-school zones (not catchments).",
         family=MONO, fontsize=7, color=MUT)
plt.subplots_adjust(wspace=.02, left=.01, right=.99, top=.96, bottom=.04)
save(fig, "map")

# 2. biggest official catchments
fig, axs = plt.subplots(2, 1, figsize=(7.6, 7.0))
AB = {"Perth and Kinross": "Perth & Kinross", "Argyll and Bute": "Argyll & Bute"}
for ax, ph in zip(axs, ("secondary", "primary")):
    rows = R[f"biggest_catchments_{ph}"][:10][::-1]
    y = np.arange(len(rows))
    ax.barh(y, [r["km2"] for r in rows], color=[PENCIL if i == len(rows) - 1 else NAVY for i in range(len(rows))], height=.72)
    ax.set_yticks(y, [r["catchment"].replace(" High School", " High").replace(" Primary School", " Primary").replace(" Academy", " Acad.") + f" ({AB.get(r['authority'], r['authority'])})" for r in rows], fontsize=8.2, family=MONO)
    for yy, r in zip(y, rows): ax.text(r["km2"] + 15, yy, f"{r['km2']:,.0f}", va="center", fontsize=8, family=MONO, color=FG)
    ax.set_title(ph.capitalize(), family=MONO, fontsize=10.5, loc="left", color=FG)
    ax.set_xlabel("km² of land", fontsize=9); ax.tick_params(axis="x", labelsize=8); ax.set_xlim(0, max(r["km2"] for r in rows) * 1.18)
plt.tight_layout(h_pad=1.5)
save(fig, "biggest")

# 3. zone size distribution by nation (log scale), primary and secondary
fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.9), sharey=True)
for ax, ph in zip(axs, ("primary", "secondary")):
    for k, n in enumerate(NATS):
        v = S[(S.nation == n) & (S[ph] == 1)][f"zone_{ph}_km2"].dropna().to_numpy()
        v = v[v > 0]
        q = np.quantile(v, [.1, .25, .5, .75, .9])
        ax.plot([q[0], q[4]], [k, k], color=NCOL[n], lw=1.2)
        ax.add_patch(plt.Rectangle((q[1], k - .22), q[3] - q[1], .44, facecolor=NCOL[n], alpha=.35, edgecolor=NCOL[n]))
        ax.plot([q[2]], [k], "o", color=NCOL[n], ms=7)
        ax.text(q[4] * 1.25, k, f"median {q[2]:.1f}" if q[2] < 10 else f"median {q[2]:.0f}", va="center", fontsize=8, family=MONO, color=FG)
    ax.set_xscale("log"); ax.set_yticks(range(4), NATS, fontsize=9); ax.invert_yaxis()
    ax.set_title(ph.capitalize(), family=MONO, fontsize=10.5, loc="left", color=FG); ax.set_xlabel("nearest-school zone, km² (log scale)", fontsize=9)
    ax.tick_params(axis="x", labelsize=8); ax.set_xlim(.05 if ph == "primary" else .5, 3000 if ph == "primary" else 30000)
fig.text(.01, -.02, "Dot: median. Box: middle half of schools. Line: 10th to 90th percentile.", family=MONO, fontsize=7.5, color=MUT)
plt.tight_layout()
save(fig, "zones")

# 4. distance from villages and hamlets
fig, axs = plt.subplots(2, 1, figsize=(7.6, 4.2))
E = R["distance_bin_edges"]; labs = [f"{E[i]} to {E[i + 1]} km" for i in range(len(E) - 1)] + [f"over {E[-1]} km"]
cols = ["#22406A", "#3A6A82", "#5E9283", "#9DB38A", "#D8C77C", "#E5A15A", "#B4412F"]
for ax, ph in zip(axs, ("primary", "secondary")):
    nats = ["England", "Wales", "Scotland"]
    for k, n in enumerate(nats):
        b = np.array(R["distance_bins"][ph][n], float); b = b / b.sum(); x = 0
        for j, v in enumerate(b):
            ax.barh(k, v, left=x, color=cols[j], height=.7, edgecolor=BG, lw=.6)
            if v > .055: ax.text(x + v / 2, k, f"{v * 100:.0f}%", ha="center", va="center", fontsize=7.5, family=MONO, color="white" if j < 3 or j == 6 else FG)
            x += v
    ax.set_yticks(range(3), nats, fontsize=9); ax.invert_yaxis(); ax.set_xlim(0, 1); ax.set_xticks([])
    ax.spines["bottom"].set_visible(False); ax.spines["left"].set_visible(False)
    ax.set_title(f"Nearest {ph} school", family=MONO, fontsize=10, loc="left", color=FG)
hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cols]
fig.legend(hs, labs, loc="lower center", ncol=4, fontsize=8, frameon=False, bbox_to_anchor=(.5, -.09), prop={"family": MONO, "size": 8})
plt.tight_layout()
save(fig, "distance")

# 5. agreement by council
A = sorted(R["agreement"]["by_authority"].items(), key=lambda t: t[1])
fig, ax = plt.subplots(figsize=(7.6, 6.2))
y = np.arange(len(A))
ax.hlines(y, 0, [v for _, v in A], color=RULE, lw=1)
ax.scatter([v for _, v in A], y, s=46, c=[AG_COL[cls(v, [.2, .4, .6, .8])] for _, v in A], edgecolors=FG, linewidths=.7, zorder=3)
ax.axvline(R["agreement"]["all"], color=PENCIL, ls="--", lw=1.4)
ax.text(R["agreement"]["all"] + .01, len(A) - .3, f"all councils {R['agreement']['all'] * 100:.0f}%", color=PENCIL, family=MONO, fontsize=8.5)
ax.set_yticks(y, [a for a, _ in A], fontsize=8.5); ax.set_xlim(0, 1); ax.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"], fontsize=8.5)
ax.set_xlabel("share of official catchment land whose nearest school is the catchment school", fontsize=9)
plt.tight_layout()
save(fig, "agreement")

# 6. pupils against land served
fig, ax = plt.subplots(figsize=(7.6, 4.8))
for n in NATS:
    t = S[(S.nation == n) & (S.primary == 1) & (S.secondary == 0) & (S.pupils > 0)]
    ax.scatter(t.zone_primary_km2, t.pupils, s=3 if n == "England" else 5, alpha=.35 if n == "England" else .55, color=NCOL[n], label=n, linewidths=0)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("nearest-school zone, km² (log scale)", fontsize=9); ax.set_ylabel("pupils (log scale)", fontsize=9)
ax.tick_params(labelsize=8.5)
lg = ax.legend(markerscale=4, fontsize=8.5, frameon=False, loc="lower left", prop={"family": MONO, "size": 8.5})
plt.tight_layout()
save(fig, "size_area", blog=False)

# 7. one council in detail: official primary catchments against nearest-school zones (Fife)
ext = (300000, 365000, 682000, 728000)
fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.4))
for ax, off in zip(axs, (True, False)):
    zone_map(ax, "primary", official=False, edge="white", lw=.5, simplify=40, extent=ext, alpha_zone=.55 if off else .9)
    if off:
        for i, r in C.iterrows():
            if r.authority == "Fife" and r.phase == "primary" and r.denominational == 0:
                draw(ax, CG[i].simplify(40), facecolor=AREA_COL[cls(r.area_km2, AREA_BRK["primary"])], edgecolor=FG, lw=.6)
    t = S[(S.la == "Fife") & (S.primary == 1)]
    ax.scatter(t.x, t.y, s=5, color=FG, zorder=5)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Official primary catchments, Fife" if off else "Nearest-school zones, same schools", family=MONO, fontsize=9.5, loc="left", color=FG)
plt.tight_layout()
save(fig, "fife")
print("figures written")
