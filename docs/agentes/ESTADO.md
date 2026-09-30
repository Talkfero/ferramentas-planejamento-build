# Estado — ferramentas-planejamento-build

Inventário de 09/09/2026. Revalidar fatos mutáveis ao retomar.

HEAD local `8b6618a`, branch `main`. Existe instalador local não rastreado em `publish/`; não foi modificado. README/workflow têm validações de layout e self-test; conferir a receita vigente quando houver pedido de build. Nenhum build/publicação executado nesta organização.

Decisões e aprendizados novos seguem o padrão comum. Não há tarefa de produto
automaticamente autorizada por este inventário.

## Contrato ONNX do Cadastro — 10/09/2026

Alteração local autorizada junto com a implementação PDF/SAP do Cadastro,
na branch `melhoria/leitura-pdf-sap-vetorial`, base `62280a5`. Lock/spec passam
a usar ONNX Runtime, Tokenizers e Hugging Face Hub; retiradas dependências
diretas Torch/ST/Transformers/Optimum/exportação ONNX. A análise do Cadastro
exclui esses módulos e o validador exige `mw_semantic.py` no fonte clonado.
AST do spec e contrato com o fonte atual do Cadastro validados sem build.
O cache de bundle já inclui hash de lock/spec/requirements, evitando reutilizar
um bundle com contrato anterior. Instalador local preexistente preservado.
Sem commit ou publicação. Pendente validar executável e tamanho após pedido de
build; integrar em conjunto com a branch correspondente do Cadastro.

## Integração autorizada — 14/09/2026

Usuário autorizou commit/push/merge do trabalho pendente. Contrato de arquivos
e requirements do Cadastro e sintaxe do spec revalidados contra a origem.
Commit inclui somente fonte e documentação; instalador preexistente continua
fora do Git. Integração remota na sessão cf559c. Nenhum build será disparado.

## Requirements e sincronizacao — 21/09/2026

Branch `main`, HEAD `1a26c90` no inicio da sessao, arvore limpa fora do
instalador `publish/FerramentasCompartilhadas-Setup-1.3.4.exe`, que continua
nao rastreado. `fetch` feito: `main` igual a `origin/main`. O HEAD `8b6618a`
citado no inventario de 09/09 esta superado por este registro.

Conferencia de requirements (script proprio, somente leitura): o lock foi
comparado com os requirements de origem de cada app que `build_all_shared.bat`
instala — launcher, diagnostico, coplan (web + build), cadastro, elexplan,
unificador e imagedx. Antes: dois pacotes ficavam fora da trava.

- `playwright` — entra pelo `requirements.txt` do Elexplan e pelo
  `_collect_all_required("playwright")` do PIM em `multi_apps.spec`.
- `pyqtgraph` — entra pelo frontend Qt legado do Elexplan.

Ambos eram instalados sem `PIP_CONSTRAINT` efetivo, ou seja, o build pegava a
versao mais nova do dia. Pinados em `playwright==1.60.0` e `pyqtgraph==0.14.0`,
versoes do ambiente local — o mesmo ambiente bate exatamente com 81 dos 83
pacotes do lock que tem instalados, o que sustenta a escolha. Apos a mudanca,
os oito conjuntos de requirements sao satisfeitos pelo lock, sem pendencia.
**As duas pinagens nao passaram por build**: confirmar no proximo build pedido.

`scripts/validate_layout.py` local acusa `mw_semantic.py` e os tres pacotes
ONNX ausentes, mas isso e' o clone descartavel em `apps/cadastro_viabilidades`,
anterior a troca para ONNX. A origem satisfaz o contrato: `main_web/mw_semantic.py`
e' rastreado no Cadastro e o `requirements-web.txt` de la tem onnxruntime,
tokenizers e huggingface-hub. Em CI o `prepare_apps.ps1` reclona antes de validar.

Sem build e sem publicacao. Instalador 1.3.4 segue como ultimo artefato local;
o proximo tem de superar essa versao.

## Build e publicacao da 1.3.5 — 23/09/2026

Autorizado pelo usuario. Instalador `FerramentasCompartilhadas-Setup-1.3.5.exe`,
235.845.846 bytes, SHA-256 `0e9c6c68e22be9a2dc4ca36f8043660114a9d6475cde22c8d184f42e2801dbec`.
Publicado na pasta de rede; `latest.json` substituido, com backup
`latest.json.bak-20260923-092016`. Relido da rede e o SHA-256 recalculado
**no servidor** confere. Versoes: Coplan 1.3.2, Cadastro 1.2.3, Elexplan 1.1.0,
com `min_version` igual a `version` nos tres — **atualizacao obrigatoria**.

