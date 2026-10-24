# -*- coding: utf-8 -*-
"""
Gera versões em português de figuras/tabelas com texto em inglês
e regenera a obra em tradu/novo sem legendas duplicadas.
"""
from __future__ import annotations

import re
import shutil
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\Users\Hugo\Documents\grok\The_Book\tradu")
NOVO = ROOT / "novo"
FIG = NOVO / "figuras"
FIG_PT = NOVO / "figuras_pt"
ORIG_FIG = FIG


def font(size, bold=False):
    paths = (
        [
            r"C:\Windows\Fonts\georgiab.ttf",
            r"C:\Windows\Fonts\timesbd.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ]
        if bold
        else [
            r"C:\Windows\Fonts\georgia.ttf",
            r"C:\Windows\Fonts\times.ttf",
            r"C:\Windows\Fonts\arial.ttf",
        ]
    )
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap_draw(draw, text, fnt, max_w):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def make_ladder_pt():
    """Figura 1.2 — Escada da Causalidade, painéis de texto em PT-BR.
    Mantém a ilustração da escada (lado esquerdo) e redesenha as caixas.
    """
    src = ORIG_FIG / "fig_1_2.png"
    if not src.exists():
        print("fig_1_2 missing")
        return None
    im = Image.open(src).convert("RGB")
    w, h = im.size
    # Crop left illustration (~45% of width) and rebuild full image
    left_w = int(w * 0.42)
    left = im.crop((0, 0, left_w, h))

    # New canvas
    new_w = int(w * 1.05)
    out = Image.new("RGB", (new_w, h), (255, 255, 255))
    out.paste(left, (0, 0))
    d = ImageDraw.Draw(out)

    # Overwrite English rung labels on left if still visible near rungs
    # Paint white over SEEING/DOING/IMAGINING areas and rewrite in PT
    # Approximate positions based on original composition
    f_rung = font(max(18, h // 45), bold=True)
    # These y positions are approximate fractions of height
    rungs = [
        (0.78, "VER"),
        (0.48, "FAZER"),
        (0.18, "IMAGINAR"),
    ]
    for yf, label in rungs:
        y = int(h * yf)
        # white bar on plank
        d.rectangle([int(left_w * 0.12), y - 8, int(left_w * 0.88), y + 22], fill=(255, 255, 255))
        # center text
        bb = d.textbbox((0, 0), label, font=f_rung)
        tw = bb[2] - bb[0]
        d.text(((left_w - tw) // 2, y - 4), label, font=f_rung, fill=(20, 20, 20))

    # Right-side boxes
    box_x0 = left_w + 20
    box_x1 = new_w - 20
    box_w = box_x1 - box_x0
    f_title = font(max(20, h // 42), bold=True)
    f_lab = font(max(15, h // 55), bold=True)
    f_body = font(max(14, h // 58))
    f_it = font(max(13, h // 62))

    boxes = [
        {
            "y0": 0.06,
            "y1": 0.34,
            "title": "3. CONTRAFACTUAIS",
            "lines": [
                ("ATIVIDADE:", "Imaginar, introspecção, compreensão"),
                (
                    "PERGUNTAS:",
                    "E se eu tivesse feito…? Por quê? (Foi X que causou Y? E se X não tivesse ocorrido? E se eu tivesse agido de outro modo?)",
                ),
                (
                    "EXEMPLOS:",
                    "Foi a aspirina que fez passar a dor de cabeça? Kennedy estaria vivo se Oswald não o tivesse matado? E se eu não tivesse fumado nos últimos 2 anos?",
                ),
            ],
        },
        {
            "y0": 0.37,
            "y1": 0.62,
            "title": "2. INTERVENÇÃO",
            "lines": [
                ("ATIVIDADE:", "Fazer, intervir"),
                (
                    "PERGUNTAS:",
                    "E se eu fizer…? Como? (O que seria de Y se eu fizer X? Como faço Y acontecer?)",
                ),
                (
                    "EXEMPLOS:",
                    "Se eu tomar aspirina, a dor de cabeça passa? E se proibirmos o cigarro?",
                ),
            ],
        },
        {
            "y0": 0.65,
            "y1": 0.92,
            "title": "1. ASSOCIAÇÃO",
            "lines": [
                ("ATIVIDADE:", "Ver, observar"),
                (
                    "PERGUNTAS:",
                    "E se eu vir…? (Como as variáveis se relacionam? Ver X muda minha crença em Y?)",
                ),
                (
                    "EXEMPLOS:",
                    "O que um sintoma me diz sobre uma doença? O que uma pesquisa diz sobre o resultado da eleição?",
                ),
            ],
        },
    ]

    for b in boxes:
        y0 = int(h * b["y0"])
        y1 = int(h * b["y1"])
        d.rectangle([box_x0, y0, box_x1, y1], outline=(30, 30, 30), width=2, fill=(255, 255, 255))
        y = y0 + 12
        d.text((box_x0 + 14, y), b["title"], font=f_title, fill=(20, 20, 20))
        y += 32
        for lab, body in b["lines"]:
            d.text((box_x0 + 14, y), lab, font=f_lab, fill=(20, 20, 20))
            lab_w = d.textbbox((0, 0), lab, font=f_lab)[2] + 8
            # body wrapped
            max_body = box_w - lab_w - 28
            # put body on same line if short, else next lines
            lines = wrap_draw(d, body, f_body, max_body)
            if not lines:
                continue
            d.text((box_x0 + 14 + lab_w, y), lines[0], font=f_body, fill=(40, 40, 40))
            y += 20
            for ln in lines[1:]:
                d.text((box_x0 + 14 + lab_w, y), ln, font=f_body, fill=(40, 40, 40))
                y += 18
            y += 8

    # footer note
    d.text((box_x0, h - 28), "Edição BR — legendas e painéis em português", font=f_it, fill=(100, 100, 100))

    FIG_PT.mkdir(parents=True, exist_ok=True)
    out_path = FIG_PT / "fig_1_2.png"
    out.save(out_path, "PNG")
    # also overwrite main figuras used by documents
    out.save(FIG / "fig_1_2.png", "PNG")
    print("PT ladder:", out_path)
    return out_path


def make_table(fname, title, headers, rows, col_widths=None):
    """Simple Portuguese table image."""
    pad = 16
    f_title = font(18, bold=True)
    f_head = font(14, bold=True)
    f_cell = font(13)
    # measure
    tmp = Image.new("RGB", (10, 10), "white")
    d0 = ImageDraw.Draw(tmp)
    n = len(headers)
    if col_widths is None:
        col_widths = []
        for j in range(n):
            vals = [headers[j]] + [str(r[j]) for r in rows]
            wmax = max(d0.textbbox((0, 0), v, font=f_head if i == 0 else f_cell)[2] for i, v in enumerate(vals))
            col_widths.append(wmax + 24)
    row_h = 32
    title_h = 40
    W = sum(col_widths) + pad * 2
    H = title_h + row_h * (1 + len(rows)) + pad * 2
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.text((pad, 10), title, font=f_title, fill=(20, 20, 20))
    y = title_h
    x = pad
    # header bg
    d.rectangle([pad, y, W - pad, y + row_h], fill=(240, 235, 225))
    for j, h in enumerate(headers):
        d.text((x + 8, y + 8), h, font=f_head, fill=(20, 20, 20))
        x += col_widths[j]
    y += row_h
    for ri, row in enumerate(rows):
        x = pad
        bg = (255, 255, 255) if ri % 2 == 0 else (250, 248, 244)
        d.rectangle([pad, y, W - pad, y + row_h], fill=bg)
        for j, cell in enumerate(row):
            d.text((x + 8, y + 8), str(cell), font=f_cell, fill=(30, 30, 30))
            x += col_widths[j]
        y += row_h
    # border
    d.rectangle([pad, title_h, W - pad, title_h + row_h * (1 + len(rows))], outline=(80, 80, 80), width=1)
    FIG_PT.mkdir(parents=True, exist_ok=True)
    path = FIG_PT / fname
    im.save(path, "PNG")
    im.save(FIG / fname, "PNG")
    print("table", path)
    return path


def make_tables_pt():
    make_table(
        "tab_3_1.png",
        "Tabela 3.1 — Dados fictícios do exemplo chá e scones",
        ["", "Scones", "Sem scones", "Total"],
        [
            ["Chá", "3", "1", "4"],
            ["Sem chá", "1", "3", "4"],
            ["Total", "4", "4", "8"],
        ],
    )
    make_table(
        "tab_3_2.png",
        "Tabela 3.2 — Tabela de probabilidade condicional simples",
        ["D (doença)", "P(T=positivo | D)", "P(T=negativo | D)"],
        [
            ["D = 1 (doente)", "0,90", "0,10"],
            ["D = 0 (sadio)", "0,12", "0,88"],
        ],
    )
    make_table(
        "tab_6_1.png",
        "Tabela 6.1 — Arranjos possíveis em Let's Make a Deal",
        ["Porta 1", "Porta 2", "Porta 3", "Monty abre", "Trocar ganha?"],
        [
            ["Carro", "Cabra", "Cabra", "2 ou 3", "Não"],
            ["Cabra", "Carro", "Cabra", "3", "Sim"],
            ["Cabra", "Cabra", "Carro", "2", "Sim"],
        ],
    )
    make_table(
        "tab_6_4.png",
        "Tabela 6.4 — Dados fictícios do paradoxo de Simpson",
        ["Grupo", "Recuperados (trat.)", "Total (trat.)", "Recuperados (contr.)", "Total (contr.)"],
        [
            ["Homens", "18", "30", "7", "10"],
            ["Mulheres", "2", "10", "9", "30"],
            ["Combinado", "20", "40", "16", "40"],
        ],
    )
    make_table(
        "tab_8_1.png",
        "Tabela 8.1 — Dados fictícios de resultados potenciais (salário)",
        ["Nome", "EX", "ED", "S", "S0", "S1", "S2"],
        [
            ["Alice", "6", "0", "81.000", "81.000", "?", "?"],
            ["Bert", "9", "1", "92.500", "?", "92.500", "?"],
            ["Caroline", "9", "2", "97.000", "?", "?", "97.000"],
            ["David", "8", "1", "91.000", "?", "91.000", "?"],
            ["Ernest", "12", "1", "100.000", "?", "100.000", "?"],
            ["Frances", "13", "0", "96.000", "96.000", "?", "?"],
        ],
    )


def make_caption_banner(key_num: str, title_pt: str, out_name: str, base_img: Path | None = None):
    """Overlay a Portuguese title banner on top of an existing figure."""
    if base_img and base_img.exists():
        base = Image.open(base_img).convert("RGB")
        w, h = base.size
        banner_h = max(48, h // 18)
        out = Image.new("RGB", (w, h + banner_h), (250, 247, 240))
        d = ImageDraw.Draw(out)
        f = font(max(16, banner_h // 2), bold=True)
        label = f"Figura {key_num} — {title_pt}"
        # wrap
        lines = wrap_draw(d, label, f, w - 40)
        y = 8
        for ln in lines[:3]:
            d.text((20, y), ln, font=f, fill=(28, 28, 28))
            y += banner_h // max(2, len(lines))
        out.paste(base, (0, banner_h))
        # subtle note
        fn = font(max(11, banner_h // 3))
        d.text((20, h + banner_h - 18), "Legenda e título em português (edição BR)", font=fn, fill=(120, 90, 55))
        path = FIG_PT / out_name
        FIG_PT.mkdir(parents=True, exist_ok=True)
        out.save(path, "PNG")
        out.save(FIG / out_name, "PNG")
        print("banner", out_name)
        return path
    return None


def make_key_banners():
    banners = [
        ("1.1", "Causas percebidas de uma caçada bem-sucedida a mamutes", "fig_1_1.png"),
        ("1.3", "O Homem-Leão da caverna de Stadel", "fig_1_3.png"),
        ("1.4", "Diagrama causal do pelotão de fuzilamento", "fig_1_4.png"),
        ("1.5", "Raciocínio sobre intervenções", "fig_1_5.png"),
        ("1.6", "Raciocínio contrafactual", "fig_1_6.png"),
        ("1.7", "Diagrama causal do exemplo da vacinação", "fig_1_7.png"),
        ("2.1", "O tabuleiro de Galton (quincunce)", "fig_2_1.png"),
        ("2.2", "Diagrama de dispersão: estaturas pai–filho", "fig_2_2.png"),
        ("2.3", "Retas de regressão de Galton", "fig_2_3.png"),
        ("2.4", "Dois modelos de herança", "fig_2_4.png"),
        ("2.5", "Karl Pearson com um crânio das Catacumbas de Paris", "fig_2_5.png"),
        ("2.6", "Sewall Wright e as cobaias", "fig_2_6.png"),
        ("2.7", "Primeiro diagrama de caminhos de Wright", "fig_2_7.png"),
        ("2.8", "Diagrama causal do peso ao nascer", "fig_2_8.png"),
        ("4.1", "Confundimento básico: Z confundidor de X→Y", "fig_4_1.png"),
        ("6.1", "Diagrama causal de Let's Make a Deal", "fig_6_1.png"),
        ("6.4", "Diagrama causal do paradoxo de Simpson", "fig_6_4.png"),
        ("7.2", "Configuração básica do critério da porta da frente", "fig_7_2.png"),
        ("8.3", "Efeito da educação e da experiência sobre o salário", "fig_8_3.png"),
        ("8.4", "Diagrama causal da mudança climática", "fig_8_4.png"),
        ("10.1", "O problema da transportabilidade", "fig_10_1.png"),
    ]
    for num, title, fname in banners:
        make_caption_banner(num, title, fname, FIG / fname if (FIG / fname).exists() else None)


def dedupe_markdown():
    """Remove duplicate consecutive figure captions and double image inserts."""
    pt = NOVO / "pt"
    for md in pt.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        # collapse repeated image+caption blocks for same figure
        # remove consecutive identical lines
        lines = text.split("\n")
        out = []
        prev = None
        seen_imgs = set()
        for line in lines:
            # skip exact duplicate consecutive lines
            if line == prev and (line.startswith("![") or "Figura " in line or "Tabela " in line):
                continue
            # skip second insert of same image file
            m = re.match(r"!\[.*?\]\((\.\./figuras/([^)]+))\)", line.strip())
            if m:
                fname = m.group(2)
                if fname in seen_imgs:
                    continue
                seen_imgs.add(fname)
            out.append(line)
            prev = line
        # remove pattern: caption line immediately followed by same caption italic
        text2 = "\n".join(out)
        text2 = re.sub(
            r"(\*\*?(Figura|Tabela)\s+(\d+\.\d+)\.?\*\*?[^\n]*)\n+\*\2\s+\3\.[^\n]*\n?",
            r"\1\n",
            text2,
        )
        # remove triple blank lines
        text2 = re.sub(r"\n{3,}", "\n\n", text2)
        md.write_text(text2, encoding="utf-8")
    print("Markdown deduplicado em", pt)


def apply_pt_over_figuras():
    """Sobrescreve figuras/ com versões PT (chamar DEPOIS de build_figure_map)."""
    FIG_PT.mkdir(parents=True, exist_ok=True)
    make_ladder_pt()
    make_tables_pt()
    make_key_banners()


def main():
    import sys

    sys.path.insert(0, str(ROOT / "build"))
    import embed_figures as ef

    print("=== 1. Mapear figuras do original ===")
    mapping = ef.build_figure_map()
    print("=== 2. Aplicar versões PT (escada, tabelas, faixas) ===")
    apply_pt_over_figuras()
    print("=== 3. Inserir imagens nos markdowns ===")
    ef.insert_images_in_markdown(mapping)
    dedupe_markdown()
    ef.write_caption_index(mapping)
    print("=== 4. Gerar HTML / LaTeX / PDF / EPUB ===")
    ef.build_html(mapping)
    ef.build_latex(mapping)
    ef.build_pdf(mapping)
    ef.build_epub(mapping)
    print("=== OK ===")
    for p in sorted(NOVO.glob("O_Livro*")):
        print(p.name, round(p.stat().st_size / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
