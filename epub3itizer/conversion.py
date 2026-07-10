#!/usr/bin/env python3
from __future__ import annotations

import html
import posixpath
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, unquote, urlsplit

from lxml import etree

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from html_namedentities import named_entities  # noqa: E402
from opf_converter import Opf_Converter  # noqa: E402
from .compat import EpubBookAdapter  # noqa: E402

XHTML_NS = "http://www.w3.org/1999/xhtml"
NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"
EPUB_NS = "http://www.idpf.org/2007/ops"
HTML5_HTTP_EQUIV = {
    "content-type",
    "default-style",
    "x-ua-compatible",
    "refresh",
    "content-security-policy",
}
HTML5_DIMENSION_ELEMENTS = {"canvas", "embed", "iframe", "img", "input", "object", "source", "video"}
PHRASING_PARENT_ELEMENTS = {
    "a",
    "abbr",
    "b",
    "bdi",
    "bdo",
    "cite",
    "code",
    "data",
    "del",
    "dfn",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "i",
    "ins",
    "kbd",
    "mark",
    "p",
    "q",
    "s",
    "samp",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "time",
    "u",
    "var",
}
BLOCK_TO_INLINE_ELEMENTS = {"div", "h1", "h2", "h3", "h4", "h5", "h6", "p"}

_guide_epubtype_map = {
    "acknowledgements": "acknowledgments",
    "other.afterword": "afterword",
    "other.appendix": "appendix",
    "other.backmatter": "backmatter",
    "bibliography": "bibliography",
    "text": "bodymatter",
    "other.chapter": "chapter",
    "colophon": "colophon",
    "other.conclusion": "conclusion",
    "other.contributors": "contributors",
    "copyright-page": "copyright-page",
    "cover": "cover",
    "dedication": "dedication",
    "other.division": "division",
    "epigraph": "epigraph",
    "other.epilogue": "epilogue",
    "other.errata": "errata",
    "other.footnotes": "footnotes",
    "foreword": "foreword",
    "other.frontmatter": "frontmatter",
    "glossary": "glossary",
    "other.halftitlepage": "halftitlepage",
    "other.imprint": "imprint",
    "other.imprimatur": "imprimatur",
    "index": "index",
    "other.introduction": "introduction",
    "other.landmarks": "landmarks",
    "other.loa": "loa",
    "loi": "loi",
    "lot": "lot",
    "other.lov": "lov",
    "notes": "",
    "other.notice": "notice",
    "other.other-credits": "other-credits",
    "other.part": "part",
    "other.preamble": "preamble",
    "preface": "preface",
    "other.prologue": "prologue",
    "other.rearnotes": "rearnotes",
    "other.subchapter": "subchapter",
    "title-page": "titlepage",
    "toc": "toc",
    "other.volume": "volume",
    "other.warning": "warning",
}

IS_NAMED_ENTITY = re.compile(r"(&\w+;)")

XML_PARSER = etree.XMLParser(
    remove_blank_text=False,
    resolve_entities=False,
    load_dtd=False,
    no_network=True,
    huge_tree=True,
)


@dataclass
class TocNode:
    label: str
    href: str
    children: List["TocNode"]


def convert_named_entities(text: str) -> str:
    pieces = IS_NAMED_ENTITY.split(text)
    for i in range(1, len(pieces), 2):
        piece = pieces[i]
        sval = named_entities.get(piece[1:], "")
        if sval != "":
            pieces[i] = "&#%d;" % ord(sval)
    return "".join(pieces)


def read_text_file(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="strict")


