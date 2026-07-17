# Desktop Packaging

Anti-Silo can be packaged as a local desktop-style executable while keeping the
same local web UI and deterministic engine.

## Windows EXE

From the repository root:

```powershell
python -m pip install -e ".[desktop]"
pyinstaller packaging/anti_silo_gui.spec
```

The executable is written to:

```text
dist/Anti-Silo.exe
```

The EXE starts the local GUI at `127.0.0.1` and opens the browser. Files are
processed locally. The packaged app makes no cloud calls and records only
privacy-safe workflow events in a local JSONL file; file paths, titles, and
contents are excluded.

For a person who only wants to use the app, distribute `Anti-Silo-Windows.zip`
instead of the repository. The ZIP contains `Anti-Silo.exe` and a short
`README.txt`; it requires neither Python nor GitHub Desktop.

## macOS DMG

The release workflow builds `Anti-Silo-macOS.dmg` from the same PyInstaller
specification on a macOS runner. Signing and notarization are opt-in and are
documented in [distribution setup](../docs/DISTRIBUTION.md).

## Shortcut

After building, create a desktop shortcut to `dist/Anti-Silo.exe`. A nontechnical
user can then open Anti-Silo like a normal desktop application.

## Notes

## Windows Explorer Context Menu

After building the EXE, register an optional current-user Explorer action:

```powershell
.\packaging\windows_context_menu.ps1 -ExecutablePath .\dist\Anti-Silo.exe
```

Right-clicking a folder then offers **Scan with Anti-Silo**. It opens the local
GUI with the folder prefilled so the consultant can add client and project
details before running Preflight. No administrator permissions are
required because the script writes only under `HKCU`.

Remove it later with:

```powershell
.\packaging\windows_context_menu.ps1 -ExecutablePath .\dist\Anti-Silo.exe -Remove
```

- `pyinstaller` is an optional packaging dependency, not a runtime dependency.
- The packaged GUI uses the same `anti_silo.gui` module as `python -m anti_silo.cli gui`.
- A future `.dmg` or AppImage can use the same `packaging/run_gui.py` entrypoint.
