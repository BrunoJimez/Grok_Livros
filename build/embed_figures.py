# -*- coding: utf-8 -*-
"""
Mapeia figuras/tabelas do PDF original → imagens, traduz legendas,
injeta no markdown e gera HTML/PDF/LaTeX/EPUB em tradu/novo/.
"""
from __future__ import annotations

import html as html_mod
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

import fitz
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Image as RLImage,
    KeepTogether,
    HRFlowable,
    ListFlowable,
    ListItem,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(r"C:\Users\Hugo\Documents\grok\The_Book\tradu")
PDF = Path(r"C:\Users\Hugo\Documents\grok\The_Book\why_the.pdf")
ORIG = ROOT / "images" / "original"
PT = ROOT / "pt"
NOVO = ROOT / "novo"
FIG = NOVO / "figuras"
BUILD = ROOT / "build"

TITLE = "O Livro do Porquê"
SUBTITLE = "A nova ciência de causa e efeito"
AUTHORS = "Judea Pearl e Dana Mackenzie"

CHAPTERS = [
    ("00_prefacio.md", "Prefácio"),
    ("00_introducao.md", "Introdução — Mente sobre dados"),
    ("01_escada.md", "Capítulo 1 — A Escada da Causalidade"),
    ("02_genesis.md", "Capítulo 2 — Dos bucaneiros às cobaias"),
    ("03_bayes.md", "Capítulo 3 — Das evidências às causas"),
    ("04_confundimento.md", "Capítulo 4 — Confundimento e desconfundimento"),
    ("05_fumaca.md", "Capítulo 5 — O debate enevoado pela fumaça"),
    ("06_paradoxos.md", "Capítulo 6 — Paradoxos à farta!"),
    ("07_intervencao.md", "Capítulo 7 — Além do ajustamento"),
    ("08_contrafactuais.md", "Capítulo 8 — Contrafactuais"),
    ("09_mediacao.md", "Capítulo 9 — Mediação"),
    ("10_bigdata.md", "Capítulo 10 — Big data, IA e as grandes perguntas"),
    ("11_agradecimentos.md", "Agradecimentos"),
    ("12_sobre_autores.md", "Sobre os autores"),
    ("13_notas.md", "Notas"),
    ("14_bibliografia.md", "Bibliografia"),
    ("15_indice.md", "Índice remissivo"),
    ("16_notas_tradutor.md", "Notas do tradutor"),
    ("17_figuras_legendas.md", "Legendas de figuras e tabelas"),
]


# ---------- Portuguese captions (from 17 + auto) ----------
def load_pt_captions() -> dict[str, str]:
    """key F1.1 / T3.1 -> Portuguese caption text."""
    out: dict[str, str] = {}
    leg = PT / "17_figuras_legendas.md"
    if leg.exists():
        text = leg.read_text(encoding="utf-8")
        for m in re.finditer(
            r"\*\*(Figura|Tabela)\s+(\d+\.\d+)\.\*\*\s*(.+?)(?=\n\n|\n\*\*|\Z)",
            text,
            re.S,
        ):
            kind, num, cap = m.group(1), m.group(2), re.sub(r"\s+", " ", m.group(3)).strip()
            key = ("F" if kind == "Figura" else "T") + num
            out[key] = cap
    # Also harvest captions already in chapter markdowns
    for f in PT.glob("*.md"):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(
            r"\*?\*?(Figura|Tabela)\s+(\d+\.\d+)\.?\*?\*?\s*[—–\-]?\s*(.+?)(?:\*?\s*$)",
            t,
            re.M,
        ):
            kind, num, cap = m.group(1), m.group(2), m.group(3).strip()
            if len(cap) < 12:
                continue
            key = ("F" if kind.lower().startswith("fig") else "T") + num
            if key not in out:
                out[key] = cap.rstrip("*").strip()
    return out