O build local foi usado, e nao o workflow do GitHub, porque a publicacao precisa
do arquivo nesta maquina. O usuario apontou que o costume era o CI; o script
local e' espelho declarado do workflow. Fica registrado para a proxima decisao.

**Tres tentativas ate passar, e as duas primeiras acharam defeito real:**

1. `WinError 3` no COLLECT. O `dist/` guardava `torch-2.13.0.dist-info`, de
   antes da migracao ONNX; as pastas de licenca do Torch somadas ao prefixo do
   OneDrive estouram os 260 caracteres do Windows, e nem o `rmtree` do
   PyInstaller limpava. O build passa a limpar `dist/` com robocopy.
2. `Elexplan.exe` nao abria: `ImportError: Can't determine version for pytz` no
   `import pandas`. O pandas 3.x importa pytz de forma lazy, o PyInstaller nao
   o via, e o hook do pytz criava `_internal/pytz/` sem `__init__.py`, que
   sombreava o modulo ausente. Atingia Elexplan, Diagnostico e Coplan;
   Unificador e Cadastro escaparam por acaso. Corrigido por hidden import.

Tamanho: caiu de 601 MB (1.3.2) para 225 MB. `torch`, `transformers` e
`sentence_transformers` estao ausentes do bundle, como a migracao ONNX
pretendia — **isso conclui a pendencia de validar tamanho apos build**.

**Limite da validacao, dito com todas as letras:** so Coplan e Elexplan tem
self-test, e o do Coplan **passaria com o app quebrado** — ele nao importa
pandas, e o pandas aparece em 24 arquivos do Coplan. Diagnostico, Unificador,
Cadastro e launcher **nao foram executados**. A regressao do pytz foi conferida
nos TOCs dos seis, mas isso nao substitui abrir os aplicativos.

## Publicacoes 1.3.6 e 1.3.7 — 25 e 28/09/2026

Consolidado em 29/09/2026 (sessao `2026-09-29-105926-claude-ferramentas-planejamento-build-cccb1e`)
a partir dos registros das sessoes que fizeram o trabalho e do Git. Nada foi
rebuildado nem relido da rede nesta consolidacao.

HEAD `a956692` em `main`. Commits desde o registro da 1.3.5 (`1f24ef5`):

- `1fe96e4` — instalador 1.3.6 (`Setup_turbinado.iss`), `[skip ci]`.
- `e321f94` — `scripts/check_latest_json.py` e passo novo em `docs/PUBLICAR.md`:
  valida o `latest.json` com as funcoes do proprio app antes e depois de publicar.
- `a956692` — instalador 1.3.7, `[skip ci]`.

| Instalador | Data | Coplan | Cadastro | Elexplan | SHA-256 | Backup do `latest.json` | Sessao |
|---|---|---|---|---|---|---|---|
| 1.3.6 | 25/09 | 1.3.3 | 1.2.3 | 1.2.0 | `f69bea6a…fb10ba` | `latest.json.bak-20260925-170740` | `2026-09-22-142711-claude-workspace-4dd754` |
| 1.3.7 | 28/09 | 1.3.3 | 1.2.3 | 1.2.1 | `c888a51e…b575a` | `latest.json.bak-20260928-154714` | `2026-09-28-152332-claude-elexplan-01e7dd` |

As duas tem `min_version` igual a `version` nos tres apps, ou seja,
atualizacao obrigatoria. O SHA-256 foi conferido na copia da rede nas duas.

**Por que surgiu o `check_latest_json.py`.** A 1.3.5 foi publicada com a url
comecando por uma contrabarra so, em vez de duas. O app recusava com
`url_invalida` e, como `min_version` obriga, o usuario ficou bloqueado. A
validacao da epoca so conferia o nome do arquivo. O defeito foi corrigido na
rede em 23/09. A 1.3.7 foi a primeira publicacao com o validador rodando antes
da copia e contra o arquivo publicado, com exit 0 nas duas vezes.

