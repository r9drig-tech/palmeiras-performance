"""
Parser de súmulas on-line da CBF (PDF -> dicionário estruturado).

O layout das súmulas da CBF tem seções fixas: cabeçalho, arbitragem, cronologia,
relação de jogadores, comissão técnica, gols, cartões amarelos, cartões vermelhos,
ocorrências e substituições. O parser trabalha em cima de LINHAS de texto,
reconstruídas a partir das coordenadas das palavras do PDF (PyMuPDF), o que
mantém cada linha de tabela em uma única linha de texto.

Uso:
    from sumula_parser import pdf_para_linhas, parse_sumula
    dados = parse_sumula(pdf_para_linhas("dados/brutos/sum260321.pdf"))
"""
from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------- #
# Leitura do PDF
# --------------------------------------------------------------------------- #

def pdf_para_linhas(caminho: str, tolerancia_y: float = 2.5) -> list[str]:
    """Converte o PDF em linhas de texto, agrupando palavras pela coordenada Y."""
    import fitz  # PyMuPDF

    linhas: list[str] = []
    with fitz.open(caminho) as doc:
        for pagina in doc:
            palavras = pagina.get_text("words")  # x0, y0, x1, y1, texto, bloco, linha, palavra
            palavras.sort(key=lambda w: (round(w[1], 1), w[0]))
            grupo: list[tuple] = []
            y_ref = None
            for w in palavras:
                if y_ref is None or abs(w[1] - y_ref) <= tolerancia_y:
                    grupo.append(w)
                    y_ref = w[1] if y_ref is None else y_ref
                else:
                    linhas.append(_juntar(grupo))
                    grupo = [w]
                    y_ref = w[1]
            if grupo:
                linhas.append(_juntar(grupo))
    return [l for l in linhas if l.strip()]


def _juntar(grupo: list[tuple]) -> str:
    grupo = sorted(grupo, key=lambda w: w[0])
    return " ".join(w[4] for w in grupo).strip()


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #

def normaliza_time(txt: str) -> str:
    """'Palmeiras / SP' -> 'Palmeiras/SP'."""
    return re.sub(r"\s*/\s*", "/", txt.strip())


