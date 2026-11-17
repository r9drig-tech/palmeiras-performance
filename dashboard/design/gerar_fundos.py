"""
Gera os fundos de página (PNG) do dashboard em verde e branco + o mapa de posições dos visuais.

Os fundos têm: menu lateral, cabeçalho com título, caixas das segmentações, painéis e
cartões de KPI. Os gráficos, números e segmentações são visuais nativos do Power BI,
posicionados por cima. Use docs/layout_posicoes.md para as coordenadas.

NÃO desenha o escudo do clube: o espaço dele fica livre (ver ESCUDO_*) para você
inserir a imagem oficial no Power BI.

Uso (na raiz do projeto):
    python dashboard/design/gerar_fundos.py
Saída:
    dashboard/fundos/pagina-01..06.png   (2560x1440 = 1280x720 @2x)
    dashboard/fundos/previa-visao-geral.png  (com dados fictícios, só para visualizar)
    docs/layout_posicoes.md
"""
from __future__ import annotations

import html
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H = 1280, 720
SIDEBAR_W = 96
MX = 112                      # margem esquerda do conteúdo
CW = 1152                     # largura do conteúdo (112 -> 1264)
GAP = 12

VERDE_ESC, VERDE, VERDE_MED, VERDE_CLARO = "#00381F", "#006437", "#1E8A4F", "#E4F1E8"
FUNDO, TINTA, MUDO, CINZA = "#F2F5F3", "#16231C", "#5E6B64", "#9AA5A0"
VERMELHO = "#B3261E"

# Espaço livre para o escudo (insira a imagem no Power BI)
ESCUDO_SIDEBAR = (18, 14, 60, 60)

NAV = [
    ("Visão\nGeral", "home"),
    ("Performance\nColetiva", "bars"),
    ("Análise de\nPartidas", "ball"),
    ("Desempenho\nIndividual", "people"),
    ("Disciplina\ne Elenco", "card"),
    ("Competições", "trophy"),
]

ICONS = {
    "home": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v9.5h13V10"/><path d="M10 19.5v-5h4v5"/>',
    "bars": '<path d="M5 20V12"/><path d="M12 20V5"/><path d="M19 20v-9"/><path d="M3 20h18"/>',
    "ball": '<circle cx="12" cy="12" r="8.5"/><path d="m12 8 3.6 2.6-1.4 4.2H9.8l-1.4-4.2z"/><path d="M12 8V3.6M15.6 10.6l4.2-1.2M14.2 14.8l2.6 3.4M9.8 14.8l-2.6 3.4M8.4 10.6 4.2 9.4"/>',
    "people": '<circle cx="9" cy="8.5" r="3.2"/><path d="M3 19c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/><circle cx="17" cy="9.5" r="2.5"/><path d="M16.5 14c2.7.1 4.5 1.8 4.5 4.5"/>',
    "card": '<rect x="6.5" y="3.5" width="11" height="17" rx="2"/><path d="M10 8h4M10 12h4"/>',
    "trophy": '<path d="M8 4h8v5a4 4 0 0 1-8 0z"/><path d="M8 6H4.5c0 3 1.5 4.5 3.7 4.8M16 6h3.5c0 3-1.5 4.5-3.7 4.8"/><path d="M12 13v4M8.5 20h7M10 17h4"/>',
    "pitch": '<rect x="3" y="5.5" width="18" height="13" rx="1.5"/><path d="M12 5.5v13"/><circle cx="12" cy="12" r="2.6"/><path d="M3 9.5h3v5H3M21 9.5h-3v5h3"/>',
    "x": '<circle cx="12" cy="12" r="8.5"/><path d="m9 9 6 6M15 9l-6 6"/>',
    "equal": '<circle cx="12" cy="12" r="8.5"/><path d="M8.5 10h7M8.5 14h7"/>',
    "pct": '<path d="M18 5 6 19"/><circle cx="7.5" cy="7.5" r="2.5"/><circle cx="16.5" cy="16.5" r="2.5"/>',
    "up": '<path d="M5 20V13M12 20V8M19 20V4"/>',
    "yellow": '<rect x="7" y="4" width="10" height="16" rx="1.8"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "user": '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20c0-3.6 3-6 7-6s7 2.4 7 6"/>',
}


