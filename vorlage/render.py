#!/usr/bin/env python3
"""EcomNex Instagram: Karussell-Slides aus einer JSON-Datei erzeugen.

Aufruf: python3 render.py <post.json> <ausgabe-ordner> <logo-hell.png> <logo-dunkel.png>
Jede Slide wird als PNG mit 1080 x 1350 Pixeln gespeichert, zusätzlich als JPG im Unterordner jpg.
Eine JSON-Datei mit genau einer Slide ergibt ein Einzelbild (ohne Fortschrittsrahmen).
Slide-Typen: cover, numbers, list, steps, calc, table, formula, statement, cta.
"""
import base64, html, json, pathlib, sys
from playwright.sync_api import sync_playwright

W, H = 1080, 1350
PAD = 84
INNER = W - 2 * PAD

THEMES = {
    "sand":   dict(bg="#EBE1CF", ink="#10291C", muted="rgba(16,41,28,.66)", line="rgba(16,41,28,.2)",
                   accent="#10984A", bar_a="#10291C", bar_b="#10984A", logo="hell"),
    "forest": dict(bg="#0E3524", ink="#F1E8D7", muted="rgba(241,232,215,.72)", line="rgba(241,232,215,.24)",
                   accent="#56CF8B", bar_a="#F1E8D7", bar_b="#56CF8B", logo="dunkel"),
}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:%(W)spx;height:%(H)spx}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--ink);
  -webkit-font-smoothing:antialiased;font-feature-settings:'cv11'}
.slide{position:relative;width:%(W)spx;height:%(H)spx;padding:%(PAD)spx;display:flex;flex-direction:column}
.top{display:flex;justify-content:space-between;align-items:center;height:64px}
.top img{height:58px;display:block}
.top span{font-size:28px;font-weight:500;color:var(--muted)}
.body{flex:1;display:flex;flex-direction:column;justify-content:center;padding:36px 0 44px}
.foot{height:34px}
.foot svg{display:block}
h1,h2,.fig,.sum,.formula,.bigfig,.figtag,.row b,.step b,.url b{font-family:'Inter Display','Inter',sans-serif;letter-spacing:-.03em;word-spacing:.1em}
h1{font-weight:900;font-size:116px;line-height:.98;text-wrap:balance}
h2{font-weight:800;font-size:68px;line-height:1.04;text-wrap:balance}
p{font-size:40px;line-height:1.32;font-weight:500;color:var(--muted);text-wrap:pretty}
h1+p{margin-top:44px;max-width:820px}
h2+*{margin-top:56px}
.hint{margin-top:auto;font-size:28px;font-weight:600;color:var(--ink)}
.body.cover{justify-content:flex-start;padding-top:112px}
.body.cover h1{font-size:128px}

/* Zahlen */
.figs{display:flex;flex-direction:column;gap:44px}
.figrow{border-top:3px solid var(--line);padding-top:30px;display:flex;align-items:flex-end;justify-content:space-between;gap:24px}
.fig{font-weight:900;font-size:132px;line-height:.9;color:var(--accent);white-space:nowrap}
.figlabel{font-size:34px;line-height:1.25;font-weight:500;color:var(--muted);margin-top:18px}
.figtag{font-family:'Inter Display';font-weight:800;font-size:54px;letter-spacing:-.03em;line-height:1;
  padding:16px 24px 18px;border:5px solid var(--ink);border-radius:26px;white-space:nowrap;margin-bottom:10px}
.figs+p{margin-top:52px}

/* Liste */
.rows{display:flex;flex-direction:column}
.row{border-top:3px solid var(--line);padding:26px 0 28px;display:grid;grid-template-columns:340px 1fr;gap:28px;align-items:baseline}
.row b{font-family:'Inter Display';font-weight:800;font-size:44px;letter-spacing:-.03em;line-height:1.1}
.row span{font-size:34px;line-height:1.28;font-weight:500;color:var(--muted)}

/* Schritte */
.step{border-top:3px solid var(--line);padding:30px 0 32px;display:grid;grid-template-columns:96px 1fr;gap:20px;align-items:start}
.step i{font-style:normal;font-family:'Inter Display';font-weight:900;font-size:76px;line-height:.9;letter-spacing:-.04em;color:var(--accent)}
.step b{display:block;font-family:'Inter Display';font-weight:800;font-size:44px;letter-spacing:-.03em;line-height:1.12}
.step span{display:block;margin-top:10px;font-size:34px;line-height:1.28;font-weight:500;color:var(--muted)}

