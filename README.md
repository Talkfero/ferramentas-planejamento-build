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

1. Configure o secret `BUILD_REPO_READ_TOKEN` com permissao de leitura nos repos privados `Talkfero/*`.
2. Rode o workflow `Build installer` manualmente no GitHub Actions.
3. Baixe o artefato `FerramentasCompartilhadas-Setup`.

O workflow monta `apps/` a partir dos repos ativos no GitHub e usa os dois apps
locais versionados aqui (`imagedx` e `unificador`).

## Build local em Windows

```bat
set BUILD_REPO_READ_TOKEN=<token-com-acesso-aos-repos>
powershell -ExecutionPolicy Bypass -File scripts\prepare_apps.ps1
build_all_shared.bat all
ISCC Setup_turbinado.iss
```
