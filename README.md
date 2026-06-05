# Ferramentas de Planejamento - build completo

Empacotador Windows para os 9 aplicativos:

- Ferramentas de Planejamento / launcher
- Elexplan
- Diagnostico de alimentadores
- ImageDx - Detalhamento
- Unificador de arquivos
- Coplan Web
- Ambiente Capex
- Status de medicao
- Sistema de Cadastro

O instalador usa Inno Setup com `PrivilegesRequired=lowest` e instala em
`{localappdata}\Programs\Ferramentas de Planejamento`, portanto nao exige
administrador do usuario final.

## Como gerar

1. Configure o secret `BUILD_REPO_READ_TOKEN` ou `GH_PAT` com permissao de leitura nos repos privados `Talkfero/*`.
2. Rode o workflow `Build installer` manualmente no GitHub Actions.
3. Baixe o instalador na release mais recente em
   [Releases](../../releases/latest) (asset `FerramentasCompartilhadas-Setup-*.exe`).

No workflow, o input `apps` escolhe qual instalador gerar:

- `all`: instalador completo.
- `coplan_web`, `capex`, `cadastro` etc.: instalador parcial de um app.

Mesmo no instalador parcial, o workflow monta o `_internal` completo. Assim da
para atualizar apenas um executavel, como `Coplan Web.exe`, sem deixar os outros
apps instalados sem as dependencias compartilhadas.

Cada build publica uma unica release com a tag fixa `latest`: o workflow apaga as
releases e os artifacts antigos e recria a release com o instalador novo, entao a
pagina de Releases sempre tem apenas o ultimo build.

O workflow monta `apps/` a partir dos repos ativos no GitHub e usa os dois apps
locais versionados aqui (`imagedx` e `unificador`).

## Build local em Windows

```bat
set BUILD_REPO_READ_TOKEN=<token-com-acesso-aos-repos>
powershell -ExecutionPolicy Bypass -File scripts\prepare_apps.ps1
python scripts\validate_layout.py --apps all
build_all_shared.bat all
ISCC Setup_turbinado.iss
```

Para compilar um instalador parcial localmente, mantenha o bundle completo e use
`APP_ONLY` apenas no Inno:

```bat
build_all_shared.bat all
ISCC /DAPP_ONLY=coplan_web Setup_turbinado.iss
```
