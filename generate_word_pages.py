import json, os, html

SITE_ROOT = "/home/claude/site"
DOMAIN = "https://example.com"  # TODO: replace with your real domain, then rerun this script

with open(os.path.join(SITE_ROOT, "data", "vocabulary.json"), encoding="utf-8") as f:
    entries = json.load(f)

WORDS_DIR = os.path.join(SITE_ROOT, "words")
os.makedirs(WORDS_DIR, exist_ok=True)

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="index, follow">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="article">
<link rel="stylesheet" href="../styles.css">
<script type="application/ld+json">{jsonld}</script>
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="../index.html">
      <span class="brand-mark">\u1275</span>
      <span class="brand-name">Tigre Dictionary<span>Ge'ez script \u00b7 English glosses</span></span>
    </a>
    <nav class="site-nav">
      <a href="../index.html#browse">Browse</a>
      <a href="../index.html">Home</a>
    </nav>
  </div>
</header>
<main class="wrap" style="max-width:720px;padding-top:40px;padding-bottom:70px">
  <div class="detail-word geez" style="font-size:44px">{headword}</div>
  {translit_html}
  <div class="detail-tags">{tags_html}</div>
  {senses_html}
  {subs_html}
  {no_gloss_html}
  {etymology_html}
  <p style="margin-top:36px"><a href="../index.html#browse" class="permalink-btn">\u2190 Back to the full dictionary</a></p>
</main>
<footer class="site-footer"><div class="wrap"><span>Tigre Dictionary &mdash; entry {entry_id}, page {page}.</span></div></footer>
</body>
</html>
"""

def esc(s):
    return html.escape(str(s), quote=True) if s is not None else ""

def sense_block(num, text, citation):
    out = '<div class="sense-block">'
    if num:
        out += f'<span class="sense-num">{esc(num)}.</span>'
    out += f'<span class="sense-text">{esc(text)}</span>'
    if citation:
        out += f'<div class="sense-cite">{esc(citation)}</div>'
    out += '</div>'
    return out

count = 0
for e in entries:
    translit_html = f'<div class="detail-translit" style="font-size:18px">{esc(e["translit"])}</div>' if e.get("translit") else ""
    tags = [e["pos"]]
    if e.get("stem_class"):
        tags.append(e["stem_class"])
    if e.get("page"):
        tags.append(f'Page {e["page"]}')
    tags_html = "".join(f'<span class="tag">{esc(t)}</span>' for t in tags)

    senses_html = "".join(sense_block(s.get("num"), s["text"], s.get("citation")) for s in (e.get("senses") or []))

    subs = e.get("sub_entries") or []
    subs_html = ""
    if subs:
        subs_html += '<div class="sub-label">Related forms</div>'
        for s in subs:
            subs_html += '<div class="sense-block">'
            if s.get("form"):
                subs_html += f'<div class="sub-form">{esc(s["form"])}</div>'
            subs_html += f'<span class="sense-text">{esc(s["text"])}</span>'
            if s.get("citation"):
                subs_html += f'<div class="sense-cite">{esc(s["citation"])}</div>'
            subs_html += '</div>'

    no_gloss_html = ""
    if not senses_html and not subs_html:
        extra = f' (compare: {esc(e["etymology"])})' if e.get("etymology") else ""
        no_gloss_html = (f'<div class="no-gloss-note">No English gloss was recorded for this headword in the '
                          f'source &mdash; it may be a cross-reference to another entry{extra}.</div>')

    etymology_html = ""
    if e.get("etymology") and senses_html:
        etymology_html = f'<div class="sense-cite" style="margin-top:14px">Etymology: {esc(e["etymology"])}</div>'

    first_gloss = None
    if e.get("senses"):
        first_gloss = e["senses"][0]["text"]
    elif e.get("sub_entries"):
        first_gloss = e["sub_entries"][0]["text"]

    title = f'{e["headword"]} ({e["translit"]}) \u2014 Tigre Dictionary' if e.get("translit") else f'{e["headword"]} \u2014 Tigre Dictionary'
    description = (f'{e["headword"]}' + (f' ({e["translit"]})' if e.get("translit") else "") +
                    (f': {first_gloss}' if first_gloss else ': Tigre headword, no English gloss recorded in source.'))
    canonical = f'{DOMAIN}/words/{e["slug"]}.html'

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "DefinedTerm",
        "name": e["headword"],
        "alternateName": e.get("translit") or None,
        "description": first_gloss or "No English gloss recorded in source.",
        "inDefinedTermSet": f"{DOMAIN}/",
        "url": canonical,
    }, ensure_ascii=False)

    page_html = TEMPLATE.format(
        title=esc(title),
        description=esc(description),
        canonical=canonical,
        og_title=esc(title),
        jsonld=jsonld,
        headword=esc(e["headword"]),
        translit_html=translit_html,
        tags_html=tags_html,
        senses_html=senses_html,
        subs_html=subs_html,
        no_gloss_html=no_gloss_html,
        etymology_html=etymology_html,
        entry_id=esc(e["id"]),
        page=esc(e.get("page") or "\u2014"),
    )
    with open(os.path.join(WORDS_DIR, f'{e["slug"]}.html'), "w", encoding="utf-8") as f:
        f.write(page_html)
    count += 1

print("Generated", count, "word pages")
