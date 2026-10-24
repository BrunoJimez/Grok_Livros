# -*- coding: utf-8 -*-
"""
Monta a obra completa em LaTeX, HTML, EPUB e PDF a partir dos .md traduzidos.
"""
from __future__ import annotations

import html
import os
import re
import zipfile
from pathlib import Path
from datetime import datetime

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Image as RLImage,
    KeepTogether,
    ListFlowable,
    ListItem,
    HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(r"C:\Users\Hugo\Documents\grok\The_Book\tradu")
PT = ROOT / "pt"
OUT = ROOT
IMG = ROOT / "images"
BUILD = ROOT / "build"

# Ordem canônica dos capítulos
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

TITLE = "O Livro do Porquê"
SUBTITLE = "A nova ciência de causa e efeito"
AUTHORS = "Judea Pearl e Dana Mackenzie"


def register_fonts():
    for name, path in [
        ("Georgia", r"C:\Windows\Fonts\georgia.ttf"),
        ("Georgia-Bold", r"C:\Windows\Fonts\georgiab.ttf"),
        ("Georgia-Italic", r"C:\Windows\Fonts\georgiai.ttf"),
        ("Georgia-BoldItalic", r"C:\Windows\Fonts\georgiaz.ttf"),
    ]:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass


def read_md(path: Path) -> str:
    if not path.exists():
        return f"# {path.name}\n\n*[Capítulo ainda não disponível na pasta pt/]*\n"
    return path.read_text(encoding="utf-8")


def md_to_blocks(text: str):
    """Converte markdown simples em blocos (tipo, conteúdo)."""
    blocks = []
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    para = []
    footnotes = {}

    def flush_para():
        nonlocal para
        if para:
            blocks.append(("p", " ".join(para).strip()))
            para = []

    while i < len(lines):
        line = lines[i]
        # footnote definition
        m = re.match(r"^\[\^(\d+)\]:\s*(.*)$", line)
        if m:
            flush_para()
            footnotes[m.group(1)] = m.group(2)
            i += 1
            continue
        if line.startswith("# "):
            flush_para()
            blocks.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            flush_para()
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            flush_para()
            blocks.append(("h3", line[4:].strip()))
        elif line.startswith("---") and len(line.strip()) <= 5:
            flush_para()
            blocks.append(("hr", ""))
        elif line.startswith("> "):
            flush_para()
            q = [line[2:]]
            i += 1
            while i < len(lines) and lines[i].startswith("> "):
                q.append(lines[i][2:])
                i += 1
            blocks.append(("quote", " ".join(q)))
            continue
        elif re.match(r"^[-*]\s+", line):
            flush_para()
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                items.append(re.sub(r"^[-*]\s+", "", lines[i]))
                i += 1
            blocks.append(("ul", items))
            continue
        elif re.match(r"^\d+\.\s+", line):
            flush_para()
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i]))
                i += 1
            blocks.append(("ol", items))
            continue
        elif line.strip() == "":
            flush_para()
        else:
            para.append(line.strip())
        i += 1
    flush_para()
    if footnotes:
        blocks.append(("footnotes", footnotes))
    return blocks


def inline_md_to_html(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"\[\^(\d+)\]", r"<sup><a href='#fn\1'>\1</a></sup>", s)
    return s


def inline_md_to_rl(s: str) -> str:
    """ReportLab-friendly markup (non-nested, safe for platypus)."""
    # Normalize triple-asterisk emphasis to italic-only to avoid nest errors
    s = re.sub(r"\*\*\*(.+?)\*\*\*", r"*\1*", s)
    # Bold with inner italic: **_x_** or *** style already handled
    s = re.sub(r"\*\*_(.+?)_\*\*", r"*\1*", s)
    s = re.sub(r"_\*\*(.+?)\*\*_", r"*\1*", s)
    # Protect code spans
    codes = []
    def _code(m):
        codes.append(m.group(1))
        return f"§§CODE{len(codes)-1}§§"
    s = re.sub(r"`(.+?)`", _code, s)
    # Bold then italic (non-greedy, no nested *)
    s = re.sub(r"\*\*([^*]+)\*\*", r"§§B§§\1§§/B§§", s)
    s = re.sub(r"\*([^*]+)\*", r"§§I§§\1§§/I§§", s)
    s = re.sub(r"_([^_]+)_", r"§§I§§\1§§/I§§", s)
    s = html.escape(s)
    s = s.replace("§§B§§", "<b>").replace("§§/B§§", "</b>")
    s = s.replace("§§I§§", "<i>").replace("§§/I§§", "</i>")
    for i, c in enumerate(codes):
        s = s.replace(f"§§CODE{i}§§", f"<font face='Courier' size='9'>{html.escape(c)}</font>")
    s = re.sub(r"\[\^(\d+)\]", r"<super>\1</super>", s)
    # Strip any remaining raw asterisks that could confuse parser
    s = s.replace("<b></b>", "").replace("<i></i>", "")
    return s


