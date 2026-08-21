"""Verify that recovered PyInstaller bytecode matches this source checkout.

Usage:
    python tools/verify_release_bytecode.py PATH_TO_EXTRACTED_EXE

The extracted directory is produced by:
    python -m pip install pyinstxtractor-ng
    python -m pyinstxtractor_ng BO2EmblemToolkit.exe
"""

from __future__ import annotations

import argparse
import marshal
import types
from pathlib import Path


APP_MODULES = ("run.pyc",)
APP_PREFIX = "emblemtool"
PYC_HEADER_SIZE = 16


def load_code(path: Path):
    data = path.read_bytes()
    if len(data) < PYC_HEADER_SIZE:
        raise ValueError(f"{path} is too small to be a Python bytecode file")
    return marshal.loads(data[PYC_HEADER_SIZE:])


def source_path(source_root: Path, bytecode_root: Path, pyc_path: Path) -> Path:
    relative = pyc_path.relative_to(bytecode_root).with_suffix(".py")
    return source_root / relative


def bytecode_paths(extracted_root: Path) -> list[Path]:
    pyz_root = extracted_root / "PYZ.pyz_extracted"
    paths = [extracted_root / module for module in APP_MODULES]
    paths.extend((pyz_root / APP_PREFIX).rglob("*.pyc"))
    return sorted(path for path in paths if path.is_file())


def equivalent_code(expected: types.CodeType, actual: types.CodeType) -> bool:
    """Compare behavior while excluding file path and debug-location metadata."""
    attributes = (
        "co_argcount",
        "co_posonlyargcount",
        "co_kwonlyargcount",
        "co_nlocals",
        "co_stacksize",
        "co_flags",
        "co_code",
        "co_names",
        "co_varnames",
        "co_freevars",
        "co_cellvars",
    )
    if any(getattr(expected, name) != getattr(actual, name) for name in attributes):
        return False
    if len(expected.co_consts) != len(actual.co_consts):
        return False
    for expected_const, actual_const in zip(expected.co_consts, actual.co_consts):
        if isinstance(expected_const, types.CodeType) and isinstance(actual_const, types.CodeType):
            if not equivalent_code(expected_const, actual_const):
                return False
        elif expected_const != actual_const:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extracted_root", type=Path)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Source checkout to compare (defaults to this repository root).",
    )
    args = parser.parse_args()

    extracted_root = args.extracted_root.resolve()
    source_root = args.source_root.resolve()
    pyz_root = extracted_root / "PYZ.pyz_extracted"
    failures: list[str] = []

    for pyc_path in bytecode_paths(extracted_root):
        bytecode_root = pyz_root if pyc_path.is_relative_to(pyz_root) else extracted_root
        expected = load_code(pyc_path)
        py_path = source_path(source_root, bytecode_root, pyc_path)
        if not py_path.is_file():
            failures.append(f"missing source: {py_path.relative_to(source_root)}")
            continue

        actual = compile(
            py_path.read_bytes(),
            expected.co_filename,
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        if not equivalent_code(expected, actual):
            failures.append(f"mismatch: {py_path.relative_to(source_root)}")
        else:
            print(f"verified: {py_path.relative_to(source_root)}")

    if failures:
        print("\nVerification failed:")
        print("\n".join(failures))
        return 1

    print("\nAll application bytecode modules match the published source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
