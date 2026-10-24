# -*- coding: utf-8 -*-
"""Capa e contracapa no estilo Companhia das Letras (minimalista, tipográfico)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"C:\Users\Hugo\Documents\grok\The_Book\tradu\images")
OUT.mkdir(parents=True, exist_ok=True)

# Formato capa ~ 6x9 in a 300 dpi
W, H = 1800, 2700
CREAM = (250, 247, 240)
INK = (28, 28, 28)
ACCENT = (140, 50, 40)  # vinho sóbrio CdL-ish
GOLD = (120, 95, 55)
GRAY = (90, 90, 90)


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\georgia.ttf",
        r"C:\Windows\Fonts\georgiab.ttf" if bold else r"C:\Windows\Fonts\georgia.ttf",
        r"C:\Windows\Fonts\times.ttf",
        r"C:\Windows\Fonts\timesbd.ttf" if bold else r"C:\Windows\Fonts\times.ttf",
        r"C:\Windows\Fonts\GARA.TTF",
        r"C:\Windows\Fonts\GARABD.TTF" if bold else r"C:\Windows\Fonts\GARA.TTF",
    ]
    if bold:
        candidates = [
            r"C:\Windows\Fonts\georgiab.ttf",
            r"C:\Windows\Fonts\timesbd.ttf",
            r"C:\Windows\Fonts\GARABD.TTF",
        ] + candidates
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def center_text(draw, y, text, fnt, fill=INK, width=W):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    draw.text((x, y), text, font=fnt, fill=fill)
    return y + (bbox[3] - bbox[1])


def draw_arrow(draw, y, length=1100):
    """Seta α → β no centro."""
    x0 = (W - length) // 2
    x1 = x0 + length
    cy = y
    # haste
    draw.line([(x0 + 40, cy), (x1 - 50, cy)], fill=GOLD, width=6)
    # pena
    feather = [
        (x0 + 20, cy),
        (x0 + 55, cy - 28),
        (x0 + 90, cy - 8),
        (x0 + 90, cy + 8),
        (x0 + 55, cy + 28),
    ]
    draw.polygon(feather, fill=ACCENT)
    # ponta
    tip = [(x1 - 55, cy - 18), (x1, cy), (x1 - 55, cy + 18)]
    draw.polygon(tip, fill=INK)
    # α β
    f = font(42)
    draw.text((x0 - 30, cy - 55), "α", font=f, fill=INK)
    draw.text((x1 + 10, cy - 55), "β", font=f, fill=INK)
    return y + 80


def wrap_text(draw, text, fnt, max_width):
    words = text.split()
    lines = []
    cur = []
    for w in words:
        test = " ".join(cur + [w])
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def make_front():
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    # margem sutil
    d.rectangle([60, 60, W - 60, H - 60], outline=(210, 200, 185), width=2)

    y = 220
    y = center_text(d, y, "JUDEA PEARL", font(48), GRAY) + 12
    y = center_text(d, y, "Premiado com o Prêmio Turing", font(28), GRAY) + 28
    y = center_text(d, y, "E DANA MACKENZIE", font(48), GRAY) + 100

    # título
    for line in ["O LIVRO", "DO", "PORQUÊ"]:
        y = center_text(d, y, line, font(120, bold=True), INK) + 18
    y += 40

    y = draw_arrow(d, y + 20)
    y += 30

    y = center_text(d, y, "A NOVA CIÊNCIA", font(40), INK) + 10
    y = center_text(d, y, "DE CAUSA E EFEITO", font(40), INK) + 120

    # linha decorativa
    d.line([(W // 2 - 80, y), (W // 2 + 80, y)], fill=ACCENT, width=2)
    y += 60

    y = center_text(d, y, "EDIÇÃO BRASILEIRA", font(26), GRAY) + 8
    y = center_text(d, y, "Tradução e notas de tradução", font(24), GRAY)

    # rodapé estilo selo
    center_text(d, H - 200, "COMPANHIA DAS LETRAS", font(32), ACCENT)
    center_text(d, H - 150, "estilo · edição de estudo", font(22), GRAY)

    path = OUT / "capa_br.png"
    img.save(path, "PNG")
    print("saved", path)
    return path


def make_back():
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle([60, 60, W - 60, H - 60], outline=(210, 200, 185), width=2)

    y = 180
    y = center_text(d, y, "O LIVRO DO PORQUÊ", font(48, bold=True), INK) + 20
    y = center_text(d, y, "Judea Pearl e Dana Mackenzie", font(32), GRAY) + 50

    d.line([(W // 2 - 100, y), (W // 2 + 100, y)], fill=ACCENT, width=2)
    y += 60

    blurb = (
        "Por que a correlação não é causalidade — e o que a ciência pode fazer a respeito? "
        "Neste livro clássico, o vencedor do Prêmio Turing Judea Pearl e o matemático "
        "Dana Mackenzie contam a história da Revolução Causal: a linguagem matemática "
        "que finalmente permite formular e responder perguntas de causa e efeito."
    )
    blurb2 = (
        "Da Escada da Causalidade aos contrafactuais, do debate sobre o cigarro aos "
        "paradoxos de Simpson e Monty Hall, os autores mostram como modelos causais "
        "transformam dados brutos em compreensão — e por que a inteligência artificial "
        "do futuro precisará pensar em termos de porquês."
    )
    blurb3 = (
        "Uma obra essencial para quem se interessa por estatística, ciência de dados, "
        "epidemiologia, economia, filosofia da ciência e o futuro da IA."
    )

    body = font(34)
    margin = 160
    max_w = W - 2 * margin
    for para in (blurb, blurb2, blurb3):
        for line in wrap_text(d, para, body, max_w):
            y = center_text(d, y, line, body, INK) + 8
        y += 28

    y += 40
    d.line([(W // 2 - 100, y), (W // 2 + 100, y)], fill=ACCENT, width=2)
    y += 50

    quote = (
        "«A causalidade foi matematizada — e com ela, a nossa capacidade "
        "de interrogar o mundo.»"
    )
    qf = font(32)
    for line in wrap_text(d, quote, qf, max_w - 40):
        y = center_text(d, y, line, qf, ACCENT) + 8

    y += 80
    y = center_text(d, y, "Inclui glossário, notas do tradutor", font(26), GRAY) + 6
    y = center_text(d, y, "e figuras com legendas em português", font(26), GRAY)

    # barcode placeholder
    bx, by, bw, bh = W // 2 - 200, H - 380, 400, 160
    d.rectangle([bx, by, bx + bw, by + bh], outline=INK, width=2)
    # fake bars
    x = bx + 20
    import random
    rng = random.Random(42)
    while x < bx + bw - 20:
        wbar = rng.choice([2, 3, 4, 6])
        d.rectangle([x, by + 15, x + wbar, by + bh - 40], fill=INK)
        x += wbar + rng.choice([2, 3, 4])
    center_text(d, by + bh - 30, "978-85-0000-000-0", font(22), GRAY)

    center_text(d, H - 160, "Tradução brasileira de estudo · PT-BR", font(24), GRAY)
    center_text(d, H - 120, "Obra original © 2018 Judea Pearl e Dana Mackenzie", font(20), GRAY)

    path = OUT / "contracapa_br.png"
    img.save(path, "PNG")
    print("saved", path)
    return path


if __name__ == "__main__":
    make_front()
    make_back()
