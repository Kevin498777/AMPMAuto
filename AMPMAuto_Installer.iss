; AMPMAuto_Installer.iss - GENERADO AUTOMÁTICAMENTE
#define MyAppName "AMPMAuto"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AMPMAuto Team"
#define MyAppURL "https://github.com/tuusuario/ampmauto"
#define MyAppExeName "AMPMAuto.exe"
#define MyAppAssocName "AMPMAuto Application"
#define MyAppAssocExt ".exe"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
ChangesAssociations=yes
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
;InfoBeforeFile=INFO.txt
;InfoAfterFile=AFTER.txt
OutputDir=AMPMAuto_Installer
OutputBaseFilename=AMPMAuto_Setup
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
Source: "dist\AMPMAuto.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "*.env"; DestDir: "{app}"; Flags: ignoreversion
Source: "*.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "*.md"; DestDir: "{app}"; Flags: ignoreversion
; Crear directorios necesarios
Source: "reports\*"; DestDir: "{app}\reports"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "logs\*"; DestDir: "{app}\logs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Code]
function InitializeSetup(): Boolean;
var
  ChromePath: string;
  ResultCode: Integer;
begin
  Result := True;
  
  // Verificar si Chrome está instalado
  if not RegKeyExists(HKLM, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe') then
  begin
    if MsgBox('Google Chrome no está detectado en el sistema. AMPMAuto requiere Chrome para funcionar correctamente.' + #13#10 + #13#10 +
              '¿Desea continuar con la instalación? Puede instalar Chrome después.', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Crear archivo .env de ejemplo si no existe
    if not FileExists(ExpandConstant('{app}\.env')) then
    begin
      SaveStringToFile(ExpandConstant('{app}\.env'),
        '# Configuración AMPMAuto' + #13#10 +
        'AMPM_USERNAME=tu_usuario' + #13#10 +
        'AMPM_PASSWORD=tu_contraseña' + #13#10 +
        'HEADLESS_MODE=True' + #13#10 +
        'TIMEOUT=30' + #13#10 +
        'MAX_RETRIES=3' + #13#10, False);
    end;
  end;
end;
