# Importação manual (competições sem súmula CBF)

O extrator só lê súmulas no formato da CBF. Para jogos do **Paulistão** (FPF), da
**Libertadores** (CONMEBOL) ou de qualquer outra competição, você tem duas opções:

1. **Preencher CSVs** com o mesmo esquema das tabelas (esta pasta). Serve para poucos jogos.
2. **Pedir um parser novo** (`sumula_parser_fpf.py`, `sumula_parser_conmebol.py`) a partir de
   **um PDF de exemplo** de cada fonte. Serve para a temporada inteira.

## Como funciona a opção 1

Os arquivos `_modelo_<tabela>.csv` desta pasta trazem só o cabeçalho de cada tabela.
Copie o modelo, **remova o prefixo `_modelo_`** e preencha:

| Arquivo a criar         | Obrigatório | Observação |
|-------------------------|-------------|------------|
| `dim_partida.csv`       | sim         | 1 linha por jogo. `id_competicao`: `PAU`, `LIB`, `SUP`, `REC`, `MUN`, `AMI` (ver `dados/referencia/competicoes.csv`) |
| `fato_participacoes.csv`| sim         | quem jogou, titular/reserva, minutos |
| `fato_gols.csv`         | se houve gol| `lado_autor` e `lado_beneficiado` = `Palmeiras` ou `Adversário` |
| `fato_cartoes.csv`      | se houve    | `cor` = `Amarelo` ou `Vermelho` |
| `fato_substituicoes.csv`| se houve    | |
| `dim_jogador.csv`       | sim         | `id_jogador` único; para jogador sem id CBF, use um número seu (ex.: 9000001 em diante) |

Regras:

- `id_partida` precisa ser único e igual em todas as tabelas (ex.: `PAU2026-001`).
- Use os mesmos nomes de coluna e a mesma ordem do modelo.
- Flags são `1`/`0` (titular, goleiro, utilizado, entrou_do_banco, gol_contra).
- `data` no formato `AAAA-MM-DD`.
- O pipeline anexa estes CSVs às tabelas extraídas. Depois rode `02_auditoria.py`.

Os arquivos de modelo (`_modelo_*.csv`) são ignorados pelo pipeline.
