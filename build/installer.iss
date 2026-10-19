; build/installer.iss  –  Inno Setup script for Studio Tools
; Run via  build\build.ps1  or manually:
;   "C:\Users\eleml\AppData\Local\Programs\Inno Setup 6\iscc.exe" build\installer.iss

#define AppName     "Studio Tools"
#define AppVersion  "1.0"
#define AppExe      "StudioTools.exe"
#define GsExe       "gs10080w64.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-4A5B-8C9D-0E1F2A3B4C5D}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\StudioTools
DefaultGroupName={#AppName}
OutputDir=..\dist
OutputBaseFilename=StudioTools-Setup
SetupIconFile=..\app\assets\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\app.ico
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExe}";      DestDir: "{app}"; Flags: ignoreversion
Source: "..\app\assets\app.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\{#GsExe}";           DestDir: "{tmp}"; Flags: deleteafterinstall nocompression

[Icons]
Name: "{group}\{#AppName}";             Filename: "{app}\{#AppExe}"; IconFilename: "{app}\app.ico"
Name: "{group}\Uninstall {#AppName}";   Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}";     Filename: "{app}\{#AppExe}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon

[Run]
Filename: "{tmp}\{#GsExe}"; Parameters: "/S"; StatusMsg: "Installing Ghostscript…"; \
    Flags: waituntilterminated; Check: NeedsGhostscript
Filename: "{app}\{#AppExe}"; Description: "Launch Studio Tools"; Flags: nowait postinstall skipifsilent

[Code]
function NeedsGhostscript: Boolean;
var FindRec: TFindRec; gsRoot: String;
begin
  gsRoot := ExpandConstant('{pf}\gs');
  Result := True;
  if FindFirst(gsRoot + '\gs*', FindRec) then
  try
    repeat
      if (FindRec.Name <> '.') and (FindRec.Name <> '..') and
         FileExists(gsRoot + '\' + FindRec.Name + '\bin\gswin64c.exe') then
      begin Result := False; Break; end;
    until not FindNext(FindRec);
  finally FindClose(FindRec); end;
end;
