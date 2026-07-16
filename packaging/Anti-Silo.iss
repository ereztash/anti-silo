#ifndef AppVersion
  #define AppVersion "0.3.3"
#endif

[Setup]
AppId={{6B2382DD-8B5B-4D8D-A6C5-7E489B4D3D20}
AppName=Anti-Silo
AppVersion={#AppVersion}
AppPublisher=Anti-Silo
DefaultDirName={autopf}\Anti-Silo
DefaultGroupName=Anti-Silo
OutputDir=..\dist
OutputBaseFilename=Anti-Silo-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "..\dist\Anti-Silo.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\Anti-Silo"; Filename: "{app}\Anti-Silo.exe"; Tasks: desktopicon
Name: "{group}\Anti-Silo"; Filename: "{app}\Anti-Silo.exe"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Run]
Filename: "{app}\Anti-Silo.exe"; Description: "Open Anti-Silo"; Flags: nowait postinstall skipifsilent
