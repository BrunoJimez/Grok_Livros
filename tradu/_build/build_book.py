#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta a edição portuguesa completa de Draper:
  - História do Conflito entre a Religião e a Ciência
Saídas: .tex (LaTeX), .html, .pdf em tradu/
"""
from __future__ import annotations

import html as html_lib
import re
import textwrap
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors

ROOT = Path(__file__).resolve().parent.parent
PT = ROOT / "_pt"
OUT = ROOT

CHAPTER_FILES = [
    "00_prefacio_e_front.md",
    "01_capitulo_I.md",
    "02_capitulo_II.md",
    "03_capitulo_III.md",
    "04_capitulo_IV.md",
    "05_capitulo_V.md",
    "06_capitulo_VI.md",
    "07_capitulo_VII.md",
    "08_capitulo_VIII.md",
    "09_capitulo_IX.md",
    "10_capitulo_X.md",
    "11_capitulo_XI.md",
    "12_capitulo_XII.md",
    "13_notas_do_tradutor.md",
    "14_glossario.md",
]

TITLE_PT = "História do Conflito entre a Religião e a Ciência"
AUTHOR = "John William Draper, M.D., LL.D."
SUBTITLE_SERIES = "Série Científica Internacional — Vol. XII"
PUBLISHER = "D. Appleton and Company, Nova York, 1875"
TRANSLATION_NOTE = "Tradução portuguesa acadêmica completa — edição de estudo"


def register_fonts() -> dict:
    windir = Path(r"C:\Windows\Fonts")
    mapping = {
        "Body": ("times.ttf", "Times-Roman"),
        "Body-Bold": ("timesbd.ttf", "Times-Bold"),
        "Body-Italic": ("timesi.ttf", "Times-Italic"),
        "Body-BoldItalic": ("timesbi.ttf", "Times-BoldItalic"),
    }
    fonts = {}
    for name, (file, fallback) in mapping.items():
        path = windir / file
        if path.exists():
            pdfmetrics.registerFont(TTFont(name, str(path)))
            fonts[name] = name
        else:
            fonts[name] = fallback
    return fonts


def read_chapters() -> list[tuple[str, str]]:
    chapters = []
    missing = []
    for fn in CHAPTER_FILES:
        p = PT / fn
        if not p.exists():
            missing.append(fn)
            continue
        chapters.append((fn, p.read_text(encoding="utf-8")))
    if missing:
        raise FileNotFoundError(
            "Capítulos em falta em _pt/:\n  - " + "\n  - ".join(missing)
        )
    return chapters


def md_to_blocks(md: str) -> list[tuple[str, str]]:
    """Converte markdown simples em blocos (tipo, texto)."""
    blocks: list[tuple[str, str]] = []
    lines = md.replace("\r\n", "\n").split("\n")
    buf: list[str] = []
    mode = "p"

    def flush():
        nonlocal buf, mode
        if not buf:
            return
        text = "\n".join(buf).strip()
        buf = []
        if text:
            blocks.append((mode, text))
        mode = "p"

    for line in lines:
        if line.startswith("# "):
            flush()
            blocks.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            flush()
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            flush()
            blocks.append(("h3", line[4:].strip()))
        elif line.startswith("|") and "|" in line[1:]:
            flush()
            blocks.append(("table_line", line))
        elif re.match(r"^---+\s*$", line):
            flush()
            blocks.append(("hr", ""))
        elif line.strip() == "":
            flush()
        else:
            # lista
            if re.match(r"^(\d+\.|-|\*)\s+", line.strip()):
                if mode != "li" and buf:
                    flush()
                mode = "li"
                buf.append(line.strip())
            else:
                if mode == "li" and buf:
                    flush()
                mode = "p"
                buf.append(line)
    flush()
    return blocks


def escape_latex(s: str) -> str:
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
    return "".join(out)


def md_inline_to_latex(s: str) -> str:
    s = escape_latex(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"\*(.+?)\*", r"\\textit{\1}", s)
    s = re.sub(r"`(.+?)`", r"\\texttt{\1}", s)
    return s


def md_inline_to_html(s: str) -> str:
    s = html_lib.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def md_inline_to_rl(s: str) -> str:
    s = html_lib.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", s)
    return s


def build_latex(chapters: list[tuple[str, str]]) -> str:
    parts = [
        r"""\documentclass[11pt,a5paper,twoside,openany]{book}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazilian]{babel}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{geometry}