def write_text_file(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8", newline="\n")


def strip_fragment(href: str) -> str:
    return href.split("#", 1)[0]


def split_href(href: str) -> Tuple[str, str]:
    base, frag = href.split("#", 1) if "#" in href else (href, "")
    if frag:
        return base, "#" + frag
    return base, ""


def resolve_zip_href(base_dir: str, href: str) -> str:
    base, frag = split_href(href)
    parts = urlsplit(base)
    if parts.scheme or parts.netloc:
        return href
    if base == "":
        return href
    joined = posixpath.normpath(posixpath.join(base_dir, base))
    if joined == ".":
        joined = ""
    return joined + frag


def rel_href(from_href: str, target_href: str) -> str:
    from_base = posixpath.dirname(from_href) or "."
    base, frag = split_href(target_href)
    parts = urlsplit(base)
    if parts.scheme or parts.netloc:
        return target_href
    if base == "":
        return target_href
    rel = posixpath.relpath(posixpath.normpath(base), start=from_base)
    if rel == ".":
        rel = posixpath.basename(base)
    return rel + frag


def encode_local_href(value: str) -> str:
    if not value:
        return value
    base, frag = split_href(value)
    parts = urlsplit(base)
    if parts.scheme or parts.netloc or base.startswith("data:"):
        return value
    return quote(unquote(base).replace(" ", "_"), safe="/%:@!$&'()*+,;=-._~") + frag


def sanitize_package_filenames(root_dir: Path) -> None:
    mapping: Dict[str, str] = {}
    for path in sorted(root_dir.rglob("*")):
        if not path.is_file() or " " not in path.name:
            continue
        new_name = path.name.replace(" ", "_")
        target = path.with_name(new_name)
        counter = 1
        while target.exists():
            target = path.with_name("%s_%d%s" % (target.stem, counter, target.suffix))
            counter += 1
        old_rel = path.relative_to(root_dir).as_posix()
        path.rename(target)
        mapping[old_rel] = target.relative_to(root_dir).as_posix()
    if not mapping:
        return
    text_suffixes = {".css", ".html", ".htm", ".ncx", ".opf", ".xhtml", ".xml"}
    replacements: List[Tuple[str, str]] = []
    for old, new in mapping.items():
        replacements.append((old, new))
        replacements.append((quote(old, safe="/%:@!$&'()*+,;=-._~"), new))
        replacements.append((posixpath.basename(old), posixpath.basename(new)))
        replacements.append((quote(posixpath.basename(old), safe="/%:@!$&'()*+,;=-._~"), posixpath.basename(new)))
    for path in root_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        data = read_text_file(path)
        updated = data
        for old, new in replacements:
            updated = updated.replace(old, new)
        if updated != data:
            write_text_file(path, updated)


def add_epub_namespace(root: etree._Element) -> etree._Element:
    nsmap = dict(root.nsmap or {})
    nsmap["epub"] = EPUB_NS
    new_root = etree.Element(root.tag, nsmap=nsmap)
    for key, value in root.attrib.items():
        new_root.set(key, value)
    new_root.text = root.text
    new_root.tail = root.tail
    for child in list(root):
        new_root.append(child)
    return new_root


def append_style(elem: etree._Element, declaration: str) -> None:
    style = elem.get("style", "").strip()
    if style and not style.endswith(";"):
        style += ";"
    elem.set("style", (style + " " + declaration).strip())


def normalize_epubcheck_xhtml(root: etree._Element) -> None:
    for elem in list(root.iter()):
        if not isinstance(elem.tag, str):
            continue
        qname = etree.QName(elem)
        local = qname.localname
        namespace = qname.namespace

        if local == "meta":
            http_equiv = elem.get("http-equiv")
            if http_equiv and http_equiv.lower() not in HTML5_HTTP_EQUIV:
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)
                continue
            if not any(elem.get(attr) for attr in ("charset", "http-equiv", "name")):
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)
                continue

        if namespace == XHTML_NS and local == "center":
            elem.tag = f"{{{XHTML_NS}}}div"
            append_style(elem, "text-align: center")
            local = "div"

        if namespace == XHTML_NS and local == "font":
            elem.tag = f"{{{XHTML_NS}}}span"
            color = elem.attrib.pop("color", "")
            face = elem.attrib.pop("face", "")
            elem.attrib.pop("size", None)
            if color:
                append_style(elem, "color: %s" % color)
            if face:
                append_style(elem, "font-family: %s" % face)
            local = "span"

        parent = elem.getparent()
        if parent is not None and namespace == XHTML_NS and local in BLOCK_TO_INLINE_ELEMENTS:
            parent_local = etree.QName(parent).localname if isinstance(parent.tag, str) else ""
            if parent_local in PHRASING_PARENT_ELEMENTS:
                elem.tag = f"{{{XHTML_NS}}}span"
                local = "span"

        for attr in list(elem.attrib):
            attr_local = etree.QName(attr).localname if attr.startswith("{") else attr
            attr_lower = attr_local.lower()
            if attr_lower.startswith("data-amznremoved"):
                del elem.attrib[attr]
            elif attr_lower == "align":
                value = elem.attrib.pop(attr, "").lower()
                if value in {"left", "right", "center", "justify"}:
                    append_style(elem, "text-align: %s" % value)
            elif namespace == XHTML_NS and attr_lower in {"height", "width"} and local not in HTML5_DIMENSION_ELEMENTS:
                del elem.attrib[attr]
            elif attr_lower in {"href", "src"}:
                base, _frag = split_href(elem.attrib[attr])
                if re.fullmatch(r"X{8,}", base):
                    del elem.attrib[attr]
                    continue
                elem.attrib[attr] = encode_local_href(elem.attrib[attr])

        if namespace == XHTML_NS and local == "link":
            link_type = elem.get("type", "")
            if link_type == "application/vnd.adobe-page-template+xml":
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)


