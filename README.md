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

O workflow tem dois inputs, e eles respondem perguntas diferentes.

**`apps` — qual INSTALADOR gerar:**

- `all`: instalador completo.
- `coplan_web`, `cadastro` etc.: instalador parcial de um app.
  (`capex` resolve para `coplan_web`; `status` resolve para `elexplan`.)

**`rebuild_only` — o que RECOMPILAR** (vazio = tudo):

- vazio: o PyInstaller monta o bundle inteiro. E' o padrao.
- `coplan_web`: recompila so' o Coplan e completa o bundle com o do ultimo
  build completo, guardado em cache. Bem mais rapido — nem o `pip` nem o
  PyInstaller tocam nas arvores pesadas dos apps que nao mudaram (torch e
  sentence-transformers do Cadastro, PySide6 e playwright do Elexplan).

Os dois sao independentes. Para "mexi so' no Coplan e quero o instalador
completo", use `apps=all` + `rebuild_only=coplan_web`.

### O `_internal` sai SEMPRE completo — e por que isso nao e' negociavel

O bundle e' compartilhado: `dist\FerramentasCompartilhadas\` tem **um** unico
`_internal\`, montado pelo `COLLECT` do fim do `multi_apps.spec`, somando as
`binaries`/`datas` de todos os apps compilados. `pandas` e `numpy` servem
Coplan, Cadastro e Diagnostico e aparecem **uma vez** — a deduplicacao acontece
ai, no PyInstaller. O Inno **nao une nada**: ele so' empacota
`dist\FerramentasCompartilhadas\_internal\*` como esta, e nao tem como enxergar
um build anterior.

Some a isso o `[InstallDelete]` do `Setup_turbinado.iss`, que apaga
`{app}\_internal` inteiro antes de instalar. Um instalador cujo `_internal`
tenha so' as libs de um app, aplicado sobre a suite instalada, substituiria o
`_internal` compartilhado e deixaria **os outros apps sem as dependencias
deles** — eles parariam de abrir.

Por isso `apps=coplan_web` sozinho **nao** encolhe o bundle: sem
`rebuild_only`, o PyInstaller compila tudo e o `apps` restringe apenas o passo
do Inno. E com `rebuild_only`, o bundle parcial e' completado a partir do cache
(`scripts/overlay_bundle.ps1`), que ao final **verifica se os 6 executaveis
estao presentes** e derruba o build se faltar algum.

> Ate 31/07/2026 este README afirmava que o instalador parcial ja montava o
> `_internal` completo. **Nao montava** — o workflow passava o `apps` tambem
> para o PyInstaller. Quem gerasse um instalador parcial quebraria os demais
> apps de quem o instalasse. Corrigido junto com a entrada do `rebuild_only`.

### Como o cache do bundle e' invalidado

A chave cobre so' o que define o conjunto de **dependencias** —
`requirements.lock.txt`, `multi_apps.spec`, `build_all_shared.bat`,
`runtime_hooks/**`, `app_configs/**` e `apps/**/requirements*.txt` — e **nunca**
o codigo-fonte dos apps. E' exatamente isso que deixa reaproveitar o bundle
quando so' o codigo do Coplan mudou. Mudou dependencia? A chave muda, o cache
nao bate e o workflow **cai sozinho para build completo**, avisando no log.

### Onde o tempo do build realmente vai

Medido no run `30637305478` (build completo, 30m45s):

| fase | tempo | % |
|---|---|---|
| checkout + clones dos apps | 0:28 | 2% |
| `pip` (baixar/instalar libs) | 4:19 | 14% |
| **PyInstaller** | **20:13** | **66%** |
| Inno Setup (lzma2/max sobre ~600 MB) | 4:30 | 15% |
| publicar release | ~1:30 | 5% |

O gargalo e' o **PyInstaller**, nao o download das libs — por isso o
`rebuild_only` (que corta as Analysis dos apps que nao mudaram) rende muito
mais que o cache do pip. Os dois estao ligados assim mesmo: ha um
`actions/cache` para os wheels do pip (`PIP_CACHE_DIR`), que recupera boa parte
daqueles 4 min. Ele usa `restore-keys` com prefixo de proposito — o cache do
pip e' aditivo e serve mesmo quando um requirements mudou, ao contrario do
cache do bundle, que exige match exato.

Para referencia local: um `build_all_local.ps1 -Apps coplan_web` leva ~2,3 min
de PyInstaller nesta maquina, com o venv e o cache do pip ja quentes.

Duas consequencias que valem saber:

- **So' o build completo alimenta o cache.** Um bundle incremental e' mistura
  (app novo + base antigo); cachear isso empilharia deriva a cada rodada. O
  base e' sempre fruto de um build completo de verdade.
- **`STRICT_COLLECT=1` no modo incremental.** Por padrao o
  `_collect_all_safe` do spec so' avisa quando um pacote nao esta no venv (para
  um build parcial do app A nao morrer por dependencia do app B). No
  incremental isso viraria armadilha: o `pip` instala apenas os requirements
  dos apps recompilados, e um pacote faltando sairia so' como print no log,
  gerando um `.exe` com o PYZ incompleto. O overlay **nao** conserta isso — os
  modulos puros viajam dentro do `.exe` recem-gerado, nao no `_internal`. Com
  `STRICT_COLLECT=1` a coleta que falhar derruba o build.

Cada build publica uma unica release com a tag fixa `latest`: o workflow apaga as
releases e os artifacts antigos e recria a release com o instalador novo, entao a
pagina de Releases sempre tem apenas o ultimo build.

O workflow monta `apps/` a partir dos repos ativos no GitHub e usa o app local
versionado aqui (`unificador`). A pasta `apps/imagedx/` continua versionada como
historico do app aposentado, mas nao entra em nenhum build.

> **Elexplan e a UI web (2026-07-31):** o Elexplan migrou para **pywebview**
> (`codigo1_web.py` -> `elexplan.webui`) e o frontend Qt foi **aposentado, nao
> removido** (`codigo1_elexplan.py`, empacotado so' pelo job `build-qt-legacy`
> do proprio repo). Esta spec apontava para o entry Qt, entao o `Elexplan.exe`
> da suite abria a **janela antiga** enquanto o `Elexplan_Setup.exe` do repo
> proprio ja trazia a web. A receita canonica e' o job **build-web** de
> `.github/workflows/build-exe.yml` no repo do Elexplan; ao mexer no
> empacotamento dele, espelhe aquele job. O `elexplan/webui/static/` (HTML/CSS/
> JS/uPlot) **precisa** entrar como `datas` — sem ele a janela abre em branco —
> e o app entrou na lista de apps pywebview do `finalize_bundle.ps1`,
> `validate_runtime_bundle.ps1` e do aviso de WebView2 do instalador.

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
