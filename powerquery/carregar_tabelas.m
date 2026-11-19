// =============================================================================
// Desempenho do Palmeiras — Consultas do Power Query (M)
//
// COMO USAR
//  1. Power BI Desktop > Transformar dados > Gerenciar parâmetros > Novo parâmetro
//       Nome: CaminhoDados | Tipo: Texto | Valor atual:
//       C:\caminho\palmeiras-performance-hub\dados\tratados\      (com a barra final)
//  2. Para CADA bloco abaixo: Nova consulta > Consulta em branco > Editor avançado,
//     cole o código do bloco e renomeie a consulta exatamente como indicado.
//  3. Crie primeiro as duas funções (fnFaixaMinuto e fnFaixaOrdem); as tabelas dependem delas.
//  4. Desmarque "Habilitar carga" nas funções e no parâmetro. Feche e aplique.
// =============================================================================


// === Consulta: fnFaixaMinuto (função — não carregar) =========================
(minuto as nullable number) as nullable text =>
    if minuto = null then null
    else if minuto <= 15 then "00-15"
    else if minuto <= 30 then "16-30"
    else if minuto <= 45 then "31-45+"
    else if minuto <= 60 then "46-60"
    else if minuto <= 75 then "61-75"
    else if minuto <= 90 then "76-90+"
    else "Prorrogação"


// === Consulta: fnFaixaOrdem (função — não carregar) ==========================
(minuto as nullable number) as nullable number =>
    if minuto = null then null
    else if minuto <= 15 then 1
    else if minuto <= 30 then 2
    else if minuto <= 45 then 3
    else if minuto <= 60 then 4
    else if minuto <= 75 then 5
    else if minuto <= 90 then 6
    else 7


// === Consulta: dim_competicao ================================================
let
    Fonte = Csv.Document(File.Contents(CaminhoDados & "dim_competicao.csv"),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho,
                {{"id_competicao", type text}, {"competicao", type text}, {"fonte", type text},
                 {"tipo", type text}, {"ordem", Int64.Type}}, "en-US")
in
    Tipos


// === Consulta: dim_partida ===================================================
let
    Fonte = Csv.Document(File.Contents(CaminhoDados & "dim_partida.csv"),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho,
                {{"id_partida", type text}, {"id_competicao", type text}, {"temporada", Int64.Type},
                 {"rodada", type text}, {"numero_jogo", Int64.Type}, {"data", type date},
                 {"horario", type text}, {"estadio", type text}, {"mandante", type text},
                 {"visitante", type text}, {"local_palmeiras", type text}, {"adversario", type text},
                 {"gols_pro", Int64.Type}, {"gols_contra", Int64.Type},
                 {"gols_pro_1t", Int64.Type}, {"gols_contra_1t", Int64.Type},
                 {"resultado", type text}, {"pontos", Int64.Type},
                 {"penaltis_pro", Int64.Type}, {"penaltis_contra", Int64.Type},
                 {"tecnico_palmeiras", type text}, {"tecnico_adversario", type text},
                 {"arbitro", type text}, {"arquivo_origem", type text}}, "en-US"),
    Ordenado = Table.Sort(Tipos, {{"data", Order.Ascending}, {"horario", Order.Ascending}}),
    Indice = Table.AddIndexColumn(Ordenado, "ordem_jogo", 1, 1, Int64.Type),
    Confronto = Table.AddColumn(Indice, "confronto",
                each if [local_palmeiras] = "Casa" then "Palmeiras x " & [adversario]
                     else [adversario] & " x Palmeiras", type text),
    Placar = Table.AddColumn(Confronto, "placar_texto",
                each if [local_palmeiras] = "Casa"
                     then "Palmeiras " & Text.From([gols_pro]) & " x " & Text.From([gols_contra]) & " " & [adversario]
                     else [adversario] & " " & Text.From([gols_contra]) & " x " & Text.From([gols_pro]) & " Palmeiras",
                type text),
    Rotulo = Table.AddColumn(Placar, "rotulo_jogo",
                each Date.ToText([data], "dd/MM") & " · " & [adversario] & " (" & Text.Start([local_palmeiras], 1) & ")",
                type text)