def icon(nome: str, cor: str, tam: int, preencher: str = "none") -> str:
    return (f'<svg width="{tam}" height="{tam}" viewBox="0 0 24 24" fill="{preencher}" stroke="{cor}" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{ICONS[nome]}</svg>')


# --------------------------------------------------------------------------- #
# Especificação das páginas (coordenadas em unidades do Power BI: 1280 x 720)
# --------------------------------------------------------------------------- #
# tipos: panel (título + área interna), kpis (faixa de cartões), pair (2 cartões Casa/Fora),
#        triple (3 mini-painéis), plain (cartão branco sem título)

def kpi(label, ic, cor_ic=None):
    return {"label": label, "icon": ic}


KPIS_GERAL = [
    kpi("Jogos\ndisputados", "pitch"), kpi("Vitórias", "trophy"), kpi("Empates", "equal"),
    kpi("Derrotas", "x"), kpi("Gols\nmarcados", "ball"), kpi("Gols\nsofridos", "ball"),
    kpi("Saldo\nde gols", "up"), kpi("Aproveitamento", "pct"),
]
KPIS_DISC = [
    kpi("Cartões\namarelos", "yellow"), kpi("Cartões\nvermelhos", "yellow"),
    kpi("Cartões\npor jogo", "card"), kpi("Jogadores\nadvertidos", "user"),
    kpi("Expulsões\n2º amarelo", "x"), kpi("Expulsões\ndiretas", "x"),
]

PAGINAS = [
    {"id": 1, "nome": "Visão Geral", "paineis": [
        {"t": "kpis", "nome": "Indicadores gerais", "x": MX, "y": 116, "w": CW, "h": 116, "itens": KPIS_GERAL},
        {"t": "panel", "nome": "Evolução por partida", "x": MX, "y": 244, "w": 372, "h": 216},
        {"t": "panel", "nome": "Produção ofensiva x solidez defensiva", "x": MX + 384, "y": 244, "w": 420, "h": 216},
        {"t": "panel", "nome": "Distribuição dos resultados", "x": MX + 816, "y": 244, "w": 336, "h": 216},
        {"t": "pair", "nome": "Desempenho por local", "x": MX, "y": 472, "w": 336, "h": 236, "itens": ["Casa", "Fora"]},
        {"t": "triple", "nome": "Principais destaques individuais", "x": MX + 348, "y": 472, "w": 480, "h": 236,
         "itens": ["Artilharia", "Jogos disputados", "Titularidades"]},
        {"t": "panel", "nome": "Taxa de participação do elenco", "x": MX + 840, "y": 472, "w": 312, "h": 236},
    ]},
    {"id": 2, "nome": "Performance Coletiva", "paineis": [
        {"t": "panel", "nome": "Saldo de gols acumulado", "x": MX, "y": 116, "w": 560, "h": 188},
        {"t": "panel", "nome": "Gols pró x contra por partida", "x": MX + 572, "y": 116, "w": 580, "h": 188},
        {"t": "panel", "nome": "Gols por faixa de minuto", "x": MX, "y": 316, "w": 400, "h": 392},
        {"t": "panel", "nome": "Casa x Fora", "x": MX + 412, "y": 316, "w": 360, "h": 392},
        {"t": "panel", "nome": "Desempenho por adversário", "x": MX + 784, "y": 316, "w": 368, "h": 392},
    ]},
    {"id": 3, "nome": "Análise de Partidas", "paineis": [
        {"t": "panel", "nome": "Selecione a partida", "x": MX, "y": 116, "w": 252, "h": 592},
        {"t": "plain", "nome": "Cabeçalho da partida", "x": MX + 264, "y": 116, "w": 888, "h": 84},
        {"t": "panel", "nome": "Gols", "x": MX + 264, "y": 212, "w": 280, "h": 220},
        {"t": "panel", "nome": "Cartões", "x": MX + 556, "y": 212, "w": 304, "h": 220},
        {"t": "panel", "nome": "Substituições", "x": MX + 872, "y": 212, "w": 280, "h": 220},
        {"t": "panel", "nome": "Participações", "x": MX + 264, "y": 444, "w": 888, "h": 264},
    ]},
    {"id": 4, "nome": "Desempenho Individual", "paineis": [
        {"t": "panel", "nome": "Artilharia (Top 10)", "x": MX, "y": 116, "w": 372, "h": 232},
        {"t": "panel", "nome": "Jogos utilizados (Top 10)", "x": MX + 384, "y": 116, "w": 372, "h": 232},
        {"t": "panel", "nome": "Minutos x gols", "x": MX + 768, "y": 116, "w": 384, "h": 232},
        {"t": "panel", "nome": "Tabela de jogadores", "x": MX, "y": 360, "w": 700, "h": 348},
        {"t": "panel", "nome": "Perfil individual", "x": MX + 712, "y": 360, "w": 440, "h": 348},
    ]},
    {"id": 5, "nome": "Disciplina e Elenco", "paineis": [
        {"t": "kpis", "nome": "Indicadores de disciplina", "x": MX, "y": 116, "w": CW, "h": 116, "itens": KPIS_DISC},
        {"t": "panel", "nome": "Cartões acumulados", "x": MX, "y": 244, "w": 372, "h": 216},
        {"t": "panel", "nome": "Cartões por faixa de minuto", "x": MX + 384, "y": 244, "w": 372, "h": 216},
        {"t": "panel", "nome": "Motivos mais comuns", "x": MX + 768, "y": 244, "w": 384, "h": 216},
        {"t": "panel", "nome": "Jogadores advertidos", "x": MX, "y": 472, "w": 560, "h": 236},
        {"t": "panel", "nome": "Utilização do elenco por partida", "x": MX + 572, "y": 472, "w": 580, "h": 236},
    ]},
    {"id": 6, "nome": "Competições", "paineis": [
        {"t": "panel", "nome": "Comparativo entre competições", "x": MX, "y": 116, "w": CW, "h": 300},
        {"t": "panel", "nome": "Aproveitamento por competição", "x": MX, "y": 428, "w": 560, "h": 280},
        {"t": "panel", "nome": "Gols do elenco por competição", "x": MX + 572, "y": 428, "w": 580, "h": 280},
    ]},
]