/* Rechnung */
.calc{display:flex;flex-direction:column}
.cl{display:flex;justify-content:space-between;align-items:baseline;border-top:3px solid var(--line);padding:24px 0 26px;font-size:42px;font-weight:500}
.cl em{font-feature-settings:'cv11','tnum';font-style:normal;font-family:'Inter Display';font-weight:700;font-size:48px;letter-spacing:-.02em;white-space:nowrap}
.cl.sum{border-top:6px solid var(--ink);font-weight:800;font-size:50px;letter-spacing:-.03em;padding-top:28px}
.cl.sum em{font-weight:900;font-size:92px;line-height:.9;color:var(--accent);letter-spacing:-.04em}
.cl.neg em{color:var(--ink)}
.calc+p{margin-top:44px}
.note{font-size:30px}

/* Tabelle */
.tb{display:flex;flex-direction:column}
.tr{display:grid;grid-template-columns:330px 1fr 270px;gap:20px;align-items:baseline;border-top:3px solid var(--line);padding:22px 0 24px;font-size:40px;font-weight:500}
.tr.head{border-top:0;padding:0 0 18px;font-size:27px;line-height:1.2;color:var(--muted);align-items:end}
.tr span:nth-child(2){text-align:right;font-feature-settings:'cv11','tnum'}
.tr em{font-style:normal;text-align:right;font-family:'Inter Display';font-weight:700;font-size:46px;letter-spacing:-.02em;white-space:nowrap;font-feature-settings:'cv11','tnum'}
.tr.head span:last-child{text-align:right}
.tr.sum{border-top:6px solid var(--ink);font-weight:800;padding-top:26px}
.tr.sum em{font-weight:900;font-size:64px;line-height:.9;color:var(--accent);letter-spacing:-.04em}
.tb+p{margin-top:40px}

/* Formel */
.formula{font-weight:800;font-size:66px;line-height:1.1;padding:38px 44px 42px;border:6px solid var(--ink);border-radius:38px;display:inline-block;align-self:flex-start}
.bigfig{font-family:'Inter Display';font-weight:900;font-size:230px;line-height:.86;letter-spacing:-.05em;color:var(--accent);margin-top:54px}
.bigfig+p{margin-top:36px;max-width:820px}

