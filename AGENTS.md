# Build da suíte — guia dos agentes

Integra repositórios de origem e produz o instalador. Leia `README.md`,
`docs/agentes/ESTADO.md` e o workflow pertinente antes de modificar a receita.

## Invariantes

- `apps/` contém clones descartáveis; versão/correção vêm da origem.
- Versão do instalador não é versão de todos os aplicativos.
- Confirmar commits desejados na branch clonada pelo build. Pendência local em
  outra sessão não deve ser publicada implicitamente.
- Build somente quando solicitado. O workflow publica release rolling `latest`;
  dispará-lo tem efeito externo, não é mera validação de documentação.
- Novo runtime/asset/import dinâmico exige avaliar recipe, layout e executável.
- Metadados de versão dos EXEs são necessários; conferir antes de distribuir.

## Publicação em rede

Validar build → copiar instalador → conferir SHA-256 da cópia → backup do
`latest.json` → publicar JSON → reler JSON da rede e validar. Preservar política
de `min_version` já decidida; ver referências do índice comum. Build aprovado
no GitHub não prova que o arquivo foi publicado na rede.

Validação depende do escopo: para layout, seguir o uso de
`scripts/validate_layout.py` no workflow; não disparar build para testar Markdown.
Documentar resultado e artefato, origem dos apps, hashes e passo de publicação
concluído no registro da sessão. Não incluir binários locais alheios no commit.

## Memória compartilhada

Localize `segundo-cerebro-arthur` como pasta irma deste projeto, ou pelo
`SECOND_BRAIN_PATH` se definido. Leia `operacao/GUIA_WORKSPACE.md` e o indice
somente se ainda nao carregados; selecione referencias pelo assunto da tarefa.
Claude e Codex seguem os mesmos procedimentos de iniciar/encerrar.
Se a fonte compartilhada estiver indisponivel, use este guia e os documentos
locais, informando a limitacao. Nao inventar memoria nem criar copia divergente.
