; ================================================================
; Setup_turbinado.iss  -  Ferramentas de Planejamento
; Inno Setup 6.x
;
; Modos de compilacao:
;   ISCC Setup_turbinado.iss                         -> instalador completo
;   ISCC /DAPP_ONLY=launcher    Setup_turbinado.iss  -> apenas launcher
;   ISCC /DAPP_ONLY=elexplan    Setup_turbinado.iss  -> apenas elexplan
;   ISCC /DAPP_ONLY=diag        Setup_turbinado.iss
;   ISCC /DAPP_ONLY=imagedx     Setup_turbinado.iss
;   ISCC /DAPP_ONLY=unif        Setup_turbinado.iss
;   ISCC /DAPP_ONLY=coplan_web  Setup_turbinado.iss   (pywebview; ja inclui Capex)
;   ISCC /DAPP_ONLY=status      Setup_turbinado.iss
;   ISCC /DAPP_ONLY=cadastro    Setup_turbinado.iss   (pywebview)
;
; OBS:
;   * O Coplan PySide6 legado (Coplan.exe) foi descontinuado; agora so
;     existe Coplan Web.exe (pywebview).
;   * O Ambiente Capex foi FUNDIDO dentro do Coplan (capex_engine): nao
;     existe mais "Ambiente Capex.exe" separado — virou feature do
;     Coplan Web.exe (regra user 2026-06-18).
;   * As chaves antigas "coplan" e "capex" sao aceitas como alias de
;     "coplan_web" pra retrocompat (viram coplan_web automaticamente).
;
; Entrada esperada:
;   dist\FerramentasCompartilhadas\_internal\...  (compartilhado)
;   dist\FerramentasCompartilhadas\<App>.exe      (um ou mais)
; ================================================================

#ifndef APP_ONLY
  #define APP_ONLY "all"
#endif

; Alias retrocompat: "coplan" antigo (legado PySide6) ja nao existe;
; aceita como atalho pro coplan_web atual.
#if APP_ONLY == "coplan"
  #undef APP_ONLY
  #define APP_ONLY "coplan_web"
#endif

; Alias retrocompat: "capex" foi fundido no Coplan (capex_engine); o
; Ambiente Capex.exe nao existe mais. Redireciona pro coplan_web.
#if APP_ONLY == "capex"
  #undef APP_ONLY
  #define APP_ONLY "coplan_web"
#endif

; Alias retrocompat: "status" (Status de Medicao) foi fundido no Elexplan; o
; Status de medicao.exe nao existe mais. Redireciona pro elexplan.
#if APP_ONLY == "status"
  #undef APP_ONLY
  #define APP_ONLY "elexplan"
#endif

#define IncludeAll    (APP_ONLY == "all")
#define WantLauncher  (IncludeAll || APP_ONLY == "launcher")
#define WantElexplan  (IncludeAll || APP_ONLY == "elexplan")
#define WantDiag      (IncludeAll || APP_ONLY == "diag")
#define WantImageDx   (IncludeAll || APP_ONLY == "imagedx")
#define WantUnif      (IncludeAll || APP_ONLY == "unif")
#define WantCoplanWeb (IncludeAll || APP_ONLY == "coplan_web")
; Capex fundido no Coplan (capex_engine): nunca ha exe/componente capex proprio.
; Mantido como 0 para compilar fora todos os blocos `#if WantCapex` antigos.
#define WantCapex     (0)
; Status de Medicao fundido no Elexplan: nunca ha exe/componente status proprio.
; Mantido como 0 para compilar fora todos os blocos `#if WantStatus` antigos.
#define WantStatus    (0)
#define WantCadastro  (IncludeAll || APP_ONLY == "cadastro")

#define AppId        "{7A3B2C8E-6C4E-4C1C-9D91-3F1A1C0AA123}"
#define AppName      "Ferramentas de Planejamento"
#define AppVersion   "1.1.4"
#define AppVersion4  "1.1.4.0"
#define AppPublisher "Arthur Cardoso"
#define SrcBundle    "dist\FerramentasCompartilhadas"

