from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from lxml import etree

try:
    from s2tw_converter import Converter as ZhTranslateConverter
except Exception:  # pragma: no cover - local integration fallback
    zhtranslate_src = Path(r"D:\github\zhTranslate\src")
    if zhtranslate_src.exists() and str(zhtranslate_src) not in sys.path:
        sys.path.insert(0, str(zhtranslate_src))
    try:
        from s2tw_converter import Converter as ZhTranslateConverter
    except Exception:
        ZhTranslateConverter = None

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

_converter = None


def _get_converter():
    global _converter
    if _converter is not None:
        return _converter
    if ZhTranslateConverter is None:
        _converter = False
        return _converter
    try:
        _converter = ZhTranslateConverter()
    except Exception:
        _converter = False
    return _converter


def to_traditional(text: str | None) -> str | None:
    if not text:
        return text
    converter = _get_converter()
    if converter:
        try:
            return converter.convert(text)
        except Exception:
            pass
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