\geometry{a5paper,margin=1.8cm,top=2cm,bottom=2.2cm}
\usepackage{setspace}
\onehalfspacing
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{hyperref}
\usepackage{longtable}
\usepackage{array}
\usepackage{booktabs}
\usepackage{enumitem}
\hypersetup{colorlinks=true,linkcolor=black,urlcolor=blue,citecolor=black}

\titleformat{\chapter}[display]
  {\normalfont\Large\bfseries\centering}{\chaptertitlename\ \thechapter}{12pt}{\LARGE}
\titleformat{\section}{\normalfont\large\bfseries\centering}{\thesection}{0.5em}{}
\titleformat{\subsection}{\normalfont\normalsize\bfseries}{\thesubsection}{0.5em}{}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE]{\small\textit{Draper}}
\fancyhead[RO]{\small\textit{Conflito entre Religião e Ciência}}
\fancyfoot[C]{\thepage}
\setlength{\headheight}{14pt}

\begin{document}

% ========== CAPA ==========
\begin{titlepage}
\centering
\vspace*{1.5cm}
{\small SÉRIE CIENTÍFICA INTERNACIONAL}\\[4pt]
{\small VOL.\ XII}\\[2cm]
{\LARGE\bfseries HISTÓRIA}\\[8pt]
{\large DO}\\[8pt]
{\LARGE\bfseries CONFLITO}\\[8pt]
{\large ENTRE A}\\[8pt]
{\LARGE\bfseries RELIGIÃO E A CIÊNCIA}\\[2.5cm]
{\large POR}\\[12pt]
{\Large JOHN WILLIAM DRAPER, M.D., LL.D.}\\[18pt]
{\small\itshape Professor na Universidade de Nova York; autor de um}\\
{\small\itshape «Tratado de Fisiologia Humana»; «História do Desenvolvimento}\\
{\small\itshape Intelectual da Europa»; «História da Guerra Civil Americana»;}\\
{\small\itshape e de muitas memórias experimentais sobre assuntos}\\
{\small\itshape químicos e outros temas científicos.}\\[2.5cm]
{\normalsize NOVA YORK:}\\[4pt]
{\normalsize D.\ APPLETON AND COMPANY}\\[2pt]
{\small 549 \& 551 BROADWAY}\\[8pt]
{\normalsize 1875}\\[1.5cm]
{\footnotesize\textit{Tradução portuguesa acadêmica completa}}\\
{\footnotesize\textit{Edição de estudo com notas do tradutor e glossário}}
\end{titlepage}

% ========== CONTRACAPA / FICHA ==========
\thispagestyle{empty}
\vspace*{3cm}
\begin{center}
{\small Entrada, conforme o Ato do Congresso, no ano de 1874, por}\\[6pt]
{\small JOHN WILLIAM DRAPER, M.D., LL.D.,}\\[6pt]
{\small no Escritório do Bibliotecário do Congresso, em Washington.}\\[2cm]
{\small Esta edição em português reproduz integralmente o conteúdo}\\
{\small da obra original em domínio público.}\\[1cm]
{\small Formatação inspirada na edição Appleton, 1875,}\\
{\small da \textit{International Scientific Series}.}
\end{center}
\newpage

