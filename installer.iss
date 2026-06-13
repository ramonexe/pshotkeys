#define AppName      "PSHotkeys"
#define AppVersion   "2.0.0"
#define AppPublisher "PSHotkeys"
#define AppExeName   "PSHotkeys.exe"
#define AppURL       ""
#define SrcDir       "dist"
#define IconFile     "assets\icon.ico"

[Setup]
AppId={{A3F7B2C1-9D4E-4F82-BE63-12A8C0D5E9F0}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=PSHotkeys-Setup
SetupIconFile={#IconFile}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableDirPage=no
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
; Wizard visual
WizardImageFile=compiler:WizClassicImage.bmp
WizardSmallImageFile=compiler:WizClassicSmallImage.bmp

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon";    Description: "Criar atalho na &Área de Trabalho";    GroupDescription: "Atalhos adicionais:"; Flags: unchecked
Name: "startupentry";   Description: "Iniciar &automaticamente com o Windows"; GroupDescription: "Opções:"

[Files]
Source: "{#SrcDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Startup com Windows — só se o usuário marcou a task
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#AppName}"; \
  ValueData: """{app}\{#AppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startupentry

[Run]
Filename: "{app}\{#AppExeName}"; \
  Description: "Iniciar {#AppName} agora"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Encerra o processo antes de desinstalar
Filename: "taskkill.exe"; Parameters: "/F /IM {#AppExeName}"; \
  Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
; Remove perfis e settings gerados em AppData
Type: filesandordirs; Name: "{localappdata}\PSHotkeys"
Type: filesandordirs; Name: "{userappdata}\PSHotkeys"

[Code]
// Encerra instância rodando antes de instalar/atualizar
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/F /IM {#AppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;
