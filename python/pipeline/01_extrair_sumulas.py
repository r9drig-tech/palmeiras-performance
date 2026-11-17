"""
Extrai as súmulas (PDF) da CBF e gera as tabelas tratadas do projeto.

Entrada : dados/brutos/*.pdf      (também aceita .txt com o texto já extraído)
          dados/manual/*.csv      (opcional: competições sem súmula CBF — mesmo esquema)
Saída   : dados/tratados/*.csv    (UTF-8 com BOM, separador vírgula)

Uso (na raiz do projeto):
    python python/pipeline/01_extrair_sumulas.py
    python python/pipeline/01_extrair_sumulas.py --brutos dados/brutos --saida dados/tratados
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sumula_parser import parse_sumula, pdf_para_linhas, sem_acento  # noqa: E402

CLUBE = "Palmeiras"
DESCRICAO_TIPO_GOL = {"NR": "Normal", "PN": "Pênalti", "CT": "Contra", "FT": "Falta"}

COLUNAS = {
    "dim_competicao": ["id_competicao", "competicao", "fonte", "tipo", "ordem"],
    "dim_partida": [
        "id_partida", "id_competicao", "temporada", "rodada", "numero_jogo", "data", "horario",
        "estadio", "mandante", "visitante", "local_palmeiras", "adversario", "gols_pro",
        "gols_contra", "gols_pro_1t", "gols_contra_1t", "resultado", "pontos",
        "penaltis_pro", "penaltis_contra", "tecnico_palmeiras", "tecnico_adversario",
        "arbitro", "arquivo_origem",
    ],
    "dim_jogador": ["id_jogador", "apelido", "nome_completo", "equipe", "lado", "goleiro"],
    "fato_participacoes": [
        "id_partida", "id_jogador", "equipe", "lado", "numero", "titular", "goleiro",
        "utilizado", "entrou_do_banco", "minuto_entrada", "minuto_saida", "minutos_jogados",
    ],
    "fato_gols": [
        "id_gol", "id_partida", "id_jogador", "numero", "nome", "equipe_autor", "lado_autor",
        "equipe_beneficiada", "lado_beneficiado", "tipo", "tipo_descricao", "gol_contra",
        "periodo", "minuto", "acrescimo", "minuto_ordem", "minuto_texto",
    ],
    "fato_cartoes": [
        "id_cartao", "id_partida", "cor", "tipo_vermelho", "papel", "id_jogador", "numero",
        "nome", "equipe", "lado", "periodo", "minuto", "acrescimo", "minuto_ordem",
        "minuto_texto", "motivo_codigo", "motivo_resumo", "motivo_texto",
    ],
    "fato_substituicoes": [
        "id_sub", "id_partida", "equipe", "lado", "periodo", "minuto", "acrescimo",
        "minuto_ordem", "minuto_texto", "id_jogador_entrou", "numero_entrou", "nome_entrou",
        "id_jogador_saiu", "numero_saiu", "nome_saiu",
    ],
}


def lado(equipe: str | None) -> str:
    return "Palmeiras" if equipe and equipe.startswith(f"{CLUBE}/") else "Adversário"


def competicao_de(campeonato: str, comps: pd.DataFrame) -> str:
    alvo = sem_acento(campeonato).lower()
    for _, r in comps.iterrows():
        padrao = str(r["padrao_nome"]) if pd.notna(r["padrao_nome"]) else ""
        if padrao and sem_acento(padrao).lower() in alvo:
            return r["id_competicao"]
    return "OUT"


def ler_linhas(caminho: Path) -> list[str]:
    if caminho.suffix.lower() == ".pdf":
        return pdf_para_linhas(str(caminho))
    return [l.rstrip("\n") for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


def processar(linhas: list[str], arquivo: str, comps: pd.DataFrame) -> dict:
    d = parse_sumula(linhas)
    cab, avisos = d["cabecalho"], list(d["avisos"])
    mand, vis = cab["mandante"], cab["visitante"]
    if not mand or not (mand.startswith(f"{CLUBE}/") or vis.startswith(f"{CLUBE}/")):
        raise ValueError(f"jogo sem {CLUBE}: {mand} x {vis}")

    id_comp = competicao_de(cab["campeonato"], comps)
    num = cab["numero_jogo"] or 0
    id_partida = f"{id_comp}{cab['temporada']}-{num:03d}"
    casa = mand.startswith(f"{CLUBE}/")
    pal, adv = (mand, vis) if casa else (vis, mand)

    def pla(k_m, k_v):
        a, b = cab[k_m], cab[k_v]
        if a is None:
            return None, None
        return (a, b) if casa else (b, a)

    gp, gc = pla("placar_mandante", "placar_visitante")
    gp1, gc1 = pla("placar_1t_mandante", "placar_1t_visitante")
    pp, pc = pla("penaltis_mandante", "penaltis_visitante")
    resultado = pontos = None
    if gp is not None:
        resultado = "V" if gp > gc else ("E" if gp == gc else "D")
        pontos = {"V": 3, "E": 1, "D": 0}[resultado]

    partida = {
        "id_partida": id_partida, "id_competicao": id_comp, "temporada": cab["temporada"],
        "rodada": cab["rodada"], "numero_jogo": cab["numero_jogo"], "data": cab["data"],
        "horario": cab["horario"], "estadio": cab["estadio"], "mandante": mand, "visitante": vis,
        "local_palmeiras": "Casa" if casa else "Fora", "adversario": adv.split("/")[0],
        "gols_pro": gp, "gols_contra": gc, "gols_pro_1t": gp1, "gols_contra_1t": gc1,
        "resultado": resultado, "pontos": pontos, "penaltis_pro": pp, "penaltis_contra": pc,
        "tecnico_palmeiras": d["tecnicos"].get(pal), "tecnico_adversario": d["tecnicos"].get(adv),
        "arbitro": cab["arbitro"], "arquivo_origem": arquivo,
    }

    # ---- elenco -------------------------------------------------------------
    idx = {(j["equipe"], j["numero"]): j["id_jogador"] for j in d["jogadores"]}

    def id_de(equipe, numero, onde):
        if numero == "TC":
            return None
        v = idx.get((equipe, numero))
        if v is None:
            avisos.append(f"{onde}: camisa {numero} de {equipe} não está na relação de jogadores")
        return v

    periodos = {e["periodo"] for k in ("gols", "amarelos", "vermelhos", "substituicoes") for e in d[k]}
    fim_jogo = 120 if periodos & {"3T", "4T"} else 90

    entrou, saiu = {}, {}
    subs = []
    for i, s in enumerate(d["substituicoes"], 1):
        ide = id_de(s["equipe"], s["numero_entrou"], "subs")
        ids = id_de(s["equipe"], s["numero_saiu"], "subs")
        if ide is not None:
            entrou[ide] = s["minuto"]
        if ids is not None:
            saiu[ids] = s["minuto"]
        subs.append({
            "id_sub": f"{id_partida}-S{i:02d}", "id_partida": id_partida, "equipe": s["equipe"],
            "lado": lado(s["equipe"]), "periodo": s["periodo"], "minuto": s["minuto"],
            "acrescimo": s["acrescimo"], "minuto_ordem": s["minuto_ordem"],
            "minuto_texto": s["minuto_texto"], "id_jogador_entrou": ide,
            "numero_entrou": s["numero_entrou"], "nome_entrou": s["nome_entrou"],
            "id_jogador_saiu": ids, "numero_saiu": s["numero_saiu"], "nome_saiu": s["nome_saiu"],
        })

    nomes_eventos: dict[int, set] = {}

    def guarda_nome(idj, nome):
        if idj is not None and nome:
            nomes_eventos.setdefault(idj, set()).add(nome)

    gols = []
    for i, g in enumerate(d["gols"], 1):
        idj = id_de(g["equipe"], g["numero"], "gols")
        guarda_nome(idj, g["nome"])
        ct = g["tipo"] == "CT"
        benef = ({mand, vis} - {g["equipe"]}).pop() if ct and g["equipe"] else g["equipe"]
        gols.append({
            "id_gol": f"{id_partida}-G{i:02d}", "id_partida": id_partida, "id_jogador": idj,
            "numero": g["numero"], "nome": g["nome"], "equipe_autor": g["equipe"],
            "lado_autor": lado(g["equipe"]), "equipe_beneficiada": benef,
            "lado_beneficiado": lado(benef), "tipo": g["tipo"],
            "tipo_descricao": DESCRICAO_TIPO_GOL.get(g["tipo"]), "gol_contra": int(ct),
            "periodo": g["periodo"], "minuto": g["minuto"], "acrescimo": g["acrescimo"],
            "minuto_ordem": g["minuto_ordem"], "minuto_texto": g["minuto_texto"],
        })

    cartoes, reds = [], {}
    n = 0
    for cor, lista in (("Amarelo", d["amarelos"]), ("Vermelho", d["vermelhos"])):
        for c in lista:
            n += 1
            idj = id_de(c["equipe"], c["numero"], f"cartões {cor.lower()}s")
            guarda_nome(idj, c["nome"])
            if cor == "Vermelho" and idj is not None:
                reds[idj] = c["minuto"]
            cartoes.append({
                "id_cartao": f"{id_partida}-C{n:02d}", "id_partida": id_partida, "cor": cor,
                "tipo_vermelho": c.get("tipo_vermelho"),
                "papel": "Técnico" if c["numero"] == "TC" else "Jogador", "id_jogador": idj,
                "numero": c["numero"], "nome": c["nome"], "equipe": c["equipe"],
                "lado": lado(c["equipe"]), "periodo": c["periodo"], "minuto": c["minuto"],
                "acrescimo": c["acrescimo"], "minuto_ordem": c["minuto_ordem"],
                "minuto_texto": c["minuto_texto"], "motivo_codigo": c["motivo_codigo"],
                "motivo_resumo": c["motivo_resumo"], "motivo_texto": c["motivo_texto"],
            })

    participacoes, jogadores = [], []
    for j in d["jogadores"]:
        idj = j["id_jogador"]
        ent = 0 if j["titular"] else entrou.get(idj)
        utilizado = j["titular"] or ent is not None
        sai = None
        if utilizado:
            candidatos = [m for m in (saiu.get(idj), reds.get(idj)) if m is not None]
            sai = min(candidatos) if candidatos else fim_jogo
        participacoes.append({
            "id_partida": id_partida, "id_jogador": idj, "equipe": j["equipe"],
            "lado": lado(j["equipe"]), "numero": j["numero"], "titular": int(j["titular"]),
            "goleiro": int(j["goleiro"]), "utilizado": int(utilizado),
            "entrou_do_banco": int((not j["titular"]) and ent is not None),
            "minuto_entrada": ent if utilizado else None, "minuto_saida": sai,
            "minutos_jogados": max(sai - ent, 0) if utilizado else 0,
        })
        jogadores.append({
            "id_jogador": idj, "apelido": j["apelido"], "nome_completo": j["nome_completo"],
            "equipe": j["equipe"], "lado": lado(j["equipe"]), "goleiro": int(j["goleiro"]),
            "_nomes_eventos": nomes_eventos.get(idj, set()),
        })

    return {
        "partida": partida, "gols": gols, "cartoes": cartoes, "subs": subs,
        "participacoes": participacoes, "jogadores": jogadores,
        "avisos": avisos, "arquivo": arquivo, "id_partida": id_partida,
    }


def melhor_texto(opcoes: list[str]) -> str:
    """Prefere texto sem truncamento ('...'); entre iguais, o mais longo."""
    opcoes = [o for o in opcoes if o]
    if not opcoes:
        return ""
    completos = [o for o in opcoes if "..." not in o]
    return max(completos or opcoes, key=len)


def consolida_jogadores(registros: list[dict]) -> pd.DataFrame:
    por_id: dict[int, dict] = {}
    for r in registros:
        p = por_id.setdefault(r["id_jogador"], {"apelidos": [], "nomes": [], "equipe": r["equipe"],
                                                "lado": r["lado"], "goleiro": r["goleiro"]})
        p["apelidos"].append(r["apelido"])
        p["nomes"] += [r["nome_completo"], *r["_nomes_eventos"]]
        p["equipe"], p["lado"] = r["equipe"], r["lado"]  # último clube conhecido
        p["goleiro"] = max(p["goleiro"], r["goleiro"])
    linhas = [{
        "id_jogador": k, "apelido": melhor_texto(v["apelidos"]), "nome_completo": melhor_texto(v["nomes"]),
        "equipe": v["equipe"], "lado": v["lado"], "goleiro": v["goleiro"],
    } for k, v in por_id.items()]
    return pd.DataFrame(linhas, columns=COLUNAS["dim_jogador"]).sort_values("id_jogador")


def junta_manual(nome: str, df: pd.DataFrame, pasta_manual: Path) -> pd.DataFrame:
    caminho = pasta_manual / f"{nome}.csv"
    if not caminho.exists():
        return df
    extra = pd.read_csv(caminho, encoding="utf-8-sig", dtype=str)
    faltando = [c for c in COLUNAS[nome] if c not in extra.columns]
    if faltando:
        print(f"  [!] {caminho.name}: colunas ausentes {faltando} — arquivo ignorado")
        return df
    print(f"  + {caminho.name}: {len(extra)} linhas manuais incluídas")
    return pd.concat([df, extra[COLUNAS[nome]]], ignore_index=True)


def main() -> int:
    raiz = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brutos", default=str(raiz / "dados" / "brutos"))
    ap.add_argument("--saida", default=str(raiz / "dados" / "tratados"))
    ap.add_argument("--manual", default=str(raiz / "dados" / "manual"))
    ap.add_argument("--referencia", default=str(raiz / "dados" / "referencia"))
    a = ap.parse_args()

    brutos, saida = Path(a.brutos), Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    comps = pd.read_csv(Path(a.referencia) / "competicoes.csv", dtype=str)

    arquivos = sorted([p for p in brutos.rglob("*") if p.suffix.lower() in (".pdf", ".txt")])
    if not arquivos:
        print(f"Nenhuma súmula (.pdf/.txt) encontrada em {brutos}")
        return 1
    print(f"{len(arquivos)} arquivo(s) encontrado(s) em {brutos}\n")

    res, log, vistos = [], [], {}
    for p in arquivos:
        try:
            r = processar(ler_linhas(p), p.name, comps)
        except Exception as e:  # noqa: BLE001
            print(f"  [ERRO] {p.name}: {e}")
            log.append({"arquivo": p.name, "id_partida": None, "status": "ERRO", "n_avisos": 1, "avisos": str(e)})
            continue
        if r["id_partida"] in vistos:
            print(f"  [DUPLICADO] {p.name} repete {vistos[r['id_partida']]} ({r['id_partida']}) — ignorado")
            log.append({"arquivo": p.name, "id_partida": r["id_partida"], "status": "DUPLICADO", "n_avisos": 0, "avisos": ""})
            continue
        vistos[r["id_partida"]] = p.name
        res.append(r)
        status = "OK" if not r["avisos"] else "AVISOS"
        pt = r["partida"]
        print(f"  [{status}] {p.name}: {pt['id_partida']} {pt['mandante']} {pt['gols_pro'] if pt['local_palmeiras']=='Casa' else pt['gols_contra']}"
              f" x {pt['gols_contra'] if pt['local_palmeiras']=='Casa' else pt['gols_pro']} {pt['visitante']}")
        log.append({"arquivo": p.name, "id_partida": r["id_partida"], "status": status,
                    "n_avisos": len(r["avisos"]), "avisos": " | ".join(r["avisos"])[:1000]})

    if not res:
        print("Nada processado com sucesso.")
        return 1

    def tabela(nome, linhas):
        return pd.DataFrame(linhas, columns=COLUNAS[nome])

    tabelas = {
        "dim_competicao": comps[["id_competicao", "competicao", "fonte", "tipo", "ordem"]],
        "dim_partida": tabela("dim_partida", [r["partida"] for r in res]),
        "dim_jogador": consolida_jogadores([j for r in res for j in r["jogadores"]]),
        "fato_participacoes": tabela("fato_participacoes", [x for r in res for x in r["participacoes"]]),
        "fato_gols": tabela("fato_gols", [x for r in res for x in r["gols"]]),
        "fato_cartoes": tabela("fato_cartoes", [x for r in res for x in r["cartoes"]]),
        "fato_substituicoes": tabela("fato_substituicoes", [x for r in res for x in r["subs"]]),
    }

    print("\nDados manuais (dados/manual):")
    for nome in list(tabelas):
        if nome in ("dim_competicao",):
            continue
        tabelas[nome] = junta_manual(nome, tabelas[nome], Path(a.manual))

    tabelas["dim_partida"] = tabelas["dim_partida"].sort_values(["data", "horario"]).reset_index(drop=True)
    for nome, df in tabelas.items():
        df.to_csv(saida / f"{nome}.csv", index=False, encoding="utf-8-sig")
        print(f"  {nome}.csv: {len(df)} linhas")
    pd.DataFrame(log).to_csv(saida / "_log_extracao.csv", index=False, encoding="utf-8-sig")
    print(f"\nConcluído. Próximo passo: python python/pipeline/02_auditoria.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
