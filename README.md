# Repositório de Documentos (MkDocs Material)

## Atualização manual

A planilha do Google Sheets continua sendo a fonte de dados, mas a atualização do site é feita manualmente:

1. Exporte a aba principal da planilha como CSV e substitua `data/catalogo.csv`.
2. Exporte a aba **Site** como CSV e substitua `data/site.csv`.
3. Gere os arquivos do site com `python scripts/build_catalogo.py data/catalogo.csv data/site.csv`.
4. Confira o resultado localmente com `mkdocs serve` e abra o endereço informado no terminal.
5. Versione as alterações nos CSVs e nos arquivos gerados e envie-as para a branch `main`. O workflow em `.github/workflows/deploy.yml` publica o site no GitHub Pages.

O script não altera a planilha. Ele lê os dois CSVs locais e gera páginas em `docs/documentos/`, `docs/programas/`, `docs/paises/` e o índice de busca `docs/assets/catalogo.json`. Assim, cada atualização do site fica registrada no repositório.

## Planilhas
- **Aba principal** (`data/catalogo.csv`): colunas do protocolo, sem alteração (ID, Grupo Temático, Título, Ano / Data, Autores, DOI / Link, Base de Origem, Palavra-chave, Incluído?, Motivo Exclusão).
- **Aba "Site"** (`data/site.csv`): `ID`, `País`, `Tipo de Documento`, `Idioma`, `Resumo` (opcional), ligada à principal pelo ID.
- Os dados atuais são os 13 registros da planilha da Coreia do Sul (KOR-001 a KOR-013). O KOR-008 está sem `Incluído?` e por isso não aparece no site até ser decidido.
- `Ano / Data` e `Autores` ainda estão vazios; o `Tipo de Documento` também.
- Só entram linhas com `Incluído? = Sim`; IDs `EX-...` são ignorados.
- Várias palavras-chave: separe com `;`.
- DOI puro (`10.xxxx/...`) vira `https://doi.org/...`.

## Primeira publicação
Repositório > Settings > Pages > Source: branch `gh-pages` (criada pelo workflow no primeiro deploy).
Descomente e ajuste `site_url` no `mkdocs.yml`.

## Teste local
```
pip install -r requirements.txt
python scripts/build_catalogo.py data/catalogo.csv data/site.csv
mkdocs serve
```
(Os CSVs incluídos são dados de exemplo; substitua-os pelos arquivos exportados da planilha antes de publicar.)
