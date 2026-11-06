#!/usr/bin/env python3
"""Converte a planilha de coleta (CSV) em páginas Markdown + catalogo.json para o MkDocs.

Uso:
    # Fluxo recomendado: exporte as abas para CSV e atualize os arquivos em data/.
    python scripts/build_catalogo.py data/catalogo.csv data/site.csv

    # Opcional: também aceita links CSV publicados do Google Sheets.
    python scripts/build_catalogo.py "<link CSV da aba principal>" "<link CSV da aba Site>"
    (link de aba: .../export?format=csv&gid=<GID>; segundo argumento opcional)

A planilha original não é alterada. O script:
  - localiza a linha de cabeçalho (a que começa com "ID"), ignorando título/subtítulo;
  - ignora linhas vazias e IDs de exemplo (EX-...);
  - publica só linhas com "Incluído?" = Sim;
  - normaliza DOI -> https://doi.org/...;
  - gera docs/documentos/<id>.md, docs/programas/, docs/paises/, docs/assets/catalogo.json.
"""
import csv
import io
import json
import re
import shutil
import sys
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# nome na planilha (sem acento, minúsculo) -> campo interno
COLUNAS = {
    "id": "id",
    "grupo tematico": "programa",
    "programa": "programa",
    "titulo": "titulo",
    "ano / data": "ano",
    "ano": "ano",
    "autores": "autores",
    "doi / link": "link",
    "base de origem": "fonte",
    "palavra-chave": "palavras",
    "palavras-chave": "palavras",
    "incluido?": "incluido",
    "motivo exclusao": "motivo",
    "pais": "pais",
    "tipo de documento": "tipo",
    "tipo": "tipo",
    "idioma": "idioma",
    "resumo": "resumo",
}


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def slug(s: str) -> str:
    s = sem_acento(s).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "sem-nome"


def ler_csv(origem: str) -> list[list[str]]:
    if origem.startswith("http"):
        with urllib.request.urlopen(origem) as r:
            texto = r.read().decode("utf-8-sig")
    else:
        texto = Path(origem).read_text(encoding="utf-8-sig")
    return list(csv.reader(io.StringIO(texto)))


def normaliza_link(v: str) -> str:
    v = v.strip()
    if re.match(r"^10\.\d{4,9}/", v):
        return "https://doi.org/" + v
    if v.lower().startswith("doi:"):
        return "https://doi.org/" + v[4:].strip()
    return v


def ano_de(v: str) -> str:
    m = re.search(r"(19|20)\d{2}", v or "")
    return m.group(0) if m else ""


def separa(v: str) -> list[str]:
    return [p.strip() for p in re.split(r"[;\n]", v or "") if p.strip()]


def yaml_str(v: str) -> str:
    return json.dumps(v, ensure_ascii=False)


def carregar_site(origem: str | None) -> dict[str, dict]:
    """Aba extra 'Site' (ID, País, Tipo de Documento, Idioma, Resumo), ligada à principal pelo ID."""
    if not origem:
        return {}
    linhas = ler_csv(origem)
    idx = next((i for i, l in enumerate(linhas) if l and sem_acento(l[0]).strip().lower() == "id"), None)
    if idx is None:
        sys.exit("Aba 'Site': não encontrei o cabeçalho (primeira coluna 'ID').")
    cab = [COLUNAS.get(sem_acento(c).strip().lower()) for c in linhas[idx]]
    extra = {}
    for l in linhas[idx + 1:]:
        r = {cab[i]: v.strip() for i, v in enumerate(l) if i < len(cab) and cab[i]}
        if r.get("id"):
            extra[slug(r["id"])] = r
    return extra