def translate_caption_fallback(en: str) -> str:
    """Lightweight EN→PT for remaining captions (glossary-aware heuristics)."""
    if not en:
        return ""
    # keep if already looks Portuguese
    if re.search(r"\b(de|da|do|para|com|que|uma|um|os|as)\b", en.lower()) and not re.search(
        r"\b(the|with|from|that|which|shows)\b", en.lower()
    ):
        return en
    # common scientific terms
    repl = [
        (r"\bCausal diagram\b", "Diagrama causal"),
        (r"\bPath diagram\b", "Diagrama de caminhos"),
        (r"\bScatter plot\b", "Diagrama de dispersão"),
        (r"\bSource:\b", "Fonte:"),
        (r"\bDrawing by\b", "Desenho de"),
        (r"\bPhotograph\b", "Fotografia"),
        (r"\bexample\b", "exemplo"),
        (r"\bExample\b", "Exemplo"),
        (r"\bmodel\b", "modelo"),
        (r"\bModel\b", "Modelo"),
        (r"\bconfounder\b", "confundidor"),
        (r"\bConfounder\b", "Confundidor"),
        (r"\btreatment\b", "tratamento"),
        (r"\boutcome\b", "resultado"),
        (r"\bprobability\b", "probabilidade"),
        (r"\bProbability\b", "Probabilidade"),
        (r"\bBayesian network\b", "Rede bayesiana"),
        (r"\bLadder of Causation\b", "Escada da Causalidade"),
        (r"\bFigure\b", "Figura"),
        (r"\bTable\b", "Tabela"),
        (r"\bfor the\b", "para o/a"),
        (r"\bof the\b", "de/da"),
        (r"\bwith\b", "com"),
        (r"\band\b", "e"),
        (r"\bin which\b", "em que"),
        (r"\bshows\b", "mostra"),
        (r"\bused by\b", "usado por"),
        (r"\bas an analogy for\b", "como analogia para"),
    ]
    s = en
    for a, b in repl:
        s = re.sub(a, b, s)
    return s


def build_figure_map() -> dict:
    NOVO.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(PDF)
    img_manifest = json.loads((ROOT / "images" / "img_manifest.json").read_text(encoding="utf-8"))
    page_imgs: dict[int, list] = defaultdict(list)
    for item in img_manifest:
        page_imgs[item["page"]].append(item)

    captions: dict[str, dict] = {}
    for i in range(doc.page_count):
        t = doc[i].get_text()
        for m in re.finditer(r"(FIGURE|TABLE)\s+(\d+\.\d+)\.?\s+([^\n]{8,400})", t):
            kind, num, rest = m.group(1), m.group(2), m.group(3).strip()
            key = ("F" if kind == "FIGURE" else "T") + num
            captions[key] = {
                "page": i + 1,
                "num": num,
                "en": rest[:600],
                "files": page_imgs.get(i + 1, []),
            }

    pt_caps = load_pt_captions()
    mapping: dict[str, dict] = {}

    for key, c in captions.items():
        files = list(c["files"])
        if not files:
            for d in (1, -1, 2, -2, 3):
                files = page_imgs.get(c["page"] + d, [])
                if files:
                    break

        num = c["num"]
        kind_pt = "figura" if key[0] == "F" else "tabela"
        prefix = "fig" if key[0] == "F" else "tab"
        fname = f"{prefix}_{num.replace('.', '_')}.png"
        dst = FIG / fname

        used_page_render = False
        if files:
            best = max(files, key=lambda x: x["w"] * x["h"])
            src = ORIG / best["file"]
            # Prefer embedded image if large enough; else full-page render
            if src.exists() and best["w"] * best["h"] >= 40000:
                shutil.copy2(src, dst)
                w, h = best["w"], best["h"]
            else:
                used_page_render = True
        else:
            used_page_render = True

        if used_page_render or not dst.exists():
            page = doc[c["page"] - 1]
            # render page; crop a bit of margins
            pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            pix.save(dst)
            w, h = pix.width, pix.height
            used_page_render = True

        pt_cap = pt_caps.get(key) or translate_caption_fallback(c["en"])
        mapping[key] = {
            "file": fname,
            "rel": f"figuras/{fname}",
            "path": str(dst),
            "page": c["page"],
            "num": num,
            "kind": kind_pt,
            "en": c["en"],
            "pt": pt_cap,
            "w": w,
            "h": h,
            "from_page": used_page_render,
        }

    # Also export every significant original image as gallery assets page_NNN
    gallery = FIG / "paginas"
    gallery.mkdir(exist_ok=True)
    for item in img_manifest:
        src = ORIG / item["file"]
        if src.exists() and item["w"] * item["h"] >= 30000:
            shutil.copy2(src, gallery / item["file"])

    (NOVO / "figuras_map.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Mapeadas {len(mapping)} figuras/tabelas → {FIG}")
    return mapping