def collect_doc_features(root: etree._Element, book_href: str) -> Tuple[str, List[str], List[str], List[Tuple[str, str, str]]]:
    ns = {"x": XHTML_NS, "epub": EPUB_NS}
    if root.tag == f"{{{XHTML_NS}}}html":
        root = add_epub_namespace(root)
    else:
        # Best effort fallback for documents without XHTML namespace.
        root.set("xmlns:epub", EPUB_NS)

    normalize_epubcheck_xhtml(root)

    # Some EPUB2 HTML TOCs use <dl>/<dt> only, which becomes invalid under
    # EPUB3/HTML5 validation. Normalize those into a simple unordered list.
    for dl in root.xpath(".//x:dl[not(.//x:dd)]", namespaces=ns):
        element_children = [child for child in dl if isinstance(child.tag, str)]
        if not element_children:
            continue
        if not all(etree.QName(child).localname == "dt" for child in element_children):
            continue
        dl.tag = f"{{{XHTML_NS}}}ul"
        for child in element_children:
            child.tag = f"{{{XHTML_NS}}}li"

    for big in root.xpath(".//x:big", namespaces=ns):
        big.tag = f"{{{XHTML_NS}}}span"
        style = big.get("style", "")
        if style:
            style = style.rstrip("; ") + "; font-size: larger"
        else:
            style = "font-size: larger"
        big.set("style", style)

    spine_properties: List[str] = []
    manifest_properties: List[str] = []
    epub_types: List[Tuple[str, str, str]] = []

    for meta in root.xpath(".//x:meta", namespaces=ns):
        name = meta.get("name", "")
        content = meta.get("content", "")
        if name in {"layout", "orientation", "page-spread"} and content:
            value = "%s-%s" % (name, content)
            if value not in spine_properties:
                spine_properties.append(value)
        if "charset" in content.lower() or meta.get("charset") is not None:
            meta.attrib.clear()
            meta.set("charset", "utf-8")

    if root.xpath(".//x:svg", namespaces=ns) or root.xpath(".//svg:svg", namespaces={"svg": "http://www.w3.org/2000/svg"}):
        manifest_properties.append("svg")
    if root.xpath(".//x:math", namespaces=ns) or root.xpath(".//m:math", namespaces={"m": "http://www.w3.org/1998/Math/MathML"}):
        manifest_properties.append("mathml")
    if root.xpath(".//epub:switch", namespaces=ns):
        manifest_properties.append("switch")
    if root.xpath(".//x:script", namespaces=ns):
        head = root.find(f".//{{{XHTML_NS}}}head")
        if head is not None and head.xpath(".//x:script", namespaces=ns):
            manifest_properties.append("scripted")

    for elem in root.iter():
        epub_type = elem.get("{%s}type" % EPUB_NS)
        elem_id = elem.get("id")
        title = elem.get("title")
        if epub_type and elem_id and title:
            epub_types.append((book_href + "#" + elem_id, epub_type, title))

    title = root.find(f".//{{{XHTML_NS}}}head/{{{XHTML_NS}}}title")
    if title is not None and not "".join(title.itertext()).strip():
        title.text = posixpath.basename(strip_fragment(book_href)) or "Untitled"

    output = etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        doctype="<!DOCTYPE html>",
        pretty_print=False,
    )
    return output.decode("utf-8"), manifest_properties, spine_properties, epub_types


