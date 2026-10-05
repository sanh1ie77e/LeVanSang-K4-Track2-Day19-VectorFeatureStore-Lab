"""Convert Jupytext sources and execute notebooks, preserving outputs on failure.

Usage: python scripts/run_notebooks.py [01 02 ...] [--convert-only]
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import jupytext
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sources = sorted((ROOT / "notebooks").glob("[0-9]*.py"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("numbers", nargs="*")
    parser.add_argument("--convert-only", action="store_true")
    args = parser.parse_args()
    available = {source.name[:2] for source in sources}
    unknown = set(args.numbers) - available
    if unknown:
        parser.error(f"Unknown notebook number(s): {', '.join(sorted(unknown))}; "
                     f"available: {', '.join(sorted(available)) or 'none'}")
    if not sources:
        parser.error("No numbered notebook sources found")
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    os.environ["PYTHONUTF8"] = "1"
    failed = []
    for source in sources:
        if args.numbers and source.name[:2] not in args.numbers:
            continue
        target = source.with_suffix(".ipynb")
        notebook = jupytext.read(source)
        notebook.metadata.kernelspec = {
            "display_name": "Python 3 (Lab 19)", "language": "python", "name": "python3"
        }
        if args.convert_only:
            nbformat.write(notebook, target)
            print(f"Converted {target.name}", flush=True)
            continue
        print(f"Running {target.name}", flush=True)
        def report_cell(cell, cell_index, **kwargs):
            if cell.cell_type == "code":
                print(f"  cell {cell_index + 1} executed", flush=True)

        try:
            NotebookClient(
                notebook, timeout=900, kernel_name="python3",
                resources={"metadata": {"path": str(source.parent)}},
                on_cell_executed=report_cell,
            ).execute()
            print(f"PASS {target.name}", flush=True)
        except Exception as exc:
            failed.append(target.name)
            print(f"FAIL {target.name}: {exc}", flush=True)
        finally:
            nbformat.write(notebook, target)
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