def insert_images_in_markdown(mapping: dict) -> None:
    """Create novo/pt/*.md with ![caption](../figuras/...) after first figure mention."""
    out_pt = NOVO / "pt"
    out_pt.mkdir(exist_ok=True)

    # index by number for regex
    by_num = {}
    for key, m in mapping.items():
        by_num[(m["kind"], m["num"])] = m

    for fname, _title in CHAPTERS:
        src = PT / fname
        if not src.exists():
            continue
        text = src.read_text(encoding="utf-8")
        inserted = set()

        def repl_figura(match):
            num = match.group(1)
            key_info = by_num.get(("figura", num))
            whole = match.group(0)
            if not key_info or num in inserted:
                return whole
            # only insert on dedicated caption lines or first "Figura X.Y."
            line_start = match.string.rfind("\n", 0, match.start()) + 1
            line = match.string[line_start : match.string.find("\n", match.start())]
            # insert after this paragraph/line
            inserted.add(num)
            rel = f"../figuras/{key_info['file']}"
            cap = key_info["pt"] or key_info["en"]
            block = (
                f"{whole}\n\n"
                f"![Figura {num}. {cap}]({rel})\n\n"
                f"*Figura {num}. {cap}*\n"
            )
            # if already a caption-style line, replace line with image+caption
            if re.match(r"^\*?\*?(Figura)\s+" + re.escape(num), line.strip()):
                return (
                    f"![Figura {num}. {cap}]({rel})\n\n"
                    f"**Figura {num}.** {cap}\n"
                )
            return block

        def repl_tabela(match):
            num = match.group(1)
            key_info = by_num.get(("tabela", num))
            whole = match.group(0)
            if not key_info or ("T" + num) in inserted:
                return whole
            inserted.add("T" + num)
            rel = f"../figuras/{key_info['file']}"
            cap = key_info["pt"] or key_info["en"]
            return (
                f"{whole}\n\n"
                f"![Tabela {num}. {cap}]({rel})\n\n"
                f"*Tabela {num}. {cap}*\n"
            )

        # Insert on first occurrence of each Figura N.M in the chapter
        # Strategy: for each mapped figure, find first "Figura N.M" and inject after that sentence/paragraph
        new_text = text
        # process figures sorted by first occurrence position (reverse insert)
        events = []
        for key, m in mapping.items():
            kind_label = "Figura" if m["kind"] == "figura" else "Tabela"
            pat = re.compile(rf"{kind_label}\s+{re.escape(m['num'])}\b")
            mo = pat.search(text)
            if mo:
                events.append((mo.start(), key, m, mo.end()))
        events.sort(key=lambda x: -x[0])  # reverse so offsets stay valid

        for start, key, m, end in events:
            # find end of paragraph
            para_end = text.find("\n\n", end)
            if para_end < 0:
                para_end = len(text)
            # avoid double insert
            window = text[end:para_end]
            if f"figuras/{m['file']}" in window or f"](../figuras/" in text[max(0,start-50):para_end+80]:
                continue
            rel = f"../figuras/{m['file']}"
            cap = m["pt"] or m["en"]
            kind_label = "Figura" if m["kind"] == "figura" else "Tabela"
            inject = (
                f"\n\n![{kind_label} {m['num']}. {cap}]({rel})\n\n"
                f"*{kind_label} {m['num']}. {cap}*\n"
            )
            text = text[:para_end] + inject + text[para_end:]

        # Also append a chapter figure gallery at end for any figures in chapter number range
        chap_num = None
        cm = re.match(r"0?(\d+)_", fname)
        if cm:
            chap_num = cm.group(1).lstrip("0") or "0"
        if chap_num and chap_num.isdigit() and 1 <= int(chap_num) <= 10:
            n = chap_num
            extras = []
            for key, m in sorted(mapping.items(), key=lambda kv: float(kv[1]["num"])):
                if m["num"].startswith(n + ".") and f"figuras/{m['file']}" not in text:
                    rel = f"../figuras/{m['file']}"
                    cap = m["pt"] or m["en"]
                    kind_label = "Figura" if m["kind"] == "figura" else "Tabela"
                    extras.append(
                        f"\n![{kind_label} {m['num']}. {cap}]({rel})\n\n"
                        f"**{kind_label} {m['num']}.** {cap}\n"
                    )
            if extras:
                text += "\n\n## Figuras e tabelas deste capítulo\n" + "".join(extras)

        (out_pt / fname).write_text(text, encoding="utf-8")
    print(f"Markdown com imagens em {out_pt}")


