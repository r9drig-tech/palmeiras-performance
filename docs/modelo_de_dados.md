# Modelo de dados

Esquema estrela com **partida** como eixo central. Todas as partidas são vistas pela
perspectiva do Palmeiras; os adversários aparecem nos eventos (coluna `lado`).

```
dim_competicao ──1:*── dim_partida ──1:*── fato_gols
dim_calendario ──1:*──┘      │      ├─1:*── fato_cartoes
                             │      ├─1:*── fato_substituicoes
                             │      └─1:*── fato_participacoes
dim_jogador ──1:*── fato_participacoes
            ├─1:*── fato_gols
            ├─1:*── fato_cartoes
            └─1:*── fato_substituicoes  (id_jogador_entrou = ativa | id_jogador_saiu = inativa)
```

## Relacionamentos (todos com filtro em direção única: dimensão → fato)

| De (lado 1)                  | Para (lado *)                            | Estado  |
|------------------------------|------------------------------------------|---------|
| `dim_competicao[id_competicao]` | `dim_partida[id_competicao]`          | Ativa   |
| `dim_calendario[Date]`       | `dim_partida[data]`                      | Ativa   |
| `dim_partida[id_partida]`    | `fato_gols[id_partida]`                  | Ativa   |
| `dim_partida[id_partida]`    | `fato_cartoes[id_partida]`               | Ativa   |
| `dim_partida[id_partida]`    | `fato_substituicoes[id_partida]`         | Ativa   |
| `dim_partida[id_partida]`    | `fato_participacoes[id_partida]`         | Ativa   |
| `dim_jogador[id_jogador]`    | `fato_participacoes[id_jogador]`         | Ativa   |
| `dim_jogador[id_jogador]`    | `fato_gols[id_jogador]`                  | Ativa   |
| `dim_jogador[id_jogador]`    | `fato_cartoes[id_jogador]`               | Ativa   |
| `dim_jogador[id_jogador]`    | `fato_substituicoes[id_jogador_entrou]`  | Ativa   |
| `dim_jogador[id_jogador]`    | `fato_substituicoes[id_jogador_saiu]`    | **Inativa** (usada por `USERELATIONSHIP` na medida `Saídas (substituição)`) |

> É por causa da cadeia `dim_competicao → dim_partida → fatos` que a segmentação de
> **competição** filtra todas as páginas de uma vez.

## Tabelas

### dim_competicao
`id_competicao` (BRA, CDB, LIB, PAU…), `competicao`, `fonte`, `tipo`, `ordem`.
Classifique `competicao` pela coluna `ordem`.

### dim_partida (1 linha por jogo do Palmeiras)
`id_partida` (ex.: `BRA2026-073`), `id_competicao`, `temporada`, `rodada`, `numero_jogo`,
`data`, `horario`, `estadio`, `mandante`, `visitante`, `local_palmeiras` (Casa/Fora),
`adversario`, `gols_pro`, `gols_contra`, `gols_pro_1t`, `gols_contra_1t`, `resultado` (V/E/D),
`pontos`, `penaltis_pro`, `penaltis_contra`, `tecnico_palmeiras`, `tecnico_adversario`,
`arbitro`, `arquivo_origem` — mais, no Power Query: `ordem_jogo`, `confronto`,
`placar_texto`, `rotulo_jogo`.

`resultado` e `pontos` são do **tempo regulamentar** (90'). Em mata-mata decidido nos
pênaltis, o jogo conta como empate e os pênaltis ficam em `penaltis_pro/contra`.

### dim_jogador
`id_jogador` (id CBF — chave estável), `apelido`, `nome_completo`, `equipe`, `lado`, `goleiro`.
A súmula trunca nomes longos (`...`); o pipeline escolhe a versão completa quando o
jogador aparece sem truncamento em algum jogo (relação ou eventos).

### fato_participacoes (1 linha por jogador relacionado em cada jogo)
`titular`, `goleiro`, `utilizado` (titular ou entrou), `entrou_do_banco`, `minuto_entrada`,
`minuto_saida`, `minutos_jogados`.
Minutos são **nominais**: base 90' (120' se houver prorrogação), sem somar acréscimos.
A saída considera substituição ou expulsão.

### fato_gols
`lado_autor` (quem fez), `lado_beneficiado` (para quem o gol conta), `tipo` (NR/PN/CT/FT),
`gol_contra`, `periodo`, `minuto`, `acrescimo`, `minuto_texto`, `faixa_minuto`, `faixa_ordem`.

> **Premissa dos gols contra:** a coluna "Equipe" da súmula é tratada como o time do atleta
> que fez o gol contra; o gol conta para o outro time. A auditoria compara com o placar
> final e acusa qualquer divergência — se aparecer, inverta a regra em `01_extrair_sumulas.py`
> (bloco `benef = ...`).

### fato_cartoes
`cor` (Amarelo/Vermelho), `tipo_vermelho` (Direto/Segundo amarelo), `papel` (Jogador/Técnico),
`id_jogador` (vazio para técnico), `motivo_codigo` (ex.: A1.13), `motivo_resumo`,
`motivo_texto`, `faixa_minuto`.
O amarelo que gerou a expulsão por 2º amarelo também consta como amarelo (como na súmula).

### fato_substituicoes
`id_jogador_entrou`, `id_jogador_saiu`, `minuto_texto` (`Intervalo` para trocas no intervalo).

## Ocultar / ajustar
- Oculte colunas de chave (`id_*`) e `minuto_ordem`, `faixa_ordem`.
- Classifique `faixa_minuto` por `faixa_ordem`; `Mês` por `Mês Nº`; `competicao` por `ordem`.
- Formate `Aproveitamento` e `Participação em Gols (%)` como porcentagem.
