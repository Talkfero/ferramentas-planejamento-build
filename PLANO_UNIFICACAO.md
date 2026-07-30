# Plano — Lupa (Elexplan + Diagnóstico de Alimentadores)

Rascunho de 30/07/2026. Objetivo: **um app só para análise de alimentador**,
chamado **Lupa**, juntando o que o Elexplan faz (medição) com o que o
Diagnóstico faz (rede simulada), e enxugar a suíte para quatro programas.

> Já houve duas fusões iguais a esta na suíte, e o padrão delas vale aqui:
> Capex → Coplan e Status de Medição → Elexplan (ambas em 18/06/2026). Nas duas,
> o app com **UI web e instalador** absorveu o outro, a chave antiga virou
> **alias** e o README da suíte registrou a mudança.

## 1. Por que faz sentido

Os dois programas respondem à mesma pergunta — *como está este alimentador?* —
com metades diferentes da evidência:

| | Elexplan | Diagnóstico |
|---|---|---|
| Fonte | Medição real (PIM, relé/SCADA) | Simulação do Interplan (fluxo de potência) |
| Responde | O que **aconteceu**: demanda, corrente, patamares, fator de carga, consistência da medição | O que a rede **aguenta**: tensão pu, carregamento, desequilíbrio, sequências ≥67%, prioridades de obra |
| Saída | Parâmetros para laudo e Interplan | Diagnóstico por alimentador e comparativo anual |
| Unidade | **Alimentador × patamar** | **Alimentador × patamar** |

Os patamares são **os mesmos quatro** (Madrugada/Manhã/Tarde/Noite) e a chave de
junção é o nome do alimentador. Hoje o engenheiro abre dois programas, exporta
dois Excel e cruza na mão.

O rebalanceamento de fases já mostrou a costura na prática: a sugestão nasceu no
Elexplan (aritmética das correntes por fase) mas só fica correta com a topologia
que o Diagnóstico já lê — a fase precisa existir no ponto inicial da chave.

## 2. Nome e identidade

**Lupa** (decidido em 30/07/2026). O sufixo `-plan` de Coplan/Elexplan foi
descartado de propósito: o produto fundido não é mais um "plan" da família, é a
ferramenta de **olhar um alimentador de perto** — medição e rede na mesma lente.
Nome de uma palavra, imediato, sem precisar de explicação, e livre para virar
ícone (`Lupa.exe`) e verbo no dia a dia ("passa na Lupa").

A identidade dos dois programas sobrevive **no vocabulário**: nenhum nome de
ação muda. Continuam iguais *Processar*, *Extrair PIM*, *Demanda em Lote
Interplan*, *Status de Medição*, *Prioridades de obra*, *Comparativo anual*,
*Sequências ≥67%*. Quem abria o Elexplan encontra as mesmas palavras; quem abria
o Diagnóstico também.

## 3. Arquitetura alvo

Base recomendada: **o repositório do Elexplan absorve o backend do Diagnóstico**.

Motivos concretos:

- `diagnostico_backend/` **não importa Qt** (está escrito no docstring do
  `interplan.py` e confirmado por varredura) — entra como pacote sob a UI web
  sem reescrever regra;
- o Elexplan já tem o que a suíte exige: UI web (pywebview), `APP_VERSION` +
  auto-update por `latest.json`, instalador NSIS *onedir*, disciplina de
  camadas e limite de 2.000 linhas por arquivo;
- o Qt do Elexplan já foi **aposentado sem ser removido** — existe precedente
  interno para manter a tela antiga funcionando durante a migração.

```
lupa/
  backend/            # regra pura, sem UI
    medicao/          # ex-elexplan: workprocess, relay, calculations, processing
    rede/             # ex-diagnostico: processing, interplan, exports
    comum/            # alimentador, patamares, leitura CSV do Interplan, Excel
  webui/              # UI web única (pywebview)
  legado_qt/          # telas Qt do Diagnóstico, aposentadas mas executáveis
```

O que vira `comum/` no dia 1 (hoje é duplicado):

| Hoje duplicado | Onde está |
|---|---|
| Leitura de CSV do Interplan com aliases de coluna | `diagnostico_backend.processing` × `elexplan.backend.topology` |
| Coordenada de chave e *snap* de nó | `processing.load_chaves_coords` × `topology.read_switch_catalog` |
| Patamares e classificação por horário | `calculations.categorize_time` × colunas por patamar |
| Exportação Excel com abas/formatação | `exports.py` × `webui.api.write_*` |
| Tema, preferências, log em `%APPDATA%` | `config.py` × `backend.runtime` |

## 4. UI — uma janela, duas frentes

Barra lateral com duas áreas, mais a tela que só existe depois da fusão:

1. **Medição** — arquivo de medição (PIM cru, Workprocess, TXT de relé),
   Processar/Solar, Status de Medição, Balanço, Cenário, Interplan.
2. **Rede** — pasta `Exporta` do Interplan, diagnóstico por alimentador,
   prioridades de obra, sequências ≥67%, comparativo anual, rebalanceamento.
