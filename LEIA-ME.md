# *O Livro do Porquê* — edição com figuras (pasta `novo`)

Esta pasta contém a **versão completa** da tradução brasileira **com imagens, figuras e tabelas embutidas**, e legendas em português.

## Arquivos principais

| Formato | Arquivo | Tamanho aprox. |
|---------|---------|----------------|
| **PDF** | `O_Livro_do_Porque.pdf` | ~33 MB · **509 páginas** · ~105 págs. com figuras |
| **EPUB** | `O_Livro_do_Porque.epub` | ~26 MB (imagens embutidas) |
| **HTML** | `O_Livro_do_Porque.html` | ~1 MB (+ pasta `figuras/`) |
| **LaTeX** | `O_Livro_do_Porque.tex` | fonte recompilável com `\includegraphics` |

## Figuras

- **`figuras/`** — 88 arquivos `fig_X_Y.png` / `tab_X_Y.png` extraídos do PDF original
- **`figuras_map.json`** — mapeamento figura → página original + legenda PT
- **`INDICE_FIGURAS.md`** — índice legível de todas as figuras/tabelas
- **`pt/*.md`** — capítulos em markdown com `![...](../figuras/...)` e legendas

## Capa / contracapa

- `capa_br.png`
- `contracapa_br.png`

## Como regenerar

```powershell
python ..\build\embed_figures.py
```

## Nota sobre legendas e rótulos

- **88 figuras/tabelas** embutidas nos quatro formatos (PDF, HTML, LaTeX, EPUB).
- Legendas em português brasileiro em todas as figuras.
- **Figura 1.2 (Escada da Causalidade):** painéis de texto refeitos em PT-BR (Associação / Intervenção / Contrafactuais).
- **Tabelas-chave** (ex.: 3.1, 3.2, 6.1, 6.4, 8.1) redesenhadas com cabeçalhos em português.
- Demais figuras: imagem original + faixa-título em português.
- Diagramas só com símbolos (*X*, *Y*, setas, *do*): mantidos (não exigem tradução de rótulos).
- Cópias PT extras também em `figuras_pt/`.

## Regenerar com figuras traduzidas

```powershell
python ..\build\figuras_pt.py
```