def sem_acento(txt: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")


BASE_PERIODO = {"1T": 0, "2T": 45, "3T": 90, "4T": 105}
FIM_PERIODO = {"1T": 45, "2T": 90, "3T": 105, "4T": 120}

RE_TEMPO = r"(?P<tempo>\+?\d{1,3}:\d{2}|-)"
RE_PERIODO = r"(?P<periodo>1T|2T|3T|4T|INT)"


def converte_tempo(tempo: str, periodo: str) -> dict:
    """
    Converte o par (tempo, período) da súmula em minuto absoluto de jogo.

    '05:00' + '1T'  -> minuto 5
    '14:00' + '2T'  -> minuto 59   (14 min do segundo tempo)
    '+04:00' + '1T' -> 45+4 (minuto_ordem 49, acrescimo 4)
    '-' + 'INT'     -> intervalo (substituição feita no intervalo -> minuto 45)
    """
    if periodo == "INT" or tempo == "-":
        return {"minuto": 45, "acrescimo": 0, "minuto_ordem": 45.0, "minuto_texto": "Intervalo"}
    base = BASE_PERIODO.get(periodo, 0)
    mm = int(tempo.lstrip("+").split(":")[0])
    if tempo.startswith("+"):
        fim = FIM_PERIODO.get(periodo, 45)
        return {"minuto": fim, "acrescimo": mm, "minuto_ordem": float(fim + mm), "minuto_texto": f"{fim}+{mm}'"}
    minuto = base + mm
    return {"minuto": minuto, "acrescimo": 0, "minuto_ordem": float(minuto), "minuto_texto": f"{minuto}'"}


SECOES = {
    "Relação de Jogadores": "jogadores",
    "Comissão Técnica": "comissao",
    "Gols": "gols",
    "Cartões Amarelos": "amarelos",
    "Cartões Vermelhos": "vermelhos",
    "Ocorrências / Observações": "ocorrencias",
    "Substituições": "substituicoes",
}

RE_RODAPE = re.compile(r"^Confederação Brasileira de Futebol\s+Publicação da Súmula", re.I)
RE_LEGENDA = re.compile(r"^(T = Titular|NR = Normal|TC - T[eé]cnico|Powered by TCPDF|\d+\s*/\s*\d+$|http://www\.tcpdf)", re.I)


# --------------------------------------------------------------------------- #
# Parser principal
# --------------------------------------------------------------------------- #

def parse_sumula(linhas: list[str]) -> dict:
    avisos: list[str] = []
    cab = _parse_cabecalho(linhas, avisos)
    times = [cab["mandante"], cab["visitante"]]

    # separa em seções
    secoes: dict[str, list[str]] = {v: [] for v in SECOES.values()}
    atual = None
    for l in linhas:
        l = l.strip()
        if RE_RODAPE.match(l) or RE_LEGENDA.match(l):
            continue
        if l in SECOES:
            atual = SECOES[l]
            continue
        if atual:
            secoes[atual].append(l)

    jogadores = _parse_jogadores(secoes["jogadores"], avisos)
    tecnicos = _parse_comissao(secoes["comissao"])
    gols = _parse_gols(secoes["gols"], times, avisos)
    amarelos = _parse_amarelos(secoes["amarelos"], times, avisos)
    vermelhos = _parse_vermelhos(secoes["vermelhos"], times, avisos)
    subs = _parse_subs(secoes["substituicoes"], times, avisos)

    return {
        "cabecalho": cab,
        "jogadores": jogadores,
        "tecnicos": tecnicos,
        "gols": gols,
        "amarelos": amarelos,
        "vermelhos": vermelhos,
        "substituicoes": subs,
        "avisos": avisos,
    }


# --------------------------------------------------------------------------- #
# Cabeçalho
# --------------------------------------------------------------------------- #

def _parse_cabecalho(linhas: list[str], avisos: list[str]) -> dict:
    texto = "\n".join(linhas)
    cab: dict = {}

    m = re.search(r"Campeonato:\s*(.+?)(?:\s+Rodada:\s*(.*))?$", next((l for l in linhas if l.startswith("Campeonato:")), ""))
    campeonato_bruto = (m.group(1).strip() if m else "")
    cab["campeonato_bruto"] = campeonato_bruto
    cab["rodada"] = (m.group(2) or "").strip() if m else ""
    ma = re.search(r"/(\d{4})$", campeonato_bruto)
    cab["temporada"] = int(ma.group(1)) if ma else None
    cab["campeonato"] = re.sub(r"/\d{4}$", "", campeonato_bruto).strip()
    if not m:
        avisos.append("cabeçalho: campeonato não encontrado")

    m = re.search(r"Jogo:\s*(\d+)", texto)
    cab["numero_jogo"] = int(m.group(1)) if m else None

    mandante = visitante = None
    for l in linhas:
        if l.startswith("Jogo:") and " X " in l and "/" in l:
            corpo = l[len("Jogo:"):].strip()
            partes = corpo.split(" X ")
            if len(partes) == 2:
                mandante, visitante = normaliza_time(partes[0]), normaliza_time(partes[1])
                break
    if not mandante:
        avisos.append("cabeçalho: mandante/visitante não encontrados")
    cab["mandante"], cab["visitante"] = mandante, visitante

    m = re.search(r"Data:\s*(\d{2})/(\d{2})/(\d{4})\s+Horário:\s*(\d{2}:\d{2})\s+Estádio:\s*(.+)", texto)
    if m:
        cab["data"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        cab["horario"] = m.group(4)
        cab["estadio"] = m.group(5).strip()
    else:
        cab["data"] = cab["horario"] = cab["estadio"] = None
        avisos.append("cabeçalho: data/horário/estádio não encontrados")

    m = re.search(r"Arbitro:\s*(.+?)\s*\(", texto)
    cab["arbitro"] = m.group(1).strip() if m else None

    m = re.search(r"Resultado do 1º Tempo:\s*(\d+)\s*X\s*(\d+)\s+Resultado Final:\s*(\d+)\s*X\s*(\d+)", texto)
    if m:
        cab["placar_1t_mandante"], cab["placar_1t_visitante"] = int(m.group(1)), int(m.group(2))
        cab["placar_mandante"], cab["placar_visitante"] = int(m.group(3)), int(m.group(4))
    else:
        cab["placar_1t_mandante"] = cab["placar_1t_visitante"] = None
        cab["placar_mandante"] = cab["placar_visitante"] = None
        avisos.append("cabeçalho: resultado final não encontrado")

    m = re.search(r"(?i)p[eê]naltis?[^\n]*?(\d+)\s*X\s*(\d+)", texto)
    cab["penaltis_mandante"] = int(m.group(1)) if m else None
    cab["penaltis_visitante"] = int(m.group(2)) if m else None
    return cab


# --------------------------------------------------------------------------- #
# Jogadores / comissão
# --------------------------------------------------------------------------- #

RE_TIME_LINHA = re.compile(r"^(?P<time>.+?)\s*/\s*(?P<uf>[A-Z]{2})$")
RE_JOGADOR = re.compile(r"^(?P<num>\d+)\s+(?P<blob>.+?)\s*(?P<tr>[TR])(?P<g>\(g\))?\s+(?P<pa>[PA])\s+(?P<cbf>\d+)$")


def _separa_apelido_nome(blob: str) -> tuple[str, str]:
    """
    A súmula traz 'Apelido Nome Completo' na mesma célula, com truncamento ' ... '.
    Heurística: o apelido costuma estar contido no nome completo. A chave confiável
    do jogador é o id CBF; esta separação é 'melhor esforço'.
    """
    toks = blob.split()
    # células coladas sem espaço ("GomezGustavo"): separa quando a 2ª parte repete o 1º token
    primeiro = sem_acento(toks[0]).lower()
    novos = [toks[0]]
    for t in toks[1:]:
        m = re.match(r"^(.*[a-zà-ú])([A-ZÀ-Ú][a-zà-ú]+)$", t)
        if m and sem_acento(m.group(2)).lower() == primeiro:
            novos += [m.group(1), m.group(2)]
        else:
            novos.append(t)
    toks = novos

    if "..." in toks and toks.index("...") < len(toks) - 1:
        # apelido truncado ('Marcos Ant ... Marcos Antonio Silva ...')
        i = toks.index("...")
        nome = re.sub(r"\s*\.\.\.$", "...", " ".join(toks[i + 1:]))
        return " ".join(toks[:i]) + "...", nome
    limpos = [t for t in toks if t != "..."]
    truncado = "..." in toks
    melhor = 1
    for k in range(1, len(limpos)):
        apel = {sem_acento(t).lower() for t in limpos[:k]}
        nome = [sem_acento(t).lower() for t in limpos[k:]]
        if all(any(n.startswith(a) for n in nome) for a in apel):
            melhor = k
    apelido = " ".join(limpos[:melhor])
    nome = " ".join(limpos[melhor:]) + ("..." if truncado else "")
    return apelido, nome


def _parse_jogadores(linhas: list[str], avisos: list[str]) -> list[dict]:
    out, time_atual = [], None
    for l in linhas:
        if l.startswith("Nº Apelido"):
            continue
        m = RE_JOGADOR.match(l)
        if m:
            apelido, nome = _separa_apelido_nome(m.group("blob"))
            out.append({
                "equipe": time_atual,
                "numero": m.group("num"),
                "apelido": apelido,
                "nome_completo": nome,
                "titular": m.group("tr") == "T",
                "goleiro": bool(m.group("g")),
                "profissional": m.group("pa") == "P",
                "id_jogador": int(m.group("cbf")),
                "linha_bruta": l,
            })
            continue
        mt = RE_TIME_LINHA.match(l)
        if mt:
            time_atual = normaliza_time(l)
            continue
        avisos.append(f"jogadores: linha não reconhecida: {l[:80]}")
    return out


def _parse_comissao(linhas: list[str]) -> dict:
    out, time_atual = {}, None
    for l in linhas:
        if l.startswith("Técnico:") and time_atual:
            out[time_atual] = l.split(":", 1)[1].strip()
        elif RE_TIME_LINHA.match(l) and ":" not in l:
            time_atual = normaliza_time(l)
    return out


# --------------------------------------------------------------------------- #
# Eventos
# --------------------------------------------------------------------------- #

def _acha_time(resto: str, times: list[str], inicio: bool = False) -> tuple[str | None, str]:
    """Localiza qual dos dois times aparece no começo/fim de 'resto'."""
    for t in times:
        t_regex = re.escape(t).replace("/", r"\s*/\s*")
        padrao = rf"^{t_regex}\s+" if inicio else rf"\s+{t_regex}$"
        m = re.search(padrao, resto)
        if m:
            return t, (resto[m.end():] if inicio else resto[:m.start()]).strip()
    return None, resto


def _parse_gols(linhas, times, avisos):
    out = []
    re_gol = re.compile(rf"^{RE_TEMPO}\s+{RE_PERIODO}\s+(?P<num>\d+|TC)\s+(?P<tipo>NR|PN|CT|FT)\s+(?P<resto>.+)$")
    for l in linhas:
        if l.startswith("Tempo 1T/2T"):
            continue
        m = re_gol.match(l)
        if not m:
            avisos.append(f"gols: linha não reconhecida: {l[:80]}")
            continue
        equipe, nome = _acha_time(m.group("resto"), times)
        if not equipe:
            avisos.append(f"gols: equipe não identificada: {l[:80]}")
        out.append({**converte_tempo(m.group("tempo"), m.group("periodo")),
                    "periodo": m.group("periodo"), "numero": m.group("num"),
                    "tipo": m.group("tipo"), "nome": nome, "equipe": equipe})
    return out


def _cartoes_por_bloco(linhas, re_cartao, times, avisos, secao):
    """Cada cartão = 1 linha de dados + linhas de 'Motivo' (podem quebrar em várias)."""
    eventos, atual = [], None
    for l in linhas:
        if l.startswith("Tempo 1T/2T"):
            continue
        m = re_cartao.match(l)
        if m:
            atual = m.groupdict()
            atual["motivo"] = ""
            eventos.append(atual)
        elif atual is not None:
            atual["motivo"] = (atual["motivo"] + " " + l).strip()
        else:
            avisos.append(f"{secao}: linha fora de bloco: {l[:80]}")
    return eventos


def _parse_amarelos(linhas, times, avisos):
    re_c = re.compile(rf"^{RE_TEMPO}\s+{RE_PERIODO}\s+(?P<num>\d+|TC)\s+(?P<resto>.+)$")
    out = []
    for e in _cartoes_por_bloco(linhas, re_c, times, avisos, "amarelos"):
        equipe, nome = _acha_time(e["resto"], times)
        if not equipe:
            avisos.append(f"amarelos: equipe não identificada: {e['resto'][:80]}")
        out.append({**converte_tempo(e["tempo"], e["periodo"]), "periodo": e["periodo"],
                    "numero": e["num"], "nome": nome, "equipe": equipe, **_motivo(e["motivo"])})
    return out


def _parse_vermelhos(linhas, times, avisos):
    re_c = re.compile(rf"^{RE_TEMPO}\s+{RE_PERIODO}\s+(?P<num>\d+|TC)\s+(?P<resto>.+)$")
    out = []
    for e in _cartoes_por_bloco(linhas, re_c, times, avisos, "vermelhos"):
        resto = e["resto"]
        equipe, nome = None, resto
        for t in times:
            t_regex = re.escape(t).replace("/", r"\s*/\s*")
            m = re.search(rf"\s+-\s+{t_regex}$", resto)
            if m:
                equipe, nome = t, resto[:m.start()].strip()
                break
        if not equipe:
            avisos.append(f"vermelhos: equipe não identificada: {resto[:80]}")
        motivo = e["motivo"]
        tipo = "Segundo amarelo" if motivo.lower().startswith("2º cartão amarelo") else "Direto"
        out.append({**converte_tempo(e["tempo"], e["periodo"]), "periodo": e["periodo"],
                    "numero": e["num"], "nome": nome, "equipe": equipe,
                    "tipo_vermelho": tipo, **_motivo(motivo)})
    return out


def _motivo(txt: str) -> dict:
    txt = re.sub(r"^2º Cartão Amarelo\s*", "", txt.strip(), flags=re.I)
    txt = re.sub(r"^Motivo:\s*", "", txt)
    m = re.match(r"^([A-Z]\d+(?:\.\d+)*)\.?\s*(.*)$", txt)
    codigo = m.group(1) if m else None
    desc = (m.group(2) if m else txt)
    desc = desc.split(" - ")[0].strip() if desc else ""
    return {"motivo_codigo": codigo, "motivo_resumo": desc[:160], "motivo_texto": txt[:600]}


def _parse_subs(linhas, times, avisos):
    out = []
    re_sub = re.compile(rf"^{RE_TEMPO}\s+{RE_PERIODO}\s+(?P<resto>.+)$")
    for l in linhas:
        if l.startswith("Tempo 1T/2T"):
            continue
        m = re_sub.match(l)
        if not m:
            avisos.append(f"subs: linha não reconhecida: {l[:80]}")
            continue
        equipe, resto = _acha_time(m.group("resto"), times, inicio=True)
        m2 = re.match(r"^(?P<n_in>\d+)\s*-\s*(?P<nome_in>.+?)\s+(?P<n_out>\d+)\s*-\s*(?P<nome_out>.+)$", resto)
        if not equipe or not m2:
            avisos.append(f"subs: formato inesperado: {l[:80]}")
            continue
        out.append({**converte_tempo(m.group("tempo"), m.group("periodo")),
                    "periodo": m.group("periodo"), "equipe": equipe,
                    "numero_entrou": m2.group("n_in"), "nome_entrou": m2.group("nome_in"),
                    "numero_saiu": m2.group("n_out"), "nome_saiu": m2.group("nome_out")})
    return out