3. **Alimentador X** — a tela nova: medição e rede lado a lado para o mesmo
   alimentador. É a justificativa da fusão e a identidade nova do produto.
   Ex.: demanda máxima medida × carregamento simulado; desequilíbrio medido
   (status) × NEMA do tronco; e o rebalanceamento sugerido com as duas
   evidências.

Clean sem perder identidade: layout e tokens de tema do Elexplan web (já
tem claro/escuro), mantendo do Diagnóstico os elementos que são marca dele —
KPIs no topo, chips de status (Críticos/Atenção/OK), selo por linha e o
destaque de valor fora do limite.

## 5. Fases

| Fase | Entrega | Estado |
|---|---|---|
| **0** | Rebalanceamento com checagem de topologia, já no `diagnostico_backend/rebalanceamento.py` (usa `load_chaves_coords` e o *snap* existentes) | **feito**, falta ligar na UI |
| **1** | Monorepo: `diagnostico_backend` entra no repo do Elexplan como `backend/rede/`, sem mudar comportamento. Suíte de testes dos dois juntas, verdes | |
| **2** | `backend/comum/`: uma só leitura de CSV do Interplan, um só *snap* de chave, um só exportador Excel. Remove as duplicatas da tabela acima | |
| **3** | UI web da área **Rede**: diagnóstico por alimentador, prioridades, sequências, comparativo anual. Qt do Diagnóstico vira `legado_qt/` (aposentado, executável) | |
| **4** | Tela **Alimentador X** (medição × rede) e rebalanceamento com as duas evidências | |
| **5** | Instalador: um componente só no lugar de `app_elexplan` + `app_diag`; chaves `elexplan`, `diag` e `status` viram alias; launcher e README atualizados | |
| **6** | Aposentar ImageDx (ver §6) | |

Ordem pensada para o app nunca ficar quebrado: até a fase 3 os dois exes atuais
continuam existindo.

## 6. ImageDx

`codigo3_imagedx.py` são 242 linhas de PySide6 + Pillow: junta imagens, aplica
legenda e redimensiona. O **detalhamento de verdade** (PPTX + KML da Daimon) já
mora no Coplan (`coplanweb/core/services/detalhamento_pptx.py` e `kml_geo.py`),
que é o mesmo caminho das fusões anteriores — a função já está absorvida.

Antes de remover, confirmar com quem usa: existe alguém montando prancha de
imagem **fora** do fluxo de detalhamento do Coplan? Se sim, a saída barata é
levar o "juntar imagens + legenda" para dentro do Coplan como uma ação do
detalhamento, e só então tirar o componente `app_imagedx` do instalador.

## 7. Suíte depois da unificação

| App | Situação |
|---|---|
| Sistema de Cadastro | mantém |
| Coplan Web (com Capex e Detalhamento) | mantém |
| Unificador de arquivos | mantém |
| **Lupa** (Elexplan + Diagnóstico) | fusão |
| ImageDx | aposentado (§6) |
| Launcher | mantém, com um card a menos |

Lembrete de release da suíte: `apps/` no repo de build é **clone descartável da
branch default** de cada repo. Nada entra no instalador enquanto não estiver na
`main` do app.

## 8. Riscos e cuidados

- **Automação do Interplan** (`diagnostico_backend/interplan.py`, ~3,7k linhas)
  dirige a interface do Interplan por automação de janelas. É a parte mais
  frágil da fusão: mover de repo sem mexer, e só depois avaliar.
- **`app.py` do Diagnóstico tem 4.852 linhas** — acima do limite de 2.000 do
  Elexplan. A migração para a UI web é a oportunidade de quebrar por tela; o
  arquivo Qt legado fica de fora da regra enquanto estiver em `legado_qt/`.
- **Duas fontes de verdade para a mesma regra** durante as fases 1–2. Vale a
  lição VC-04 do Elexplan: dois algoritmos da mesma regra divergem. Nada de
  duplicar rebalanceamento, leitura de topologia ou patamar.
- **Retreinamento**: quem usa hoje abre dois ícones. O launcher deve manter os
  dois nomes antigos apontando para o app novo por pelo menos um ciclo.
- **Comparabilidade de laudo**: a fusão não pode mudar número de laudo sem
  aviso. Toda mudança de cálculo continua exigindo docs + testes +
  `LICOES_APRENDIDAS.md`.

## 9. Decisões

**Fechadas em 30/07/2026:**

- **Nome: Lupa** (ver §2).
- **Base do rebalanceamento: corrente do tronco** — o trecho de maior carga do
  alimentador, o mesmo ponto onde o diagnóstico calcula o %Desbal. NEMA. Assim
  o Δspread da sugestão é o ganho no número que o laudo reporta. Já é o padrão
  de `build_rebalance_report(..., base="tronco")`; a soma das chaves continua
  disponível como `base="chaves"` para comparar com resultado antigo do
  Elexplan (ela conta chaves em série em duplicidade e, no export real, produzia
  reduções de 0,03 A).

**Em aberto:**

1. **Repo base** — recomendado: o do Elexplan absorve (§3).
2. **ImageDx**: alguém ainda usa fora do detalhamento do Coplan?