def carregar(origem: str, site: str | None = None) -> list[dict]:
    extra = carregar_site(site)
    linhas = ler_csv(origem)
    idx = next((i for i, l in enumerate(linhas) if l and sem_acento(l[0]).strip().lower() == "id"), None)
    if idx is None:
        sys.exit("Não encontrei a linha de cabeçalho (primeira coluna 'ID').")
    cab = [COLUNAS.get(sem_acento(c).strip().lower()) for c in linhas[idx]]
    registros = []
    for l in linhas[idx + 1:]:
        r = {cab[i]: v.strip() for i, v in enumerate(l) if i < len(cab) and cab[i]}
        rid = r.get("id", "")
        if not rid or not r.get("titulo"):
            continue
        if rid.upper().startswith("EX-"):
            continue
        if sem_acento(r.get("incluido", "")).lower() != "sim":
            continue
        r["id"] = slug(rid)
        r["titulo"] = re.sub(r"\s+", " ", r["titulo"]).strip()
        for campo in ("pais", "tipo", "idioma", "resumo"):
            if not r.get(campo) and extra.get(r["id"], {}).get(campo):
                r[campo] = extra[r["id"]][campo]
        if extra and r["id"] not in extra:
            print(f"AVISO: {rid} não tem linha na aba 'Site' (sem país/tipo/idioma).")
        r["ano"] = ano_de(r.get("ano", ""))
        r["link"] = normaliza_link(r.get("link", ""))
        r["palavras"] = separa(r.get("palavras", ""))
        for campo in ("programa", "pais", "tipo", "idioma", "fonte", "autores", "resumo"):
            r.setdefault(campo, "")
        registros.append(r)
    return registros


def limpar_gerados():
    for pasta in ("documentos", "programas", "paises"):
        shutil.rmtree(DOCS / pasta, ignore_errors=True)
        (DOCS / pasta).mkdir(parents=True, exist_ok=True)


def pagina_documento(r: dict) -> str:
    tags = [t for t in r["palavras"]]
    fm = ["---", f"title: {yaml_str(r['titulo'])}"]
    if tags:
        fm.append("tags:")
        fm += [f"  - {yaml_str(t)}" for t in tags]
    fm.append("---\n")
    corpo = [f"# {r['titulo']}\n"]
    meta = [
        ("Autores", r["autores"]),
        ("Ano", r["ano"]),
        ("País", r["pais"]),
        ("Programa", r["programa"]),
        ("Tipo de documento", r["tipo"]),
        ("Idioma", r["idioma"]),
        ("Fonte", r["fonte"]),
    ]
    corpo += [f"**{k}:** {v}  " for k, v in meta if v]
    corpo.append("")
    if r["resumo"]:
        corpo += [r["resumo"], ""]
    if tags:
        corpo.append("**Palavras-chave:** " + ", ".join(tags) + "\n")
    if r["link"]:
        corpo.append(f"[:material-open-in-new: Consultar a fonte original]({r['link']}){{ .md-button .md-button--primary target=_blank rel=noopener }}\n")
    return "\n".join(fm + corpo)


def paginas_agrupadas(registros, campo, pasta, titulo_indice, rotulo_vazio):
    grupos = defaultdict(list)
    for r in registros:
        grupos[r[campo] or rotulo_vazio].append(r)
    indice = [f"# {titulo_indice}\n"]
    for nome in sorted(grupos, key=lambda s: sem_acento(s).lower()):
        docs = sorted(grupos[nome], key=lambda r: (r["ano"] or "0", r["titulo"]), reverse=True)
        s = slug(nome)
        indice.append(f"- [{nome}]({s}.md) — {len(docs)} documento(s)")
        linhas = [f"# {nome}\n"]
        for r in docs:
            extra = " · ".join(x for x in (r["ano"], r["tipo"], r["fonte"]) if x)
            linhas.append(f"- [{r['titulo']}](../documentos/{r['id']}.md)" + (f" — {extra}" if extra else ""))
        (DOCS / pasta / f"{s}.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    (DOCS / pasta / "index.md").write_text("\n".join(indice) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    registros = carregar(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
    limpar_gerados()
    for r in registros:
        (DOCS / "documentos" / f"{r['id']}.md").write_text(pagina_documento(r), encoding="utf-8")
    paginas_agrupadas(registros, "programa", "programas", "Programas", "Sem programa")
    paginas_agrupadas(registros, "pais", "paises", "Países", "Sem país")
    (DOCS / "assets").mkdir(exist_ok=True)
    publico = [
        {k: r[k] for k in ("id", "titulo", "autores", "ano", "pais", "programa", "tipo", "idioma", "fonte", "palavras", "link")}
        for r in registros
    ]
    (DOCS / "assets" / "catalogo.json").write_text(json.dumps(publico, ensure_ascii=False), encoding="utf-8")
    print(f"{len(registros)} documento(s) publicados.")


if __name__ == "__main__":
    main()
