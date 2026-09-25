# Gerar instalador e publicar — procedimento

Definido pelo usuário em 22/09/2026. **Os dois gatilhos são diferentes e a
diferença é proposital:** um mexe só na máquina, o outro mexe no servidor.

| O que o usuário diz | O que fazer | Toca o servidor? |
|---|---|---|
| **"gerar novo instalador"** | Partes 1 e 2 (versão + build + validação) | **Não** |
| **"gerar instalador e publicar"** | Partes 1, 2 e 3 | **Sim** |

Sem um desses pedidos, não gerar build. Não publicar por iniciativa própria,
nem "aproveitar" um instalador já gerado: publicar é sempre pedido explícito.

---

## Parte 1 — Versão, antes de qualquer build

1. Ler a versão publicada de verdade, na rede, não a do repositório:
   `cat "//fs-celpa-02/GEPLP/COPLD/10 - SOFTWARES/Ferramentas de Planejamento/latest.json"`
   Um instalador pode existir no repo e nunca ter sido publicado — foi o caso
   do 1.3.4, que ficou local enquanto a rede seguia no 1.3.2.
2. A versão do **instalador** fica em `Setup_turbinado.iss`, em duas linhas que
   andam juntas: `AppVersion` e `AppVersion4` (esta com o `.0` no fim). Ela tem
   de superar a maior já gerada, publicada ou não.
3. A versão de **cada app** é a constante do próprio app, e não se inventa aqui:
   - Coplan: `coplanweb/backend/_state.py`, `APP_VERSION`
   - Cadastro: `sistemadecadastro/main_web/main_web.py`, `APP_VERSION`
   - Elexplan: `elexplan/elexplan/webui/updates.py`, `APP_VERSION`
   App cuja constante não mudou **mantém** a versão publicada. Não subir versão
   de app só porque o instalador subiu: são numerações independentes.
4. Commitar a mudança de versão **antes** do build, para o instalador
   corresponder a um commit.

## Parte 2 — Build

```
powershell -ExecutionPolicy Bypass -File scripts\build_all_local.ps1 -Apps all
```

Roda na raiz de `ferramentas-planejamento-build`. Espelha o CI e faz tudo
offline: monta `apps/` a partir dos repos irmãos, valida o layout, instala as
dependências num venv isolado, roda o PyInstaller, copia os configs .NET,
valida o runtime e compila o Inno Setup. Demora bastante.

Pré-requisitos: Python 3.12 pelo `py` launcher (o `python` do PATH pode ser
outro) e o ISCC do Inno Setup — nesta máquina em
`%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`, que o script já procura.

Saída:
- bundle em `dist\FerramentasCompartilhadas`
- instalador em `Output\FerramentasCompartilhadas-Setup-<versão>.exe`

Antes de seguir: conferir que o script terminou em "BUILD ALL CONCLUIDO", que
o `.exe` existe e que o tamanho é compatível com os anteriores (~600 MB). Build
verde no GitHub **não** prova que o arquivo foi publicado na rede.

`scripts/validate_layout.py` rodado na mão costuma acusar falta em
`apps/cadastro_viabilidades` — é o clone descartável velho, não o contrato.
O build reclona antes de validar; conferir a origem antes de tratar como erro.

### Quando o build falha no `COLLECT` com WinError 3

Sintoma: os executáveis são todos gerados, e o build morre no último passo,
ao limpar `dist/`, com `FileNotFoundError: [WinError 3]` num caminho que
existe. Aconteceu em 22/09/2026.