; ---------------------------------------------------------------
; Em cada instalacao, _internal e o launcher sempre entram no
; componente "main". Em modo completo, cada app extra tem seu
; proprio componente. Em modo APP_ONLY, o unico app selecionado
; tambem entra no "main" (simplifica a wizard).
; ---------------------------------------------------------------
#if IncludeAll
  #define CompLauncher  "main"
  #define CompElexplan  "app_elexplan"
  #define CompDiag      "app_diag"
  #define CompImageDx   "app_imagedx"
  #define CompUnif      "app_unificador"
  #define CompCoplanWeb "app_coplan_web"
  #define CompCapex     "app_capex"
  #define CompStatus    "app_status"
  #define CompCadastro  "app_cadastro"
  #define OutSuffix     ""
  #define InstallerDesc AppName + " - instalador completo"
#else
  #define CompLauncher  "main"
  #define CompElexplan  "main"
  #define CompDiag      "main"
  #define CompImageDx   "main"
  #define CompUnif      "main"
  #define CompCoplanWeb "main"
  #define CompCapex     "main"
  #define CompStatus    "main"
  #define CompCadastro  "main"
  #define OutSuffix     "-" + APP_ONLY
  #define InstallerDesc AppName + " - " + APP_ONLY
#endif

; ---------------------------------------------------------------
; Valida o bundle antes de iniciar a compilacao.
; Assim o instalador nao comeca a compactar para falhar depois.
; ---------------------------------------------------------------
#if !FileExists(AddBackslash(SourcePath) + SrcBundle + "\_internal\base_library.zip")
  #error "Bundle ausente. Rode 'build_all_shared.bat' antes de compilar este .iss. Esperado: " + SrcBundle + "\_internal\"
#endif

; Valida que o .exe do app escolhido existe no bundle
#if WantLauncher && !FileExists(AddBackslash(SourcePath) + SrcBundle + "\Ferramentas de Planejamento.exe")
  #error "Launcher ausente no bundle. Rebuild: build_all_shared.bat launcher"
#endif
#if WantElexplan && !FileExists(AddBackslash(SourcePath) + SrcBundle + "\Elexplan.exe")
  #error "Elexplan.exe ausente. Rebuild: build_all_shared.bat elexplan"
#endif
#if WantDiag && !FileExists(AddBackslash(SourcePath) + SrcBundle + "\Diagnostico de alimentadores.exe")
  #error "Diagnostico de alimentadores.exe ausente. Rebuild: build_all_shared.bat diag"
#endif
#if WantImageDx && !FileExists(AddBackslash(SourcePath) + SrcBundle + "\ImageDx- Detalhamento.exe")
  #error "ImageDx- Detalhamento.exe ausente. Rebuild: build_all_shared.bat imagedx"
#endif
#if WantUnif && !FileExists(AddBackslash(SourcePath) + SrcBundle + "\Unificador de arquivos.exe")
  #error "Unificador de arquivos.exe ausente. Rebuild: build_all_shared.bat unif"
#endif
#if WantCoplanWeb && !FileExists(AddBackslash(SourcePath) + SrcBundle + "\Coplan Web.exe")
  #error "Coplan Web.exe ausente. Rebuild: build_all_shared.bat coplan_web"
#endif
#if WantCapex && !FileExists(AddBackslash(SourcePath) + SrcBundle + "\Ambiente Capex.exe")
  #error "Ambiente Capex.exe ausente. Rebuild: build_all_shared.bat capex"
#endif
#if WantStatus && !FileExists(AddBackslash(SourcePath) + SrcBundle + "\Status de medicao.exe")
  #error "Status de medicao.exe ausente. Rebuild: build_all_shared.bat status"
#endif
#if WantCadastro && !FileExists(AddBackslash(SourcePath) + SrcBundle + "\Sistema de Cadastro.exe")
  #error "Sistema de Cadastro.exe ausente. Rebuild: build_all_shared.bat cadastro"
#endif