def convert_xhtml_file(src_path: Path, book_href: str) -> Tuple[str, List[str], List[str], List[Tuple[str, str, str]]]:
    raw = convert_named_entities(read_text_file(src_path))
    root = etree.fromstring(raw.encode("utf-8"), XML_PARSER)
    return collect_doc_features(root, book_href)


def parse_ncx_file(src_path: Path, ncx_href: str) -> Tuple[Optional[str], List[TocNode], List[Tuple[str, str]]]:
    raw = convert_named_entities(read_text_file(src_path))
    root = etree.fromstring(raw.encode("utf-8"), XML_PARSER)
    ns = {"n": NCX_NS}

    for elem in root.iter():
        local = etree.QName(elem).localname
        if local in {"doctitle", "docauthor", "navmap", "navpoint", "navlabel", "pagelist", "pagetarget", "playorder"}:
            pass

    doc_title_el = root.find(".//n:docTitle/n:text", namespaces=ns)
    doctitle = doc_title_el.text if doc_title_el is not None else None

    def parse_navpoint(navpoint: etree._Element) -> TocNode:
        label = navpoint.findtext("n:navLabel/n:text", default="", namespaces=ns) or ""
        content = navpoint.find("n:content", namespaces=ns)
        href = content.get("src", "") if content is not None else ""
        children = [parse_navpoint(child) for child in navpoint.findall("n:navPoint", namespaces=ns)]
        return TocNode(label=label, href=href, children=children)

    toc_nodes = [parse_navpoint(node) for node in root.findall(".//n:navMap/n:navPoint", namespaces=ns)]

    pagelist: List[Tuple[str, str]] = []
    current_page = None
    for elem in root.iter():
        local = etree.QName(elem).localname
        if local == "pageTarget" and elem.get("value"):
            current_page = elem.get("value")
        elif local == "content" and current_page is not None and elem.get("src"):
            pagelist.append((current_page, elem.get("src")))
            current_page = None

    out_root = root
    for elem in out_root.iter():
        local = etree.QName(elem).localname
        if local in {"doctitle", "docauthor", "navmap", "navpoint", "navlabel", "pagelist", "pagetarget", "playorder"}:
            camel = {
                "doctitle": "docTitle",
                "docauthor": "docAuthor",
                "navmap": "navMap",
                "navpoint": "navPoint",
                "playorder": "playOrder",
                "navlabel": "navLabel",
                "pagelist": "pageList",
                "pagetarget": "pageTarget",
            }.get(local, local)
            elem.tag = f"{{{NCX_NS}}}{camel}"

    if current_page is not None:
        current_page = None

    write_text_file(src_path, etree.tostring(out_root, encoding="utf-8", xml_declaration=True, pretty_print=True).decode("utf-8"))
    return doctitle, toc_nodes, pagelist


