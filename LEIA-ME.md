# *O Livro do Porquê* — Edição brasileira de estudo

**Título original:** *The Book of Why: The New Science of Cause and Effect*  
**Autores:** Judea Pearl e Dana Mackenzie  
**Obra original:** © 2018 Judea Pearl and Dana Mackenzie · Basic Books / Hachette  

Esta pasta contém uma **tradução completa para o português brasileiro** (edição de estudo), com capa e contracapa no estilo tipográfico da tradição de não ficção da Companhia das Letras, glossário, notas do tradutor e legendas de figuras em português.

> **Aviso:** tradução não oficial, elaborada para fins de estudo e leitura.  
> Todos os direitos da obra original pertencem aos autores e à editora.

---

## Arquivos finais

| Formato | Arquivo | Observação |
|---------|---------|------------|
| **PDF** | `O_Livro_do_Porque.pdf` | **504 páginas** (A5), capa + contracapa |
| **HTML** | `O_Livro_do_Porque.html` | Leitura no navegador, sumário com âncoras |
| **LaTeX** | `O_Livro_do_Porque.tex` (e `latex/`) | Fonte tipográfica recompilável |
| **EPUB** | `O_Livro_do_Porque.epub` | e-reader / apps de leitura |

## Capa e contracapa

- `images/capa_br.png` — capa estilo Companhia das Letras (creme, tipografia serifada, seta α→β)
- `images/contracapa_br.png` — sinopse, citação e código de barras de estudo

## Estrutura da tradução (`pt/`)

| Arquivo | Conteúdo |
|---------|----------|
| `00_prefacio.md` … `10_bigdata.md` | Prefácio, introdução e capítulos 1–10 |
| `11_agradecimentos.md` … `15_indice.md` | Apêndices |
| `16_notas_tradutor.md` | Critérios e decisões de tradução |
| `17_figuras_legendas.md` | Legendas de figuras/tabelas em PT-BR |
| `GLOSSARIO.md` (pasta pai) | Glossário canônico EN→PT-BR |

**Volume aproximado da tradução:** ~139 mil palavras em português.

## Critérios principais de tradução

- *Ladder of Causation* → **Escada da Causalidade**
- *confounding* → **confundimento** (epidemiologia BR)
- *counterfactual* → **contrafactual**
- *back-door / front-door* → **porta dos fundos / porta da frente**
- operador *do*(·) e equações **mantidos** na notação original
- Títulos de artigos/livros na bibliografia: **originais em inglês**

## Como regenerar os formatos

```powershell
python tradu\build\gerar_capas.py
python tradu\build\montar_obra.py all
# ou: html | latex | pdf | epub
```

## Imagens do original

Extraídas em `images/original/` (117 imagens significativas).  
Diagramas com rótulos simbólicos permanecem no original; legendas traduzidas em `pt/17_figuras_legendas.md`.
