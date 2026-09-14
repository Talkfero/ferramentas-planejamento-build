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