# ---------- parsers / builders (simplified from montar_obra) ----------
def register_fonts():
    for name, path in [
        ("Georgia", r"C:\Windows\Fonts\georgia.ttf"),
        ("Georgia-Bold", r"C:\Windows\Fonts\georgiab.ttf"),
        ("Georgia-Italic", r"C:\Windows\Fonts\georgiai.ttf"),
    ]:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass


def md_to_blocks(text: str):
    blocks = []
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    para = []
    footnotes = {}

    def flush():
        nonlocal para
        if para:
            blocks.append(("p", " ".join(para).strip()))
            para = []

    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\[\^(\d+)\]:\s*(.*)$", line)
        if m:
            flush()
            footnotes[m.group(1)] = m.group(2)
            i += 1
            continue
        # image markdown
        im = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", line.strip())
        if im:
            flush()
            blocks.append(("img", im.group(1), im.group(2)))
            i += 1
            continue
        if line.startswith("# "):
            flush()
            blocks.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            flush()
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            flush()
            blocks.append(("h3", line[4:].strip()))
        elif line.startswith("---") and len(line.strip()) <= 5:
            flush()
            blocks.append(("hr", ""))
        elif line.startswith("> "):
            flush()
            q = [line[2:]]
            i += 1
            while i < len(lines) and lines[i].startswith("> "):
                q.append(lines[i][2:])
                i += 1
            blocks.append(("quote", " ".join(q)))
            continue
        elif re.match(r"^[-*]\s+", line):
            flush()
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                items.append(re.sub(r"^[-*]\s+", "", lines[i]))
                i += 1
            blocks.append(("ul", items))
            continue
        elif line.strip() == "":
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    if footnotes:
        blocks.append(("footnotes", footnotes))
    return blocks


def inline_html(s: str) -> str:
    s = html_mod.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def inline_rl(s: str) -> str:
    s = re.sub(r"\*\*\*(.+?)\*\*\*", r"*\1*", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"§B§\1§/B§", s)
    s = re.sub(r"\*([^*]+)\*", r"§I§\1§/I§", s)
    s = html_mod.escape(s)
    s = s.replace("§B§", "<b>").replace("§/B§", "</b>")
    s = s.replace("§I§", "<i>").replace("§/I§", "</i>")
    return s


def safe_p(text: str, style):
    try:
        return Paragraph(inline_rl(text), style)
    except Exception:
        return Paragraph(html_mod.escape(re.sub(r"[*_`]+", "", text)[:2000]), style)


def resolve_img(path_str: str) -> Path | None:
    p = path_str.replace("\\", "/")
    candidates = [
        NOVO / p,
        NOVO / "pt" / p,
        (NOVO / "pt" / p).resolve(),
        FIG / Path(p).name,
        NOVO / "figuras" / Path(p).name,
    ]
    # relative from markdown ../figuras/x
    if p.startswith("../"):
        candidates.append(NOVO / p[3:])
    for c in candidates:
        try:
            if c.exists() and c.is_file():
                return c
        except Exception:
            pass
    return None