def safe_paragraph(text: str, style):
    """Paragraph with fallback if markup is invalid."""
    try:
        return Paragraph(inline_md_to_rl(text), style)
    except Exception:
        plain = html.escape(re.sub(r"[*_`#\[\]]+", "", text))
        try:
            return Paragraph(plain, style)
        except Exception:
            return Paragraph(html.escape(text[:500]), style)


def inline_md_to_tex(s: str) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for ch in s:
        out.append(repl.get(ch, ch))
    s = "".join(out)
    s = re.sub(r"\\\*\\\*(.+?)\\\*\\\*", r"\\textbf{\1}", s)  # won't work after escape
    # better: process bold/italic before escape
    return s


def md_inline_tex(s: str) -> str:
    # extract bold/italic first
    parts = []
    # simple approach
    def esc(t):
        for a, b in [
            ("\\", r"\textbackslash{}"),
            ("&", r"\&"),
            ("%", r"\%"),
            ("$", r"\$"),
            ("#", r"\#"),
            ("_", r"\_"),
            ("{", r"\{"),
            ("}", r"\}"),
            ("~", r"\textasciitilde{}"),
            ("^", r"\textasciicircum{}"),
        ]:
            t = t.replace(a, b)
        return t

    # temporary markers
    s2 = s
    stores = []

    def store(m, cmd):
        stores.append((cmd, m.group(1)))
        return f"@@{len(stores)-1}@@"

    s2 = re.sub(r"\*\*(.+?)\*\*", lambda m: store(m, "textbf"), s2)
    s2 = re.sub(r"\*(.+?)\*", lambda m: store(m, "textit"), s2)
    s2 = re.sub(r"`(.+?)`", lambda m: store(m, "texttt"), s2)
    s2 = re.sub(r"\[\^(\d+)\]", r"\\footnote{N. do T. ref. \1}", s2)
    s2 = esc(s2)
    for i, (cmd, content) in enumerate(stores):
        s2 = s2.replace(f"@@{i}@@", f"\\{cmd}{{{esc(content)}}}")
    return s2