def sync_ncx_uid(src_path: Path, uid: str) -> None:
    if not uid or not src_path.exists():
        return
    raw = convert_named_entities(read_text_file(src_path))
    root = etree.fromstring(raw.encode("utf-8"), XML_PARSER)
    ns = {"n": NCX_NS}
    meta = root.find(".//n:meta[@name='dtb:uid']", namespaces=ns)
    if meta is None:
        found = root.xpath(".//*[local-name()='meta' and @name='dtb:uid']")
        meta = found[0] if found else None
    if meta is None:
        return
    if meta.get("content") == uid:
        return
    meta.set("content", uid)
    write_text_file(
        src_path,
        etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=False).decode("utf-8"),
    )


def normalize_ncx_play_order(src_path: Path) -> None:
    if not src_path.exists():
        return
    raw = convert_named_entities(read_text_file(src_path))
    root = etree.fromstring(raw.encode("utf-8"), XML_PARSER)
    changed = False
    for index, elem in enumerate(root.xpath(".//*[@playOrder]"), start=1):
        value = str(index)
        if elem.get("playOrder") != value:
            elem.set("playOrder", value)
            changed = True
    if changed:
        write_text_file(
            src_path,
            etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=False).decode("utf-8"),
        )


def sanitize_css(data: str) -> str:
    data = re.sub(
        r"@font-face\s*\{.*?\}",
        "",
        data,
        flags=re.IGNORECASE | re.DOTALL,
    )
    data = re.sub(r"url\(\s*(['\"]?)(?:file:|res:/)[^)]+\)", "none", data, flags=re.IGNORECASE)
    return data


def resolve_href_for_output(nav_href: str, source_href: str, target_href: str) -> str:
    nav_dir = posixpath.dirname(nav_href) or "."
    source_dir = posixpath.dirname(source_href) or "."
    base, frag = split_href(target_href)
    parts = urlsplit(base)
    if parts.scheme or parts.netloc or not base:
        return target_href
    absolute = posixpath.normpath(posixpath.join(source_dir, base))
    rel = posixpath.relpath(absolute, start=nav_dir)
    if rel == ".":
        rel = posixpath.basename(absolute)
    return rel + frag


