@echo off
setlocal EnableDelayedExpansion

rem ================================================================
rem Build unificado (COLLECT compartilhado, _internal unico)
rem
rem Uso:
rem   build_all_shared.bat                         -> menu interativo
rem   build_all_shared.bat all                     -> todos os apps
rem   build_all_shared.bat launcher                -> apenas launcher
rem   build_all_shared.bat launcher cadastro       -> subset
rem
rem Chaves validas:
rem   launcher, elexplan, diag, imagedx, unif,
rem   coplan_web, cadastro
rem
rem coplan_web  = Coplan Web.exe   (pywebview; ja embarca o motor CAPEX)
rem elexplan    = Elexplan.exe     (ja inclui o Status de Medicao: chaves/
rem               rebalanceamento, status PIM por alimentador e estatistica)
rem cadastro    = Sistema de Cadastro.exe (pywebview)
rem
rem Aliases retrocompat:
rem   "coplan" -> "coplan_web"
rem   "capex"  -> "coplan_web" (Ambiente Capex fundido no Coplan / capex_engine)
rem   "status" -> "elexplan"   (Status de Medicao fundido no Elexplan)
rem
rem Dependencias: antes do PyInstaller, instala o requirements de cada
rem app selecionado (apps web usam requirements-web.txt; apps sem arquivo
rem recebem os pacotes inline). Para pular essa etapa e usar o venv como
rem esta:  set "SKIP_DEPS=1"  antes de rodar.
rem ================================================================

set "SPEC_FILE=multi_apps.spec"
set "DIST_NAME=FerramentasCompartilhadas"

if "%~1"=="" goto menu
if /I "%~1"=="menu" goto menu
if /I "%~1"=="/?" goto usage
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--help" goto usage

set "APPS="
:parse_args
if "%~1"=="" goto do_build
rem Alias retrocompat: "coplan" antigo vira "coplan_web"
set "ARG=%~1"
if /I "!ARG!"=="coplan" set "ARG=coplan_web"
rem Capex fundido no Coplan: aceita "capex" como alias de coplan_web.
if /I "!ARG!"=="capex" set "ARG=coplan_web"
rem Status de Medicao fundido no Elexplan: aceita "status" como alias.
if /I "!ARG!"=="status" set "ARG=elexplan"
if defined APPS (
  set "APPS=!APPS!,!ARG!"
) else (
  set "APPS=!ARG!"
)
shift
goto parse_args

:usage
echo.
echo Uso:
echo   %~nx0                        menu interativo
echo   %~nx0 all                    todos os apps
echo   %~nx0 launcher               apenas launcher
echo   %~nx0 launcher cadastro      subset (launcher + cadastro)
echo.
echo Chaves: launcher, elexplan, diag, imagedx, unif, coplan_web, cadastro
echo.
exit /b 0

:menu
echo.
echo =====================================================
echo   Build - Ferramentas de Planejamento
echo =====================================================
echo     0  Todos
echo     1  Launcher (Ferramentas de Planejamento)
echo     2  Elexplan           (ja inclui o Status de Medicao)
echo     3  Diagnostico de alimentadores
echo     4  ImageDx - Detalhamento
echo     5  Unificador de arquivos
echo     6  Coplan Web         (pywebview, ja inclui o Capex)
echo     7  Sistema de Cadastro (pywebview)
echo =====================================================
echo  Dicas: pode combinar (ex. "1 3 7") ou digitar as chaves
echo         (ex. "launcher diag cadastro coplan_web")
echo.
set /p "CHOICE=Escolha: "

if "!CHOICE!"=="" goto menu

set "APPS="
for %%N in (!CHOICE!) do (
  set "KEY="
  if "%%N"=="0"        set "KEY=all"
  if "%%N"=="1"        set "KEY=launcher"
  if "%%N"=="2"        set "KEY=elexplan"
  if "%%N"=="3"        set "KEY=diag"
  if "%%N"=="4"        set "KEY=imagedx"
  if "%%N"=="5"        set "KEY=unif"
  if "%%N"=="6"        set "KEY=coplan_web"
  if "%%N"=="7"        set "KEY=cadastro"
  if /I "%%N"=="all"        set "KEY=all"
  if /I "%%N"=="launcher"   set "KEY=launcher"
  if /I "%%N"=="elexplan"   set "KEY=elexplan"
  if /I "%%N"=="diag"       set "KEY=diag"
  if /I "%%N"=="imagedx"    set "KEY=imagedx"
  if /I "%%N"=="unif"       set "KEY=unif"
  rem Alias: "coplan" antigo vira "coplan_web"
  if /I "%%N"=="coplan"     set "KEY=coplan_web"
  if /I "%%N"=="coplan_web" set "KEY=coplan_web"
  rem Alias: "capex" fundido no Coplan -> coplan_web
  if /I "%%N"=="capex"      set "KEY=coplan_web"
  rem Alias: "status" fundido no Elexplan -> elexplan
  if /I "%%N"=="status"     set "KEY=elexplan"
  if /I "%%N"=="cadastro"   set "KEY=cadastro"
  if defined KEY (
    if defined APPS (
      set "APPS=!APPS!,!KEY!"
    ) else (
      set "APPS=!KEY!"
    )
  )
)

if not defined APPS (
  echo [aviso] Nenhuma opcao valida. Tente de novo.
  goto menu
)

:do_build
echo.
echo =====================================================
echo  Alvos selecionados: !APPS!
echo =====================================================
set "APPS_TO_BUILD=!APPS!"

if not exist "%SPEC_FILE%" (
  echo [ERRO] %SPEC_FILE% nao encontrado em %CD%
  exit /b 1
)