**Espaco na rede.** A copia da 1.3.6 falhou por disco cheio (0,15 GB livres de
150 GB). Com autorizacao, as seis versoes anteriores a 1.2.0 foram apagadas.
Depois da 1.3.7 restam cerca de 1,1 GB, o que da para umas quatro publicacoes
deste tamanho. O share inteiro esta cheio, entao o assunto e com a TI
(`WS-share-cheio`).

**Travas `playwright`/`pyqtgraph` (`WS-lock-sem-build`).** Continuam em
`requirements.lock.txt` (`playwright==1.60.0`, `pyqtgraph==0.14.0`), e os
builds da 1.3.5 a 1.3.7 passaram com elas, incluindo o self-test do Elexplan.
O caminho do PIM que usa o Playwright nao foi executado. Proposta: fechar a
pendencia quando o usuario confirmar que o PIM abre no app instalado.

**Limites que continuam valendo:**

- Nenhuma das duas versoes teve os apps abertos em janela real (`ELEX-ui-real`).
- So Coplan e Elexplan tem self-test, e o do Coplan nao importa o pandas.
  Diagnostico, Unificador, Cadastro e launcher nunca sao executados no build
  (`WS-validacao-so-dois-apps`).
- Os instaladores 1.3.5 a 1.3.7 nao estao em `publish/`, onde so ha o 1.3.4
  (nao rastreado, preservado) e `latest-1.3.2.json`.
- Branches locais extras: `build-incremental-cache` (tres commits nao
  mesclados, `WS-build-incremental-cache`), `fix/valida-playwright-elexplan` e
  `melhoria/leitura-pdf-sap-vetorial`. O destino delas nao foi revisado nesta
  consolidacao.

## Build e publicacao da 1.3.8 — 30/09/2026

Pedido do usuario: *"gerar instalador e publicar; tem que atualizar versao do
elexplan que mexi"*. Sessao `2026-09-29-105926-claude-ferramentas-planejamento-build-cccb1e`.

Origem conferida com `fetch` antes do build: launcher, Diagnostico, Coplan,
Cadastro e Elexplan limpos e iguais ao `origin`. No Elexplan sobravam so
`codigo1_web.py` (linha em branco no fim) e `interplan.py` (fim de linha),
herdados e sem efeito. O build local copia a arvore de trabalho, entao isso
foi conferido antes.

- Elexplan `APP_VERSION` 1.2.1 -> **1.3.0**, MINOR pela regra do `updates.py`
  (funcoes novas: comparacao PIM x rele e periodo do banco no Mercado).
  `0ac040c` no Elexplan, `[skip ci]`.
- Instalador -> **1.3.8** em `Setup_turbinado.iss`, `b288f46`, `[skip ci]`.

