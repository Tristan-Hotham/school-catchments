"""Step 10. Blog post (release/blog/post.html from code/blog_template.html), blog and Zenodo meta files, and the Zenodo
folder (paper, key CSVs, results.json and a code-and-data zip). Image placeholders {{IMG|file|alt|caption}} are left for the uploader.
Run: python3 code/10_release.py
"""
import json, os, re, shutil, zipfile
from common import DATA, ROOT, HERE, DOI, PAGE, REPO

R = json.load(open(os.path.join(DATA, "results.json"), encoding="utf-8"))


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f in (None, "", "raw"): return str(v)
    if f == "int": return f"{round(v):,}"
    if f == "pct": return f"{round(v * 100)}%"
    if f == "f1": return f"{v:.1f}"
    raise ValueError(f)


t = open(os.path.join(HERE, "blog_template.html"), encoding="utf-8").read()
t = re.sub(r"\{\{(?!IMG\|)([^}|]+)(\|(\w+))?\}\}", lambda m: fmt(get(m.group(1)), m.group(3)), t)
assert "{{" not in t.replace("{{IMG|", "")
vis = re.sub(r"<!--.*?-->", "", t, flags=re.S)
for bad in ("—", "–", "--"): assert bad not in vis, bad
B = os.path.join(ROOT, "release", "blog"); os.makedirs(B, exist_ok=True)
open(os.path.join(B, "post.html"), "w", encoding="utf-8").write(t)
for m in re.findall(r"\{\{IMG\|([^|]+)\|", t):
    assert os.path.exists(os.path.join(B, m)), m
big = R["biggest_catchments_secondary"][0]
meta = dict(
    title="School catchments: how much of the UK does one school serve?",
    slug="school-catchments",
    excerpt=(f"Every one of the UK's {R['schools']['all_n']:,} state schools, the official catchments that {R['catchments']['authorities']} councils publish openly, "
             f"and nearest-school zones everywhere else. The biggest catchment, {big['catchment']}, covers {big['km2']:,.0f} km²."),
    seo_description=f"Every UK state school, official catchments where councils publish them and nearest-school zones elsewhere. Find the biggest and the most remote.",
    tags=["schools", "catchment areas", "education", "maps", "Scotland", "rural", "interactive", "data"],
    header_alt=("Title card reading 'School catchments' in navy and pencil yellow on cream paper, beside a map of the UK in which every patch of land is coloured "
                "by how much land its secondary school serves, pale cream in cities and deep navy across the Scottish Highlands. Text: How much of the UK does "
                f"one school serve? {R['schools']['all_n']:,} state schools, official catchments where published, nearest-school zones elsewhere. "
                f"Biggest: {big['catchment']}, {big['km2']:,.0f} km²."))
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
for v in meta.values():
    for bad in ("—", "–", "--"): assert bad not in str(v)
json.dump(meta, open(os.path.join(B, "meta.json"), "w"), indent=2, ensure_ascii=False)

NAME = "Hotham_School_Catchments"
pt = open(os.path.join(ROOT, "release", "paper", NAME + ".tex"), encoding="utf-8").read()
ab = pt.split("\\begin{center}\\textbf{Abstract}\\end{center}")[1].split("\\textbf{Keywords:}")[0].strip()
ab = ab.replace("\\%", "%").replace("\\&", "&").replace("km\\textsuperscript{2}", "km²")
assert "\\" not in ab and "$" not in ab, ab
Z = os.path.join(ROOT, "release", "zenodo"); os.makedirs(Z, exist_ok=True)
zmeta = dict(
    title="How Much Land Does One School Serve? Official Catchments and Nearest-School Zones Across the United Kingdom",
    description_html=f"<p>{ab}</p><p>Interactive version: {PAGE}. Data and code: {REPO}. Blog post: to follow.</p>"
                     "<p>Sources: Department for Education, Get Information About Schools; Welsh Government address list of schools; Scottish Government, "
                     "Scottish School Roll and Locations; Department of Education Northern Ireland school level enrolment data 2025/26; councils' open catchment "
                     "services (listed in catchment_sources.csv); ONS Local Authority Districts boundaries; OS Open Names. Open Government Licence v3.0. "
                     "Contains OS data © Crown copyright and database right 2026.</p>",
    keywords=["school catchments", "school admissions", "Voronoi", "nearest school", "accessibility", "rural schools", "United Kingdom", "Scotland",
              "open data", "geographic information systems"],
    licence="cc-by-4.0",
    related=[
        dict(identifier=REPO, relation="issupplementedby", resource_type="software"),
        dict(identifier=PAGE, relation="issupplementedby", resource_type="other"),
        dict(identifier="https://get-information-schools.service.gov.uk/Downloads", relation="isderivedfrom", resource_type="dataset"),
        dict(identifier="https://gov.wales/address-list-schools", relation="isderivedfrom", resource_type="dataset"),
        dict(identifier="https://maps.gov.scot/server/rest/services/ScotGov/UtilityGovernmental/MapServer/0", relation="isderivedfrom", resource_type="dataset"),
        dict(identifier="https://www.education-ni.gov.uk/publications/school-enrolment-school-level-data-20252026", relation="isderivedfrom", resource_type="dataset"),
        dict(identifier="https://geoportal.statistics.gov.uk", relation="isderivedfrom", resource_type="dataset"),
        dict(identifier="https://www.ordnancesurvey.co.uk/products/os-open-names", relation="isderivedfrom", resource_type="dataset"),
        dict(identifier="https://data.spatialhub.scot/dataset/school_catchments-is", relation="isderivedfrom", resource_type="other"),
    ])
for v in json.dumps(zmeta, ensure_ascii=False).split('"'):
    for bad in ("—", "–"): assert bad not in v
json.dump(zmeta, open(os.path.join(Z, "meta.json"), "w"), indent=2, ensure_ascii=False)
shutil.copy(os.path.join(ROOT, "release", NAME + ".pdf"), Z)
for f in ["schools_uk.csv", "catchments.csv", "catchment_sources.csv", "zones_summary.csv", "la_summary.csv", "settlements_distance.csv", "results.json"]:
    shutil.copy(os.path.join(DATA, f), Z)
with zipfile.ZipFile(os.path.join(Z, "school-catchments_code_and_data.zip"), "w", zipfile.ZIP_DEFLATED) as zf:
    for sub in ("code", "data"):
        for f in sorted(os.listdir(os.path.join(ROOT, sub))):
            p = os.path.join(ROOT, sub, f)
            if os.path.isfile(p) and not f.endswith(".pyc"): zf.write(p, f"school-catchments/{sub}/{f}")
    for f in ("README.md", "LICENSE"): zf.write(os.path.join(ROOT, f), f"school-catchments/{f}")
words = len(re.sub(r"<[^>]+>", " ", re.sub(r"\{\{IMG\|.*?\}\}", "", t)).split())
print("release files written; post words:", words)