def build_html(mapping: dict):
    parts = [
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'/>",
        f"<title>{html_mod.escape(TITLE)}</title>",
        """<style>
        :root{--ink:#1c1c1c;--cream:#faf7f0;--accent:#8c3228;--gray:#5a5a5a;}
        body{font-family:Georgia,serif;background:var(--cream);color:var(--ink);
             line-height:1.65;max-width:46rem;margin:0 auto;padding:2rem 1.25rem;}
        h1{font-size:1.85rem;margin-top:2.5rem;border-bottom:1px solid #d2c8b9;padding-bottom:.4rem;}
        h2{font-size:1.35rem;margin-top:2rem;color:var(--accent);}
        p{text-align:justify;margin:.85rem 0;}
        figure{margin:1.5rem 0;text-align:center;}
        figure img{max-width:100%;height:auto;border:1px solid #e5ddd0;background:#fff;
                   box-shadow:0 4px 16px rgba(0,0,0,.08);}
        figcaption{font-size:.92rem;color:var(--gray);margin-top:.5rem;font-style:italic;text-align:left;}
        .cover{text-align:center;padding:2rem 0;}
        .cover img{max-width:min(100%,420px);box-shadow:0 8px 24px rgba(0,0,0,.12);}
        nav.toc{background:#fff;border:1px solid #e5ddd0;padding:1.25rem 1.5rem;margin:2rem 0;}
        nav.toc a{color:var(--ink);text-decoration:none;} li{margin:.35rem 0;}
        .chapter{page-break-before:always;}
        </style></head><body>
        """,
        "<header class='cover'>",
    ]
    capa = ROOT / "images" / "capa_br.png"
    if capa.exists():
        # copy to novo
        shutil.copy2(capa, NOVO / "capa_br.png")
        shutil.copy2(ROOT / "images" / "contracapa_br.png", NOVO / "contracapa_br.png")
        parts.append(f"<img src='capa_br.png' alt='Capa'/>")
    parts.append(f"<h1>{html_mod.escape(TITLE)}</h1>")
    parts.append(f"<p>{html_mod.escape(SUBTITLE)}</p>")
    parts.append(f"<p><strong>{html_mod.escape(AUTHORS)}</strong></p>")
    parts.append("<p><em>Edição brasileira com figuras e legendas traduzidas</em></p></header>")
    parts.append("<nav class='toc'><h2>Sumário</h2><ol>")
    for fname, title in CHAPTERS:
        if (NOVO / "pt" / fname).exists():
            parts.append(f"<li><a href='#{fname[:-3]}'>{html_mod.escape(title)}</a></li>")
    parts.append("</ol></nav>")

    for fname, title in CHAPTERS:
        path = NOVO / "pt" / fname
        if not path.exists():
            continue
        parts.append(f"<section class='chapter' id='{fname[:-3]}'>")
        for block in md_to_blocks(path.read_text(encoding="utf-8")):
            kind = block[0]
            if kind == "h1":
                parts.append(f"<h1>{inline_html(block[1])}</h1>")
            elif kind == "h2":
                parts.append(f"<h2>{inline_html(block[1])}</h2>")
            elif kind == "h3":
                parts.append(f"<h3>{inline_html(block[1])}</h3>")
            elif kind == "p":
                parts.append(f"<p>{inline_html(block[1])}</p>")
            elif kind == "quote":
                parts.append(f"<blockquote><p>{inline_html(block[1])}</p></blockquote>")
            elif kind == "ul":
                parts.append("<ul>" + "".join(f"<li>{inline_html(x)}</li>" for x in block[1]) + "</ul>")
            elif kind == "img":
                cap, src = block[1], block[2]
                img_path = resolve_img(src)
                if img_path:
                    # path relative to novo root html
                    rel = img_path.relative_to(NOVO).as_posix()
                    parts.append(
                        f"<figure><img src='{html_mod.escape(rel)}' alt='{html_mod.escape(cap)}'/>"
                        f"<figcaption>{inline_html(cap)}</figcaption></figure>"
                    )
                else:
                    parts.append(f"<p><em>[Imagem não encontrada: {html_mod.escape(src)}]</em></p>")
            elif kind == "hr":
                parts.append("<hr/>")
            elif kind == "footnotes":
                parts.append("<div class='footnotes'><h3>Notas</h3>")
                for k, v in block[1].items():
                    parts.append(f"<p><sup>{k}</sup> {inline_html(v)}</p>")
                parts.append("</div>")
        parts.append("</section>")

    if (NOVO / "contracapa_br.png").exists():
        parts.append("<section class='cover'><img src='contracapa_br.png' alt='Contracapa'/></section>")
    parts.append("</body></html>")
    out = NOVO / "O_Livro_do_Porque.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    print("HTML:", out, out.stat().st_size)