/* Abschluss */
.url{margin-top:64px;align-self:flex-start;position:relative;height:124px}
.url::before,.url::after{content:'';position:absolute;top:0;bottom:0;border:6px solid var(--bar-a)}
.url::before{left:0;width:calc(62%% - 6px);border-right:0;border-radius:62px 0 0 62px}
.url::after{right:0;width:calc(38%% - 6px);border-left:0;border-radius:0 62px 62px 0;border-color:var(--bar-b)}
.url b{position:relative;display:block;font-family:'Inter Display';font-weight:900;font-size:60px;letter-spacing:-.03em;line-height:120px;padding:0 52px}
"""


def esc(s):
    # geschützter Bindestrich, damit E-Mail nicht am Zeilenende getrennt wird
    return html.escape(s, quote=False).replace("E-Mail", "E\u2011Mail")


def split_frame(w, h, split, a, b, stroke=5, gap=5):
    """Der geteilte Rahmen aus dem Logo. Die Teilung zeigt die Position im Karussell."""
    r = (h - stroke) / 2
    o = stroke / 2
    if split >= w:
        return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect x="{o}" y="{o}" width="{w - stroke}" '
                f'height="{h - stroke}" rx="{r}" fill="none" stroke-width="{stroke}" stroke="{a}"/></svg>')
    rect = f'<rect x="{o}" y="{o}" width="{w - stroke}" height="{h - stroke}" rx="{r}" fill="none" stroke-width="{stroke}"'
    uid = f"c{int(split)}{w}{h}"
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<defs><clipPath id="{uid}a"><rect x="0" y="0" width="{split - gap}" height="{h}"/></clipPath>'
        f'<clipPath id="{uid}b"><rect x="{split + gap}" y="0" width="{w - split - gap}" height="{h}"/></clipPath></defs>'
        f'{rect} stroke="{a}" clip-path="url(#{uid}a)"/>{rect} stroke="{b}" clip-path="url(#{uid}b)"/></svg>'
    )


def body(s):
    t = s["type"]
    if t == "cover":
        return ("cover", f'<h1>{esc(s["title"])}</h1><p>{esc(s["sub"])}</p><div class="hint">{esc(s.get("hint", ""))}</div>')
    if t == "numbers":
        rows = ""
        for f in s["figures"]:
            tag = f'<div class="figtag">{esc(f["tag"])}</div>' if f.get("tag") else ""
            rows += (f'<div class="figrow"><div><div class="fig">{esc(f["value"])}</div>'
                     f'<div class="figlabel">{esc(f["label"])}</div></div>{tag}</div>')
        text = f'<p>{esc(s["text"])}</p>' if s.get("text") else ""
        return ("", f'<h2>{esc(s["title"])}</h2><div class="figs">{rows}</div>{text}')
    if t == "list":
        rows = "".join(f'<div class="row"><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in s["rows"])
        return ("", f'<h2>{esc(s["title"])}</h2><div class="rows">{rows}</div>')
    if t == "steps":
        rows = "".join(f'<div class="step"><i>{n}</i><div><b>{esc(a)}</b><span>{esc(b)}</span></div></div>'
                       for n, (a, b) in enumerate(s["steps"], 1))
        return ("", f'<h2>{esc(s["title"])}</h2><div class="rows">{rows}</div>')
    if t == "calc":
        rows = ""
        for line in s["lines"]:
            cls = "cl " + line.get("kind", "")
            rows += f'<div class="{cls}"><span>{esc(line["label"])}</span><em>{esc(line["value"])}</em></div>'
        text = f'<p class="{"note" if s.get("small") else ""}">{esc(s["text"])}</p>' if s.get("text") else ""
        return ("", f'<h2>{esc(s["title"])}</h2><div class="calc">{rows}</div>{text}')
    if t == "table":
        h = s["head"]
        rows = f'<div class="tr head"><span>{esc(h[0])}</span><span>{esc(h[1])}</span><span>{esc(h[2])}</span></div>'
        for n, r in enumerate(s["rows"]):
            cls = "tr sum" if n == len(s["rows"]) - 1 else "tr"
            rows += f'<div class="{cls}"><span>{esc(r[0])}</span><span>{esc(r[1])}</span><em>{esc(r[2])}</em></div>'
        text = f'<p class="note">{esc(s["text"])}</p>' if s.get("text") else ""
        return ("", f'<h2>{esc(s["title"])}</h2><div class="tb">{rows}</div>{text}')
    if t == "formula":
        return ("", f'<h2>{esc(s["title"])}</h2><div class="formula">{esc(s["formula"])}</div>'
                    f'<div class="bigfig">{esc(s["result"])}</div><p>{esc(s["text"])}</p>')
    if t == "statement":
        return ("", f'<h1>{esc(s["title"])}</h1><p>{esc(s["text"])}</p>')
    if t == "cta":
        return ("", f'<h1>{esc(s["title"])}</h1><p>{esc(s["text"])}</p>'
                    f'<div class="url"><b>{esc(s["url"])}</b></div>')
    raise ValueError(t)


def page(s, i, n, logos):
    th = THEMES[s.get("theme", "sand")]
    cls, inner = body(s)
    split = round(INNER * i / n)
    bar = "" if n == 1 else split_frame(INNER, 34, split, th["bar_a"], th["bar_b"])
    vars_ = f'--bg:{th["bg"]};--ink:{th["ink"]};--muted:{th["muted"]};--line:{th["line"]};--accent:{th["accent"]};--bar-a:{th["bar_a"]};--bar-b:{th["bar_b"]}'
    css = CSS % dict(W=W, H=H, PAD=PAD)
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><style>{css}</style></head>
<body style="{vars_}"><div class="slide">
<div class="top"><img src="data:image/png;base64,{logos[th['logo']]}" alt="EcomNex"><span>ecomnex.de</span></div>
<div class="body {cls}">{inner}</div>
<div class="foot">{bar}</div>
</div>
</body></html>"""


def main():
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    logos = {"hell": base64.b64encode(pathlib.Path(sys.argv[3]).read_bytes()).decode(),
             "dunkel": base64.b64encode(pathlib.Path(sys.argv[4]).read_bytes()).decode()}
    slides = spec["slides"]
    problems = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for i, s in enumerate(slides, 1):
            pg.set_content(page(s, i, len(slides), logos))
            pg.wait_for_timeout(150)
            over = pg.evaluate("(()=>{const b=document.querySelector('.body');return b.scrollHeight-b.clientHeight})()")
            wide = pg.evaluate('''(()=>{let m=0;const w=document.createTreeWalker(document.querySelector('.slide'),NodeFilter.SHOW_TEXT);
              while(w.nextNode()){const r=document.createRange();r.selectNodeContents(w.currentNode);
              for(const q of r.getClientRects())m=Math.max(m,q.right)}
              for(const e of document.querySelectorAll('.figtag,.formula,.url'))m=Math.max(m,e.getBoundingClientRect().right);
              return Math.ceil(m)})()''')
            name = out / f"{spec['slug']} {i:02d}.png"
            pg.screenshot(path=str(name), clip={"x": 0, "y": 0, "width": W, "height": H})
            from PIL import Image
            (out / "jpg").mkdir(exist_ok=True)
            Image.open(name).convert("RGB").save(out / "jpg" / (name.stem + ".jpg"), quality=95, subsampling=0)
            flag = "  ACHTUNG Überlauf" if over > 0 or wide > W - PAD else ""
            problems += 1 if flag else 0
            print(f"{name.name}{flag} (hoch {over}, breit {wide})")
        b.close()
    if problems:
        sys.exit(f"{problems} Slide(s) mit Überlauf. Text kürzen und neu rendern.")


if __name__ == "__main__":
    main()
