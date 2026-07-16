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
processed locally; the packaged app does not add cloud calls or telemetry.

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
GUI and immediately scans the selected folder. No administrator permissions are
required because the script writes only under `HKCU`.

Remove it later with:

```powershell
.\packaging\windows_context_menu.ps1 -ExecutablePath .\dist\Anti-Silo.exe -Remove
```

- `pyinstaller` is an optional packaging dependency, not a runtime dependency.
- The packaged GUI uses the same `anti_silo.gui` module as `python -m anti_silo.cli gui`.
- A future `.dmg` or AppImage can use the same `packaging/run_gui.py` entrypoint.