def build_latex(mapping: dict):
    latex_dir = NOVO / "latex"
    latex_dir.mkdir(exist_ok=True)
    parts = [
        r"\documentclass[11pt,a5paper]{book}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[brazil]{babel}",
        r"\usepackage{geometry}",
        r"\geometry{margin=1.8cm}",
        r"\usepackage{graphicx}",
        r"\usepackage{hyperref}",
        r"\usepackage{microtype}",
        r"\usepackage{setspace}",
        r"\onehalfspacing",
        rf"\title{{{TITLE}\\\large {SUBTITLE}}}",
        rf"\author{{{AUTHORS}}}",
        r"\begin{document}",
        r"\maketitle",
        r"\tableofcontents",
        r"\mainmatter",
    ]
    if (NOVO / "capa_br.png").exists():
        parts.append(r"\begin{titlepage}\centering")
        parts.append(r"\includegraphics[width=0.95\textwidth]{../capa_br.png}")
        parts.append(r"\end{titlepage}")

    def tex_esc(s: str) -> str:
        for a, b in [
            ("\\", r"\textbackslash{}"),
            ("&", r"\&"),
            ("%", r"\%"),
            ("$", r"\$"),
            ("#", r"\#"),
            ("_", r"\_"),
            ("{", r"\{"),
            ("}", r"\}"),
        ]:
            s = s.replace(a, b)
        s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
        s = re.sub(r"\*(.+?)\*", r"\\textit{\1}", s)
        return s

    for fname, title in CHAPTERS:
        path = NOVO / "pt" / fname
        if not path.exists():
            continue
        blocks = md_to_blocks(path.read_text(encoding="utf-8"))
        first_h1 = next((b[1] for b in blocks if b[0] == "h1"), title)
        parts.append(rf"\chapter{{{tex_esc(first_h1)}}}")
        for block in blocks:
            kind = block[0]
            if kind == "h1":
                continue
            elif kind == "h2":
                parts.append(rf"\section{{{tex_esc(block[1])}}}")
            elif kind == "h3":
                parts.append(rf"\subsection{{{tex_esc(block[1])}}}")
            elif kind == "p":
                parts.append(tex_esc(block[1]) + "\n")
            elif kind == "quote":
                parts.append(r"\begin{quote}" + tex_esc(block[1]) + r"\end{quote}")
            elif kind == "img":
                cap, src = block[1], block[2]
                img_path = resolve_img(src)
                if img_path:
                    rel = Path(r"../figuras") / img_path.name
                    parts.append(r"\begin{figure}[ht]")
                    parts.append(r"\centering")
                    parts.append(rf"\includegraphics[width=0.92\textwidth]{{{rel.as_posix()}}}")
                    parts.append(rf"\caption{{{tex_esc(cap)}}}")
                    parts.append(r"\end{figure}")
            elif kind == "ul":
                parts.append(r"\begin{itemize}")
                for it in block[1]:
                    parts.append(rf"\item {tex_esc(it)}")
                parts.append(r"\end{itemize}")
    if (NOVO / "contracapa_br.png").exists():
        parts.append(r"\clearpage\centering\includegraphics[width=0.95\textwidth]{../contracapa_br.png}")
    parts.append(r"\end{document}")
    out = latex_dir / "O_Livro_do_Porque.tex"
    out.write_text("\n".join(parts), encoding="utf-8")
    shutil.copy2(out, NOVO / "O_Livro_do_Porque.tex")
    print("LaTeX:", out, out.stat().st_size)