Causa: **limite de 260 caracteres do Windows**. O repositório mora sob
`OneDrive - GRUPO EQUATORIAL ENERGIA\Documentos\Arquivos\Codigos\`, um
prefixo longo, e o `dist/` anterior guardava `torch-2.13.0.dist-info` — resto
de antes da migração para ONNX. O Torch traz licenças em pastas muito
aninhadas (`.../kineto/libkineto/third_party/dynolog/third_party/DCGM/...`),
e somado ao prefixo o `shutil.rmtree` do PyInstaller não consegue nem caminhar
na árvore. `WinError 3` num caminho que existe é a assinatura disso.

Correção: apagar `dist/FerramentasCompartilhadas` com método que aguenta
caminho longo, porque `Remove-Item` comum falha igual:

```
robocopy <pasta vazia> <dist\FerramentasCompartilhadas> /MIR
Remove-Item -LiteralPath <dist\FerramentasCompartilhadas> -Recurse -Force
```

`dist/` é saída de build e está no `.gitignore`: apagar é seguro e é o que o
próprio PyInstaller tentava fazer. **Não confundir com interrupção:** a
primeira tentativa desse dia foi atribuída a processo morto e era o mesmo
WinError 3 — só faltava o log inteiro para ver.

## Parte 3 — Publicação na rede (só no gatilho com "publicar")

Nesta ordem, sem pular etapa:

1. **Copiar** o instalador para
   `//fs-celpa-02/GEPLP/COPLD/10 - SOFTWARES/Ferramentas de Planejamento/`.
2. **Conferir o SHA-256 da CÓPIA**, não o do arquivo local. O hash que vai no
   JSON é o da cópia que o usuário vai baixar.
3. **Backup do `latest.json`** que está lá, no padrão já usado na pasta:
   `latest.json.bak-AAAAMMDD-HHMMSS`.
4. **Publicar o JSON novo.** Uma seção por app — `coplanweb`,
   `sistemadecadastro`, `elexplan` — cada uma com `version`, `url`, `sha256`,
   `notes` e `min_version`. As três apontam para o **mesmo** instalador, com o
   mesmo `sha256`: o pacote é um só.
5. **Validar o JSON com as regras do próprio app, ANTES de copiar para a rede:**

   ```
   python scripts/check_latest_json.py <o json novo>
   ```

   Ele importa `looks_like_fs_path` e `fs_path_from` do Cadastro — as funções
   que decidem, em produção, se o download acontece — e confere url por url,
   o SHA-256 do arquivo que a url **resolve**, e se `min_version` não ficou
   maior que `version`. Sai 1 se algo estiver errado.

6. **Reler o JSON da rede** e rodar o validador **de novo**, agora contra o
   arquivo publicado. Escrever não é publicar; publicado é o que se lê de volta.

### Por que o validador existe

Em 23/09/2026 a publicação saiu com a url escrita com **uma** barra invertida
inicial em vez de duas. Sem o prefixo UNC completo, `looks_like_fs_path`
devolve `False` e o app recusa com `url_invalida`. Como `min_version` obriga a
atualizar, o usuário ficou **bloqueado e sem conseguir atualizar**.

A validação daquele dia passou porque conferia só o **nome** do arquivo
(`PurePath(url).name`), descartando o caminho — ou seja, **não falharia com o
defeito presente**. Nunca validar `latest.json` com verificação própria:
usar as funções do app, que são a regra de verdade.

**Nunca escrever a url à mão.** Partir da url que já funcionava (o backup) e
trocar apenas o nome do instalador: escapar contrabarra em Python e em JSON ao
mesmo tempo é onde o erro nasce.

### `min_version` trava o aplicativo

Não é rótulo. Quando a versão instalada é menor que `min_version`, o app mostra
uma tela de bloqueio **sem como fechar** — `force_required` em
`backend/domains/config.py` do Coplan e o equivalente nos outros. Subir
`min_version` tranca todo mundo que ainda não instalou.

A prática registrada nas publicações anteriores é `min_version` **igual** à
`version` daquele app. Mantê-la assim é o padrão; qualquer coisa diferente é
decisão do usuário, não do agente.

### `notes`

Vão para a tela de atualização do usuário final. Uma por app, começando com o
nome e a versão do app, em linguagem de quem usa o programa — não mensagem de
commit, não nome de arquivo. Descrever o que mudou para quem abre a tela.
