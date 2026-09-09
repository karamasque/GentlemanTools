; Inno Setup Script for GentlemanStation
#define MyAppName "GentlemanStation"
#define MyAppVersion "1.2.4"
#define MyAppPublisher "GentlemanTools"
#define MyAppURL "https://github.com/karamasque/GentlemanTools"
#define MyAppExeName "GentlemanStation.exe"

[Setup]
; Basic App Info
AppId={{D37E7A56-3C89-4B52-9A4E-7BC8A2D738F1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=C:\Users\kilic\.gemini\antigravity-ide\scratch\GentlemanTools\LICENSE
OutputDir=C:\Users\kilic\Desktop
OutputBaseFilename=GentlemanStation_Kurulum_v1.2.4
SetupIconFile=C:\Users\kilic\.gemini\antigravity-ide\scratch\GentlemanTools\src\LuaToolsGui\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "desktopicon\common"; Description: "Masaüstü simgesi oluştur"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkablealone

[Files]
Source: "C:\Users\kilic\.gemini\antigravity-ide\scratch\GentlemanTools\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon or desktopicon\common

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
