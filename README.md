# Ferramentas de Planejamento - build completo

Empacotador Windows para os 6 aplicativos:

- Ferramentas de Planejamento / launcher
- Elexplan (ja inclui o **Status de Medicao**: chaves/rebalanceamento, status PIM e estatistica)
- Diagnostico de alimentadores
- Unificador de arquivos
- Coplan Web (ja inclui o **Ambiente Capex** embarcado — `capex_engine`)
- Sistema de Cadastro

> **Capex fundido no Coplan (2026-06-18):** o antigo app *Ambiente Capex* deixou
> de ter exe/repo proprios. O motor de calculo foi vendorizado para
> `coplanweb/capex_engine/` e exposto como o "Gerenciador de Cenarios" dentro do
> **Coplan Web.exe**. As chaves `capex` e `coplan` continuam aceitas como alias
> de `coplan_web` para retrocompat.
>
> **Status de Medicao fundido no Elexplan (2026-06-18):** o antigo app *Status de
> medicao* deixou de ter exe/repo proprios. Suas funcoes (Gerar arquivo de
> chaves + otimizador de rebalanceamento de fases, Status PIM por alimentador e
> Analise Estatistica) viraram abas do **Elexplan.exe**. A chave `status`
> continua aceita como alias de `elexplan`.

> **ImageDx aposentado (2026-07-30):** o *ImageDx - Detalhamento* deixou de ter
> exe e componente proprios. O detalhamento (PPTX + KML da Daimon) e feito no
> **Coplan Web**, em `coplanweb/core/services/detalhamento_pptx.py` e
> `kml_geo.py`. A chave `imagedx` continua aceita como alias de `coplan_web`, e
> o instalador remove o `ImageDx- Detalhamento.exe` e o atalho de quem ja tinha
> a suite instalada.
>
> **O fonte fica guardado de proposito** em `apps/imagedx/` (nao e ignorado pelo
> git, nao entra em build nenhum). Se um dia alguem precisar do app de volta,
> basta desfazer o commit "Aposenta o ImageDx da suite": ele tem, num lugar so,
> a chave nas listas de `multi_apps.spec` / `build_gui.py` /
> `build_all_shared.bat` / `scripts/validate_layout.py` e o `WantImageDx` do
> `Setup_turbinado.iss`.

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
- `coplan_web`, `cadastro` etc.: instalador parcial de um app.
  (`capex` resolve para `coplan_web`; `status` resolve para `elexplan`.)

Mesmo no instalador parcial, o workflow monta o `_internal` completo. Assim da
para atualizar apenas um executavel, como `Coplan Web.exe`, sem deixar os outros
apps instalados sem as dependencias compartilhadas.

Cada build publica uma unica release com a tag fixa `latest`: o workflow apaga as
releases e os artifacts antigos e recria a release com o instalador novo, entao a
pagina de Releases sempre tem apenas o ultimo build.

O workflow monta `apps/` a partir dos repos ativos no GitHub e usa o app local
versionado aqui (`unificador`). A pasta `apps/imagedx/` continua versionada como
historico do app aposentado, mas nao entra em nenhum build.

> **Sistema de Cadastro:** o build compartilhado precisa espelhar o
> `main_web/requirements-web.txt` do repo `sistemadecadastro`. Desde a automação
> SAP/1ª Medida, isso inclui leitura de PDF/7z/e-mail (`pypdf`, `py7zr`,
> `extract-msg`) e o fallback semântico local para formulários desconhecidos
> (`sentence-transformers[onnx]`), além de SAP GUI/Excel no Windows (`pywin32`).
> O `multi_apps.spec`
> declara os hidden imports/collects correspondentes; atualize o spec e o
> `requirements.lock.txt` sempre que esse contrato mudar.

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
