# -*- coding: utf-8 -*-
# cte_lineage_builder.py

# 1) Dependência
# Colab: ok. Local: garanta internet na 1ª execução ou já tenha sqlglot instalado.
try:
    import sqlglot
except Exception:
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sqlglot>=19.0.0"])
from sqlglot import parse_one, exp

import json
from pathlib import Path
from textwrap import dedent

# =========================
# 2) Insira seu SQL aqui
# =========================
SQL = dedent("""
WITH CTE_SOURCE AS (
  SELECT COL1, COL2, COL3
  FROM TABLE_A
)
, CTE_GROUP AS (
  SELECT COL1, SUM(COL2), MAX(COL3)
  FROM CTE_SOURCE
)
, CTE_SOURCE_2 AS (
  SELECT COL4, COL5
  FROM TABLE_B
)
, CTE_JOIN AS (
  SELECT COL1, COL2, COL3, COL5
  FROM CTE_GROUP AS A
  INNER JOIN CTE_SOURCE_2 AS B
  ON COL4 = COL1
)
, CTE_FILTER AS (
  SELECT *
  FROM CTE_JOIN
  WHERE COL5 >= 100
)
, CTE_SOURCE_3 AS (
  SELECT *
  FROM TABLE_C
)
, CTE_JOIN_2 AS (
  SELECT COL1, COL2, COL3, COL5, COL7
  FROM CTE_FILTER AS A
  LEFT JOIN CTE_SOURCE_3 AS B
  ON COL6 = COL1
)
SELECT COL1, COL2, COL3, COL4
FROM CTE_FILTER;
""").strip()


# =========================
# 3) Utilitários de parsing
# =========================
def table_alias_of(tbl: exp.Table):
    alias = None
    a = tbl.args.get("alias")
    if a and isinstance(a, exp.TableAlias):
        id_ = a.this
        if isinstance(id_, exp.Identifier):
            alias = id_.name
    return alias

def extract_predecessors_and_aliases(sel: exp.Select, known_cte_names):
    """Retorna:
       - predecessors: set de CTEs usadas diretamente no FROM/JOIN
       - alias_map: dict alias->cte_name (ou table_name)
    """
    predecessors = set()
    alias_map = {}

    for t in sel.find_all(exp.Table):
        name = t.name  # nome base (CTE ou tabela)
        alias = table_alias_of(t)
        if name in known_cte_names:
            predecessors.add(name)
            if alias:
                alias_map[alias] = name
            else:
                alias_map[name] = name
        else:
            # tabela física
            if alias:
                alias_map[alias] = name
            else:
                alias_map[name] = name
    return predecessors, alias_map

def select_projections(sel: exp.Select):
    """Lista de expressões do SELECT (exp) na ordem."""
    # Alguns dialetos podem usar sel.expressions, outros .args['expressions']
    exps = list(sel.expressions)
    return exps

def output_name_of(expr: exp.Expression):
    """Nome 'apresentável' da coluna de saída."""
    if isinstance(expr, exp.Alias):
        return expr.alias
    # Column simples
    if isinstance(expr, exp.Column):
        return expr.name
    # Func/Expr: retornar SQL legível
    s = expr.sql()
    # limpar quebras grandes
    return s.replace("\n", " ").strip()

def columns_referenced(expr: exp.Expression):
    """Lista de exp.Column referenciadas dentro de uma expressão."""
    return list(expr.find_all(exp.Column))

def qual_of(col: exp.Column):
    """Retorna (qualificador, nome_col). qualificador pode ser None."""
    q = col.table
    return q, col.name

def pretty_sql(node: exp.Expression):
    return node.sql(pretty=True)