\tableofcontents
\newpage
"""
    ]

    for fn, md in chapters:
        blocks = md_to_blocks(md)
        table_buf: list[str] = []

        def flush_table():
            nonlocal table_buf
            if not table_buf:
                return
            # parse markdown table
            rows = []
            for tl in table_buf:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                if all(re.match(r"^:?-+:?$", c.replace(" ", "")) for c in cells):
                    continue
                rows.append(cells)
            table_buf = []
            if not rows:
                return
            ncol = max(len(r) for r in rows)
            colspec = " ".join(["X"] * ncol) if False else ("l" * ncol)
            # use longtable with p columns
            colspec = " | ".join([r"p{0.28\textwidth}"] * ncol)
            parts.append(r"\begin{longtable}{" + colspec + "}")
            for i, row in enumerate(rows):
                while len(row) < ncol:
                    row.append("")
                parts.append(
                    " & ".join(md_inline_to_latex(c) for c in row) + r" \\"
                )
                if i == 0:
                    parts.append(r"\hline")
            parts.append(r"\end{longtable}")
            parts.append("")

        first_h1 = True
        for kind, text in blocks:
            if kind == "table_line":
                table_buf.append(text)
                continue
            else:
                flush_table()

            if kind == "h1":
                # Prefácio e apêndices sem numeração automática se já contêm o título
                t = text.strip()
                if first_h1 and (
                    "PREFÁCIO" in t.upper()
                    or "PREFACIO" in t.upper()
                    or "CAPÍTULO" in t.upper()
                    or "CAPITULO" in t.upper()
                    or "NOTAS" in t.upper()
                    or "GLOSSÁRIO" in t.upper()
                    or "GLOSSARIO" in t.upper()
                    or "HISTÓRIA" in t.upper()
                    or "HISTORIA" in t.upper()
                ):
                    parts.append(r"\chapter*{" + md_inline_to_latex(t) + "}")
                    parts.append(r"\addcontentsline{toc}{chapter}{" + md_inline_to_latex(t) + "}")
                else:
                    parts.append(r"\chapter*{" + md_inline_to_latex(t) + "}")
                    parts.append(r"\addcontentsline{toc}{chapter}{" + md_inline_to_latex(t) + "}")
                first_h1 = False
            elif kind == "h2":
                parts.append(r"\section*{" + md_inline_to_latex(text) + "}")
            elif kind == "h3":
                parts.append(r"\subsection*{" + md_inline_to_latex(text) + "}")
            elif kind == "hr":
                parts.append(r"\par\medskip\noindent\hrulefill\par\medskip")
            elif kind == "li":
                parts.append(r"\begin{itemize}")
                for item in text.split("\n"):
                    item = re.sub(r"^(\d+\.|-|\*)\s+", "", item.strip())
                    parts.append(r"\item " + md_inline_to_latex(item))
                parts.append(r"\end{itemize}")
            else:
                # paragraphs: split double newlines already handled; wrap long para
                para = " ".join(text.split())
                parts.append(md_inline_to_latex(para))
                parts.append("")
        flush_table()
        parts.append(r"\clearpage")

    # Capa final
    parts.append(
        r"""
\thispagestyle{empty}
\vspace*{4cm}
\begin{center}
{\Large\bfseries FIM}\\[2cm]
{\large HISTÓRIA DO CONFLITO}\\
{\large ENTRE A RELIGIÃO E A CIÊNCIA}\\[1cm]
{\normalsize John William Draper}\\[2cm]
{\small Edição original: Nova York, D.\ Appleton and Company, 1875.}\\[8pt]
{\small Domínio público.}\\[1.5cm]
{\small Tradução portuguesa acadêmica com notas e glossário.}\\[8pt]
{\small Gerada para estudo e consulta.}
\end{center}
\end{document}
"""
    )
    return "\n".join(parts)


def build_html(chapters: list[tuple[str, str]]) -> str:
    css = """
