from __future__ import annotations

from pathlib import Path
from typing import Iterable

from lxml import etree

try:
    from opencc import OpenCC
except Exception:  # pragma: no cover - optional dependency
    OpenCC = None

TEXT_SUFFIXES = {".html", ".htm", ".xhtml", ".opf", ".ncx", ".xml"}
TEXT_ATTRS = {
    "alt",
    "aria-label",
    "content",
    "label",
    "placeholder",
    "title",
}
SKIP_TEXT_ELEMENTS = {"script", "style"}
CUSTOM_REPLACEMENTS_FILE = Path(__file__).with_name("custom_replacements.tsv")

_converter = None


def _load_custom_replacements() -> tuple[tuple[str, str], ...]:
    if not CUSTOM_REPLACEMENTS_FILE.exists():
        return ()
    replacements: dict[str, str] = {}
    with CUSTOM_REPLACEMENTS_FILE.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "\t" not in line:
                continue
            source, target = line.split("\t", 1)
            source = source.strip()
            target = target.strip().split()[0] if target.strip() else ""
            if source and target:
                replacements[source] = target
    return tuple(sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True))


CUSTOM_REPLACEMENTS = _load_custom_replacements()


def _get_converter():
    global _converter
    if _converter is not None:
        return _converter
    if OpenCC is None:
        _converter = False
        return _converter
    try:
        _converter = OpenCC("s2tw")
    except Exception:
        _converter = False
    return _converter


def to_traditional(text: str | None) -> str | None:
    if not text:
        return text
    converter = _get_converter()
    converted = _apply_custom_replacements(text)
    if converter:
        try:
            converted = converter.convert(converted)
        except Exception:
            converted = text
    converted = _apply_custom_replacements(converted)
    return converted


def _apply_custom_replacements(text: str) -> str:
    for old, new in CUSTOM_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def convert_chinese_text(text: str | None, mode: str | None) -> str | None:
    if mode in {None, "", "none"}:
        return text
    if mode == "s2tw":
        return to_traditional(text)
    raise ValueError(f"Unsupported Chinese conversion mode: {mode}")


def convert_chinese_in_package(root_dir: Path, mode: str | None) -> None:
    if mode in {None, "", "none"}:
        return
    for path in _iter_text_files(root_dir):
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        converted = convert_chinese_document(original, mode)
        if converted != original:
            path.write_text(converted, encoding="utf-8", newline="\n")


def convert_chinese_document(data: str, mode: str | None) -> str:
    if mode in {None, "", "none"}:
        return data
    parser = etree.XMLParser(
        remove_blank_text=False,
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        huge_tree=True,
        recover=True,
    )
    root = etree.fromstring(data.encode("utf-8"), parser)
    _convert_element_text(root, mode)
    return etree.tostring(root, encoding="unicode", xml_declaration=False)


def _iter_text_files(root_dir: Path) -> Iterable[Path]:
    for path in root_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _convert_element_text(root: etree._Element, mode: str) -> None:
    for elem in root.iter():
        if not isinstance(elem.tag, str):
            continue
        local = etree.QName(elem).localname.lower()
        if elem.text and local not in SKIP_TEXT_ELEMENTS and not _has_skip_ancestor(elem):
            elem.text = convert_chinese_text(elem.text, mode)
        if elem.tail and not _parent_is_skip(elem):
            elem.tail = convert_chinese_text(elem.tail, mode)
        for attr in list(elem.attrib):
            attr_local = etree.QName(attr).localname.lower() if attr.startswith("{") else attr.lower()
            if attr_local in TEXT_ATTRS:
                elem.set(attr, convert_chinese_text(elem.attrib[attr], mode) or "")


def _has_skip_ancestor(elem: etree._Element) -> bool:
    parent = elem.getparent()
    while parent is not None:
        if isinstance(parent.tag, str) and etree.QName(parent).localname.lower() in SKIP_TEXT_ELEMENTS:
            return True
        parent = parent.getparent()
    return False


def _parent_is_skip(elem: etree._Element) -> bool:
    parent = elem.getparent()
    return bool(
        parent is not None
        and isinstance(parent.tag, str)
        and etree.QName(parent).localname.lower() in SKIP_TEXT_ELEMENTS
    )
