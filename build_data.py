import json, glob, re, os, unicodedata

SRC = "/home/claude/website_extracted/website/data"
OUT_DATA = "/home/claude/site/data"

def classify(stem):
    if not stem:
        return "Uncertain"
    s = stem.lower()
    def has(*pats):
        return any(re.search(p, s) for p in pats)
    if has(r'\bnisbe', r'\badj', r'part\.\s*a', r'part\.\s*p', r'part\.a', r'part\.p'):
        return "Adjective"
    if has(r'\bpron'):
        return "Pronoun"
    if has(r'präp', r'\bprep\b'):
        return "Preposition"
    if has(r'\bkonj', r'\bconj'):
        return "Conjunction"
    if has(r'interj', r'\bvoc\b'):
        return "Interjection"
    if has(r'\badv\b', r'frageadv'):
        return "Adverb"
    if has(r'\bzw\.', r'zahlwort'):
        return "Numeral"
    if has(r'proper name', r'toponym', r'monatsname', r'schwertname'):
        return "Proper name"
    if has(r'\bphrase', r'\bidiom', r'expression', r'compound'):
        return "Phrase / idiom"
    if has(r'partikel', r'\benkl', r'\bprokl'):
        return "Particle"
    # verb stem codes (Tigre grammar): O1-O4, A1-A3, T1-T4, AT1-3, ATA1-3, AN1-3, AS1-3, K, Ka, M, F, G, R, N, St, SO
    verb_pat = r'\b(O[1-4]|A[1-3]|T[1-4]|AT[1-3]|ATA[1-3]|AN[1-3]|AS[1-3]|Ka?|M|F|G|R|N|St1?|SO)\b'
    if re.search(verb_pat, stem):
        return "Verb"
    if has(r'\bnoun\b', r'\bs\.', r'\bs\b', r'coll', r'n\. un', r'\bm\.', r'\bf\.', r'\bpl\.'):
        return "Noun"
    return "Other"

def slugify(text, fallback):
    if not text:
        text = fallback
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower()
    return text or fallback

entries = []
files = sorted(glob.glob(os.path.join(SRC, "pg-*.json")))
for fp in files:
    with open(fp, encoding='utf-8') as f:
        recs = json.load(f)
    for e in recs:
        hw = e.get('headword_geez')
        if not hw:
            continue  # skip continuation/orphan records without a headword
        senses_out = []
        for s in (e.get('senses') or []):
            eng = s.get('english')
            if eng:
                senses_out.append({
                    "num": s.get('sense_num'),
                    "text": eng,
                    "citation": s.get('citation'),
                })
        subs_out = []
        for s in (e.get('sub_entries') or []):
            eng = s.get('english')
            if eng:
                subs_out.append({
                    "form": s.get('form'),
                    "text": eng,
                    "citation": s.get('citation'),
                })
        translit = e.get('headword_translit')
        stem = e.get('stem_class')
        entry_id = e.get('entry_id')
        slug = slugify(translit, entry_id) + "-" + entry_id
        entries.append({
            "id": entry_id,
            "slug": slug,
            "headword": hw,
            "translit": translit,
            "stem_class": stem,
            "pos": classify(stem),
            "page": e.get('page'),
            "senses": senses_out,
            "sub_entries": subs_out,
            "etymology": e.get('etymology'),
            "has_english": bool(senses_out or subs_out),
        })

# dedupe slugs just in case
seen = {}
for e in entries:
    base = e['slug']
    if base in seen:
        seen[base] += 1
        e['slug'] = f"{base}-{seen[base]}"
    else:
        seen[base] = 0

# search_text for client search
for e in entries:
    parts = [e['headword'] or '', e['translit'] or '']
    for s in e['senses']:
        parts.append(s['text'] or '')
    for s in e['sub_entries']:
        parts.append(s['text'] or '')
    e['search_text'] = " ".join(parts).lower()

def base_letter(translit):
    if not translit:
        return None
    ch = translit[0]
    norm = unicodedata.normalize('NFKD', ch)
    norm = ''.join(c for c in norm if not unicodedata.combining(c))
    norm = norm.upper()
    if norm and norm[0].isalpha() and norm[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        return norm[0]
    return "#"

for e in entries:
    e['letter'] = base_letter(e['translit'])

os.makedirs(OUT_DATA, exist_ok=True)
with open(os.path.join(OUT_DATA, "vocabulary.json"), "w", encoding='utf-8') as f:
    json.dump(entries, f, ensure_ascii=False, separators=(',', ':'))

# stats
pos_counts = {}
letter_counts = {}
with_english = 0
pages = set()
for e in entries:
    pos_counts[e['pos']] = pos_counts.get(e['pos'], 0) + 1
    if e['has_english']:
        with_english += 1
    if e['page']:
        pages.add(e['page'])
    if e['letter']:
        letter_counts[e['letter']] = letter_counts.get(e['letter'], 0) + 1

stats = {
    "total_headwords": len(entries),
    "with_english": with_english,
    "without_english": len(entries) - with_english,
    "total_pages": len(pages),
    "pos_counts": dict(sorted(pos_counts.items(), key=lambda x: -x[1])),
    "letter_counts": dict(sorted(letter_counts.items())),
}
with open(os.path.join(OUT_DATA, "stats.json"), "w", encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print("Entries:", len(entries))
print("With English:", with_english)
print("Stats:", json.dumps(stats, indent=2)[:1000])
