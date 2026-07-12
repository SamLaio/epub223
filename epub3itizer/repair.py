from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import conversion as conv
from .compat import EpubBookAdapter

__all__ = [
    "repair_epub",
    "repair_epub_contents",
]


def repair_epub_contents(root_dir: Path, opf_href: str) -> None:
    """Run the reusable EPUB repair pipeline in-place."""
    conv.convert_bmp_images(root_dir)
    conv.fix_case_mismatched_local_hrefs(root_dir)
    conv.repair_missing_xhtml_references(root_dir)
    conv.repair_missing_css_references(root_dir)
    conv.add_missing_manifest_items(root_dir, opf_href)
    conv.cleanup_opf_manifest(root_dir, opf_href)
    conv.strip_links_from_legacy_toc_files(root_dir, opf_href)
    conv.cleanup_nav_leaf_spans(root_dir, opf_href)
    conv.normalize_all_xhtml_files(root_dir)
    conv.add_fixed_layout_viewports(root_dir, opf_href)
    conv.repair_missing_xhtml_references(root_dir)
    conv.repair_missing_css_references(root_dir)
    conv.add_missing_manifest_items(root_dir, opf_href)
    conv.cleanup_opf_manifest(root_dir, opf_href)
    conv.cleanup_nav_leaf_spans(root_dir, opf_href)
    conv.sanitize_all_css_files(root_dir)


def _default_repair_output_path(input_path: Path) -> Path:
    if input_path.is_dir():
        return input_path.with_name(f"{input_path.name}_repaired.epub")
    return input_path.with_name(f"{input_path.stem}_repaired.epub")


def repair_epub(input_path: Path, output_path: Optional[Path] = None) -> Path:
    """Repair an EPUB file or EPUB folder and write a new EPUB archive."""
    input_path = input_path.resolve()
    if output_path is None:
        output_path = _default_repair_output_path(input_path)
    output_path = output_path.resolve()

    with EpubBookAdapter.open(input_path) as book:
        conv.sanitize_package_filenames(book.root_dir)
        book._load()
        opf_href = book.get_opfbookpath()
        repair_epub_contents(book.root_dir, opf_href)
        mimetype_path = book.root_dir / "mimetype"
        conv.write_text_file(mimetype_path, "application/epub+zip")
        conv.zip_epub(book.root_dir, output_path)

    return output_path