in
    Rotulo


// === Consulta: dim_jogador ===================================================
let
    Fonte = Csv.Document(File.Contents(CaminhoDados & "dim_jogador.csv"),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho,
                {{"id_jogador", Int64.Type}, {"apelido", type text}, {"nome_completo", type text},
                 {"equipe", type text}, {"lado", type text}, {"goleiro", Int64.Type}}, "en-US")
in
    Tipos


// === Consulta: fato_participacoes ============================================
let
    Fonte = Csv.Document(File.Contents(CaminhoDados & "fato_participacoes.csv"),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho,
                {{"id_partida", type text}, {"id_jogador", Int64.Type}, {"equipe", type text},
                 {"lado", type text}, {"numero", type text}, {"titular", Int64.Type},
                 {"goleiro", Int64.Type}, {"utilizado", Int64.Type}, {"entrou_do_banco", Int64.Type},
                 {"minuto_entrada", Int64.Type}, {"minuto_saida", Int64.Type},
                 {"minutos_jogados", Int64.Type}}, "en-US")
in
    Tipos


// === Consulta: fato_gols =====================================================
let
    Fonte = Csv.Document(File.Contents(CaminhoDados & "fato_gols.csv"),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho,
                {{"id_gol", type text}, {"id_partida", type text}, {"id_jogador", Int64.Type},
                 {"numero", type text}, {"nome", type text}, {"equipe_autor", type text},
                 {"lado_autor", type text}, {"equipe_beneficiada", type text},
                 {"lado_beneficiado", type text}, {"tipo", type text}, {"tipo_descricao", type text},
                 {"gol_contra", Int64.Type}, {"periodo", type text}, {"minuto", Int64.Type},
                 {"acrescimo", Int64.Type}, {"minuto_ordem", type number}, {"minuto_texto", type text}}, "en-US"),
    Faixa = Table.AddColumn(Tipos, "faixa_minuto", each fnFaixaMinuto([minuto]), type text),
    FaixaOrdem = Table.AddColumn(Faixa, "faixa_ordem", each fnFaixaOrdem([minuto]), Int64.Type)
in
    FaixaOrdem


// === Consulta: fato_cartoes ==================================================
let
    Fonte = Csv.Document(File.Contents(CaminhoDados & "fato_cartoes.csv"),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho,
                {{"id_cartao", type text}, {"id_partida", type text}, {"cor", type text},
                 {"tipo_vermelho", type text}, {"papel", type text}, {"id_jogador", Int64.Type},
                 {"numero", type text}, {"nome", type text}, {"equipe", type text}, {"lado", type text},
                 {"periodo", type text}, {"minuto", Int64.Type}, {"acrescimo", Int64.Type},
                 {"minuto_ordem", type number}, {"minuto_texto", type text},
                 {"motivo_codigo", type text}, {"motivo_resumo", type text}, {"motivo_texto", type text}}, "en-US"),
    Faixa = Table.AddColumn(Tipos, "faixa_minuto", each fnFaixaMinuto([minuto]), type text),
    FaixaOrdem = Table.AddColumn(Faixa, "faixa_ordem", each fnFaixaOrdem([minuto]), Int64.Type)
in
    FaixaOrdem


// === Consulta: fato_substituicoes ============================================
let
    Fonte = Csv.Document(File.Contents(CaminhoDados & "fato_substituicoes.csv"),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Cabecalho,
                {{"id_sub", type text}, {"id_partida", type text}, {"equipe", type text},
                 {"lado", type text}, {"periodo", type text}, {"minuto", Int64.Type},
                 {"acrescimo", Int64.Type}, {"minuto_ordem", type number}, {"minuto_texto", type text},
                 {"id_jogador_entrou", Int64.Type}, {"numero_entrou", type text}, {"nome_entrou", type text},
                 {"id_jogador_saiu", Int64.Type}, {"numero_saiu", type text}, {"nome_saiu", type text}}, "en-US")
in
    Tipos