Build local (`build_all_local.ps1 -Apps all`), 10:09 a 10:36, terminou em
"BUILD ALL CONCLUIDO", exit 0, na primeira tentativa. Requirements e layout
verdes; self-test do Coplan OK; self-test do Elexplan OK ("Playwright e driver
disponiveis"); runtime pywebview OK em Elexplan, Coplan e Cadastro. Versoes nos
clones: Coplan 1.3.3, Cadastro 1.2.3, Elexplan 1.3.0.

| Instalador | Coplan | Cadastro | Elexplan | Bytes | SHA-256 | Backup do `latest.json` |
|---|---|---|---|---|---|---|
| 1.3.8 | 1.3.3 | 1.2.3 | 1.3.0 | 236.080.853 | `dee40652a835db79fa018dd54c55b15382c3915fff5b71c3558f1ad4fbb24b95` | `latest.json.bak-20260930-104218` |

Publicacao, na ordem do `docs/PUBLICAR.md`: copia para a rede com o SHA-256 da
copia igual ao local; backup; JSON montado a partir do backup trocando so o
nome do instalador na url; comparado campo a campo com o backup (mudaram so
url e sha256 nas tres secoes, e version, min_version e notes no Elexplan);
`check_latest_json.py` com exit 0 antes de publicar e de novo contra o arquivo
lido da rede. `min_version` do Elexplan = 1.3.0: **atualizacao obrigatoria**.
Espaco na rede depois: ~0,9 GB.

**Achados deste build:**

- **Os seis EXEs saem com `FileVersion` 0.0.0.** O `multi_apps.spec` le
  `APP_VERSION` do ambiente, que o workflow define e o `build_all_local.ps1`
  nao. CompanyName, ProductName e FileDescription estao preenchidos, que e o
  que resolveu o bloqueio do Defender em 04/08. **Nao e regressao:** a 1.3.7
  instalada nesta maquina tambem tem os seis com 0.0.0, assim como todo build
  local desde a 1.3.5. Correcao proposta: o script local exportar a versao do
  `.iss` antes do PyInstaller.
- A mensagem final do script diz "Instalador gerado: ...Setup-1.0.2.exe"; o
  ISCC gerou o 1.3.8. O script escolhe o arquivo errado de `Output/` so para
  imprimir. Nao afeta o artefato, mas engana quem le so o fim do log.

Continuam valendo: nenhum app aberto em janela real; Diagnostico, Unificador,
Cadastro e launcher nao sao executados no build.

## Republicacao da 1.3.8 com a mesma versao — 30/09/2026 (tarde)

Pedido do usuario: *"fiz uma mexida no elexplan e quero novo instalador mas
sem aplicar nova versao no elexplan; rebuilda e publica de novo a mesma
versao"*. Sessao `2026-09-30-151510-claude-ferramentas-planejamento-build-ec08e2`.
Excecao explicita a regra do `docs/PUBLICAR.md` de subir a versao do
instalador: continua **1.3.8**, com Elexplan **1.3.0**.

Entrou o Elexplan `112df01` (piso interno de 3% no IMPOSSIVEL do Mercado,
`PISO_DO_IMPOSSIVEL = 0.03`, conferido no clone). Notas da tela de
atualizacao **nao** mudaram: o usuario pediu que os 3% nao aparecam ("e' uma
regra interna").

| Instalador | Coplan | Cadastro | Elexplan | Bytes | SHA-256 | Backup do `latest.json` |
|---|---|---|---|---|---|---|
| 1.3.8 (rebuild) | 1.3.3 | 1.2.3 | 1.3.0 | 236.065.146 | `0f0e7b236fe456154f6a2998d6e1fd32b0d453c0e41fcba106206b98924f98ad` | `latest.json.bak-20260930-162423` |

O 1.3.8 da manha (`dee40652…`) foi substituido na rede; copia local em
`Output/FerramentasCompartilhadas-Setup-1.3.8-anterior-dee40652.exe`.

Build: `APP_VERSION=1.3.8` definido no ambiente, como o workflow faz, e **os
seis EXEs sairam com FileVersion 1.3.8** — confirma a correcao proposta em
`WS-build-local-sem-versao-exe`, ainda nao incorporada ao script. Self-tests
Coplan e Elexplan OK, pywebview OK nos tres.

Tres tentativas, nenhuma por defeito de codigo:

1. O venv `%TEMP%\fplan_build_venv`, criado em 22/09, teve arquivos apagados
   as 12:39 por limpeza automatica de Temp (sumiram `pip/__main__.py` e
   `pywin32_bootstrap`); o script so confere a minor do Python e morreu em
   "Falha ao atualizar pip no venv". Refeito com `-RecreateVenv`.
2. Com o venv novo, o pip 26.2.1 travou num `access violation` de conexao
   (nao reproduziu em teste isolado); os dois processos do pip do proprio
   build foram encerrados e o bat seguiu. A rodada foi morta pelo limite de
   30 min das tarefas em segundo plano do agente, no ultimo EXE.
3. Disparada com `Start-Process`, fora desse limite: 15:52-16:22, exit 0.

Publicacao: instalador copiado como `.novo`, SHA da copia igual; backup;
troca 16:24:24; JSON a partir do backup trocando so o `sha256`; validador exit
0 antes; JSON publicado 16:24:33 (~9 s com sha antigo: o app recusaria o
download, sem instalar arquivo errado); relido e validado de novo.

**`min_version` do Elexplan.** De manha foi publicado 1.3.0; as 12:27 o
usuario baixou para 1.2.0 na rede, sem backup, "pra ninguem alterar"
enquanto a correcao nao saia. A republicacao preservou o 1.2.0. Pedido o
retorno, a escrita pelo agente foi bloqueada pelo controle de permissoes; o
**usuario editou as 17:05** e o relido da rede tem `min_version` 1.3.0,
validador exit 0, diferenca para o backup so nos `sha256` e nesse campo.

Quem ja tinha instalado o Elexplan 1.3.0 antes do rebuild **nao** recebe aviso
(mesma versao); so pega a correcao reinstalando pelo instalador da rede.
Rede: ~0,9 GB livres.
