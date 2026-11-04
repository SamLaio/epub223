from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import Iterable

from lxml import etree

try:
    from s2tw_converter import Converter as ZhTranslateConverter, simplified_pattern
except Exception:  # pragma: no cover - local integration fallback
    zhtranslate_src = Path(r"D:\github\zhTranslate\src")
    if zhtranslate_src.exists() and str(zhtranslate_src) not in sys.path:
        sys.path.insert(0, str(zhtranslate_src))
    try:
        from s2tw_converter import Converter as ZhTranslateConverter, simplified_pattern
    except Exception:
        ZhTranslateConverter = None
        simplified_pattern = None

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
        converter = _get_converter()
        if not converter:
            raise RuntimeError("簡轉正失敗：無法載入共享 zhTranslate")
        return converter.convert(text)
    raise ValueError(f"Unsupported Chinese conversion mode: {mode}")


def convert_chinese_in_package(root_dir: Path, mode: str | None) -> None:
    if mode in {None, "", "none"}:
        return
    convert_chinese_text("", mode)  # 明確要求轉換時，缺相依不可靜默略過。
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
    # 延後匯入以共用保文解析，同時避免 conversion 與 chinese 的循環初始化。
    from .conversion import parse_xml_recovering
    root = parse_xml_recovering(data)
    _convert_element_text(root, mode)
    return etree.tostring(root, encoding="unicode", xml_declaration=False)


def _iter_text_files(root_dir: Path) -> Iterable[Path]:
    for path in root_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _convert_element_text(root: etree._Element, mode: str) -> None:
    def simplified_source(elem):
        for node in (elem, *elem.iterancestors()):
            language = node.get('{http://www.w3.org/XML/1998/namespace}lang') or node.get('lang')
            if language:
                return language.lower().replace('_', '-') in {'zh-hans', 'zh-cn', 'zh-sg'}
        return False

    for elem in root.iter():
        if not isinstance(elem.tag, str):
            continue
        local = etree.QName(elem).localname.lower()
        skip = elem.get('translate', '').lower() == 'no' or (elem.get('{http://www.w3.org/XML/1998/namespace}lang') or elem.get('lang', '')).lower().split('-')[0] == 'ja' or local in SKIP_TEXT_ELEMENTS or _has_skip_ancestor(elem)
        if elem.text and not skip:
            elem.text = _convert_simplified_field(elem.text, mode, simplified_source(elem))
        if elem.tail and not _parent_is_skip(elem):
            elem.tail = _convert_simplified_field(elem.tail, mode, simplified_source(elem.getparent()) if elem.getparent() is not None else False)
        for attr in list(elem.attrib):
            attr_local = etree.QName(attr).localname.lower() if attr.startswith("{") else attr.lower()
            if attr_local in TEXT_ATTRS and not skip:
                elem.set(attr, _convert_simplified_field(elem.attrib[attr], mode, simplified_source(elem)))
    # 轉換後更新明確來源語言，避免重跑時再次強制轉換正體文字。
    for elem in root.iter():
        if not isinstance(elem.tag, str):
            continue
        if etree.QName(elem).localname.lower() in SKIP_TEXT_ELEMENTS or elem.get('translate', '').lower() == 'no' or _has_skip_ancestor(elem):
            continue
        for attr in ('lang', '{http://www.w3.org/XML/1998/namespace}lang'):
            if elem.get(attr, '').lower().replace('_', '-') in {'zh-hans', 'zh-cn', 'zh-sg'}:
                elem.set(attr, 'zh-Hant')


def _convert_simplified_field(text: str, mode: str, force: bool = False) -> str:
    # 只選有明確簡體字的可讀欄位；詞彙／標點仍唯一由 zhTranslate 處理。
    parts = re.split(r'(「[^「」]*[\u3040-\u30ff][^「」]*」|〈[^〈〉]*[\u3040-\u30ff][^〈〉]*〉|《[^《》]*[\u3040-\u30ff][^《》]*》|（[^（）]*[\u3040-\u30ff][^（）]*）|\([^()]*[\u3040-\u30ff][^()]*\))', text)
    if simplified_pattern is None:
        raise RuntimeError("簡轉正失敗：缺少共享字形偵測")
    pattern = simplified_pattern(True)
    return ''.join(part if i % 2 or not (force or pattern.search(part)) else convert_chinese_text(part, mode) for i, part in enumerate(parts))


def _has_skip_ancestor(elem: etree._Element) -> bool:
    parent = elem.getparent()
    while parent is not None:
        if isinstance(parent.tag, str) and (etree.QName(parent).localname.lower() in SKIP_TEXT_ELEMENTS or parent.get('translate', '').lower() == 'no' or (parent.get('{http://www.w3.org/XML/1998/namespace}lang') or parent.get('lang', '')).lower().split('-')[0] == 'ja'):
            return True
        parent = parent.getparent()
    return False


def _parent_is_skip(elem: etree._Element) -> bool:
    parent = elem.getparent()
    return bool(
        parent is not None
        and isinstance(parent.tag, str)
        and (etree.QName(parent).localname.lower() in SKIP_TEXT_ELEMENTS or parent.get('translate', '').lower() == 'no' or (parent.get('{http://www.w3.org/XML/1998/namespace}lang') or parent.get('lang', '')).lower().split('-')[0] == 'ja' or _has_skip_ancestor(parent))
    )