# =========================
# 4) Construção da linhagem
# =========================
def build_lineage(sql: str):
    ast = parse_one(sql)  # programa com várias CTEs + query final
    ctes = list(ast.find_all(exp.CTE))
    cte_order = [c.alias_or_name for c in ctes]
    cte_map = {c.alias_or_name: c for c in ctes}

    # Armazena para cada CTE:
    # outputs[name] = [ { "name": out_name, "expr": expr, "immediate_deps": [(cte_or_table, out_col_name_or_base)], "leaves": set((cte, col)) } ]
    outputs = {}
    # Texto SQL da CTE:
    cte_sql_text = {}

    # Para expandir SELECT * quando origem é CTE
    def expand_star_from_cte(src_cte):
        return [o["name"] for o in outputs.get(src_cte, [])]

    # Computa leaves recursivamente
    def leaves_of_dependency(dep):
        # dep = (source_name, source_output_name_or_base, is_from_cte_output)
        s_name, s_col, is_cte_out = dep
        if is_cte_out and s_name in outputs:
            # encontrar o output na CTE de origem
            for o in outputs[s_name]:
                if o["name"] == s_col:
                    return set(o["leaves"])
        # base/física ou não mapeado a output da CTE → folha é o próprio par
        return {(s_name, s_col)}

    # 1) Percorre CTEs em ordem, derivando outputs e dependências imediatas
    for cte_name in cte_order:
        cte_node = cte_map[cte_name]
        sel = cte_node.this  # Select dentro da CTE
        if not isinstance(sel, exp.Select):
            # Suporte básico: caso seja um Subquery mais elaborado
            sel = next(cte_node.find_all(exp.Select), None)
            if sel is None:
                continue

        cte_sql_text[cte_name] = pretty_sql(sel)

        predecessors, alias_map = extract_predecessors_and_aliases(sel, set(cte_order))

        outs = []
        exprs = select_projections(sel)

        # Heurística para expandir SELECT * quando única origem é CTE conhecida
        only_cte_src = None
        if len(predecessors) == 1:
            only_cte_src = list(predecessors)[0]

        for e in exprs:
            # * (Star) → expandir da CTE única; se múltiplas origens ou tabela física, manter como "*"
            if isinstance(e, exp.Star) or isinstance(e, exp.Column) and e.name == "*" :
                if only_cte_src is not None:
                    for nm in expand_star_from_cte(only_cte_src):
                        outs.append({
                            "name": nm,
                            "expr": e,
                            "immediate_deps": [(only_cte_src, nm, True)],
                            "leaves": set(outputs[only_cte_src][[o["name"] for o in outputs[only_cte_src]].index(nm)]["leaves"]) if outputs.get(only_cte_src) else {(only_cte_src, nm)}
                        })
                else:
                    outs.append({
                        "name": "*",
                        "expr": e,
                        "immediate_deps": [],
                        "leaves": set()
                    })
                continue

            out_name = output_name_of(e)
            # dentro da expressão, capturar colunas referenciadas
            cols = columns_referenced(e if not isinstance(e, exp.Alias) else e.this)

            deps = []
            # Resolver cada coluna referenciada para (cte_or_table, out_col) com heurísticas
            for c in cols:
                qual, colname = qual_of(c)
                candidate_sources = []

                if qual:
                    # qualificador pode ser alias → resolver no alias_map
                    src = alias_map.get(qual, qual)
                    candidate_sources = [src]
                else:
                    # sem qualificador: tentar desambiguar pelo(s) predecessor(es)
                    # 1) se só há um predecessor, assumir
                    if len(predecessors) == 1:
                        candidate_sources = list(predecessors)
                    else:
                        # 2) tentar por nome de output existente ou por folhas
                        candidate_sources = list(predecessors)  # checar adiante

                resolved = False
                for src in candidate_sources:
                    if src in outputs:
                        # src é CTE conhecida → tentar match direto pelo output
                        names = [o["name"] for o in outputs[src]]
                        if colname in names:
                            deps.append((src, colname, True))
                            resolved = True
                            break
                        # Heurística: procurar por folhas que contenham base colname
                        hits = []
                        for o in outputs[src]:
                            leaf_names = {leaf_col for (_s, leaf_col) in o["leaves"]}
                            if colname in leaf_names:
                                hits.append(o["name"])
                        if len(hits) == 1:
                            deps.append((src, hits[0], True))
                            resolved = True
                            break
                        elif len(hits) > 1:
                            # ambíguo: conecta a todos
                            for h in hits:
                                deps.append((src, h, True))
                            resolved = True
                            break
                    else:
                        # src é tabela física
                        deps.append((src, colname, False))
                        resolved = True
                        break

                if not resolved:
                    # fallback: se não conseguiu, conecta a todos predecessores como base
                    for src in candidate_sources:
                        deps.append((src, colname, src in outputs))

            # computar folhas do output atual a partir das folhas dos deps
            leaves = set()
            for d in deps:
                leaves |= leaves_of_dependency(d)

            outs.append({
                "name": out_name,
                "expr": e,
                "immediate_deps": deps,
                "leaves": leaves
            })

        outputs[cte_name] = outs

    # 2) Query final (fora das CTEs)
    final_select = next(ast.find_all(exp.Select), None)
    final_name = "FINAL_QUERY"
    final_outs = []
    final_sql = ""
    if final_select:
        final_sql = pretty_sql(final_select)
        predecessors, alias_map = extract_predecessors_and_aliases(final_select, set(cte_order))
        exprs = select_projections(final_select)
        only_cte_src = list(predecessors)[0] if len(predecessors) == 1 else None
        for e in exprs:
            if isinstance(e, exp.Star) or isinstance(e, exp.Column) and e.name == "*" :
                if only_cte_src is not None and only_cte_src in outputs:
                    for nm in [o["name"] for o in outputs[only_cte_src]]:
                        final_outs.append({
                            "name": nm,
                            "expr": e,
                            "immediate_deps": [(only_cte_src, nm, True)],
                            "leaves": set(outputs[only_cte_src][[o["name"] for o in outputs[only_cte_src]].index(nm)]["leaves"])
                        })
                else:
                    final_outs.append({"name": "*", "expr": e, "immediate_deps": [], "leaves": set()})
                continue

            out_name = output_name_of(e)
            cols = columns_referenced(e if not isinstance(e, exp.Alias) else e.this)
            deps = []
            for c in cols:
                qual, colname = qual_of(c)
                candidate_sources = []
                if qual:
                    src = alias_map.get(qual, qual)
                    candidate_sources = [src]
                else:
                    candidate_sources = list(predecessors) if predecessors else []
                resolved = False
                for src in candidate_sources:
                    if src in outputs:
                        names = [o["name"] for o in outputs[src]]
                        if colname in names:
                            deps.append((src, colname, True)); resolved = True; break
                        hits = []
                        for o in outputs[src]:
                            leaf_names = {leaf_col for (_s, leaf_col) in o["leaves"]}
                            if colname in leaf_names:
                                hits.append(o["name"])
                        if len(hits) >= 1:
                            for h in hits:
                                deps.append((src, h, True))
                            resolved = True; break
                    else:
                        deps.append((src, colname, False)); resolved = True; break
                if not resolved and candidate_sources:
                    for src in candidate_sources:
                        deps.append((src, colname, src in outputs))
            leaves = set()
            for d in deps:
                s = leaves_of_dependency(d)
                leaves |= s
            final_outs.append({"name": out_name, "expr": e, "immediate_deps": deps, "leaves": leaves})
        outputs[final_name] = final_outs
        cte_sql_text[final_name] = final_sql

    # 3) JSON no formato solicitado + dados para o gráfico
    cte_nodes = list(cte_order) + ([final_name] if final_outs else [])
    edges_cte = []
    for tgt in cte_order:
        sel = cte_map[tgt].this
        preds, _ = extract_predecessors_and_aliases(sel, set(cte_order))
        for src in preds:
            edges_cte.append((src, tgt))
    if final_outs:
        # ligar a última CTE usada no final
        preds, _ = extract_predecessors_and_aliases(final_select, set(cte_order))
        for src in preds:
            edges_cte.append((src, final_name))

    # colLinks: pares (src_cte, src_col_out) -> (tgt_cte, tgt_col_out) quando imediatos
    col_links = []
    for tgt_cte in cte_nodes:
        if tgt_cte not in outputs: continue
        for o in outputs[tgt_cte]:
            for dep in o["immediate_deps"]:
                src, src_col, is_cte_out = dep
                if is_cte_out:
                    col_links.append({
                        "from": f"{src}.{src_col}",
                        "to": f"{tgt_cte}.{o['name']}"
                    })

    # JSON principal (por CTE)
    cte_json = []
    for name in cte_nodes:
        if name not in outputs: continue
        cte_json.append({
            "cte_name": name,
            "cte_query": cte_sql_text.get(name, ""),
            "cte_column": [
                {
                    "column_name": o["name"],
                    "dependencies": [
                        {"cte_name": s, "column_name": c}
                        for (s, c, is_out) in o["immediate_deps"] if is_out
                    ] + [
                        # bases (tabela física): mantemos, mas sem aprofundar
                        {"cte_name": s, "column_name": c}
                        for (s, c, is_out) in o["immediate_deps"] if not is_out
                    ]
                }
                for o in outputs[name]
            ]
        })

    return {
        "cte_nodes": cte_nodes,
        "edges_cte": edges_cte,
        "columns_by_cte": {name: [o["name"] for o in outputs.get(name, [])] for name in cte_nodes},
        "col_links": col_links,
        "cte_json": cte_json
    }