echo.
echo [1/3] Instalando dependencias dos apps selecionados...
if /I "%SKIP_DEPS%"=="1" (
  echo   [deps] SKIP_DEPS=1 -^> pulando instalacao ^(usando o venv como esta^).
  goto after_deps
)

rem PyInstaller e' sempre necessario.
python -m pip install pyinstaller
if errorlevel 1 (
  echo [ERRO] Falha ao instalar pyinstaller.
  exit /b 1
)

rem Expande "all" para todas as chaves; senao usa a lista selecionada.
set "DEP_KEYS=!APPS!"
if /I "!APPS!"=="all" set "DEP_KEYS=launcher,elexplan,diag,imagedx,unif,coplan_web,cadastro"

set "DEP_FAIL="
for %%K in (!DEP_KEYS!) do call :install_for %%K
if defined DEP_FAIL (
  echo.
  echo [ERRO] Falha ao instalar dependencias de pelo menos um app.
  echo        Corrija o ambiente ou use SKIP_DEPS=1 para pular.
  exit /b 1
)
:after_deps

echo.
echo [2/3] Limpando build/dist anteriores...
if exist build rmdir /s /q build
if exist "dist\%DIST_NAME%" rmdir /s /q "dist\%DIST_NAME%"

echo [3/3] Executando PyInstaller (APPS_TO_BUILD=!APPS_TO_BUILD!)...
python -m PyInstaller --noconfirm --clean "%SPEC_FILE%"
if errorlevel 1 (
  echo.
  echo [ERRO] PyInstaller falhou.
  exit /b 1
)

if exist "app_configs\*.exe.config" (
  echo.
  echo [fixup] Copiando configs .NET dos apps pywebview...
  copy /Y "app_configs\*.exe.config" "dist\%DIST_NAME%\" >nul
  if errorlevel 1 (
    echo [ERRO] Falha ao copiar app_configs\*.exe.config para dist\%DIST_NAME%\
    exit /b 1
  )
)

echo.
echo =====================================================
echo  Build concluido.
echo  Saida: dist\%DIST_NAME%\
echo.

rem Dica: mostra a chamada do Inno Setup correspondente
if /I "!APPS!"=="all" (
  echo  Para gerar o instalador completo:
  echo      ISCC Setup_turbinado.iss
) else (
  rem Se ha somente 1 chave, sugere APP_ONLY
  echo  Para gerar o instalador correspondente:
  for /f "tokens=1,2 delims=," %%a in ("!APPS!") do (
    if "%%b"=="" (
      echo      ISCC /DAPP_ONLY=%%a Setup_turbinado.iss
    ) else (
      echo      ISCC Setup_turbinado.iss
      echo      [obs] /DAPP_ONLY aceita apenas 1 chave; com subset use o completo.
    )
  )
)
echo =====================================================

endlocal
exit /b 0

rem ================================================================
rem Subrotina: instala as dependencias de UMA chave de app.
rem  - apps web (coplan_web/capex/cadastro) -> requirements-web.txt
rem    (NAO o requirements.txt desktop da raiz do app)
rem  - apps sem arquivo de requirements -> pacotes inline (PySide6...)
rem Define DEP_FAIL=1 em qualquer falha (lido pelo chamador).
rem Chamada: call :install_for <chave>
rem ================================================================
:install_for
set "K=%~1"
set "REQ="
set "REQ_EXTRA="
set "PKGS="
if /I "!K!"=="launcher"   set "REQ=apps\launcher\requirements.txt"
if /I "!K!"=="diag"       set "REQ=apps\diagnostico\requirements.txt"
if /I "!K!"=="coplan_web" (
  set "REQ=apps\coplan\requirements-web.txt"
  set "REQ_EXTRA=apps\coplan\scripts\build\requirements-build.txt"
)
if /I "!K!"=="cadastro" (
  set "REQ=apps\cadastro_viabilidades\main_web\requirements-web.txt"
  set "PKGS=pywebview pythonnet clr_loader"
)
rem Elexplan agora inclui Status de Medicao e Extracao PIM;
rem usa o requirements.txt do proprio app (pandas/numpy/PySide6/openpyxl/playwright).
if /I "!K!"=="elexplan"   set "REQ=apps\elexplan\requirements.txt"
rem imagedx e unif tem requirements.txt PINADO (versoes ==) no proprio app.
if /I "!K!"=="imagedx"    set "REQ=apps\imagedx\requirements.txt"
if /I "!K!"=="unif"       set "REQ=apps\unificador\requirements.txt"

if defined REQ  goto install_req
if defined PKGS goto install_pkgs
echo   [!K!] [aviso] chave sem dependencias mapeadas
goto :eof

:install_req
if not exist "!REQ!" (
  echo   [!K!] [aviso] requirements ausente: !REQ!
  set "DEP_FAIL=1"
  goto :eof
)
echo   [!K!] pip install -r !REQ!
python -m pip install -r "!REQ!"
if errorlevel 1 set "DEP_FAIL=1"
if defined REQ_EXTRA (
  if not exist "!REQ_EXTRA!" (
    echo   [!K!] [aviso] requirements extra ausente: !REQ_EXTRA!
    set "DEP_FAIL=1"
    goto :eof
  )
  echo   [!K!] pip install -r !REQ_EXTRA!
  python -m pip install -r "!REQ_EXTRA!"
  if errorlevel 1 set "DEP_FAIL=1"
)
if defined PKGS goto install_pkgs
goto :eof

:install_pkgs
echo   [!K!] pip install !PKGS!
python -m pip install !PKGS!
if errorlevel 1 set "DEP_FAIL=1"
goto :eof
