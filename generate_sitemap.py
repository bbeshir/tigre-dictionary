import json, os
from xml.sax.saxutils import escape

SITE_ROOT = "/home/claude/site"
DOMAIN = "https://example.com"  # TODO: replace with your real domain, then rerun this script

with open(os.path.join(SITE_ROOT, "data", "vocabulary.json"), encoding="utf-8") as f:
    entries = json.load(f)

urls = [(f"{DOMAIN}/index.html", "1.0")]
urls += [(f"{DOMAIN}/words/{e['slug']}.html", "0.6") for e in entries]

lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for loc, priority in urls:
    lines.append(f"  <url><loc>{escape(loc)}</loc><priority>{priority}</priority></url>")
lines.append("</urlset>")

with open(os.path.join(SITE_ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Wrote sitemap.xml with", len(urls), "URLs")