def build_nav(
    nav_href: str,
    doctitle: Optional[str],
    toc_nodes: List[TocNode],
    pagelist: List[Tuple[str, str]],
    guide_info: List[Tuple[str, str, str]],
    opf_dir: str,
) -> str:
    lines: List[str] = []

    def href_for(target_href: str) -> str:
        return resolve_href_for_output(nav_href, opf_dir + "/placeholder", target_href)

    def flatten_toc(nodes: List[TocNode], level: int = 1) -> List[Tuple[int, str, str]]:
        flat: List[Tuple[int, str, str]] = []
        for node in nodes:
            flat.append((level, node.label, node.href))
            if node.children:
                flat.extend(flatten_toc(node.children, level + 1))
        return flat

    flat_toc = flatten_toc(toc_nodes)

    lines.append('<?xml version="1.0" encoding="utf-8"?>\n')
    lines.append("<!DOCTYPE html>\n")
    lines.append(
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="%s" lang="en" xml:lang="en">\n'
        % EPUB_NS
    )
    lines.append("  <head>\n")
    lines.append("    <meta charset=\"utf-8\" />\n")
    lines.append("    <title>ePub Nav</title>\n")
    lines.append("    <style type=\"text/css\">\n")
    lines.append("      ol { list-style-type: none; }\n")
    lines.append("    </style>\n")
    lines.append("  </head>\n")
    lines.append('  <body epub:type="frontmatter">\n')

    lines.append('    <nav epub:type="toc" id="toc">\n')
    lines.append("      <h1>Table of Contents</h1>\n")
    lines.append("      <ol>\n")
    curlvl = 1
    initial = True
    for lvl, lbl, bookhref in flat_toc:
        href = href_for(bookhref)
        label = lbl.strip() or posixpath.basename(strip_fragment(bookhref)) or "Untitled"
        if lvl > curlvl:
            while lvl > curlvl:
                indent = "      " + "  " * curlvl
                lines.append(indent + "<ol>\n")
                lines.append(indent + "  <li>\n")
                lines.append(indent + "    <a href=\"%s\">%s</a>\n" % (html.escape(href, quote=True), html.escape(label)))
                curlvl += 1
        elif lvl < curlvl:
            while lvl < curlvl:
                indent = "      " + "  " * (curlvl - 1)
                lines.append(indent + "  </li>\n")
                lines.append(indent + "</ol>\n")
                curlvl -= 1
            indent = "      " + "  " * (lvl - 1)
            lines.append(indent + "  </li>\n")
            lines.append(indent + "  <li>\n")
            lines.append(indent + "    <a href=\"%s\">%s</a>\n" % (html.escape(href, quote=True), html.escape(label)))
        else:
            indent = "      " + "  " * (lvl - 1)
            if not initial:
                lines.append(indent + "  </li>\n")
            lines.append(indent + "  <li>\n")
            lines.append(indent + "    <a href=\"%s\">%s</a>\n" % (html.escape(href, quote=True), html.escape(label)))
        initial = False
        curlvl = lvl
    while curlvl > 0:
        indent = "      " + "  " * (curlvl - 1)
        lines.append(indent + "  </li>\n")
        lines.append(indent + "</ol>\n")
        curlvl -= 1
    lines.append("    </nav>\n")

    if pagelist:
        lines.append('    <nav epub:type="page-list" id="page-list" hidden="">\n')
        lines.append("      <ol>\n")
        for page_num, href in pagelist:
            lines.append(
                '        <li><a href="%s">%s</a></li>\n'
                % (html.escape(href_for(href), quote=True), html.escape(page_num))
            )
        lines.append("      </ol>\n")
        lines.append("    </nav>\n")

    landmark_lines: List[str] = []
    for gtyp, gtitle, ghref in guide_info:
        etyp = _guide_epubtype_map.get(gtyp, "")
        if not etyp:
            continue
        label = gtitle.strip() or posixpath.basename(strip_fragment(ghref)) or etyp
        landmark_lines.append("        <li>\n")
        landmark_lines.append(
            '          <a epub:type="%s" href="%s">%s</a>\n'
            % (
                html.escape(etyp, quote=True),
                html.escape(href_for(ghref), quote=True),
                html.escape(label),
            )
        )
        landmark_lines.append("        </li>\n")
    if landmark_lines:
        lines.append('    <nav epub:type="landmarks" id="landmarks" hidden="">\n')
        lines.append("      <h2>Guide</h2>\n")
        lines.append("      <ol>\n")
        lines.extend(landmark_lines)
        lines.append("      </ol>\n")
        lines.append("    </nav>\n")

    lines.append("  </body>\n")
    lines.append("</html>\n")
    return "".join(lines)


def filter_guide_to_spine(guide_info: List[Tuple[str, str, str]], spine_hrefs: Iterable[str]) -> List[Tuple[str, str, str]]:
    spine_set = {strip_fragment(href) for href in spine_hrefs}
    filtered: List[Tuple[str, str, str]] = []
    for gtyp, gtitle, ghref in guide_info:
        if strip_fragment(ghref) in spine_set:
            filtered.append((gtyp, gtitle, ghref))
    return filtered


def remove_nav_spine_itemref(opf_text: str) -> str:
    return re.sub(
        r"\n?\s*<itemref[^>]*idref=\"[^\"]*nav[^\"]*\"[^>]*/>\s*",
        "\n",
        opf_text,
        flags=re.IGNORECASE,
    )


def zip_epub(temp_dir: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as zf:
        mimetype = temp_dir / "mimetype"
        if not mimetype.exists():
            raise FileNotFoundError("Converted EPUB is missing mimetype")
        zf.writestr("mimetype", mimetype.read_text(encoding="utf-8"), compress_type=zipfile.ZIP_STORED)
        for file_path in sorted(temp_dir.rglob("*")):
            if not file_path.is_file() or file_path.name == "mimetype":
                continue
            arcname = file_path.relative_to(temp_dir).as_posix()
            zf.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED)


