# Roteiro do dashboard (6 páginas)

**Segmentações globais** (sincronize em todas as páginas: Exibir > Sincronizar segmentações):
`dim_competicao[competicao]` (lista, multisseleção — é o filtro Paulistão / Libertadores /
Brasileirão / Copa do Brasil…), `dim_partida[temporada]`, `dim_partida[local_palmeiras]`.

Cabeçalho de todas as páginas: cartão com a medida `Título Competição`.

---

## 01 · Visão Geral
- **Cartões:** `Partidas`, `Vitórias`, `Empates`, `Derrotas`, `Pontos`, `Aproveitamento`,
  `Gols Pró`, `Gols Contra`, `Saldo de Gols`.
- **Cartão de texto:** `Forma Recente` (últimos 5: V V E D V).
- **Linha:** eixo `dim_partida[ordem_jogo]`, valor `Pontos Acumulados`.
- **Colunas empilhadas:** eixo `dim_competicao[competicao]`, valores `Vitórias`, `Empates`, `Derrotas`.
- **Tabela de jogos:** `rotulo_jogo`, `placar_texto`, `resultado` (cor de fundo com `Resultado Cor`).
- **Destaques:** `Artilheiro`, `Mais Utilizado`.

## 02 · Performance Coletiva
- **Linha:** `Saldo Acumulado` por `ordem_jogo`.
- **Colunas agrupadas:** `Gols Pró` e `Gols Contra` por `rotulo_jogo`.
- **Colunas:** `Gols Pró (eventos)` e `Gols Sofridos (eventos)` por `fato_gols[faixa_minuto]`
  (ordenada por `faixa_ordem`) — mostra em que momento do jogo o time marca e sofre.
- **Matriz Casa x Fora:** linhas `local_palmeiras`; valores `Partidas`, `Pontos`,
  `Aproveitamento`, `Gols Pró`, `Gols Contra`, `Saldo de Gols`.
- **Matriz por adversário:** linhas `adversario`; valores `Vitórias`, `Empates`, `Derrotas`, `Saldo de Gols`.
- **Cartões:** `Jogos sem Sofrer Gols`, `Média Gols Pró`, `Média Gols Contra`.

## 03 · Análise de Partidas
- **Segmentação (seleção única):** `dim_partida[rotulo_jogo]`.
- **Cabeçalho:** `Partida Selecionada`, `Detalhe Competição`, `Estádio Selecionado`,
  `Técnico Selecionado`, `Árbitro Selecionado`.
- **Tabela de gols:** `minuto_texto`, `nome`, `tipo_descricao`, `equipe_autor`
  (classificar por `minuto_ordem`).
- **Tabela de cartões:** `minuto_texto`, `cor`, `nome`, `equipe`, `motivo_resumo`.
- **Tabela de substituições:** `minuto_texto`, `equipe`, `nome_entrou`, `nome_saiu`.
- **Tabela de participações:** `dim_jogador[apelido]`, `titular`, `minuto_entrada`,
  `minuto_saida`, `minutos_jogados` (filtro visual `lado = Palmeiras`).

## 04 · Desempenho Individual
- **Barras (Top 10):** `dim_jogador[apelido]` × `Gols do Elenco`.
- **Barras (Top 10):** `Jogos Utilizados` e `Titularidades`.
- **Tabela de jogadores:** `apelido`, `Jogos Utilizados`, `Titularidades`, `Entradas do Banco`,
  `Minutos Jogados`, `Gols do Elenco`, `Gols por 90`, `Cartões Amarelos`, `Cartões Vermelhos`
  (filtro visual `dim_jogador[lado] = Palmeiras`).
- **Dispersão:** X = `Minutos Jogados`, Y = `Gols do Elenco`, detalhe = `apelido`.
- **Perfil individual:** segmentação `dim_jogador[apelido]` + cartões `Jogos Utilizados`,
  `Minutos Jogados`, `Média de Minutos por Jogo`, `Gols do Elenco`, `Gols por 90`,
  `Minutos por Gol`, `Participação em Gols (%)`, `Entradas (substituição)`, `Saídas (substituição)`.
- **Goleiros:** tabela filtrada por `dim_jogador[goleiro] = 1` com `Jogos Utilizados`,
  `Jogos sem Sofrer Gols (goleiros)`.

## 05 · Disciplina e Elenco
- **Cartões:** `Cartões Amarelos`, `Cartões Vermelhos`, `Expulsões Diretas`,
  `Expulsões por 2º Amarelo`, `Cartões por Jogo`, `Jogadores Advertidos`.
- **Linha:** `Cartões Acumulados` por `ordem_jogo`.
- **Colunas:** `Cartões Amarelos` por `fato_cartoes[faixa_minuto]`.
- **Barras:** contagem de cartões por `motivo_resumo` (Top 10).
- **Tabela de advertidos:** `apelido`, `Cartões Amarelos`, `Cartões Vermelhos`.
- **Utilização do elenco:** colunas com `Jogadores Utilizados` por `rotulo_jogo`;
  cartões `Jogadores Utilizados`, `Substituições Realizadas`.
- **Comparativo com adversários:** `Cartões Amarelos` x `Cartões Amarelos Adversário`.

## 06 · Comparativo entre Competições
- **Matriz:** linhas `dim_competicao[competicao]`; valores `Partidas`, `Vitórias`, `Empates`,
  `Derrotas`, `Aproveitamento`, `Gols Pró`, `Gols Contra`, `Saldo de Gols`, `Média Gols Pró`,
  `Média Gols Contra`, `Cartões por Jogo`, `Jogos sem Sofrer Gols`.
- **Barras:** `Aproveitamento` por competição; `Gols do Elenco` por competição.
- **Dica:** nesta página, desative a sincronização da segmentação de competição, senão a
  matriz mostra só a competição selecionada.

---

## Página de auditoria (opcional, oculta)
Tabela com `rotulo_jogo`, `Gols Pró`, `Gols Pró (eventos)`, `Gols Contra`,
`Gols Sofridos (eventos)` e a medida `Divergência Placar x Eventos` (deve ser 0 em todas as linhas).

## Identidade visual
Verde-escuro (`#006437`) para destaque, verde-claro para apoio, cinza neutro para
empates, vermelho (`#B3261E`) só para derrotas/expulsões. Fonte Segoe UI.
Projeto independente de portfólio, sem vínculo oficial com o clube ou com a CBF.