# Segmentações do cabeçalho (iguais em todas as páginas)
SEGMENTACOES = [("Competição", 670), ("Período", 872), ("Adversário", 1074)]
SEG_Y, SEG_W, SEG_H = 30, 190, 62

# --------------------------------------------------------------------------- #
# Geometria derivada
# --------------------------------------------------------------------------- #
PAD_X, TOP, PAD_B = 12, 36, 12


def area_interna(p):
    return {"x": p["x"] + PAD_X, "y": p["y"] + TOP, "w": p["w"] - 2 * PAD_X, "h": p["h"] - TOP - PAD_B}


def cartoes_kpi(p):
    n = len(p["itens"])
    gap = 10
    w = (p["w"] - 24 - gap * (n - 1)) / n
    out = []
    for i, it in enumerate(p["itens"]):
        out.append({"x": p["x"] + 12 + i * (w + gap), "y": p["y"] + 36, "w": w, "h": p["h"] - 48, "item": it})
    return out


def subpaineis(p):
    n = len(p["itens"])
    gap = 10
    w = (p["w"] - 24 - gap * (n - 1)) / n
    return [{"x": p["x"] + 12 + i * (w + gap), "y": p["y"] + 36, "w": w, "h": p["h"] - 48, "nome": nm}
            for i, nm in enumerate(p["itens"])]


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #

def esc(s):
    return html.escape(s).replace("\n", "<br>")


CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{position:relative;background:{FUNDO};font-family:'Inter','DejaVu Sans',sans-serif;color:{TINTA}}}
.abs{{position:absolute}}
.deco{{position:absolute;left:0;top:0;width:{W}px;height:{H}px}}
.side{{position:absolute;left:0;top:0;width:{SIDEBAR_W}px;height:{H}px;
  background:linear-gradient(180deg,{VERDE_ESC} 0%,{VERDE} 55%,#04502C 100%);overflow:hidden}}
.side:before{{content:"";position:absolute;left:-40px;bottom:-30px;width:220px;height:300px;
  background:linear-gradient(135deg,rgba(255,255,255,.10),rgba(255,255,255,0));transform:skewY(-28deg)}}
.side:after{{content:"";position:absolute;left:-10px;bottom:30px;width:120px;height:3px;background:rgba(255,255,255,.35);transform:rotate(-28deg)}}
.nav{{position:absolute;left:8px;width:80px;height:64px;border-radius:10px;color:rgba(255,255,255,.82);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;
  font-size:8.2px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;text-align:center;line-height:1.15}}
.nav.on{{background:linear-gradient(180deg,#2FA566,{VERDE_MED});color:#fff;box-shadow:0 4px 12px rgba(0,0,0,.28)}}
.nav-sep{{position:absolute;left:18px;width:60px;height:1px;background:rgba(255,255,255,.14)}}
.head-bg{{position:absolute;left:{SIDEBAR_W}px;top:0;width:{W-SIDEBAR_W}px;height:112px;background:#fff;
  border-bottom:1px solid #E1E8E3;box-shadow:0 2px 10px rgba(0,50,25,.06);overflow:hidden}}
.head-deco{{position:absolute;right:0;top:0;width:700px;height:112px}}
.titulo{{position:absolute;left:{MX}px;top:16px}}
.titulo .a{{font-family:'Inter Display','Inter';font-weight:900;font-size:41px;line-height:1;letter-spacing:-.02em;
  color:{VERDE};transform:skewX(-6deg);transform-origin:left bottom;display:inline-block}}
.titulo .b{{font-weight:700;font-size:13px;letter-spacing:.42em;color:{TINTA};margin-top:7px}}
.tag{{position:absolute;left:{MX+318}px;top:22px;padding-left:16px;border-left:2px solid {VERDE};
  font-size:10.5px;font-weight:600;letter-spacing:.2em;color:{MUDO};line-height:1.45;text-transform:uppercase}}
.seg{{position:absolute;top:{SEG_Y}px;width:{SEG_W}px;height:{SEG_H}px;background:#fff;border-radius:10px;
  border:1px solid #E1E8E3;box-shadow:0 3px 10px rgba(0,50,25,.10)}}
.seg .l{{position:absolute;left:12px;top:8px;display:flex;align-items:center;gap:6px;font-size:10.5px;font-weight:700}}
.panel{{position:absolute;background:#fff;border-radius:10px;border:1px solid #E1E8E3;box-shadow:0 2px 8px rgba(0,50,25,.07)}}
.panel .ti{{position:absolute;left:12px;top:11px;display:flex;align-items:center;gap:7px;font-size:10.5px;font-weight:800;
  letter-spacing:.03em;text-transform:uppercase}}
.panel .ti:before{{content:"";width:3px;height:14px;background:{VERDE};border-radius:2px;display:block}}
.inner{{position:absolute;background:#F1F5F2;border-radius:8px}}
.kcard{{position:absolute;background:#fff;border-radius:9px;border:1px solid #E1E8E3;box-shadow:0 1px 4px rgba(0,50,25,.06)}}
.kcard .lb{{position:absolute;left:0;right:0;top:7px;display:flex;align-items:center;justify-content:center;gap:5px;
  font-size:8.6px;font-weight:800;letter-spacing:.02em;text-transform:uppercase;line-height:1.1;text-align:left}}
.kcard .v{{position:absolute;left:8px;right:8px;bottom:8px;background:#F1F5F2;border-radius:6px}}
.kcard:before{{content:"";position:absolute;left:0;top:22px;bottom:12px;width:3px;background:{VERDE};border-radius:0 2px 2px 0}}
.sub{{position:absolute;background:#fff;border-radius:9px;border:1px solid #E1E8E3;overflow:hidden}}
.sub .hd{{height:26px;display:flex;align-items:center;justify-content:center;gap:6px;color:#fff;
  font-size:9.5px;font-weight:800;letter-spacing:.04em;text-transform:uppercase}}
.sub .bd{{position:absolute;left:8px;right:8px;top:34px;bottom:8px;background:#F1F5F2;border-radius:6px}}
.mini-label{{position:absolute;font-size:9px;font-weight:700;color:{MUDO}}}
"""


def deco_header() -> str:
    # faixas diagonais verdes atrás das segmentações (ecoa a arte do topo do modelo original)
    return f"""
    <svg class="head-deco" viewBox="0 0 700 112" preserveAspectRatio="none">
      <defs>
        <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="{VERDE_MED}"/><stop offset="1" stop-color="{VERDE_ESC}"/>
        </linearGradient>
      </defs>
      <polygon points="700,0 700,112 300,112 372,0" fill="url(#g1)"/>
      <polygon points="372,0 300,112 270,112 342,0" fill="{VERDE_CLARO}"/>
      <polygon points="342,0 270,112 252,112 324,0" fill="#fff" opacity=".9"/>
      <polygon points="700,0 700,40 520,0" fill="rgba(255,255,255,.10)"/>
      <polygon points="700,112 700,70 560,112" fill="rgba(255,255,255,.08)"/>
    </svg>"""


def render_pagina(pg: dict, previa: bool = False) -> str:
    partes = [f"<style>{CSS}</style>"]
    # sidebar
    partes.append('<div class="side"></div>')
    top0 = 88
    for i, (rot, ic) in enumerate(NAV):
        y = top0 + i * 76
        on = (i + 1) == pg["id"]
        cor = "#fff" if on else "rgba(255,255,255,.85)"
        partes.append(f'<div class="nav{" on" if on else ""}" style="top:{y}px">{icon(ic, cor, 24)}<span>{esc(rot)}</span></div>')
        if i < len(NAV) - 1:
            partes.append(f'<div class="nav-sep" style="top:{y + 70}px"></div>')
    # header
    partes.append('<div class="head-bg">' + deco_header() + "</div>")
    partes.append(f'<div class="titulo"><div class="a">PALMEIRAS</div><div class="b">PERFORMANCE HUB</div></div>')
    partes.append('<div class="tag">Análise<br>Desempenho<br>Evolução<br>Resultados</div>')
    ic_seg = {"Competição": "trophy", "Período": "clock", "Adversário": "people"}
    for nome, x in SEGMENTACOES:
        partes.append(f'<div class="seg" style="left:{x}px"><div class="l">{icon(ic_seg[nome], VERDE, 14)}<span>{nome}</span></div></div>')

    # painéis
    for p in pg["paineis"]:
        st = f'left:{p["x"]}px;top:{p["y"]}px;width:{p["w"]}px;height:{p["h"]}px'
        if p["t"] == "plain":
            partes.append(f'<div class="panel" style="{st}"></div>')
            continue
        partes.append(f'<div class="panel" style="{st}"><div class="ti">{esc(p["nome"])}</div></div>')
        if p["t"] == "panel":
            a = area_interna(p)
            partes.append(f'<div class="inner" style="left:{a["x"]}px;top:{a["y"]}px;width:{a["w"]}px;height:{a["h"]}px"></div>')
        elif p["t"] == "kpis":
            for c in cartoes_kpi(p):
                it = c["item"]
                partes.append(
                    f'<div class="kcard" style="left:{c["x"]:.1f}px;top:{c["y"]}px;width:{c["w"]:.1f}px;height:{c["h"]}px">'
                    f'<div class="lb">{icon(it["icon"], VERDE, 17)}<span>{esc(it["label"])}</span></div>'
                    f'<div class="v" style="top:38px"></div></div>')
        elif p["t"] in ("pair", "triple"):
            for i, sp in enumerate(subpaineis(p)):
                escuro = (p["t"] == "pair" and i == 1) or (p["t"] == "triple" and i == 1)
                cor = "#2B3A32" if escuro else VERDE
                ic = {"Casa": "home", "Fora": "up", "Artilharia": "ball", "Jogos disputados": "people", "Titularidades": "user"}[sp["nome"]]
                if sp["nome"] == "Fora":
                    ic = "pitch"
                partes.append(
                    f'<div class="sub" style="left:{sp["x"]:.1f}px;top:{sp["y"]}px;width:{sp["w"]:.1f}px;height:{sp["h"]}px">'
                    f'<div class="hd" style="background:{cor}">{icon(ic, "#fff", 13)}<span>{esc(sp["nome"])}</span></div>'
                    f'<div class="bd"></div></div>')
    if previa:
        partes.append(previa_pagina1())
    return f'<!doctype html><html><head><meta charset="utf-8"></head><body>{"".join(partes)}</body></html>'


# --------------------------------------------------------------------------- #
# Prévia (dados FICTÍCIOS, só para visualizar o design)
# --------------------------------------------------------------------------- #

def previa_pagina1() -> str:
    pg = PAGINAS[0]
    P = {p["nome"]: p for p in pg["paineis"]}
    out = []

    def texto(x, y, w, h, t, tam=26, cor=TINTA, peso=700, al="center"):
        return (f'<div class="abs" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;display:flex;align-items:center;'
                f'justify-content:{al};font-size:{tam}px;font-weight:{peso};color:{cor}">{t}</div>')

    # KPIs
    valores = ["12", "7", "3", "2", "21", "8", "+13", "66,7%"]
    for c, v in zip(cartoes_kpi(P["Indicadores gerais"]), valores):
        out.append(texto(c["x"] + 8, c["y"] + 38, c["w"] - 16, c["h"] - 46, v, 24))

    pro = [4, 2, 1, 2, 0, 3, 1, 0, 2, 1, 3, 1]
    con = [0, 1, 1, 0, 1, 0, 0, 0, 1, 2, 1, 1]

    # evolução por partida (gols marcados)
    a = area_interna(P["Evolução por partida"])
    n, bw = len(pro), (a["w"] - 20) / len(pro)
    svg = [f'<svg class="abs" style="left:{a["x"]}px;top:{a["y"]}px" width="{a["w"]}" height="{a["h"]}">']
    for i, v in enumerate(pro):
        h = v / 4 * (a["h"] - 40)
        x = 10 + i * bw + 3
        svg.append(f'<rect x="{x:.1f}" y="{a["h"]-22-h:.1f}" width="{bw-6:.1f}" height="{max(h,1):.1f}" rx="2" fill="{VERDE}"/>')
        svg.append(f'<text x="{x+(bw-6)/2:.1f}" y="{a["h"]-26-h:.1f}" font-size="9" font-weight="700" text-anchor="middle" fill="{TINTA}">{v}</text>')
        svg.append(f'<text x="{x+(bw-6)/2:.1f}" y="{a["h"]-8}" font-size="7.5" text-anchor="middle" fill="{MUDO}">P{i+1}</text>')
    svg.append("</svg>")
    out.append("".join(svg))

    # pró x contra
    a = area_interna(P["Produção ofensiva x solidez defensiva"])
    bw = (a["w"] - 20) / len(pro)
    svg = [f'<svg class="abs" style="left:{a["x"]}px;top:{a["y"]}px" width="{a["w"]}" height="{a["h"]}">']
    for i, (p_, c_) in enumerate(zip(pro, con)):
        x = 10 + i * bw
        for k, (v, cor) in enumerate(((p_, VERDE), (c_, CINZA))):
            h = v / 4 * (a["h"] - 44)
            svg.append(f'<rect x="{x+k*(bw/2-1)+2:.1f}" y="{a["h"]-22-h:.1f}" width="{bw/2-3:.1f}" height="{max(h,1):.1f}" rx="2" fill="{cor}"/>')
        svg.append(f'<text x="{x+bw/2:.1f}" y="{a["h"]-8}" font-size="7.5" text-anchor="middle" fill="{MUDO}">P{i+1}</text>')
    svg.append(f'<circle cx="{a["w"]/2-50}" cy="9" r="4" fill="{VERDE}"/><text x="{a["w"]/2-42}" y="12" font-size="8.5" fill="{MUDO}">Gols marcados</text>')
    svg.append(f'<circle cx="{a["w"]/2+40}" cy="9" r="4" fill="{CINZA}"/><text x="{a["w"]/2+48}" y="12" font-size="8.5" fill="{MUDO}">Gols sofridos</text>')
    svg.append("</svg>")
    out.append("".join(svg))

    # rosca
    import math
    a = area_interna(P["Distribuição dos resultados"])
    cx, cy, r, sw = a["w"] / 2, a["h"] / 2 - 8, 44, 17
    dados = [("Vitória", 7, VERDE), ("Empate", 3, CINZA), ("Derrota", 2, VERMELHO)]
    tot = sum(d[1] for d in dados)
    svg = [f'<svg class="abs" style="left:{a["x"]}px;top:{a["y"]}px" width="{a["w"]}" height="{a["h"]}">']
    ang = -math.pi / 2
    for nome, v, cor in dados:
        frac = v / tot
        a2 = ang + frac * 2 * math.pi
        x1, y1, x2, y2 = cx + r * math.cos(ang), cy + r * math.sin(ang), cx + r * math.cos(a2), cy + r * math.sin(a2)
        svg.append(f'<path d="M{x1:.1f} {y1:.1f} A{r} {r} 0 {1 if frac>.5 else 0} 1 {x2:.1f} {y2:.1f}" stroke="{cor}" stroke-width="{sw}" fill="none"/>')
        am = (ang + a2) / 2
        ancora = "start" if math.cos(am) >= 0 else "end"
        lx_ = cx + (r + sw / 2 + 8) * math.cos(am) + (4 if ancora == "start" else -4)
        ly_ = cy + (r + sw / 2 + 8) * math.sin(am) + 3
        svg.append(f'<text x="{lx_:.1f}" y="{ly_:.1f}" font-size="9" font-weight="700" text-anchor="{ancora}" fill="{TINTA}">'
                   f'{v} ({str(round(frac*100,1)).replace(".",",")}%)</text>')
        ang = a2
    svg.append(f'<text x="{cx}" y="{cy+8}" font-size="24" font-weight="800" text-anchor="middle" fill="{TINTA}">{tot}</text>')
    lx = a["w"] / 2 - 78
    for i, (nome, v, cor) in enumerate(dados):
        svg.append(f'<circle cx="{lx+i*58}" cy="{a["h"]-12}" r="3.5" fill="{cor}"/><text x="{lx+i*58+7}" y="{a["h"]-9}" font-size="8.5" fill="{MUDO}">{nome}</text>')
    svg.append("</svg>")
    out.append("".join(svg))

    # casa x fora
    sp = subpaineis(P["Desempenho por local"])
    for s, v in zip(sp, ["77,8%", "55,6%"]):
        out.append(texto(s["x"] + 8, s["y"] + 34, s["w"] - 16, s["h"] - 42, v, 30, TINTA, 600))

    # destaques (nomes fictícios genéricos)
    sp = subpaineis(P["Principais destaques individuais"])
    nomes = ["Atleta A", "Atleta B", "Atleta C"]
    vals = [[6, 4, 3], [12, 12, 11], [12, 11, 10]]
    for i, s in enumerate(sp):
        mx = max(vals[i])
        for k in range(3):
            y = s["y"] + 44 + k * 44
            if i == 0:
                h = vals[i][k] / mx * 70
                out.append(f'<div class="abs" style="left:{s["x"]+16+k*40}px;top:{s["y"]+34+82-h}px;width:26px;height:{h}px;background:{VERDE};border-radius:3px"></div>')
                out.append(texto(s["x"] + 12 + k * 40, s["y"] + 34 + 82 - h - 14, 34, 12, str(vals[i][k]), 9, TINTA, 700))
                out.append(texto(s["x"] + 8 + k * 40, s["y"] + 34 + 86, 42, 12, nomes[k], 7, MUDO, 600))
            else:
                w = vals[i][k] / mx * (s["w"] - 70)
                out.append(texto(s["x"] + 10, y - 6, 40, 10, nomes[k], 7.5, MUDO, 600, "flex-start"))
                out.append(f'<div class="abs" style="left:{s["x"]+52}px;top:{y-4}px;width:{w:.0f}px;height:9px;background:{VERDE if i==2 else "#2B3A32"};border-radius:2px"></div>')
                out.append(texto(s["x"] + 54 + w, y - 6, 20, 10, str(vals[i][k]), 8, TINTA, 700, "flex-start"))

    # participação
    a = area_interna(P["Taxa de participação do elenco"])
    nom = [f"Atleta {c}" for c in "ABCDEFG"]
    taxa = [100, 100, 100, 91.7, 83.3, 83.3, 75]
    for k, (nme, t) in enumerate(zip(nom, taxa)):
        y = a["y"] + 8 + k * 27
        out.append(texto(a["x"] + 8, y, 56, 14, nme, 8, MUDO, 600, "flex-start"))
        out.append(f'<div class="abs" style="left:{a["x"]+66}px;top:{y+3}px;width:{(a["w"]-130)*t/100:.0f}px;height:8px;background:{VERDE};border-radius:2px"></div>')
        out.append(texto(a["x"] + a["w"] - 50, y, 44, 14, f"{str(t).replace('.',',')}%", 8, TINTA, 700, "flex-end"))

    # aviso
    out.append(f'<div class="abs" style="left:{MX}px;top:709px;font-size:8px;line-height:11px;color:{MUDO}">Prévia com dados fictícios, somente para visualizar o design.</div>')
    return "".join(out)


# --------------------------------------------------------------------------- #
# Documento de posições
# --------------------------------------------------------------------------- #

def gerar_md() -> str:
    L = ["# Posições dos visuais (Power BI)", "",
         "Todas as medidas em **pixels do Power BI** para uma página de **1280 x 720** "
         "(Exibir > Configurações da página > Tamanho: *Personalizado* 1280 x 720). "
         "Para posicionar: selecione o visual > Formato > Geral > Propriedades > Tamanho e posição "
         "(`X`, `Y`, `Largura`, `Altura`).", "",
         "Imagem de fundo: Formato da página > Tela de fundo > Imagem > *Ajustar*, transparência **0%**.",
         "Os gráficos devem ter **fundo desligado** (o tema já faz isso).", "",
         "## Itens comuns a todas as páginas", "",
         "| Item | X | Y | Largura | Altura |", "|---|---:|---:|---:|---:|"]
    for nome, x in SEGMENTACOES:
        L.append(f"| Segmentação **{nome}** (dentro da caixa; deixe o cabeçalho do visual oculto) | {x+8} | {SEG_Y+26} | {SEG_W-16} | {SEG_H-34} |")
    ex, ey, ew, eh = ESCUDO_SIDEBAR
    L.append(f"| **Escudo** do clube (imagem sua, no menu lateral) | {ex} | {ey} | {ew} | {eh} |")
    for i, (rot, _) in enumerate(NAV):
        L.append(f"| Botão de navegação **{rot.replace(chr(10), ' ')}** (botão transparente > Ação: Navegação de página) | 8 | {88 + i*76} | 80 | 64 |")
    L.append("")
    for pg in PAGINAS:
        L += [f"## Página {pg['id']:02d} · {pg['nome']}", "", "Arquivo de fundo: `dashboard/fundos/pagina-%02d.png`" % pg["id"], "",
              "| Visual | X | Y | Largura | Altura |", "|---|---:|---:|---:|---:|"]
        for p in pg["paineis"]:
            if p["t"] == "panel":
                a = area_interna(p)
                L.append(f"| {p['nome']} | {a['x']} | {a['y']} | {a['w']} | {a['h']} |")
            elif p["t"] == "plain":
                L.append(f"| {p['nome']} (cartões de texto: placar, competição, estádio...) | {p['x']+8} | {p['y']+8} | {p['w']-16} | {p['h']-16} |")
            elif p["t"] == "kpis":
                for c in cartoes_kpi(p):
                    L.append(f"| Cartão: {c['item']['label'].replace(chr(10), ' ')} | {c['x']+8:.0f} | {c['y']+38:.0f} | {c['w']-16:.0f} | {c['h']-46:.0f} |")
            else:
                for s in subpaineis(p):
                    L.append(f"| {p['nome']}: {s['nome']} | {s['x']+8:.0f} | {s['y']+34:.0f} | {s['w']-16:.0f} | {s['h']-42:.0f} |")
        L.append("")
    L += ["## Dica de produtividade", "",
          "Monte a **página 1** inteira, depois use *Duplicar página*, troque o fundo e reaproveite as "
          "segmentações sincronizadas (Exibir > Sincronizar segmentações). Os botões de navegação e a "
          "segmentação de competição podem ser copiados e colados entre as páginas (mesma posição)."]
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
def main() -> None:
    raiz = Path(__file__).resolve().parents[2]
    saida = raiz / "dashboard" / "fundos"
    saida.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pagina = nav.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for pg in PAGINAS:
            pagina.set_content(render_pagina(pg))
            pagina.wait_for_timeout(150)
            alvo = saida / f"pagina-{pg['id']:02d}.png"
            pagina.screenshot(path=str(alvo))
            print("ok", alvo.name)
        pagina.set_content(render_pagina(PAGINAS[0], previa=True))
        pagina.wait_for_timeout(150)
        pagina.screenshot(path=str(saida / "previa-visao-geral.png"))
        print("ok previa-visao-geral.png")
        nav.close()
    (raiz / "docs" / "layout_posicoes.md").write_text(gerar_md(), encoding="utf-8")
    print("ok docs/layout_posicoes.md")


if __name__ == "__main__":
    main()