data = build_lineage(SQL)

# 5) Salva JSON
Path("lineage.json").write_text(json.dumps(data["cte_json"], indent=2, ensure_ascii=False), encoding="utf-8")
print("✅ lineage.json gerado.")

# 6) Gera HTML interativo (CTE como caixas; colunas desenhadas dentro; ligações coluna→coluna ao expandir)
html = f"""<!doctype html>
<html><head><meta charset="utf-8"/>
<title>CTE Lineage Viewer</title>
<style>
  html,body {{ height:100%; margin:0; font-family: Inter, Arial, sans-serif; }}
  #wrap {{ position:relative; height:100vh; }}
  #cy {{ position:absolute; inset:0; }}
  #overlay {{ position:absolute; inset:0; pointer-events:none; }}
  #legend {{ position:absolute; right:12px; top:12px; background:#fff; border:1px solid #ddd; padding:8px 10px; border-radius:8px; font-size:12px; }}
  .badge {{ display:inline-block; padding:2px 6px; border-radius:6px; margin-left:6px; font-size:11px; }}
</style>
</head>
<body>
<div id="wrap">
  <div id="cy"></div>
  <canvas id="overlay"></canvas>
  <div id="legend">
    Clique numa CTE para expandir/colapsar.<br/>
    <span class="badge" style="background:#0074D9;color:#fff;">CTE</span>
    <span class="badge" style="background:#2ECC40;color:#fff;">Coluna</span>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
<script>
const DATA = {json.dumps(data, ensure_ascii=False)};

// nós CTE
const elements = [];
for (const id of DATA.cte_nodes) {{
  elements.push({{ data: {{ id, label: id, type: 'cte' }} }});
}}
// arestas CTE→CTE
for (const [s,t] of DATA.edges_cte) {{
  elements.push({{ data: {{ id: s+"->"+t, source: s, target: t, type: 'cte_edge' }} }});
}}

const cy = cytoscape({{
  container: document.getElementById('cy'),
  elements,
  style: [
    {{ selector: 'node[type="cte"]', style: {{
      'label': 'data(label)',
      'background-color': '#0074D9',
      'color': '#fff',
      'shape': 'round-rectangle',
      'text-valign': 'top',
      'text-halign': 'center',
      'width': 240,
      'height': 64,
      'padding': '12px',
      'font-size': 12
    }} }},
    {{ selector: 'edge[type="cte_edge"]', style: {{
      'curve-style': 'taxi',
      'taxi-direction': 'auto',
      'line-color': '#B0B0B0',
      'target-arrow-color': '#B0B0B0',
      'target-arrow-shape': 'triangle',
      'width': 1.8,
      'opacity': 1.0
    }} }}
  ],
  layout: {{ name: 'breadthfirst', directed: true, padding: 40, spacingFactor: 1.4 }},
  wheelSensitivity: 0.2
}});

// Estado de expansão
const expanded = Object.create(null);

// Canvas overlay
const canvas = document.getElementById('overlay');
const ctx = canvas.getContext('2d');
function resizeCanvas(){{
  const bb = cy.container().getBoundingClientRect();
  canvas.width = Math.max(1, bb.width);
  canvas.height = Math.max(1, bb.height);
}}
resizeCanvas();
window.addEventListener('resize', ()=>{{ resizeCanvas(); drawOverlay(); }});

// Geometria das "tabelas"
const ROW_H = 18;
const HEADER_H = 22;
const PADDING = 10;
const COL_MARGIN_X = 6;

// coordenadas auxiliares em pixel (rendered)
function nodeBox(n){{
  const pos = n.renderedPosition();
  const w = n.renderedWidth();
  const h = n.renderedHeight();
  return {{
    left: pos.x - w/2,
    right: pos.x + w/2,
    top: pos.y - h/2,
    bottom: pos.y + h/2,
    width: w,
    height: h
  }};
}}

function drawTable(n){{
  const id = n.id();
  const cols = DATA.columns_by_cte[id] || [];
  // base node box
  const box = nodeBox(n);
  // altura expandida
  const tableH = HEADER_H + cols.length * ROW_H + PADDING*2;
  const expandTop = box.top; // “cresce” para baixo
  const expandLeft = box.left;
  const width = box.width;

  // fundo
  ctx.fillStyle = 'rgba(255,255,255,0.06)';
  ctx.fillRect(expandLeft, expandTop, width, tableH);

  // borda
  ctx.strokeStyle = '#004a89';
  ctx.lineWidth = 1;
  ctx.strokeRect(expandLeft+0.5, expandTop+0.5, width-1, tableH-1);

  // header
  ctx.fillStyle = 'rgba(255,255,255,0.12)';
  ctx.fillRect(expandLeft, expandTop, width, HEADER_H);
  ctx.fillStyle = '#FFFFFF';
  ctx.font = '12px Arial';
  ctx.textBaseline = 'middle';
  ctx.fillText(id, expandLeft + 8, expandTop + HEADER_H/2);

  // linhas de colunas
  ctx.font = '11px Arial';
  ctx.textBaseline = 'middle';
  cols.forEach((c, i) => {{
    const y = expandTop + HEADER_H + PADDING + i*ROW_H + ROW_H/2;
    // célula
    ctx.fillStyle = '#2ECC40';
    ctx.fillRect(expandLeft + COL_MARGIN_X, y-11, width - COL_MARGIN_X*2, 16);
    ctx.fillStyle = '#FFFFFF';
    const label = String(c).slice(0, 80);
    ctx.fillText(label, expandLeft + COL_MARGIN_X + 6, y);
  }});
}}

function colAnchor(n, colName, side){{ // side: 'left' | 'right'
  const id = n.id();
  const cols = DATA.columns_by_cte[id] || [];
  const idx = cols.indexOf(colName);
  if (idx < 0) return null;
  const box = nodeBox(n);
  const y = box.top + HEADER_H + PADDING + idx*ROW_H + ROW_H/2;
  const x = side === 'right' ? box.right - 4 : box.left + 4;
  return {{x, y}};
}}

function drawLinks(){{
  // cte→cte opacidade
  cy.edges('[type="cte_edge"]').forEach(e => {{
    const s = e.source().id(), t = e.target().id();
    const both = !!(expanded[s] && expanded[t]);
    e.style('opacity', both ? 0.18 : 1.0);
  }});

  // coluna→coluna
  ctx.lineWidth = 1.5;
  DATA.col_links.forEach(link => {{
    const [sCte, sCol] = link.from.split('.');
    const [tCte, tCol] = link.to.split('.');
    const sNode = cy.getElementById(sCte);
    const tNode = cy.getElementById(tCte);
    if (!sNode || !tNode || !sNode.renderedPosition || !tNode.renderedPosition) return;

    const sExpanded = !!expanded[sCte];
    const tExpanded = !!expanded[tCte];

    if (sExpanded && tExpanded){{
      const a1 = colAnchor(sNode, sCol, 'right');
      const a2 = colAnchor(tNode, tCol, 'left');
      if (!a1 || !a2) return;
      ctx.strokeStyle = '#FFD166';
      ctx.beginPath();
      ctx.moveTo(a1.x, a1.y);
      // curva suave
      const midx = (a1.x + a2.x)/2;
      ctx.bezierCurveTo(midx, a1.y, midx, a2.y, a2.x, a2.y);
      ctx.stroke();
    }} else if (sExpanded && !tExpanded){{
      // coluna → caixa destino
      const a1 = colAnchor(sNode, sCol, 'right');
      if (!a1) return;
      const tBox = nodeBox(tNode);
      const a2 = {{ x: tBox.left + 4, y: tBox.top + tBox.height/2 }};
      ctx.strokeStyle = '#B5E48C';
      ctx.beginPath();
      ctx.moveTo(a1.x, a1.y);
      const midx = (a1.x + a2.x)/2;
      ctx.bezierCurveTo(midx, a1.y, midx, a2.y, a2.x, a2.y);
      ctx.stroke();
    }} else if (!sExpanded && tExpanded){{
      // caixa origem → coluna destino
      const sBox = nodeBox(sNode);
      const a1 = {{ x: sBox.right - 4, y: sBox.top + sBox.height/2 }};
      const a2 = colAnchor(tNode, tCol, 'left');
      if (!a2) return;
      ctx.strokeStyle = '#B5E48C';
      ctx.beginPath();
      ctx.moveTo(a1.x, a1.y);
      const midx = (a1.x + a2.x)/2;
      ctx.bezierCurveTo(midx, a1.y, midx, a2.y, a2.x, a2.y);
      ctx.stroke();
    }} else {{
      // ambas colapsadas → deixamos somente CTE→CTE padrão (já desenhado pelo Cytoscape)
    }}
  }});

function drawOverlay(){{
  const bb = cy.container().getBoundingClientRect();
  ctx.clearRect(0,0,bb.width,bb.height);

  // desenha tabelas expandidas
  cy.nodes('[type="cte"]').forEach(n => {{
    if (expanded[n.id()]) drawTable(n);
  }});

  // desenha links coluna→coluna (e ajusta opacidade das CTE→CTE)
  drawLinks();
}}

// Redesenhar quando a cena muda
["render","pan","zoom","dragfree","position"].forEach(ev => cy.on(ev, drawOverlay));
cy.on('resize', ()=>{{ resizeCanvas(); drawOverlay(); }});

// Toggle expand/collapse
cy.on('tap', 'node[type="cte"]', evt => {{
  const id = evt.target.id();
  expanded[id] = !expanded[id];
  drawOverlay();
}});

// Primeira pintura
drawOverlay();
</script>
</body></html>
"""

Path("cte_lineage.html").write_text(html, encoding="utf-8")
print("✅ cte_lineage.html gerado.")

# Dicas de uso no Colab:
try:
    from IPython.display import IFrame, display
    display(IFrame(src="cte_lineage.html", width="100%", height=600))
    print("\nAbra também localmente se preferir: cte_lineage.html")
except Exception:
    pass