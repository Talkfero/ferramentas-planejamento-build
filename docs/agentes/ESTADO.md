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