def convert_epub2_to_epub3(input_path: Path, output_path: Optional[Path] = None) -> Path:
    input_path = input_path.resolve()
    if output_path is None:
        if input_path.is_dir():
            output_path = input_path.with_name(input_path.name + "_epub3.epub")
        else:
            output_path = input_path.with_name(input_path.stem + "_epub3.epub")
    output_path = output_path.resolve()

    with EpubBookAdapter.open(input_path) as book:
        sanitize_package_filenames(book.root_dir)
        book._load()
        opf_href = book.get_opfbookpath()
        opf_path = book.resolve_bookpath(opf_href)
        opf_dir = book.get_startingdir(opf_href)

        opf_text = book.readotherfile(opf_href)
        manifest_items = list(book.manifest_iter())
        spine_hrefs = [href for _, _, href in book.spine_iter() if href]

        spine_properties: Dict[str, str] = {}
        manifest_properties: Dict[str, str] = {}
        epub_types: Dict[str, List[Tuple[str, str, str]]] = {}

        for mid, href in book.text_iter():
            xhtml_path = book.resolve_bookpath(book.id_to_bookpath(mid))
            if not xhtml_path.exists():
                continue
            book_href = book.id_to_bookpath(mid)
            print("..converting:", href, "with manifest id:", mid)
            data, mprops, sprops, etypes = convert_xhtml_file(xhtml_path, book_href)
            if sprops:
                spine_properties[mid] = " ".join(dict.fromkeys(sprops))
            if mprops:
                manifest_properties[mid] = " ".join(dict.fromkeys(mprops))
            if etypes:
                epub_types[mid] = etypes
            write_text_file(xhtml_path, data)

        for _mid, href, media_type in manifest_items:
            if media_type == "text/css":
                css_path = book.resolve_bookpath(book.id_to_bookpath(_mid))
                if css_path.exists():
                    write_text_file(css_path, sanitize_css(read_text_file(css_path)))

        ncx_id = None
        try:
            ncx_id = book.gettocid()
        except KeyError:
            ncx_id = None
        ncx_href = book.id_to_bookpath(ncx_id) if ncx_id is not None else "toc.ncx"
        ncx_path = book.resolve_bookpath(ncx_href)
        doctitle = None
        toc_nodes: List[TocNode] = []
        pagelist: List[Tuple[str, str]] = []
        if ncx_path.exists():
            print("..parsing:", ncx_href)
            doctitle, toc_nodes, pagelist = parse_ncx_file(ncx_path, ncx_href)

        man_ids = [mid for mid, _, _ in manifest_items if mid]
        opfconv = Opf_Converter(opf_text, spine_properties, manifest_properties, {}, man_ids)
        lang = opfconv.get_lang()
        uid = opfconv.get_uid()
        if ncx_path.exists():
            sync_ncx_uid(ncx_path, uid)
            normalize_ncx_play_order(ncx_path)
        opf3 = opfconv.get_opf3()
        # In the standalone tool, keep nav.xhtml out of the spine so epubCheck
        # does not treat it as non-linear reachable content.
        opf3 = remove_nav_spine_itemref(opf3)
        guide = filter_guide_to_spine(opfconv.get_guide(), spine_hrefs)

        opf3_path = opf_path
        write_text_file(opf3_path, opf3)

        nav_href = book.build_bookpath("nav.xhtml", opf_dir)
        nav_path = book.resolve_bookpath(nav_href)
        print("..creating:", nav_href)
        navdata = build_nav(nav_href, doctitle, toc_nodes, pagelist, guide, opf_dir)
        write_text_file(nav_path, navdata)

        mimetype_path = book.root_dir / "mimetype"
        write_text_file(mimetype_path, "application/epub+zip")

        print("..creating: epub3")
        zip_epub(book.root_dir, output_path)

    return output_path
