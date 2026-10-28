"""Step 9. Paper PDF: fill code/paper_template.tex from data/results.json, write release/paper/Hotham_School_Catchments.tex,
compile with xelatex (figures from step 8) and copy the PDF to release/.
Run: python3 code/09_paper.py
"""
import json, os, re, shutil, subprocess
from common import DATA, ROOT, HERE

R = json.load(open(os.path.join(DATA, "results.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_School_Catchments"
tex = lambda s: str(s).replace("\\", "").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "pct": return f"{v * 100:.0f}\\%"
    if f == "pct1": return f"{v * 100:.1f}\\%"
    if f == "f1": return f"{v:.1f}"
    return tex(v)


def sub(m):
    path, _, f = m.group(1).rpartition("|")
    return fmt(get(path), f)


SC = R["schools"]; Z = R["zones"]
rows = ""
for n in ["England", "Wales", "Scotland", "Northern Ireland"]:
    s = SC[n]
    rows += (f"{n} & {s['primary']:,} & {s['secondary']:,} & {s['special']:,} & {s['pupils']:,} & {s['land_km2']:,} & "
             f"{Z[n + '|primary']['median_km2']:.1f} & {Z[n + '|secondary']['median_km2']:.1f}\\\\\n")
s = SC["UK"]
rows += f"\\midrule UK & {s['primary']:,} & {s['secondary']:,} & {s['special']:,} & {s['pupils']:,} & {s['land_km2']:,} & & \\\\\n"
TN = ("\\begin{table}[tbp]\\centering\\small\\caption{Open state schools by nation, pupils on roll, land area and median nearest-school zone "
      "(km\\textsuperscript{2}). All-through schools are counted as both primary and secondary.}\\label{tab:nations}"
      "\\begin{tabular}{lrrrrrrr}\\toprule Nation & Primary & Secondary & Special & Pupils & Land km\\textsuperscript{2} & Primary zone & Secondary zone\\\\\\midrule\n"
      + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = ""
for ph in ("secondary", "primary"):
    for c in R[f"biggest_catchments_{ph}"][:6]:
        pu = "" if c["pupils"] is None else f"{int(c['pupils']):,}"
        rows += f"{ph.capitalize()} & {tex(c['catchment'])} & {tex(c['authority'])} & {c['km2']:,.0f} & {pu}\\\\\n"
TB = ("\\begin{table}[tbp]\\centering\\small\\caption{The biggest official catchments (non-denominational) among the councils covered. Pupils: roll of the linked school.}"
      "\\label{tab:biggest}\\begin{tabular}{lllrr}\\toprule Phase & Catchment & Council & km\\textsuperscript{2} & Pupils\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = "".join(f"{tex(c['authority'])} & {c['nation']} & {c['primary'] or ''} & {c['secondary'] or ''} & {c['denom'] or ''} & {c['km2']:,}\\\\\n" for c in R["coverage"])
TC = ("\\begin{table}[tbp]\\centering\\small\\caption{Councils whose open catchment services are used: number of non-denominational primary and secondary catchments, "
      "Roman Catholic catchments, and land covered (km\\textsuperscript{2}).}\\label{tab:coverage}\\begin{tabular}{llrrrr}\\toprule Council & Nation & Primary & Secondary & Catholic & km\\textsuperscript{2}\\\\\\midrule\n"
      + rows + "\\bottomrule\\end{tabular}\\end{table}")

t = open(os.path.join(HERE, "paper_template.tex"), encoding="utf-8").read()
t = re.sub(r"\{\{(.+?)\}\}", sub, t)
t = t.replace("\\TABNATIONS", TN).replace("\\TABBIGGEST", TB).replace("\\TABCOVERAGE", TC)
assert "{{" not in t
for bad in ("—", "–", "--"): assert bad not in t, bad
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
if not os.path.exists(os.path.join(OUT, NAME + ".pdf")): print(r.stdout[-3000:]); raise SystemExit(1)
for ext in (".aux", ".log", ".out"):
    p = os.path.join(OUT, NAME + ext)
    if os.path.exists(p): os.remove(p)
shutil.move(os.path.join(OUT, NAME + ".pdf"), os.path.join(ROOT, "release", NAME + ".pdf"))
txt = subprocess.run(["pdftotext", os.path.join(ROOT, "release", NAME + ".pdf"), "-"], capture_output=True, text=True).stdout
print("pdf written; words", len(txt.split()), "dashes", sum(txt.count(b) for b in ("—", "–", "--")))
