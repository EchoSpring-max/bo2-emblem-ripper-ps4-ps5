# Release Binary Audit

The `v1.0.0` release executable was extracted from the shipped
`BO2EmblemToolkit.exe` with `pyinstxtractor-ng`. It is a PyInstaller package
built with Python 3.14.

The package contains these application modules:

- `run.py`
- `emblemtool/__init__.py`
- `emblemtool/broadcast.py`
- `emblemtool/config.py`
- `emblemtool/proxy.py`
- `emblemtool/state.py`
- `emblemtool/storage.py`
- `emblemtool/shapes/__init__.py`
- `emblemtool/shapes/render.py`
- `emblemtool/shapes/shape_id_map.py`
- `emblemtool/web/__init__.py`
- `emblemtool/web/netinfo.py`
- `emblemtool/web/server.py`

The static control panel files and 261 reference-shape images are included in
the executable as separate package data and are also committed in this
repository.

## Reproduce the audit

```powershell
python -m pip install pyinstxtractor-ng
python -m pyinstxtractor_ng BO2EmblemToolkit.exe
python tools/verify_release_bytecode.py .\BO2EmblemToolkit.exe_extracted
```

The verifier loads every recovered application `.pyc` code object and
recompiles the matching public `.py` file using the binary's original
filename. It compares every execution-relevant code field recursively,
including instructions, constants, names, arguments, and closures. It ignores
only filenames and debug-location metadata, which can change without changing
behavior.

This is intentionally stronger than a best-effort decompilation. Python 3.14
bytecode is newer than the support available in common decompilers, so a
decompiler can emit incorrect or invalid code. The source in this repository
is the readable recovery of the executable, and this verifier provides a
repeatable proof that it matches the shipped application modules.
