"""#30Tage30Tools – baut alle Post-Texte + Zeitplan als posts.json (Basis für Postiz und Review-Seite)."""
import json, os, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, "content", "challenge")
T = json.load(open(os.path.join(C, "tools.json"), encoding="utf-8"))
START = dt.date(2026, 10, 20)
DST_END = dt.date(2026, 10, 25)  # ab hier MEZ (UTC+1)

def utc(d, hh, mm):
    off = 2 if d < DST_END else 1
    return (dt.datetime(d.year, d.month, d.day, hh, mm) - dt.timedelta(hours=off)).strftime("%Y-%m-%dT%H:%M:%S")

def P(s): return "".join(f"<p>{l}</p>" if l else "<p></p>" for l in s.split("\n"))

def body(n, t, ig=False):
    oss = "Open Source" in t["badge"]
    lines = [f"<strong>Tag {n}/30: {t['name']} – {t['hook']}</strong>", ""]
    if n == 1:
        lines += ["🚀 Heute startet unsere Challenge #30Tage30Tools: 30 Tage lang stellen wir dir jeden Tag ein Tool vor, das im Betrieb echte Arbeit abnimmt – überwiegend Open Source.", ""]
    lines += [t["what"], "", f"So nutzt dein Betrieb {t['name']}:"] + [f"✅ {u}" for u in t["uses"]]
    lines += ["", f"💡 {t['tip']}", "", f"🔗 {t['url']}", "", f"💬 {t['q']}"]
    if n == 30:
        lines += ["", "🎉 Das war Tag 30 von 30 – danke, dass du dabei warst! Wenn du wissen willst, welche Tools in deinem Betrieb Sinn ergeben: Schreib uns einfach."]
    tags = ["#30Tage30Tools"] + [f"#{x}" for x in t["tags"]] + (["#OpenSource"] if oss else [])
    if ig: tags += ["#KMU", "#Digitalisierung"]
    lines += ["", " ".join(dict.fromkeys(tags))]
    return "\n".join(lines)

RECAPS = [
    {"date": dt.date(2026, 10, 23), "a": 1, "b": 4, "title": "Woche 1", "hook": "4 Tools, die Betrieben echte Arbeit abnehmen",
     "intro": "Diese Woche haben wir bei bettersorted die Challenge #30Tage30Tools gestartet: 30 Tage lang jeden Tag ein Tool, das im Betrieb wirklich hilft – überwiegend Open Source. 🛠️\n\nDie ersten vier:"},
    {"date": dt.date(2026, 10, 30), "a": 5, "b": 11, "title": "Woche 2", "hook": "Woche 2 der #30Tage30Tools: Cloud, Passwörter, Office",
     "intro": "Woche 2 unserer Challenge ist durch – diesmal ging es um die Basics im Büro. 🗂️\n\nDiese sieben Tools waren dabei:"},
    {"date": dt.date(2026, 11, 6), "a": 12, "b": 18, "title": "Woche 3", "hook": "Halbzeit: 7 Tools für Kommunikation und Projekte",
     "intro": "Halbzeit bei #30Tage30Tools! 🎯 In Woche 3 ging es um Kommunikation, Projekte und KI im Alltag.\n\nDie sieben Tools der Woche:"},
    {"date": dt.date(2026, 11, 13), "a": 19, "b": 25, "title": "Woche 4", "hook": "Woche 4: Wissen, Marketing und offene KI",
     "intro": "Woche 4 von #30Tage30Tools ist geschafft. 📚 Diesmal: Firmenwissen sichern, Marketing automatisieren und offene KI-Modelle finden.\n\nDie Tools der Woche:"},
    {"date": dt.date(2026, 11, 20), "a": 26, "b": 30, "title": "Finale", "hook": "30 Tage, 30 Tools – das Finale",
     "intro": "Geschafft: 30 Tage, 30 Tools! 🎉 Zum Abschluss ging es um Rechnungen, sichere Kommunikation, Self-Hosting, Kennzahlen und ERP.\n\nDie letzten fünf:"},
]
NUM = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]

def recap_text(r):
    lines = [f"<strong>{r['hook']}</strong>", ""] + r["intro"].split("\n")
    for i, n in enumerate(range(r["a"], r["b"] + 1)):
        t = T[n - 1]; lines.append(f"{NUM[i]} {t['name']} – {t['cat']}")
    lines += [""]
    if r["title"] == "Finale":
        lines += ["Im Karussell findest du alle fünf mit Beispiel – und auf der letzten Seite alle 30 Tools auf einen Blick. 👉", "",
                  "Mein Fazit: Für fast jede Aufgabe im Betrieb gibt es eine gute Lösung, oft Open Source und auf eigenem Server. Man muss nur wissen, wo man anfängt.", "",
                  "💬 Welches Tool war dein Favorit?"]
    else:
        lines += ["Alle Tools mit Beispiel findest du im Karussell. 👉", "",
                  "Die Challenge läuft täglich auf der Seite von bettersorted – folg gern, wenn du keinen Tag verpassen willst.", "",
                  "💬 Welches davon nutzt du schon?"]
    lines += ["", "#30Tage30Tools #OpenSource #KMU #Digitalisierung"]
    return "\n".join(lines)

posts = []
for n, t in enumerate(T, 1):
    d = START + dt.timedelta(days=n - 1)
    posts.append({"day": n, "name": t["name"], "date": d.isoformat(),
                  "linkedin_page": {"date": utc(d, 16, 0), "html": P(body(n, t))},
                  "facebook": {"date": utc(d, 18, 30), "html": P(body(n, t)), "title": f"Tag {n}/30: {t['name']} – {t['hook']}"},
                  "instagram": {"date": utc(d, 18, 30), "html": P(body(n, t, ig=True))},
                  "youtube": {"date": utc(d, 19, 0), "html": P(body(n, t)), "title": f"Tag {n}/30: {t['name']} – {t['hook']} #Shorts"[:100],
                              "tags": ["30Tage30Tools", t["name"].replace(" ", "")] + t["tags"][:3] + ["bettersorted"]},
                  "plain": body(n, t)})
recaps = [{"title": r["title"], "a": r["a"], "b": r["b"], "date": r["date"].isoformat(), "utc": utc(r["date"], 7, 45),
           "html": P(recap_text(r)), "plain": recap_text(r), "carousel_name": f"#30Tage30Tools – {r['title']}"} for r in RECAPS]
json.dump({"posts": posts, "recaps": recaps}, open(os.path.join(C, "posts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(posts), len(recaps), max(len(p["youtube"]["title"]) for p in posts))
