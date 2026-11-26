[Setup]
AppName=Mir-Time Launcher
AppVersion=2.0.0
AppPublisher=Mir-Time Project
AppPublisherURL=https://mir-time.ru
DefaultDirName={localappdata}\MirTimeLauncher
DefaultGroupName=Mir-Time Launcher
OutputDir=dist
OutputBaseFilename=MirTimeLauncher-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на Рабочем столе"; GroupDescription: "Дополнительные значки:"

[Files]
Source: "dist\MirTimeLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Mir-Time Launcher"; Filename: "{app}\MirTimeLauncher.exe"
Name: "{autodesktop}\Mir-Time Launcher"; Filename: "{app}\MirTimeLauncher.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MirTimeLauncher.exe"; Description: "Запустить Mir-Time Launcher"; Flags: nowait postinstall skipifsilent
