"""
Auditoria das tabelas tratadas. Confere consistência entre partidas, eventos e elenco.

Uso (na raiz do projeto):
    python python/pipeline/02_auditoria.py
    python python/pipeline/02_auditoria.py --tratados dados/tratados

Sai com código 1 se houver alguma verificação FALHA (avisos não derrubam).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

OK, AVISO, FALHA = "OK", "AVISO", "FALHA"
resultados: list[tuple[str, str, str]] = []


def registra(nome: str, ok: bool, detalhe: str = "", gravidade: str = FALHA) -> None:
    resultados.append((nome, OK if ok else gravidade, detalhe))


def main() -> int:
    raiz = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--tratados", default=str(raiz / "dados" / "tratados"))
    pasta = Path(ap.parse_args().tratados)

    ler = lambda n: pd.read_csv(pasta / f"{n}.csv", encoding="utf-8-sig")  # noqa: E731
    pt, jg = ler("dim_partida"), ler("dim_jogador")
    pa, gl = ler("fato_participacoes"), ler("fato_gols")
    ca, sb = ler("fato_cartoes"), ler("fato_substituicoes")
    cp = ler("dim_competicao")
    log = pd.read_csv(pasta / "_log_extracao.csv", encoding="utf-8-sig") if (pasta / "_log_extracao.csv").exists() else pd.DataFrame()

    # 1. Chaves ---------------------------------------------------------------
    registra("id_partida único em dim_partida", pt["id_partida"].is_unique,
             f"{pt['id_partida'].duplicated().sum()} duplicado(s)")
    registra("id_jogador único em dim_jogador", jg["id_jogador"].is_unique)
    for nome, df in (("fato_gols", gl), ("fato_cartoes", ca), ("fato_substituicoes", sb), ("fato_participacoes", pa)):
        orf = set(df["id_partida"]) - set(pt["id_partida"])
        registra(f"{nome}: id_partida existe em dim_partida", not orf, f"órfãos: {sorted(orf)[:5]}")
    orf = set(pa["id_jogador"].dropna()) - set(jg["id_jogador"])
    registra("fato_participacoes: id_jogador existe em dim_jogador", not orf, f"órfãos: {sorted(orf)[:5]}")
    orf = set(pt["id_competicao"]) - set(cp["id_competicao"])
    registra("dim_partida: id_competicao existe em dim_competicao", not orf, f"órfãos: {sorted(orf)}")
    outras = pt[pt["id_competicao"] == "OUT"]
    registra("Todas as partidas mapeadas para uma competição", outras.empty,
             f"{len(outras)} partida(s) em 'Outras' — ajuste dados/referencia/competicoes.csv", AVISO)

    # 2. Placar x gols ---------------------------------------------------------
    pro = gl[gl["lado_beneficiado"] == "Palmeiras"].groupby("id_partida").size()
    contra = gl[gl["lado_beneficiado"] == "Adversário"].groupby("id_partida").size()
    base = pt.set_index("id_partida")[["gols_pro", "gols_contra", "gols_pro_1t", "gols_contra_1t"]].copy()
    base["ev_pro"] = pro.reindex(base.index).fillna(0).astype(int)
    base["ev_contra"] = contra.reindex(base.index).fillna(0).astype(int)
    ruins = base[(base["ev_pro"] != base["gols_pro"]) | (base["ev_contra"] != base["gols_contra"])]
    detalhe = "; ".join(f"{i}: placar {r.gols_pro}x{r.gols_contra} vs eventos {r.ev_pro}x{r.ev_contra}" for i, r in ruins.head(6).iterrows())
    registra("Gols dos eventos batem com o placar final", ruins.empty, detalhe)

    # gols contra: a regra 'beneficiado = outro time' é uma premissa — mostra onde ela decide
    ct = gl[gl["gol_contra"] == 1]
    registra("Gols contra encontrados (premissa: 'Equipe' = time de quem fez o gol contra)",
             True, f"{len(ct)} gol(s) contra — confira se o placar bateu acima", AVISO if len(ct) else OK)

    g1 = gl[gl["periodo"] == "1T"]
    p1 = g1[g1["lado_beneficiado"] == "Palmeiras"].groupby("id_partida").size().reindex(base.index).fillna(0).astype(int)
    c1 = g1[g1["lado_beneficiado"] == "Adversário"].groupby("id_partida").size().reindex(base.index).fillna(0).astype(int)
    ruins1 = base[(p1 != base["gols_pro_1t"]) | (c1 != base["gols_contra_1t"])]
    registra("Gols do 1º tempo batem com o placar do intervalo", ruins1.empty, f"{len(ruins1)} partida(s)")

    # 3. Elenco -----------------------------------------------------------------
    tit = pa[pa["titular"] == 1].groupby(["id_partida", "lado"]).size()
    ruins_t = tit[tit != 11]
    registra("11 titulares por equipe em cada partida", ruins_t.empty, f"{len(ruins_t)} caso(s): {list(ruins_t.index[:4])}")

    ent_sub = sb.groupby(["id_partida", "equipe"]).size()
    ent_pa = pa[pa["entrou_do_banco"] == 1].groupby(["id_partida", "equipe"]).size()
    cmp = pd.concat([ent_sub.rename("subs"), ent_pa.rename("entradas")], axis=1).fillna(0)
    registra("Substituições == reservas que entraram", (cmp["subs"] == cmp["entradas"]).all(),
             f"{(cmp['subs'] != cmp['entradas']).sum()} divergência(s)")

    sem_id = sb[sb["id_jogador_entrou"].isna() | sb["id_jogador_saiu"].isna()]
    registra("Substituições com os dois jogadores identificados", sem_id.empty, f"{len(sem_id)} linha(s)")

    # 4. Cartões ----------------------------------------------------------------
    vm = ca[(ca["cor"] == "Vermelho") & (ca["tipo_vermelho"] == "Segundo amarelo")]
    falta = []
    for _, r in vm.iterrows():
        n = ca[(ca["cor"] == "Amarelo") & (ca["id_partida"] == r["id_partida"]) & (ca["numero"].astype(str) == str(r["numero"])) & (ca["equipe"] == r["equipe"])]
        if len(n) < 1:
            falta.append(f"{r['id_partida']} #{r['numero']}")
    registra("Vermelho por 2º amarelo tem amarelo correspondente", not falta, "; ".join(falta[:5]))

    sem_id_c = ca[(ca["papel"] == "Jogador") & ca["id_jogador"].isna()]
    registra("Cartões de jogadores com id_jogador", sem_id_c.empty, f"{len(sem_id_c)} linha(s)")
    sem_id_g = gl[gl["id_jogador"].isna()]
    registra("Gols com id_jogador", sem_id_g.empty, f"{len(sem_id_g)} linha(s)")

    # 5. Minutos ------------------------------------------------------------------
    usados = pa[pa["utilizado"] == 1]
    registra("Minutos jogados entre 0 e 120", usados["minutos_jogados"].between(0, 120).all())

    # 6. Log da extração -----------------------------------------------------------
    if not log.empty:
        com_av = log[log["n_avisos"] > 0]
        registra("Extração sem avisos de parsing", com_av.empty,
                 f"{len(com_av)} arquivo(s) com avisos — veja _log_extracao.csv", AVISO)
        erros = log[log["status"] == "ERRO"]
        registra("Extração sem erros", erros.empty, f"{len(erros)} arquivo(s): {list(erros['arquivo'][:4])}")

    # ---- relatório ------------------------------------------------------------------
    print(f"\nAUDITORIA — {len(pt)} partida(s), {len(jg)} jogador(es)\n" + "-" * 78)
    for nome, status, det in resultados:
        extra = f"  -> {det}" if det and status != OK else ""
        print(f"[{status:<5}] {nome}{extra}")
    n_f = sum(1 for _, s, _ in resultados if s == FALHA)
    n_a = sum(1 for _, s, _ in resultados if s == AVISO)
    print("-" * 78 + f"\n{len(resultados) - n_f - n_a} OK | {n_a} aviso(s) | {n_f} falha(s)")
    return 1 if n_f else 0


if __name__ == "__main__":
    raise SystemExit(main())