def build_pdf(mapping: dict):
    register_fonts()
    out = NOVO / "O_Livro_do_Porque.pdf"
    page = A5
    doc = SimpleDocTemplate(
        str(out),
        pagesize=page,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.8 * cm,
        title=TITLE,
        author=AUTHORS,
    )
    font_name = "Georgia" if "Georgia" in pdfmetrics.getRegisteredFontNames() else "Times-Roman"
    font_bold = "Georgia-Bold" if "Georgia-Bold" in pdfmetrics.getRegisteredFontNames() else "Times-Bold"
    font_italic = "Georgia-Italic" if "Georgia-Italic" in pdfmetrics.getRegisteredFontNames() else "Times-Italic"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyBR", fontName=font_name, fontSize=9.5, leading=13, alignment=TA_JUSTIFY, spaceAfter=7, firstLineIndent=10))
    styles.add(ParagraphStyle(name="H1BR", fontName=font_bold, fontSize=13, leading=16, spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="H2BR", fontName=font_bold, fontSize=11, leading=14, spaceBefore=12, spaceAfter=6, textColor=HexColor("#8c3228")))
    styles.add(ParagraphStyle(name="H3BR", fontName=font_bold, fontSize=10, leading=13, spaceBefore=8, spaceAfter=5))
    styles.add(ParagraphStyle(name="QuoteBR", fontName=font_italic, fontSize=9, leading=12, leftIndent=12, textColor=HexColor("#5a5a5a"), spaceAfter=8))
    styles.add(ParagraphStyle(name="CapBR", fontName=font_italic, fontSize=8, leading=10, alignment=TA_CENTER, textColor=HexColor("#5a5a5a"), spaceAfter=10))
    styles.add(ParagraphStyle(name="CenterBR", fontName=font_name, fontSize=10, leading=13, alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle(name="TitleBR", fontName=font_bold, fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="TOCItem", fontName=font_name, fontSize=9, leading=12, spaceAfter=2))
    styles.add(ParagraphStyle(name="FN", fontName=font_name, fontSize=7.5, leading=9, spaceAfter=3))

    story = []
    max_w = page[0] - 3.2 * cm
    max_h = 10 * cm

    def add_img(path: Path, caption: str):
        try:
            # scale to fit
            from PIL import Image as PILImage

            with PILImage.open(path) as im:
                w_px, h_px = im.size
            aspect = h_px / max(w_px, 1)
            w = max_w
            h = w * aspect
            if h > max_h:
                h = max_h
                w = h / aspect
            elems = [RLImage(str(path), width=w, height=h), Spacer(1, 4), safe_p(caption, styles["CapBR"])]
            story.append(KeepTogether(elems))
        except Exception as e:
            story.append(safe_p(f"[Figura: {caption}] ({e})", styles["CapBR"]))

    # cover
    capa = NOVO / "capa_br.png"
    if not capa.exists() and (ROOT / "images" / "capa_br.png").exists():
        shutil.copy2(ROOT / "images" / "capa_br.png", capa)
        shutil.copy2(ROOT / "images" / "contracapa_br.png", NOVO / "contracapa_br.png")
    if capa.exists():
        story.append(Spacer(1, 0.3 * cm))
        story.append(RLImage(str(capa), width=9.5 * cm, height=14.2 * cm))
        story.append(PageBreak())

    story.append(Paragraph(TITLE, styles["TitleBR"]))
    story.append(Paragraph(SUBTITLE, styles["CenterBR"]))
    story.append(Paragraph(AUTHORS, styles["CenterBR"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        safe_p(
            "Edição brasileira de estudo com figuras, tabelas e legendas em português. "
            "Obra original: *The Book of Why*, © 2018 Judea Pearl and Dana Mackenzie.",
            styles["BodyBR"],
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("Sumário", styles["H1BR"]))
    for fname, title in CHAPTERS:
        if (NOVO / "pt" / fname).exists():
            story.append(safe_p(title, styles["TOCItem"]))
    story.append(PageBreak())

    def on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(HexColor("#5a5a5a"))
        canvas.drawCentredString(page[0] / 2, 1.0 * cm, str(canvas.getPageNumber()))
        canvas.restoreState()

    for fname, title in CHAPTERS:
        path = NOVO / "pt" / fname
        if not path.exists():
            continue
        for block in md_to_blocks(path.read_text(encoding="utf-8")):
            kind = block[0]
            if kind == "h1":
                story.append(safe_p(block[1], styles["H1BR"]))
            elif kind == "h2":
                story.append(safe_p(block[1], styles["H2BR"]))
            elif kind == "h3":
                story.append(safe_p(block[1], styles["H3BR"]))
            elif kind == "p":
                if block[1].strip():
                    story.append(safe_p(block[1], styles["BodyBR"]))
            elif kind == "quote":
                story.append(safe_p(block[1], styles["QuoteBR"]))
            elif kind == "ul":
                for it in block[1]:
                    story.append(safe_p("• " + it, styles["BodyBR"]))
            elif kind == "img":
                cap, src = block[1], block[2]
                img_path = resolve_img(src)
                if img_path:
                    add_img(img_path, cap)
            elif kind == "hr":
                story.append(HRFlowable(width="100%", thickness=0.4, color=HexColor("#d2c8b9")))
            elif kind == "footnotes":
                story.append(Paragraph("Notas", styles["H3BR"]))
                for k, v in block[1].items():
                    story.append(safe_p(f"{k}. {v}", styles["FN"]))
        story.append(PageBreak())

    contracapa = NOVO / "contracapa_br.png"
    if contracapa.exists():
        story.append(RLImage(str(contracapa), width=9.5 * cm, height=14.2 * cm))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("PDF:", out, out.stat().st_size)


def build_epub(mapping: dict):
    try:
        from ebooklib import epub
    except ImportError:
        print("ebooklib missing")
        return

    book = epub.EpubBook()
    book.set_identifier("olivrodoporque-ptbr-figuras")
    book.set_title(TITLE)
    book.set_language("pt")
    book.add_author(AUTHORS)

    style = (
        "body{font-family:Georgia,serif;line-height:1.5;margin:1em;}"
        "h1{font-size:1.5em;} h2{color:#8c3228;}"
        "p{text-align:justify;} figure{text-align:center;margin:1em 0;}"
        "figure img{max-width:100%;height:auto;} figcaption{font-size:0.9em;font-style:italic;color:#555;}"
    )
    nav_css = epub.EpubItem(uid="style", file_name="style/default.css", media_type="text/css", content=style.encode())
    book.add_item(nav_css)

    capa = NOVO / "capa_br.png"
    if capa.exists():
        book.set_cover("capa_br.png", capa.read_bytes())

    # register figure images once
    added_imgs = set()
    chapters = []
    for idx, (fname, title) in enumerate(CHAPTERS):
        path = NOVO / "pt" / fname
        if not path.exists():
            continue
        body_parts = [f"<h1>{html_mod.escape(title)}</h1>"]
        for block in md_to_blocks(path.read_text(encoding="utf-8")):
            kind = block[0]
            if kind == "h1":
                body_parts.append(f"<h1>{inline_html(block[1])}</h1>")
            elif kind == "h2":
                body_parts.append(f"<h2>{inline_html(block[1])}</h2>")
            elif kind == "h3":
                body_parts.append(f"<h3>{inline_html(block[1])}</h3>")
            elif kind == "p":
                if block[1].strip():
                    body_parts.append(f"<p>{inline_html(block[1])}</p>")
            elif kind == "quote":
                body_parts.append(f"<blockquote><p>{inline_html(block[1])}</p></blockquote>")
            elif kind == "ul":
                body_parts.append("<ul>" + "".join(f"<li>{inline_html(x)}</li>" for x in block[1]) + "</ul>")
            elif kind == "img":
                cap, src = block[1], block[2]
                img_path = resolve_img(src)
                if img_path and img_path.name not in added_imgs:
                    item = epub.EpubItem(
                        uid=f"img_{img_path.stem}",
                        file_name=f"images/{img_path.name}",
                        media_type="image/png",
                        content=img_path.read_bytes(),
                    )
                    book.add_item(item)
                    added_imgs.add(img_path.name)
                if img_path:
                    body_parts.append(
                        f"<figure><img src='images/{html_mod.escape(img_path.name)}' alt=''/>"
                        f"<figcaption>{inline_html(cap)}</figcaption></figure>"
                    )
            elif kind == "footnotes":
                body_parts.append("<hr/><h3>Notas</h3>")
                for k, v in block[1].items():
                    body_parts.append(f"<p><sup>{k}</sup> {inline_html(v)}</p>")

        c = epub.EpubHtml(title=title[:200], file_name=f"chap_{idx:02d}.xhtml", lang="pt", uid=f"c{idx}")
        c.set_content(
            f'<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml"><head>'
            f"<title>{html_mod.escape(title[:80])}</title>"
            f'<link rel="stylesheet" type="text/css" href="style/default.css"/>'
            f"</head><body>{''.join(body_parts)}</body></html>"
        )
        c.add_item(nav_css)
        book.add_item(c)
        chapters.append(c)

    book.toc = tuple(chapters)
    book.spine = ["nav"] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    out = NOVO / "O_Livro_do_Porque.epub"
    if out.exists():
        out.unlink()
    epub.write_epub(str(out), book, {})
    print("EPUB:", out, out.stat().st_size)


def write_caption_index(mapping: dict):
    lines = ["# Índice de figuras e tabelas (edição com imagens)\n"]
    for key in sorted(mapping.keys(), key=lambda k: (k[0], float(mapping[k]["num"]))):
        m = mapping[key]
        label = "Figura" if m["kind"] == "figura" else "Tabela"
        lines.append(f"- **{label} {m['num']}** (pág. original {m['page']}): {m['pt'] or m['en']}")
        lines.append(f"  - arquivo: `figuras/{m['file']}`\n")
    (NOVO / "INDICE_FIGURAS.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    print("=== 1. Mapear e copiar figuras ===")
    mapping = build_figure_map()
    print("=== 2. Inserir imagens nos markdowns ===")
    insert_images_in_markdown(mapping)
    write_caption_index(mapping)
    print("=== 3. HTML ===")
    build_html(mapping)
    print("=== 4. LaTeX ===")
    build_latex(mapping)
    print("=== 5. PDF ===")
    build_pdf(mapping)
    print("=== 6. EPUB ===")
    build_epub(mapping)
    print("=== CONCLUÍDO ===")
    for p in sorted(NOVO.glob("O_Livro*")):
        print(p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
