#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple

from .conversion import convert_epub2_to_epub3


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _iter_epub_files(input_dir: Path, recursive: bool, exclude_dir: Optional[Path] = None) -> Iterator[Path]:
    iterator = input_dir.rglob("*.epub") if recursive else input_dir.glob("*.epub")
    for path in sorted(iterator):
        if not path.is_file():
            continue
        if exclude_dir is not None and _is_under(path, exclude_dir):
            continue
        yield path


def _default_output_dir(input_dir: Path) -> Path:
    return input_dir.parent / f"{input_dir.name}_epub3"


def _configure_text_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _convert_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    recursive: bool = False,
    suffix: str = "_epub3",
    overwrite: bool = False,
) -> Tuple[List[Path], List[Path]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    converted: List[Path] = []
    failed: List[Path] = []
    for source in _iter_epub_files(input_dir, recursive, exclude_dir=output_dir):
        rel = source.relative_to(input_dir)
        target = output_dir / rel.parent / f"{rel.stem}{suffix}{rel.suffix}"
        if target.exists() and not overwrite:
            print(f"Skipping existing file: {target}")
            continue
        try:
            result = convert_epub2_to_epub3(source, target)
            converted.append(result)
            print(f"Output written to {result}")
        except Exception as exc:
            failed.append(source)
            print(f"Error: {source}: {exc}", file=sys.stderr)
    return converted, failed


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert EPUB2 books into EPUB3.")
    parser.add_argument("input", help="Input .epub file or EPUB folder")
    parser.add_argument("-o", "--output", help="Output .epub file path for a single file input")
    parser.add_argument("--output-dir", help="Output directory for batch folder conversion")
    parser.add_argument("--recursive", action="store_true", help="Recursively scan subfolders for .epub files")
    parser.add_argument("--suffix", default="_epub3", help="Suffix added before .epub in batch mode")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    _configure_text_streams()
    args = parse_args(argv)
    input_path = Path(args.input)

    if input_path.is_dir():
        if args.output:
            print("Error: use --output-dir when the input is a folder", file=sys.stderr)
            return 1
        output_dir = Path(args.output_dir) if args.output_dir else _default_output_dir(input_path)
        converted, failed = _convert_directory(
            input_path,
            output_dir,
            recursive=args.recursive,
            suffix=args.suffix,
            overwrite=args.overwrite,
        )
        print(f"Batch complete: {len(converted)} converted, {len(failed)} failed")
        return 1 if failed else 0

    if args.output_dir:
        print("Error: use --output-dir only when the input is a folder", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else None
    try:
        result = convert_epub2_to_epub3(input_path, output_path)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Output written to {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
