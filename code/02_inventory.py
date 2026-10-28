"""Step 2. Inventory of every harvested catchment layer: which council it covers (majority of polygon
centroids by ONS local authority district), which phase (primary or secondary) and whether it is a
denominational (Roman Catholic) layer, worked out from the layer and item titles. Writes
work/inventory.csv for checking and for step 3, which picks one layer per council, phase and denomination.
Run: python3 code/02_inventory.py
"""
import os, re, collections
import pandas as pd
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from common import WORK, load_gz

B = load_gz("sc_catchments_bundle_20261028.json.gz")
lad = [(f["properties"]["LAD24CD"], f["properties"]["LAD24NM"], shape(f["geometry"]).buffer(0)) for f in B["lad"]["features"]]
tree = STRtree([g for _, _, g in lad])


def where(pt):
    for i in tree.query(pt):
        if lad[i][2].contains(pt):
            return lad[i][0], lad[i][1]
    return None, None


SKIP = re.compile(r"radius|walk|isochrone|travel|capacity|proposed|future|model|overlap|cycle|land cover|boundary|buffer|postcode|parish|second priority|"
                  r"gaelic|roll_projection|statistics|1996|2013|2015|2016|2017|2019|2020|2021|non catchment|grammer|episcopal|st_ninians|devcon|rag|"
                  r"assessment|compare|outside|clive|severn|latimer|feb2020|dec2020|january2019|uprns", re.I)
rows = []
for src in ("ckan", "agol", "extra"):
    for it in B[src]:
        title = it.get("t") or it.get("title") or ""
        owner = it.get("org") or it.get("owner") or ""
        for L in it.get("layers", []):
            if not L.get("feats"):
                continue
            name = L.get("name") or ""
            text = f"{title} | {name}"
            cnt = collections.Counter()
            for f in L["feats"]:
                if not f.get("geometry"):
                    continue
                try:
                    g = shape(f["geometry"])
                    c = g.representative_point()
                except Exception:
                    continue
                cnt[where(c)] += 1
            (code, ladnm), k = cnt.most_common(1)[0] if cnt else ((None, None), 0)
            low = text.lower()
            if re.search(r"secondary|high school|academy|11.16|\bhigh\b|\.high", low): phase = "secondary"
            elif re.search(r"primary|first|infant|4.6|junior|7.10|prisch", low): phase = "primary"
            elif "middle" in low: phase = "middle"
            elif re.search(r"priority area|gpa", low): phase = "secondary"
            else: phase = "?"
            denom = bool(re.search(r"\brc\b|rc |roman|catholic|(?<!non )(?<!non-)(?<!non_)denominational|_rc|rcss|rcps|denominat(?!ional)\b", low)) and not re.search(r"non.?denom|\bnd\b|nd ", low)
            rows.append(dict(src=src, owner=owner, title=title, layer=name, n=len(L["feats"]), lad=code, lad_name=ladnm, lad_share=round(k / max(1, sum(cnt.values())), 2),
                             phase=phase, denom=int(denom), skip=int(bool(SKIP.search(text))), url=L.get("url"), item_url=it.get("url") or "",
                             lic=(it.get("lic") or "")[:120], modified=it.get("modified"), fields=",".join(list(L["feats"][0]["properties"].keys())[:14])))
I = pd.DataFrame(rows)
I.to_csv(os.path.join(WORK, "inventory.csv"), index=False)
pd.set_option("display.width", 250, "display.max_rows", 300, "display.max_colwidth", 40)
print(I[I.skip == 0][["src", "owner", "layer", "n", "lad_name", "lad_share", "phase", "denom"]].to_string())