# ---------- HTML ----------
def build_html():
    parts = [
        "<!DOCTYPE html>",
        '<html lang="pt-BR">',
        "<head>",
        '<meta charset="utf-8"/>',
        f"<title>{html.escape(TITLE)} — {html.escape(AUTHORS)}</title>",
        "<style>",
        """
        :root { --ink:#1c1c1c; --cream:#faf7f0; --accent:#8c3228; --gray:#5a5a5a; }
        body { font-family: Georgia, 'Times New Roman', serif; background: var(--cream);
               color: var(--ink); line-height: 1.65; max-width: 42rem; margin: 0 auto;
               padding: 2rem 1.25rem; }
        h1 { font-size: 1.85rem; margin-top: 2.5rem; border-bottom: 1px solid #d2c8b9;
             padding-bottom: .4rem; }
        h2 { font-size: 1.35rem; margin-top: 2rem; color: var(--accent); }
        h3 { font-size: 1.1rem; margin-top: 1.4rem; }
        p { text-align: justify; margin: 0.85rem 0; hyphens: auto; }
        blockquote { border-left: 3px solid var(--accent); margin: 1.2rem 0; padding: .2rem 1rem;
                     color: var(--gray); font-style: italic; }
        .cover { text-align: center; padding: 3rem 1rem 2rem; }
        .cover h1 { border: none; font-size: 2.4rem; letter-spacing: .04em; }
        .cover .sub { font-size: 1.15rem; color: var(--gray); }
        .cover .auth { margin-top: 1.5rem; letter-spacing: .08em; }
        .cover img { max-width: 100%; height: auto; margin: 1.5rem 0; box-shadow: 0 8px 24px rgba(0,0,0,.12); }
        nav.toc { background: #fff; border: 1px solid #e5ddd0; padding: 1.25rem 1.5rem;
                  margin: 2rem 0; border-radius: 4px; }
        nav.toc a { color: var(--ink); text-decoration: none; }
        nav.toc a:hover { color: var(--accent); }
        nav.toc li { margin: .35rem 0; }
        .footnotes { font-size: .9rem; border-top: 1px solid #d2c8b9; margin-top: 2rem; padding-top: 1rem; }
        .chapter { page-break-before: always; }
        footer.book { text-align: center; margin-top: 4rem; padding-top: 1rem;
                      border-top: 1px solid #d2c8b9; color: var(--gray); font-size: .85rem; }
        code { font-family: Consolas, monospace; font-size: .9em; }
        """,
        "</style>",
        "</head>",
        "<body>",
        '<header class="cover">',
        f'<p class="auth">{html.escape(AUTHORS.upper())}</p>',
        f"<h1>{html.escape(TITLE)}</h1>",
        f'<p class="sub">{html.escape(SUBTITLE)}</p>',
    ]
    capa = IMG / "capa_br.png"
    if capa.exists():
        parts.append(f'<img src="images/capa_br.png" alt="Capa — {html.escape(TITLE)}"/>')
    parts.append("<p><em>Edição brasileira de estudo · Português brasileiro</em></p>")
    parts.append("</header>")

    # TOC
    parts.append('<nav class="toc"><h2>Sumário</h2><ol>')
    for fname, title in CHAPTERS:
        if (PT / fname).exists():
            anchor = fname.replace(".md", "")
            parts.append(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>')
    parts.append("</ol></nav>")

    for fname, title in CHAPTERS:
        path = PT / fname
        if not path.exists():
            continue
        anchor = fname.replace(".md", "")
        parts.append(f'<section class="chapter" id="{anchor}">')
        blocks = md_to_blocks(read_md(path))
        for kind, content in blocks:
            if kind == "h1":
                parts.append(f"<h1>{inline_md_to_html(content)}</h1>")
            elif kind == "h2":
                parts.append(f"<h2>{inline_md_to_html(content)}</h2>")
            elif kind == "h3":
                parts.append(f"<h3>{inline_md_to_html(content)}</h3>")
            elif kind == "p":
                parts.append(f"<p>{inline_md_to_html(content)}</p>")
            elif kind == "quote":
                parts.append(f"<blockquote><p>{inline_md_to_html(content)}</p></blockquote>")
            elif kind == "ul":
                parts.append("<ul>" + "".join(f"<li>{inline_md_to_html(x)}</li>" for x in content) + "</ul>")
            elif kind == "ol":
                parts.append("<ol>" + "".join(f"<li>{inline_md_to_html(x)}</li>" for x in content) + "</ol>")
            elif kind == "hr":
                parts.append("<hr/>")
            elif kind == "footnotes":
                parts.append('<div class="footnotes"><h3>Notas</h3>')
                for k, v in content.items():
                    parts.append(f'<p id="fn{k}"><sup>{k}</sup> {inline_md_to_html(v)}</p>')
                parts.append("</div>")
        parts.append("</section>")

    contracapa = IMG / "contracapa_br.png"
    if contracapa.exists():
        parts.append('<section class="cover"><img src="images/contracapa_br.png" alt="Contracapa"/></section>')

    parts.append(
        f'<footer class="book">Tradução brasileira de estudo · {datetime.now().year}<br/>'
        f"Obra original © 2018 Judea Pearl e Dana Mackenzie · Basic Books / Hachette</footer>"
    )
    parts.append("</body></html>")

    out = OUT / "O_Livro_do_Porque.html"
    # copy images ref relative: put html in tradu root, images already there
    out.write_text("\n".join(parts), encoding="utf-8")
    print("HTML:", out, "bytes", out.stat().st_size)
    return out


# ---------- LaTeX ----------
def build_latex():
    parts = [
        r"\documentclass[11pt,a5paper,twoside]{book}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[brazil]{babel}",
        r"\usepackage{geometry}",
        r"\geometry{margin=2cm}",
        r"\usepackage{graphicx}",
        r"\usepackage{setspace}",
        r"\usepackage{hyperref}",
        r"\usepackage{csquotes}",
        r"\usepackage{microtype}",
        r"\onehalfspacing",
        r"\hypersetup{colorlinks=true,linkcolor=black,urlcolor=blue}",
        rf"\title{{{TITLE}\\\large {SUBTITLE}}}",
        rf"\author{{{AUTHORS}}}",
        r"\date{Edição brasileira de estudo}",
        r"\begin{document}",
        r"\frontmatter",
        r"\maketitle",
    ]
    capa = IMG / "capa_br.png"
    if capa.exists():
        # use relative path from latex folder
        rel = os.path.relpath(capa, OUT / "latex").replace("\\", "/")
        parts.append(r"\begin{titlepage}\centering\vspace*{1cm}")
        parts.append(rf"\includegraphics[width=\textwidth]{{{rel}}}")
        parts.append(r"\end{titlepage}")

    parts.append(r"\tableofcontents")
    parts.append(r"\mainmatter")

    in_front = True
    for fname, title in CHAPTERS:
        path = PT / fname
        if not path.exists():
            continue
        if fname.startswith("11_") and in_front:
            parts.append(r"\backmatter")
            in_front = False
        # chapter heading from first h1 or title
        text = read_md(path)
        blocks = md_to_blocks(text)
        first_h1 = next((c for k, c in blocks if k == "h1"), title)
        parts.append(rf"\chapter{{{md_inline_tex(first_h1)}}}")
        for kind, content in blocks:
            if kind == "h1":
                continue  # already chapter
            elif kind == "h2":
                parts.append(rf"\section{{{md_inline_tex(content)}}}")
            elif kind == "h3":
                parts.append(rf"\subsection{{{md_inline_tex(content)}}}")
            elif kind == "p":
                parts.append(md_inline_tex(content))
                parts.append("")
            elif kind == "quote":
                parts.append(r"\begin{quote}")
                parts.append(md_inline_tex(content))
                parts.append(r"\end{quote}")
            elif kind == "ul":
                parts.append(r"\begin{itemize}")
                for it in content:
                    parts.append(rf"\item {md_inline_tex(it)}")
                parts.append(r"\end{itemize}")
            elif kind == "ol":
                parts.append(r"\begin{enumerate}")
                for it in content:
                    parts.append(rf"\item {md_inline_tex(it)}")
                parts.append(r"\end{enumerate}")
            elif kind == "hr":
                parts.append(r"\vspace{1em}\hrule\vspace{1em}")
            elif kind == "footnotes":
                parts.append(r"\section*{Notas de rodapé deste capítulo}")
                for k, v in content.items():
                    parts.append("\\paragraph{" + str(k) + ".} " + md_inline_tex(v))

    contracapa = IMG / "contracapa_br.png"
    if contracapa.exists():
        rel = os.path.relpath(contracapa, OUT / "latex").replace("\\", "/")
        parts.append(r"\clearpage\centering")
        parts.append(rf"\includegraphics[width=\textwidth]{{{rel}}}")

    parts.append(r"\end{document}")
    latex_dir = OUT / "latex"
    latex_dir.mkdir(exist_ok=True)
    out = latex_dir / "O_Livro_do_Porque.tex"
    out.write_text("\n".join(parts), encoding="utf-8")
    # also copy to root
    root_tex = OUT / "O_Livro_do_Porque.tex"
    root_tex.write_text("\n".join(parts), encoding="utf-8")
    print("LaTeX:", out, "bytes", out.stat().st_size)
    return out


# ---------- PDF (reportlab) ----------
def build_pdf():
    register_fonts()
    out = OUT / "O_Livro_do_Porque.pdf"
    page = A5  # literary size-ish
    doc = SimpleDocTemplate(
        str(out),
        pagesize=page,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
        title=TITLE,
        author=AUTHORS,
    )

    font_name = "Georgia" if "Georgia" in pdfmetrics.getRegisteredFontNames() else "Times-Roman"
    font_bold = "Georgia-Bold" if "Georgia-Bold" in pdfmetrics.getRegisteredFontNames() else "Times-Bold"
    font_italic = "Georgia-Italic" if "Georgia-Italic" in pdfmetrics.getRegisteredFontNames() else "Times-Italic"

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BodyBR",
            fontName=font_name,
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            firstLineIndent=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TitleBR",
            fontName=font_bold,
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=16,
            textColor=HexColor("#1c1c1c"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1BR",
            fontName=font_bold,
            fontSize=14,
            leading=18,
            spaceBefore=18,
            spaceAfter=10,
            textColor=HexColor("#1c1c1c"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2BR",
            fontName=font_bold,
            fontSize=12,
            leading=15,
            spaceBefore=14,
            spaceAfter=8,
            textColor=HexColor("#8c3228"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="H3BR",
            fontName=font_bold,
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="QuoteBR",
            fontName=font_italic,
            fontSize=10,
            leading=13,
            leftIndent=15,
            rightIndent=15,
            spaceBefore=8,
            spaceAfter=8,
            textColor=HexColor("#5a5a5a"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CenterBR",
            fontName=font_name,
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TOCItem",
            fontName=font_name,
            fontSize=10,
            leading=14,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FN",
            fontName=font_name,
            fontSize=8,
            leading=10,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontName=font_bold,
            fontSize=22,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )

    story = []
    page_count_holder = {"n": 0}

    def add_page_number(canvas, doc_):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(HexColor("#5a5a5a"))
        page_num = canvas.getPageNumber()
        page_count_holder["n"] = max(page_count_holder["n"], page_num)
        canvas.drawCentredString(page[0] / 2, 1.2 * cm, str(page_num))
        canvas.restoreState()

    # Capa (cabe no frame A5 com margens ~10.8 x 16.8 cm úteis)
    capa = IMG / "capa_br.png"
    if capa.exists():
        iw, ih = 10 * cm, 15 * cm
        story.append(Spacer(1, 0.4 * cm))
        story.append(RLImage(str(capa), width=iw, height=ih))
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 3 * cm))
        story.append(Paragraph(AUTHORS.upper(), styles["CenterBR"]))
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(TITLE, styles["CoverTitle"]))
        story.append(Paragraph(SUBTITLE, styles["CenterBR"]))
        story.append(PageBreak())

    # Falsa folha de rosto / créditos
    story.append(Paragraph(TITLE, styles["TitleBR"]))
    story.append(Paragraph(SUBTITLE, styles["CenterBR"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(AUTHORS, styles["CenterBR"]))
    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            "Tradução brasileira de estudo para o português brasileiro. "
            "Obra original: <i>The Book of Why: The New Science of Cause and Effect</i>, "
            "© 2018 Judea Pearl and Dana Mackenzie. Basic Books / Hachette Book Group.",
            styles["BodyBR"],
        )
    )
    story.append(
        Paragraph(
            "Esta edição inclui glossário, notas do tradutor (N. do T.) e legendas de figuras em português. "
            "Estilo editorial inspirado na tradição de não ficção científica da Companhia das Letras.",
            styles["BodyBR"],
        )
    )
    story.append(PageBreak())

    # Sumário
    story.append(Paragraph("Sumário", styles["H1BR"]))
    for fname, title in CHAPTERS:
        if (PT / fname).exists():
            story.append(safe_paragraph(title, styles["TOCItem"]))
    story.append(PageBreak())

    for fname, title in CHAPTERS:
        path = PT / fname
        if not path.exists():
            story.append(safe_paragraph(title, styles["H1BR"]))
            story.append(
                Paragraph(
                    "[Capítulo pendente de tradução — será incluído na próxima compilação.]",
                    styles["BodyBR"],
                )
            )
            story.append(PageBreak())
            continue
        blocks = md_to_blocks(read_md(path))
        first = True
        for kind, content in blocks:
            if kind == "h1":
                if not first:
                    pass
                story.append(safe_paragraph(content, styles["H1BR"]))
                first = False
            elif kind == "h2":
                story.append(safe_paragraph(content, styles["H2BR"]))
            elif kind == "h3":
                story.append(safe_paragraph(content, styles["H3BR"]))
            elif kind == "p":
                # skip empty
                if content.strip():
                    story.append(safe_paragraph(content, styles["BodyBR"]))
            elif kind == "quote":
                story.append(safe_paragraph(content, styles["QuoteBR"]))
            elif kind == "ul":
                for it in content:
                    story.append(safe_paragraph("• " + it, styles["BodyBR"]))
            elif kind == "ol":
                for n, it in enumerate(content, 1):
                    story.append(safe_paragraph(f"{n}. " + it, styles["BodyBR"]))
            elif kind == "hr":
                story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#d2c8b9")))
                story.append(Spacer(1, 6))
            elif kind == "footnotes":
                story.append(Spacer(1, 8))
                story.append(Paragraph("Notas", styles["H3BR"]))
                for k, v in content.items():
                    story.append(safe_paragraph(f"{k}. {v}", styles["FN"]))
        story.append(PageBreak())

    # Contracapa
    contracapa = IMG / "contracapa_br.png"
    if contracapa.exists():
        story.append(Spacer(1, 0.3 * cm))
        story.append(RLImage(str(contracapa), width=10 * cm, height=15 * cm))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print("PDF:", out, "bytes", out.stat().st_size, "approx pages tracked", page_count_holder["n"])
    return out


# ---------- EPUB ----------
def build_epub():
    try:
        from ebooklib import epub
    except ImportError:
        print("ebooklib missing")
        return None

    book = epub.EpubBook()
    book.set_identifier("olivrodoporque-ptbr-estudo-2018")
    book.set_title(TITLE)
    book.set_language("pt")
    book.add_author(AUTHORS)
    book.add_metadata("DC", "description", SUBTITLE)
    book.add_metadata("DC", "rights", "Traducao de estudo. Original (c) 2018 Pearl & Mackenzie")

    style = (
        "body{font-family:Georgia,serif;line-height:1.5;margin:1em;}"
        "h1{font-size:1.6em;margin-top:1.2em;}"
        "h2{font-size:1.25em;color:#8c3228;}"
        "p{text-align:justify;margin:0.7em 0;}"
        "blockquote{font-style:italic;margin:1em;color:#444;"
        "border-left:2px solid #8c3228;padding-left:0.8em;}"
    )
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/default.css",
        media_type="text/css",
        content=style.encode("utf-8"),
    )
    book.add_item(nav_css)

    capa = IMG / "capa_br.png"
    if capa.exists():
        book.set_cover("capa_br.png", capa.read_bytes())

    chapters_epub = []
    for idx, (fname, title) in enumerate(CHAPTERS):
        path = PT / fname
        if not path.exists():
            continue
        blocks = md_to_blocks(read_md(path))
        parts_html = [f"<h1>{html.escape(title)}</h1>"]
        for kind, content in blocks:
            if kind == "h1":
                parts_html.append(f"<h1>{inline_md_to_html(content)}</h1>")
            elif kind == "h2":
                parts_html.append(f"<h2>{inline_md_to_html(content)}</h2>")
            elif kind == "h3":
                parts_html.append(f"<h3>{inline_md_to_html(content)}</h3>")
            elif kind == "p":
                if content.strip():
                    parts_html.append(f"<p>{inline_md_to_html(content)}</p>")
            elif kind == "quote":
                parts_html.append(
                    f"<blockquote><p>{inline_md_to_html(content)}</p></blockquote>"
                )
            elif kind == "ul":
                parts_html.append(
                    "<ul>"
                    + "".join(f"<li>{inline_md_to_html(x)}</li>" for x in content)
                    + "</ul>"
                )
            elif kind == "ol":
                parts_html.append(
                    "<ol>"
                    + "".join(f"<li>{inline_md_to_html(x)}</li>" for x in content)
                    + "</ol>"
                )
            elif kind == "footnotes":
                parts_html.append("<hr/><h3>Notas</h3>")
                for k, v in content.items():
                    parts_html.append(
                        f"<p><sup>{html.escape(str(k))}</sup> {inline_md_to_html(v)}</p>"
                    )

        body_inner = "".join(parts_html)
        if not body_inner.strip():
            body_inner = f"<h1>{html.escape(title)}</h1><p>(vazio)</p>"

        # Body-only content; ebooklib wraps it. Avoid empty / invalid docs.
        uid = f"chap_{idx:02d}"
        c = epub.EpubHtml(
            title=title[:200],
            file_name=f"{uid}.xhtml",
            lang="pt",
            uid=uid,
        )
        c.set_content(
            f'<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml">'
            f"<head><title>{html.escape(title[:80])}</title>"
            f'<link rel="stylesheet" type="text/css" href="style/default.css"/>'
            f"</head><body>{body_inner}</body></html>"
        )
        c.add_item(nav_css)
        book.add_item(c)
        chapters_epub.append(c)

    book.toc = tuple(chapters_epub)
    book.spine = ["nav"] + chapters_epub
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    out = OUT / "O_Livro_do_Porque.epub"
    if out.exists():
        out.unlink()
    epub.write_epub(str(out), book, {})
    print("EPUB:", out, "bytes", out.stat().st_size)
    return out


def status():
    print("=== Status dos capítulos ===")
    present = 0
    for fname, title in CHAPTERS:
        ok = (PT / fname).exists()
        present += int(ok)
        words = 0
        if ok:
            words = len(read_md(PT / fname).split())
        print(f"  [{'OK' if ok else '--'}] {fname:28} {words:6} palavras  {title}")
    print(f"Presentes: {present}/{len(CHAPTERS)}")
    return present, len(CHAPTERS)


if __name__ == "__main__":
    import sys

    status()
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all", "html"):
        build_html()
    if mode in ("all", "latex", "tex"):
        build_latex()
    if mode in ("all", "pdf"):
        build_pdf()
    if mode in ("all", "epub"):
        build_epub()
    print("Done.")
