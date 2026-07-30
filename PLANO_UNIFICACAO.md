# Rascunho — levantamento sobre unificar Elexplan e Diagnóstico

> **Status: não aprovado.** A unificação foi avaliada em 30/07/2026 e **abortada
> por decisão do usuário** — os dois apps continuam separados e nenhum código
> foi fundido. O documento fica como levantamento técnico: se o assunto voltar,
> o trabalho de investigação já está feito. **Não há nome de produto definido**
> (as sugestões avaliadas foram descartadas).

O que esta análise apurou e continua válido independentemente da fusão:

1. `diagnostico_backend/` **não importa Qt** — está no docstring do
   `interplan.py` e foi confirmado por varredura. Qualquer reuso daquela regra
   sob outra UI não precisa de reescrita.
2. Existem **cinco duplicações reais** entre os dois apps (§3), sendo a mais
   cara a leitura de topologia do Interplan, que hoje tem duas implementações.
3. O ImageDx já tinha sua função absorvida pelo Coplan — o que sustentou a
   aposentadoria dele, executada em 30/07/2026 (§6).
4. Os dois programas usam **os mesmos quatro patamares** e a mesma chave de
   junção (nome do alimentador), então cruzá-los é barato quando for a hora.

## 1. Por que a ideia apareceu

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

## 2. Identidade

Não há nome definido — a discussão de nome foi encerrada sem escolha. O que
ficou registrado como requisito, caso o tema volte: o nome precisa carregar o
sentido de **diagnosticar e concluir**, não o de apenas observar.

Requisito de identidade: nenhum nome de ação muda. Continuam iguais *Processar*, *Extrair PIM*, *Demanda em Lote
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
<app>/
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

## 5. Fases (se um dia for retomado)

| Fase | Entrega |
|---|---|
| **1** | Monorepo: `diagnostico_backend` entra como pacote do outro app, sem mudar comportamento. Suítes de teste juntas, verdes |
| **2** | `comum/`: uma só leitura de CSV do Interplan, um só *snap* de chave, um só exportador Excel |
| **3** | UI web da área **Rede**; Qt do Diagnóstico vira legado executável |
| **4** | Tela **Alimentador X** (medição × rede) |
| **5** | Instalador: um componente no lugar de `app_elexplan` + `app_diag`; chaves antigas viram alias |

Ordem pensada para o app nunca ficar quebrado: até a fase 3 os dois exes atuais
continuam existindo.

## 6. ImageDx — aposentado em 30/07/2026

`codigo3_imagedx.py` são 242 linhas de PySide6 + Pillow: junta imagens, aplica
legenda e redimensiona. O **detalhamento de verdade** (PPTX + KML da Daimon) já
mora no Coplan (`coplanweb/core/services/detalhamento_pptx.py` e `kml_geo.py`),
o mesmo caminho das fusões anteriores — a função já estava absorvida.

Executado (esta é a única parte do documento que virou código):

- `Setup_turbinado.iss`: `WantImageDx = 0`, chave `imagedx` vira alias de
  `coplan_web`, e o `[InstallDelete]` remove o exe e o atalho de quem já tinha a
  suíte instalada;
- `multi_apps.spec`, `build_gui.py`, `build_all_shared.bat`,
  `scripts/validate_layout.py` e o workflow: app fora de todas as listas;
- `apps/imagedx/` **permanece versionado como histórico** e não entra em build.

Sem pendência: o usuário confirmou em 30/07/2026 que **ninguém mais usa** o
ImageDx, nem para montar prancha de imagem fora do detalhamento do Coplan. A
aposentadoria está fechada; `apps/imagedx/` fica só como histórico versionado.

## 7. Suíte hoje

| App | Situação |
|---|---|
| Sistema de Cadastro | mantém |
| Coplan Web (com Capex e Detalhamento) | mantém |
| Unificador de arquivos | mantém |
| Elexplan e Diagnóstico | **seguem separados** (fusão abortada) |
| ImageDx | aposentado (§6) |
| Launcher | mantém; o card do ImageDx some sozinho (ele varre executáveis) |

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

- **Base do rebalanceamento: corrente do tronco** — o trecho de maior carga do
  alimentador, o mesmo ponto onde o diagnóstico calcula o %Desbal. NEMA. Assim
  o Δspread da sugestão é o ganho no número que o laudo reporta. Já é o padrão
  de `build_rebalance_report(..., base="tronco")`; a soma das chaves continua
  disponível como `base="chaves"` para comparar com resultado antigo do
  Elexplan (ela conta chaves em série em duplicidade e, no export real, produzia
  reduções de 0,03 A).

- **ImageDx aposentado** — executado, ver §6.
- **Unificação abortada** — os dois apps seguem separados. Se voltar, a
  recomendação técnica registrada é o repo do Elexplan absorver (§3).