[Setup]
AppId={{#AppId}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppContact={#AppPublisher}

; Metadados que aparecem em Propriedades do .exe do instalador
VersionInfoVersion={#AppVersion4}
VersionInfoProductVersion={#AppVersion4}
VersionInfoProductName={#AppName}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#InstallerDesc}
VersionInfoCopyright=Copyright (C) 2026 {#AppPublisher}

PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=FerramentasCompartilhadas-Setup{#OutSuffix}-{#AppVersion}

Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes

WizardStyle=modern
WizardResizable=yes
AllowNoIcons=yes
AlwaysShowDirOnReadyPage=yes
AlwaysShowGroupOnReadyPage=yes
ShowComponentSizes=yes
SetupLogging=yes

UsePreviousAppDir=yes
UsePreviousTasks=yes
UsePreviousGroup=yes
UsePreviousLanguage=yes

; Fecha apps rodando do bundle antes de substituir arquivos.
CloseApplications=force
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=no

DisableWelcomePage=no
DisableDirPage=auto
DisableProgramGroupPage=auto

MinVersion=6.1sp1
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

SetupIconFile=apps\launcher\eng.ico
UninstallDisplayName={#InstallerDesc} {#AppVersion}
UninstallDisplayIcon={app}\Ferramentas de Planejamento.exe,0

; Evita que dois instaladores rodem simultaneamente (corromperia _internal)
SetupMutex=FerramentasDePlanejamentoSetupMutex

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Types]
Name: "full";    Description: "Tipica (todos os apps disponiveis)"
Name: "compact"; Description: "Somente o launcher"
Name: "custom";  Description: "Personalizada"; Flags: iscustom

[Components]
Name: "main"; Description: "{#InstallerDesc} (obrigatorio)"; Types: full compact custom; Flags: fixed
#if IncludeAll
  #if WantElexplan
Name: "app_elexplan";   Description: "Elexplan";                         Types: full custom
  #endif
  #if WantDiag
Name: "app_diag";       Description: "Diagnostico de alimentadores";     Types: full custom
  #endif
  #if WantImageDx
Name: "app_imagedx";    Description: "ImageDx - Detalhamento";           Types: full custom
  #endif
  #if WantUnif
Name: "app_unificador"; Description: "Unificador de arquivos";           Types: full custom
  #endif
  #if WantCoplanWeb
Name: "app_coplan_web"; Description: "Coplan Web (pywebview)";           Types: full custom
  #endif
  #if WantCapex
Name: "app_capex";      Description: "Ambiente Capex (pywebview)";       Types: full custom
  #endif
  #if WantStatus
Name: "app_status";     Description: "Status de medicao";                Types: full custom
  #endif
  #if WantCadastro
Name: "app_cadastro";   Description: "Sistema de Cadastro (pywebview)";  Types: full custom
  #endif
#endif

[Tasks]
#if IncludeAll
Name: "desktopicon"; Description: "Criar atalho na Area de Trabalho (launcher)"; GroupDescription: "Atalhos:"; Flags: unchecked
#else
  #if WantCadastro
Name: "desktopicon_cadastro"; Description: "Criar atalho na Area de Trabalho (Sistema de Cadastro)"; GroupDescription: "Atalhos:"; Flags: unchecked
  #endif
#endif
Name: "runafter";    Description: "Abrir apos concluir"; Flags: unchecked

#if IncludeAll
Name: "clean_previous";  Description: "Remover instalacao anterior antes de instalar"; GroupDescription: "Limpeza:"; Check: HasPreviousInstall
#else
Name: "clean_previous";  Description: "Atualizar runtime e remover somente arquivos antigos do app selecionado"; GroupDescription: "Limpeza:"; Check: HasPreviousInstall
#endif
Name: "clean_user_json"; Description: "Tambem remover arquivos .json de configuracao do usuario ({app}/AppData)"; GroupDescription: "Limpeza:"; Flags: unchecked; Check: HasUserJsonToClean

[Dirs]
Name: "{app}"; Flags: uninsalwaysuninstall

[InstallDelete]
; Remove _internal antigo SEMPRE antes do novo (evita orfaos de versoes anteriores).
Type: filesandordirs; Name: "{app}\_internal"
; Remove tambem o log do launcher para nao ficar gigante
Type: files;          Name: "{app}\logs\*.log"
Type: files;          Name: "{app}\launcher.log"
; Remove o Coplan.exe (legado PySide6) deixado por versoes anteriores —
; foi substituido pelo Coplan Web.exe (pywebview).
Type: files;          Name: "{app}\Coplan.exe"
; Remove o Ambiente Capex.exe (+ config) de bundles antigos: o Capex foi
; fundido dentro do Coplan Web.exe (capex_engine), nao ha mais exe separado.
Type: files;          Name: "{app}\Ambiente Capex.exe"
Type: files;          Name: "{app}\Ambiente Capex.exe.config"
; Remove o Status de medicao.exe de bundles antigos: foi fundido dentro do
; Elexplan.exe (abas Chaves/Status/Estatistica), nao ha mais exe separado.
Type: files;          Name: "{app}\Status de medicao.exe"

[Files]
; ------------------- NUCLEO -------------------
Source: "{#SrcBundle}\_internal\*"; DestDir: "{app}\_internal"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: main

#if WantLauncher
Source: "{#SrcBundle}\Ferramentas de Planejamento.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: {#CompLauncher}
#endif

; ------------------- APPS OPCIONAIS -------------------
#if WantElexplan
Source: "{#SrcBundle}\Elexplan.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: {#CompElexplan}
#endif
#if WantDiag
Source: "{#SrcBundle}\Diagnostico de alimentadores.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: {#CompDiag}
#endif
#if WantImageDx
Source: "{#SrcBundle}\ImageDx- Detalhamento.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: {#CompImageDx}
#endif
#if WantUnif
Source: "{#SrcBundle}\Unificador de arquivos.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: {#CompUnif}
#endif
#if WantCoplanWeb
Source: "{#SrcBundle}\Coplan Web.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: {#CompCoplanWeb}
#endif
#if WantCapex
Source: "{#SrcBundle}\Ambiente Capex.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: {#CompCapex}
#endif
#if WantStatus
Source: "{#SrcBundle}\Status de medicao.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: {#CompStatus}
#endif

; Configs do .NET host para pywebview/pythonnet. Precisam ficar ao lado
; do .exe, nao dentro de _internal, para o .NET Framework ler no startup.
#if WantCoplanWeb
Source: "{#SrcBundle}\Coplan Web.exe.config"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; Components: {#CompCoplanWeb}
#endif
#if WantCapex
Source: "{#SrcBundle}\Ambiente Capex.exe.config"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; Components: {#CompCapex}
#endif
#if WantCadastro
Source: "{#SrcBundle}\Sistema de Cadastro.exe.config"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; Components: {#CompCadastro}
#endif
#if WantCadastro
Source: "{#SrcBundle}\Sistema de Cadastro.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: {#CompCadastro}
#endif

[Icons]
#if WantLauncher
Name: "{group}\{#AppName}";       Filename: "{app}\Ferramentas de Planejamento.exe"; WorkingDir: "{app}"; Components: {#CompLauncher}
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\Ferramentas de Planejamento.exe"; WorkingDir: "{app}"; Tasks: desktopicon; Components: {#CompLauncher}
#endif

#if WantElexplan
Name: "{group}\Elexplan"; Filename: "{app}\Elexplan.exe"; WorkingDir: "{app}"; Components: {#CompElexplan}
#endif
#if WantDiag
Name: "{group}\Diagnostico de alimentadores"; Filename: "{app}\Diagnostico de alimentadores.exe"; WorkingDir: "{app}"; Components: {#CompDiag}
#endif
#if WantImageDx
Name: "{group}\ImageDx - Detalhamento"; Filename: "{app}\ImageDx- Detalhamento.exe"; WorkingDir: "{app}"; Components: {#CompImageDx}
#endif
#if WantUnif
Name: "{group}\Unificador de arquivos"; Filename: "{app}\Unificador de arquivos.exe"; WorkingDir: "{app}"; Components: {#CompUnif}
#endif
#if WantCoplanWeb
Name: "{group}\Coplan Web"; Filename: "{app}\Coplan Web.exe"; WorkingDir: "{app}"; Components: {#CompCoplanWeb}
#endif
#if WantCapex
Name: "{group}\Ambiente Capex"; Filename: "{app}\Ambiente Capex.exe"; WorkingDir: "{app}"; Components: {#CompCapex}
#endif
#if WantStatus
Name: "{group}\Status de medicao"; Filename: "{app}\Status de medicao.exe"; WorkingDir: "{app}"; Components: {#CompStatus}
#endif
#if WantCadastro
Name: "{group}\Sistema de Cadastro"; Filename: "{app}\Sistema de Cadastro.exe"; WorkingDir: "{app}"; Components: {#CompCadastro}
  #if !IncludeAll
Name: "{userdesktop}\Sistema de Cadastro"; Filename: "{app}\Sistema de Cadastro.exe"; WorkingDir: "{app}"; Tasks: desktopicon_cadastro; Components: {#CompCadastro}
  #endif
#endif

Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"

[Run]
#if WantLauncher
Filename: "{app}\Ferramentas de Planejamento.exe"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent; Tasks: runafter
#endif
#if WantCadastro
  #if !IncludeAll
Filename: "{app}\Sistema de Cadastro.exe"; Description: "Abrir Sistema de Cadastro"; Flags: nowait postinstall skipifsilent; Tasks: runafter
  #endif
#endif

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: files;          Name: "{app}\launcher.log"
Type: files;          Name: "{app}\*.log"
Type: dirifempty;     Name: "{app}"

; ================================================================
; Pascal Script
; Constante FILE_ATTRIBUTE_DIRECTORY = 16 (nao dependemos do simbolo).
; ================================================================
[Code]
const
  LogPrefix = 'Setup: ';
  ATTR_DIRECTORY = 16;

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------
function HasPreviousInstall(): Boolean;
begin
  Result := DirExists(ExpandConstant('{app}\_internal')) or
            DirExists(ExpandConstant('{app}\Ferramentas')) or
            FileExists(ExpandConstant('{app}\Ferramentas de Planejamento.exe'));
end;

function HasJsonIn(const Dir: string): Boolean;
var
  FindRec: TFindRec;
begin
  Result := False;
  if not DirExists(Dir) then Exit;
  if FindFirst(Dir + '\*.json', FindRec) then
  begin
    try
      repeat
        if (FindRec.Attributes and ATTR_DIRECTORY) = 0 then
        begin
          Result := True;
          Exit;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

function HasUserJsonInApp(): Boolean;
begin
  Result := HasJsonIn(ExpandConstant('{app}'));
end;

function HasUserJsonToClean(): Boolean;
begin
  Result := HasUserJsonInApp();

#if WantCadastro
  if not Result then
    Result := HasJsonIn(ExpandConstant('{userappdata}\Cadastro_Viabilidades'));
  if not Result then
    Result := HasJsonIn(ExpandConstant('{userappdata}\Cadastro_Viabilidades\_backups'));
#endif

#if WantCoplanWeb
  if not Result then
    Result := HasJsonIn(ExpandConstant('{localappdata}\COPLAN\config'));
#endif

#if WantCapex
  if not Result then
    Result := HasJsonIn(ExpandConstant('{localappdata}\AmbienteCAPEX'));
#endif

#if WantElexplan
  if not Result then
    Result := HasJsonIn(ExpandConstant('{userappdata}\..\..\.elexplan'));
#endif

#if WantStatus
  if not Result then
    Result := HasJsonIn(ExpandConstant('{userappdata}\..\..\.statuspim'));
#endif
end;

procedure RemoveAllJsonIn(const Dir: string);
var
  FindRec: TFindRec;
  Full: string;
begin
  if not DirExists(Dir) then Exit;
  if FindFirst(Dir + '\*.json', FindRec) then
  begin
    try
      repeat
        if (FindRec.Attributes and ATTR_DIRECTORY) = 0 then
        begin
          Full := Dir + '\' + FindRec.Name;
          try
            if not DeleteFile(Full) then
              Log(LogPrefix + 'Falha ao remover JSON: ' + Full);
          except
            Log(LogPrefix + 'Excecao ao remover JSON: ' + Full);
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

procedure DeleteFileIfExists(const Full: string);
begin
  if not FileExists(Full) then Exit;
  try
    if not DeleteFile(Full) then
      Log(LogPrefix + 'Falha ao remover: ' + Full);
  except
    Log(LogPrefix + 'Excecao ao remover: ' + Full);
  end;
end;

procedure RemoveSelectedAppJsonInApp(const AppDir: string);
begin
#if WantLauncher
  DeleteFileIfExists(AppDir + '\config_launcher.json');
#endif

#if WantDiag
  // Diagnostico ainda grava config.json ao lado do executavel.
  DeleteFileIfExists(AppDir + '\config.json');
#endif
end;

procedure RemoveKnownUserJson();
begin
  // Apps desktop antigos/launcher ainda gravam JSON ao lado do executavel.
#if IncludeAll
  RemoveAllJsonIn(ExpandConstant('{app}'));
#else
  RemoveSelectedAppJsonInApp(ExpandConstant('{app}'));
#endif

#if WantCadastro
  // Sistema de Cadastro em modo PyInstaller grava config/logs por usuario.
  RemoveAllJsonIn(ExpandConstant('{userappdata}\Cadastro_Viabilidades'));
  // Remove tambem backups rotacionados do config.json do Cadastro.
  RemoveAllJsonIn(ExpandConstant('{userappdata}\Cadastro_Viabilidades\_backups'));
#endif

#if WantCoplanWeb
  // Coplan Web grava config.json em %LOCALAPPDATA%\COPLAN\config.
  RemoveAllJsonIn(ExpandConstant('{localappdata}\COPLAN\config'));
#endif

#if WantCapex
  // Ambiente CAPEX grava config.json/scenarios.json em %LOCALAPPDATA%\AmbienteCAPEX.
  RemoveAllJsonIn(ExpandConstant('{localappdata}\AmbienteCAPEX'));
#endif

#if WantElexplan
  // Elexplan usa Path.home()\.elexplan\prefs.json.
  RemoveAllJsonIn(ExpandConstant('{userappdata}\..\..\.elexplan'));
#endif

#if WantStatus
  // Status de medicao usa Path.home()\.statuspim\prefs.json.
  RemoveAllJsonIn(ExpandConstant('{userappdata}\..\..\.statuspim'));
#endif
end;

// Remove layout antigo (pasta Ferramentas\<AppName>\) que o instalador
// anterior criava. Ignora falhas individuais.
procedure CleanLegacyLayout();
var
  i: Integer;
  Base, Sub: string;
  Legacy: TArrayOfString;
begin
  Base := ExpandConstant('{app}') + '\Ferramentas';
  if not DirExists(Base) then Exit;

  SetArrayLength(Legacy, 10);
  Legacy[0] := 'Elexplan';
  Legacy[1] := 'Diagnostico de alimentadores';
  Legacy[2] := 'ImageDx- Detalhamento';
  Legacy[3] := 'Unificador de arquivos';
  Legacy[4] := 'Coplan';
  Legacy[5] := 'Ambiente Capex';
  Legacy[6] := 'Status de medição';
  Legacy[7] := 'Sistema de Cadastro';
  Legacy[8] := 'Status de medicao';
  Legacy[9] := 'Coplan Web';

  for i := 0 to GetArrayLength(Legacy) - 1 do
  begin
    Sub := Base + '\' + Legacy[i];
    if DirExists(Sub) then
    begin
      try
        DelTree(Sub, True, True, True);
        Log(LogPrefix + 'Layout antigo removido: ' + Sub);
      except
        Log(LogPrefix + 'Falha ao remover layout antigo: ' + Sub);
      end;
    end;
  end;

  // Se Ferramentas\ ficou vazia, remove.
  try
    RemoveDir(Base);
  except
    // ok se estiver em uso
  end;
end;

procedure CleanSelectedAppFiles(const AppDir: string; const RemoveJson: Boolean);
begin
#if WantLauncher
  DeleteFileIfExists(AppDir + '\Ferramentas de Planejamento.exe');
#endif

#if WantElexplan
  DeleteFileIfExists(AppDir + '\Elexplan.exe');
#endif

#if WantDiag
  DeleteFileIfExists(AppDir + '\Diagnostico de alimentadores.exe');
#endif

#if WantImageDx
  DeleteFileIfExists(AppDir + '\ImageDx- Detalhamento.exe');
#endif

#if WantUnif
  DeleteFileIfExists(AppDir + '\Unificador de arquivos.exe');
#endif

#if WantCoplanWeb
  DeleteFileIfExists(AppDir + '\Coplan Web.exe');
  DeleteFileIfExists(AppDir + '\Coplan Web.exe.config');
  DeleteFileIfExists(AppDir + '\Coplan.exe');
#endif

#if WantCapex
  DeleteFileIfExists(AppDir + '\Ambiente Capex.exe');
  DeleteFileIfExists(AppDir + '\Ambiente Capex.exe.config');
#endif

#if WantStatus
  DeleteFileIfExists(AppDir + '\Status de medicao.exe');
#endif

#if WantCadastro
  DeleteFileIfExists(AppDir + '\Sistema de Cadastro.exe');
  DeleteFileIfExists(AppDir + '\Sistema de Cadastro.exe.config');
#endif

  if RemoveJson then
    RemoveSelectedAppJsonInApp(AppDir);
end;

// Modo completo: remove _internal + arquivos soltos para uma instalacao
// limpa. Modo APP_ONLY: remove _internal + somente o app selecionado,
// preservando executaveis/configs dos outros apps ja instalados.
procedure CleanCurrentInstall(const RemoveJson: Boolean);
var
  AppDir, InternalDir, Full, Ext: string;
  FindRec: TFindRec;
begin
  AppDir := ExpandConstant('{app}');
  if not DirExists(AppDir) then Exit;

  InternalDir := AppDir + '\_internal';
  if DirExists(InternalDir) then
  begin
    try
      DelTree(InternalDir, True, True, True);
      Log(LogPrefix + 'Removido: ' + InternalDir);
    except
      Log(LogPrefix + 'Falha ao remover _internal');
    end;
  end;

#if !IncludeAll
  CleanSelectedAppFiles(AppDir, RemoveJson);
#else
  if FindFirst(AppDir + '\*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Attributes and ATTR_DIRECTORY) = 0 then
        begin
          Full := AppDir + '\' + FindRec.Name;
          Ext := Lowercase(ExtractFileExt(FindRec.Name));
          if (Ext = '.json') and (not RemoveJson) then
          begin
            // preserva config do usuario
          end
          else
          begin
            try
              if not DeleteFile(Full) then
                Log(LogPrefix + 'Falha ao remover: ' + Full);
            except
              Log(LogPrefix + 'Excecao ao remover: ' + Full);
            end;
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
#endif
end;

// ----------------------------------------------------------------
// Verificacao de dependencias de runtime
// ----------------------------------------------------------------
function IsVCRedistInstalled(): Boolean;
begin
  Result := False;
  if RegValueExists(HKLM,   'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft Visual C++ 2015-2022 Redistributable (x64)', 'DisplayName') then
    Result := True;
  if not Result then
    Result := RegValueExists(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft Visual C++ 2015-2022 Redistributable (x64)', 'DisplayName');
  if not Result then
    Result := RegValueExists(HKLM,   'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft Visual C++ 2015-2019 Redistributable (x64)', 'DisplayName');
  if not Result then
    Result := RegValueExists(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft Visual C++ 2015-2019 Redistributable (x64)', 'DisplayName');
  if not Result then
    Result := RegValueExists(HKLM,   'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed');
  if not Result then
    Result := RegValueExists(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed');
end;

// Detecta Microsoft WebView2 Runtime (requerido por todos os apps
// pywebview: Cadastro, Coplan Web e Capex).
// Chave oficial (Evergreen): {F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}.
function IsWebView2Installed(): Boolean;
var
  Version: string;
begin
  Result := False;
  if RegQueryStringValue(HKLM64, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) then
    Result := (Version <> '') and (Version <> '0.0.0.0');
  if not Result then
    if RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) then
      Result := (Version <> '') and (Version <> '0.0.0.0');
  if not Result then
    if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) then
      Result := (Version <> '') and (Version <> '0.0.0.0');
  if not Result then
    if RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) then
      Result := (Version <> '') and (Version <> '0.0.0.0');
end;

// True se ALGUM app pywebview sera instalado (Cadastro, Coplan Web ou
// Capex). Eles compartilham o requisito do WebView2 Runtime.
function WillNeedWebView2(): Boolean;
begin
  Result := False;
#if WantCadastro
  #if IncludeAll
  if IsComponentSelected('app_cadastro') then Result := True;
  #else
  Result := True;
  #endif
#endif
#if WantCoplanWeb
  if not Result then
  begin
    #if IncludeAll
    if IsComponentSelected('app_coplan_web') then Result := True;
    #else
    Result := True;
    #endif
  end;
#endif
#if WantCapex
  if not Result then
  begin
    #if IncludeAll
    if IsComponentSelected('app_capex') then Result := True;
    #else
    Result := True;
    #endif
  end;
#endif
end;

function OpenUrl(const Url: string): Boolean;
var
  ErrCode: Integer;
begin
  Result := ShellExec('open', Url, '', '', SW_SHOWNORMAL, ewNoWait, ErrCode);
  if not Result then
    MsgBox('Nao foi possivel abrir o navegador. Acesse manualmente:' + #13#10 + Url,
           mbInformation, MB_OK);
end;

// ----------------------------------------------------------------
// Eventos do wizard
// ----------------------------------------------------------------
procedure InitializeWizard();
begin
  if not IsVCRedistInstalled() then
  begin
    if MsgBox('Microsoft Visual C++ Redistributable (2015-2022) nao foi detectado.' + #13#10 +
              'Ele e necessario para os apps baseados em Python/PySide6 funcionarem.' + #13#10 + #13#10 +
              'Deseja abrir a pagina de download agora?',
              mbConfirmation, MB_YESNO) = IDYES then
      OpenUrl('https://aka.ms/vs/17/release/vc_redist.x64.exe');
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  // Quando o usuario sai da pagina de componentes, ja sabemos quais apps
  // pywebview serao instalados. Se algum deles ficou marcado e o
  // WebView2 nao esta presente, avisamos uma unica vez.
  if CurPageID = wpSelectComponents then
  begin
    if WillNeedWebView2() and not IsWebView2Installed() then
    begin
      if MsgBox('Os apps Cadastro e Coplan Web (que ja inclui o Capex) precisam do' + #13#10 +
                'Microsoft WebView2 Runtime, que nao foi detectado.' + #13#10 +
                'Sem ele, a interface desses apps nao abre.' + #13#10 + #13#10 +
                'Deseja baixar o WebView2 Runtime agora? (abrira o navegador)',
                mbConfirmation, MB_YESNO) = IDYES then
        OpenUrl('https://go.microsoft.com/fwlink/p/?LinkId=2124703');
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    // Sempre migra do layout antigo (pasta Ferramentas\<App>\) para o novo
    CleanLegacyLayout();

    if WizardIsTaskSelected('clean_previous') then
      CleanCurrentInstall(WizardIsTaskSelected('clean_user_json'));

    if WizardIsTaskSelected('clean_user_json') then
      RemoveKnownUserJson();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    if HasJsonIn(AppDir) then
    begin
      if MsgBox('Foram encontrados arquivos de configuracao (.json) em:' + #13#10 +
                AppDir + #13#10 + #13#10 +
                'Deseja remove-los tambem? (Nao pode ser desfeito.)',
                mbConfirmation, MB_YESNO) = IDYES then
        RemoveAllJsonIn(AppDir);
    end;
  end;
end;
