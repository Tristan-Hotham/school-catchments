"""Step 7. header.png, the 1200 by 630 social card.
Run: python3 code/07_header.py
"""
from figlib import *

fig = plt.figure(figsize=(6, 3.15), dpi=200)
ax = fig.add_axes([.53, .0, .47, 1])
zone_map(ax, "secondary", lw=.05, simplify=400)
frame(ax, xlim=(-60000, 680000), ylim=(-20000, 1230000))
B = R["biggest_catchments_secondary"][0]
fig.text(.055, .86, "DATA STUDY  ·  SCHOOLS  ·  UK", family=MONO, fontsize=6.2, color=MUT)
fig.text(.05, .80, "School", fontproperties=DISP, fontsize=40, color=NAVY, va="top")
fig.text(.05, .585, "catchments", fontproperties=DISP, fontsize=33, color=PENCIL, va="top")
fig.text(.055, .395, f"How much of the UK does one school serve?\n{R['schools']['all_n']:,} state schools, official catchments\nwhere published, nearest-school zones\nelsewhere. Biggest: {B['catchment']}, {B['km2']:,.0f} km².",
         family=SER, fontsize=8.0, color=FG, va="top", linespacing=1.12)
lg = fig.add_axes([.055, .085, .4, .07]); lg.axis("off")
area_legend(lg, "secondary", 0, .25, w=.1, h=.28, fs=5, title="land served by each secondary school, km²", ends=True)
fig.text(.055, .018, "Dr Tristan Hotham · Independent researcher", family=MONO, fontsize=5.6, color=MUT)
fig.savefig(os.path.join(ROOT, "header.png"), dpi=200)
print("header.png written")