:root { --fg:#1a1a1a; --muted:#444; --bg:#f7f3ea; --paper:#fffdf7; --accent:#3a2f1e; }
* { box-sizing: border-box; }
body {
  margin: 0; font-family: "Times New Roman", Times, Georgia, serif;
  color: var(--fg); background: var(--bg); line-height: 1.65;
}
.page {
  max-width: 42rem; margin: 0 auto; background: var(--paper);
  padding: 2.5rem 2rem 3rem; box-shadow: 0 0 0 1px #ddd, 0 8px 30px rgba(0,0,0,.08);
}
@media (min-width: 700px) { .page { padding: 3rem 3.5rem 4rem; margin: 1.5rem auto; } }
.cover {
  min-height: 85vh; display:flex; flex-direction:column; justify-content:center;
  text-align:center; border: 2px solid var(--accent); padding: 2rem 1.5rem;
  margin-bottom: 2rem;
}
.cover .series { letter-spacing: .12em; font-size: .85rem; text-transform: uppercase; }
.cover h1 { font-size: 1.85rem; margin: 1.2rem 0 .4rem; line-height: 1.25; }
.cover .by { margin-top: 1.5rem; font-size: .95rem; }
.cover .author { font-size: 1.15rem; font-weight: bold; margin: .6rem 0; }
.cover .pub { margin-top: 2rem; font-size: .95rem; }
.cover .tr { margin-top: 1.5rem; font-size: .8rem; font-style: italic; color: var(--muted); }
.verso { text-align:center; color: var(--muted); font-size: .9rem; margin: 2rem 0 3rem; }
nav#toc { margin: 2rem 0 3rem; }
nav#toc h2 { text-align:center; }
nav#toc ol { line-height: 1.9; }
h1.chap { font-size: 1.5rem; text-align:center; margin: 2.5rem 0 1rem; page-break-before: always; }
h2 { font-size: 1.15rem; text-align:center; margin: 1.8rem 0 1rem; }
h3 { font-size: 1.05rem; margin: 1.4rem 0 .7rem; }
p { text-align: justify; hyphens: auto; margin: 0 0 .9rem; text-indent: 1.25em; }
h1 + p, h2 + p, h3 + p { text-indent: 0; }
table { width:100%; border-collapse: collapse; font-size: .88rem; margin: 1rem 0 1.5rem; }
th, td { border: 1px solid #bbb; padding: .4rem .5rem; vertical-align: top; text-align: left; }
th { background: #efe8d8; }
hr { border: none; border-top: 1px solid #aaa; margin: 2rem 0; }
.back-cover {
  margin-top: 3rem; min-height: 60vh; border: 2px solid var(--accent);
  display:flex; flex-direction:column; justify-content:center; text-align:center; padding: 2rem;
}
footer.meta { text-align:center; color: var(--muted); font-size: .8rem; margin-top: 2rem; }
a { color: #243b6b; }
"""
    body_parts = [
        f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html_lib.escape(TITLE_PT)} — {html_lib.escape(AUTHOR)}</title>
<meta name="author" content="{html_lib.escape(AUTHOR)}"/>
<meta name="description" content="Tradução portuguesa completa da obra de John William Draper (1875)."/>
<style>{css}</style>
</head>
<body>
<div class="page">
<section class="cover" id="capa">
  <div class="series">Série Científica Internacional · Vol. XII</div>
  <h1>HISTÓRIA<br/>DO CONFLITO<br/>ENTRE A<br/>RELIGIÃO E A CIÊNCIA</h1>
  <div class="by">POR</div>
  <div class="author">JOHN WILLIAM DRAPER, M.D., LL.D.</div>
  <p style="text-indent:0;font-size:.85rem;color:var(--muted);max-width:28rem;margin:0 auto;">
  Professor na Universidade de Nova York; autor de um «Tratado de Fisiologia Humana»,
  «História do Desenvolvimento Intelectual da Europa», «História da Guerra Civil Americana»
  e de muitas memórias experimentais sobre assuntos químicos e outros temas científicos.
  </p>
  <div class="pub">NOVA YORK<br/>D. APPLETON AND COMPANY<br/>549 &amp; 551 BROADWAY<br/><strong>1875</strong></div>
  <div class="tr">{html_lib.escape(TRANSLATION_NOTE)}</div>
</section>

<section class="verso" id="contracapa">
  <p style="text-indent:0">Entrada, conforme o Ato do Congresso, no ano de 1874, por<br/>
  <strong>JOHN WILLIAM DRAPER, M.D., LL.D.</strong><br/>
  no Escritório do Bibliotecário do Congresso, em Washington.</p>
  <p style="text-indent:0">Obra original em domínio público.<br/>
  Formatação inspirada na edição Appleton, 1875.</p>
</section>

<nav id="toc">
  <h2>Sumário</h2>
  <ol>
"""
    ]

    # TOC entries from h1s
    toc_items = []
    content_html = []
    chap_id = 0
    for fn, md in chapters:
        blocks = md_to_blocks(md)
        table_buf = []

        def flush_table_html(out_list, buf):
            if not buf:
                return []
            rows = []
            for tl in buf:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                if all(re.match(r"^:?-+:?$", c.replace(" ", "")) for c in cells):
                    continue
                rows.append(cells)
            if not rows:
                return []
            html_rows = ["<table>"]
            for i, row in enumerate(rows):
                tag = "th" if i == 0 else "td"
                html_rows.append(
                    "<tr>"
                    + "".join(f"<{tag}>{md_inline_to_html(c)}</{tag}>" for c in row)
                    + "</tr>"
                )
            html_rows.append("</table>")
            return html_rows

        for kind, text in blocks:
            if kind == "table_line":
                table_buf.append(text)
                continue
            if table_buf:
                content_html.extend(flush_table_html(content_html, table_buf))
                table_buf = []
            if kind == "h1":
                chap_id += 1
                aid = f"c{chap_id}"
                toc_items.append(
                    f'<li><a href="#{aid}">{html_lib.escape(text)}</a></li>'
                )
                content_html.append(
                    f'<h1 class="chap" id="{aid}">{md_inline_to_html(text)}</h1>'
                )
            elif kind == "h2":
                content_html.append(f"<h2>{md_inline_to_html(text)}</h2>")
            elif kind == "h3":
                content_html.append(f"<h3>{md_inline_to_html(text)}</h3>")
            elif kind == "hr":
                content_html.append("<hr/>")
            elif kind == "li":
                content_html.append("<ul>")
                for item in text.split("\n"):
                    item = re.sub(r"^(\d+\.|-|\*)\s+", "", item.strip())
                    content_html.append(f"<li>{md_inline_to_html(item)}</li>")
                content_html.append("</ul>")
            else:
                para = " ".join(text.split())
                content_html.append(f"<p>{md_inline_to_html(para)}</p>")
        if table_buf:
            content_html.extend(flush_table_html(content_html, table_buf))

    body_parts.append("\n".join(toc_items))
    body_parts.append("</ol>\n</nav>\n")
    body_parts.append("\n".join(content_html))
    body_parts.append(
        f"""
<section class="back-cover" id="capa-final">
  <h2 style="border:none;">FIM</h2>
  <p style="text-indent:0"><strong>{html_lib.escape(TITLE_PT)}</strong></p>
  <p style="text-indent:0">{html_lib.escape(AUTHOR)}</p>
  <p style="text-indent:0">Edição original: {html_lib.escape(PUBLISHER)}.<br/>Domínio público.</p>
  <p style="text-indent:0;font-size:.9rem;color:var(--muted)">Tradução portuguesa acadêmica com notas do tradutor e glossário de termos.</p>
</section>
<footer class="meta">Edição de estudo · PDF · HTML · LaTeX</footer>
</div>
</body>
</html>
"""
    )
    return "".join(body_parts)


def build_pdf(chapters: list[tuple[str, str]], out_path: Path) -> int:
    fonts = register_fonts()
    page = A5  # próximo do formato de bolso da International Scientific Series
    width, height = page

    doc = BaseDocTemplate(
        str(out_path),
        pagesize=page,
        leftMargin=1.7 * cm,
        rightMargin=1.7 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=TITLE_PT,
        author=AUTHOR,
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
    )

    def add_page_number(canvas, doc_):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        canvas.setFont(fonts["Body"], 9)
        # header
        if page_num > 2:
            canvas.setFont(fonts["Body-Italic"], 8)
            if page_num % 2 == 0:
                canvas.drawString(doc.leftMargin, height - 1.2 * cm, "Draper")
            else:
                canvas.drawRightString(
                    width - doc.rightMargin,
                    height - 1.2 * cm,
                    "Conflito entre Religião e Ciência",
                )
            canvas.setFont(fonts["Body"], 9)
            canvas.drawCentredString(width / 2, 1.0 * cm, str(page_num))
        canvas.restoreState()

    def blank_page(canvas, doc_):
        canvas.saveState()
        canvas.restoreState()

    doc.addPageTemplates(
        [
            PageTemplate(id="cover", frames=[frame], onPage=blank_page),
            PageTemplate(id="main", frames=[frame], onPage=add_page_number),
        ]
    )

    styles = getSampleStyleSheet()
    body_name = fonts["Body"]
    bold_name = fonts["Body-Bold"]
    italic_name = fonts["Body-Italic"]

    style_cover_series = ParagraphStyle(
        "CoverSeries",
        fontName=body_name,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    style_cover_title = ParagraphStyle(
        "CoverTitle",
        fontName=bold_name,
        fontSize=14,
        leading=17,
        alignment=TA_CENTER,
        spaceBefore=3,
        spaceAfter=3,
    )
    style_cover_sub = ParagraphStyle(
        "CoverSub",
        fontName=body_name,
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    style_cover_author = ParagraphStyle(
        "CoverAuthor",
        fontName=bold_name,
        fontSize=11,
        leading=13,
        alignment=TA_CENTER,
        spaceBefore=6,
        spaceAfter=4,
    )
    style_cover_bio = ParagraphStyle(
        "CoverBio",
        fontName=italic_name,
        fontSize=7.5,
        leading=10,
        alignment=TA_CENTER,
        spaceAfter=3,
    )
    style_cover_pub = ParagraphStyle(
        "CoverPub",
        fontName=body_name,
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=1,
    )
    style_h1 = ParagraphStyle(
        "H1",
        fontName=bold_name,
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        spaceBefore=12,
        spaceAfter=14,
    )
    style_h2 = ParagraphStyle(
        "H2",
        fontName=bold_name,
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        spaceBefore=12,
        spaceAfter=10,
    )
    style_h3 = ParagraphStyle(
        "H3",
        fontName=bold_name,
        fontSize=10.5,
        leading=13,
        alignment=TA_LEFT,
        spaceBefore=10,
        spaceAfter=6,
    )
    style_body = ParagraphStyle(
        "BodyJust",
        fontName=body_name,
        fontSize=10,
        leading=13.5,
        alignment=TA_JUSTIFY,
        firstLineIndent=14,
        spaceAfter=6,
    )
    style_body_first = ParagraphStyle(
        "BodyFirst",
        parent=style_body,
        firstLineIndent=0,
    )
    style_li = ParagraphStyle(
        "Li",
        fontName=body_name,
        fontSize=10,
        leading=13,
        leftIndent=12,
        spaceAfter=3,
    )
    style_center = ParagraphStyle(
        "Center",
        fontName=body_name,
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
    )
    style_toc = ParagraphStyle(
        "TOC",
        fontName=body_name,
        fontSize=10,
        leading=14,
        leftIndent=10,
        spaceAfter=3,
    )

    story = []
    # CAPA
    story.append(NextPageTemplate("cover"))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("SÉRIE CIENTÍFICA INTERNACIONAL", style_cover_series))
    story.append(Paragraph("VOL. XII", style_cover_series))
    story.append(Spacer(1, 0.55 * cm))
    story.append(Paragraph("HISTÓRIA", style_cover_title))
    story.append(Paragraph("DO", style_cover_sub))
    story.append(Paragraph("CONFLITO", style_cover_title))
    story.append(Paragraph("ENTRE A", style_cover_sub))
    story.append(Paragraph("RELIGIÃO E A CIÊNCIA", style_cover_title))
    story.append(Spacer(1, 0.45 * cm))
    story.append(Paragraph("POR", style_cover_sub))
    story.append(Paragraph("JOHN WILLIAM DRAPER, M.D., LL.D.", style_cover_author))
    story.append(
        Paragraph(
            "Professor na Universidade de Nova York; autor de um «Tratado de Fisiologia Humana»; "
            "«História do Desenvolvimento Intelectual da Europa»; «História da Guerra Civil Americana»; "
            "e de muitas memórias experimentais sobre assuntos químicos e outros temas científicos.",
            style_cover_bio,
        )
    )
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("NOVA YORK:", style_cover_pub))
    story.append(Paragraph("D. APPLETON AND COMPANY", style_cover_pub))
    story.append(Paragraph("549 &amp; 551 BROADWAY", style_cover_pub))
    story.append(Paragraph("<b>1875</b>", style_cover_pub))
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            "<i>Tradução portuguesa acadêmica completa<br/>Edição de estudo com notas e glossário</i>",
            style_center,
        )
    )

    # CONTRACAPA
    story.append(PageBreak())
    story.append(Spacer(1, 3 * cm))
    story.append(
        Paragraph(
            "Entrada, conforme o Ato do Congresso, no ano de 1874, por",
            style_center,
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph("<b>JOHN WILLIAM DRAPER, M.D., LL.D.</b>", style_center)
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "no Escritório do Bibliotecário do Congresso, em Washington.",
            style_center,
        )
    )
    story.append(Spacer(1, 2 * cm))
    story.append(
        Paragraph(
            "Esta edição em português reproduz integralmente o conteúdo<br/>"
            "da obra original em domínio público.<br/><br/>"
            "Formatação inspirada na edição Appleton, 1875,<br/>"
            "da <i>International Scientific Series</i>.",
            style_center,
        )
    )

    # SUMÁRIO simplificado
    story.append(NextPageTemplate("main"))
    story.append(PageBreak())
    story.append(Paragraph("SUMÁRIO", style_h1))
    for fn, md in chapters:
        for kind, text in md_to_blocks(md):
            if kind == "h1":
                story.append(Paragraph(f"• {md_inline_to_rl(text)}", style_toc))
                break

    # CORPO
    for fn, md in chapters:
        story.append(PageBreak())
        blocks = md_to_blocks(md)
        after_heading = True
        table_buf: list[str] = []

        def flush_table():
            nonlocal table_buf
            if not table_buf:
                return
            rows_raw = []
            for tl in table_buf:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                if all(re.match(r"^:?-+:?$", c.replace(" ", "")) for c in cells):
                    continue
                rows_raw.append(cells)
            table_buf = []
            if not rows_raw:
                return
            data = []
            for row in rows_raw:
                data.append(
                    [
                        Paragraph(md_inline_to_rl(c), style_li)
                        for c in row
                    ]
                )
            ncol = max(len(r) for r in data)
            for r in data:
                while len(r) < ncol:
                    r.append(Paragraph("", style_li))
            col_w = doc.width / ncol
            t = Table(data, colWidths=[col_w] * ncol, repeatRows=1)
            t.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.93, 0.90, 0.82)),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(Spacer(1, 6))
            story.append(t)
            story.append(Spacer(1, 8))

        for kind, text in blocks:
            if kind == "table_line":
                table_buf.append(text)
                continue
            flush_table()
            if kind == "h1":
                story.append(Paragraph(md_inline_to_rl(text), style_h1))
                after_heading = True
            elif kind == "h2":
                story.append(Paragraph(md_inline_to_rl(text), style_h2))
                after_heading = True
            elif kind == "h3":
                story.append(Paragraph(md_inline_to_rl(text), style_h3))
                after_heading = True
            elif kind == "hr":
                story.append(Spacer(1, 8))
            elif kind == "li":
                for item in text.split("\n"):
                    item = re.sub(r"^(\d+\.|-|\*)\s+", "", item.strip())
                    story.append(Paragraph(f"• {md_inline_to_rl(item)}", style_li))
                after_heading = False
            else:
                para = " ".join(text.split())
                st = style_body_first if after_heading else style_body
                story.append(Paragraph(md_inline_to_rl(para), st))
                after_heading = False
        flush_table()

    # CAPA FINAL
    story.append(PageBreak())
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("FIM", style_h1))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("HISTÓRIA DO CONFLITO", style_cover_sub))
    story.append(Paragraph("ENTRE A RELIGIÃO E A CIÊNCIA", style_cover_sub))
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("John William Draper", style_cover_author))
    story.append(Spacer(1, 1.5 * cm))
    story.append(
        Paragraph(
            "Edição original: Nova York, D. Appleton and Company, 1875.<br/>"
            "Domínio público.<br/><br/>"
            "Tradução portuguesa acadêmica com notas e glossário.<br/>"
            "Gerada para estudo e consulta.",
            style_center,
        )
    )

    doc.build(story)
    # page count from file via fitz if available
    try:
        import fitz

        d = fitz.open(str(out_path))
        n = d.page_count
        d.close()
        return n
    except Exception:
        return -1


def main():
    print("Lendo capítulos traduzidos...")
    chapters = read_chapters()
    print(f"  {len(chapters)} arquivos")

    tex_path = OUT / "Historia_do_Conflito_entre_Religiao_e_Ciencia.tex"
    html_path = OUT / "Historia_do_Conflito_entre_Religiao_e_Ciencia.html"
    pdf_path = OUT / "Historia_do_Conflito_entre_Religiao_e_Ciencia.pdf"

    print("Gerando LaTeX...")
    tex = build_latex(chapters)
    tex_path.write_text(tex, encoding="utf-8")
    print(f"  -> {tex_path}")

    print("Gerando HTML...")
    html = build_html(chapters)
    html_path.write_text(html, encoding="utf-8")
    print(f"  -> {html_path}")

    print("Gerando PDF (ReportLab)...")
    n = build_pdf(chapters, pdf_path)
    print(f"  -> {pdf_path} ({n} páginas)" if n > 0 else f"  -> {pdf_path}")

    # stats
    total_words = 0
    for _, md in chapters:
        total_words += len(md.split())
    print(f"Palavras PT (aprox.): {total_words}")
    print("Concluído.")


if __name__ == "__main__":
    main()
