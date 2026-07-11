#!/usr/bin/env python3
from __future__ import annotations

import html
import mimetypes
import posixpath
import re
import sys
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, unquote, urlsplit

from lxml import etree
try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional BMP repair dependency
    Image = None

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from html_namedentities import named_entities  # noqa: E402
from opf_converter import Opf_Converter  # noqa: E402
from .compat import EpubBookAdapter  # noqa: E402

XHTML_NS = "http://www.w3.org/1999/xhtml"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"
XLINK_NS = "http://www.w3.org/1999/xlink"
NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"
EPUB_NS = "http://www.idpf.org/2007/ops"
RECOVER_XML_PARSER = etree.XMLParser(
    remove_blank_text=False,
    resolve_entities=False,
    load_dtd=False,
    no_network=True,
    huge_tree=True,
    recover=True,
)
HTML5_HTTP_EQUIV = {
    "content-type",
    "default-style",
    "x-ua-compatible",
    "refresh",
    "content-security-policy",
}
HTML5_DIMENSION_ELEMENTS = {"canvas", "embed", "iframe", "img", "input", "object", "source", "video"}
JAVASCRIPT_MEDIA_TYPES = {"application/javascript", "application/ecmascript", "text/javascript", "text/ecmascript"}
CALIBRE_BOOKMARKS = {"meta-inf/calibre_bookmarks.txt"}
LIST_CONTAINER_ELEMENTS = {"menu", "ol", "ul"}
FOREIGN_IMAGE_SUFFIXES = {".emf", ".wmf"}
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
BLOCK_TO_INLINE_ELEMENTS = {"address", "article", "aside", "blockquote", "div", "dl", "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "li", "nav", "ol", "p", "section", "table", "ul"}
XHTML_TAG_RENAMES = {
    "case": "div",
    "debagame": "div",
    "defaultcase": "div",
    "do": "span",
    "fa": "span",
    "la": "span",
    "mi": "span",
    "order": "span",
    "pubu": "div",
    "r": "span",
    "re": "span",
    "si": "span",
    "so": "span",
    "spen": "span",
    "spine": "div",
    "ti": "span",
    "tt": "span",
}
SAFE_RENAMED_TAG_ATTRS = {"class", "id", "lang", "style", "title", "xml:lang"}
HTML5_NAME_ELEMENTS = {"button", "fieldset", "form", "iframe", "input", "map", "meta", "object", "output", "param", "select", "textarea"}
XML_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")
DC_METADATA_ELEMENTS = {
    "contributor",
    "coverage",
    "creator",
    "date",
    "description",
    "format",
    "identifier",
    "language",
    "publisher",
    "relation",
    "rights",
    "source",
    "subject",
    "title",
    "type",
    "meta",
}

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
    nsmap = {key: value for key, value in dict(root.nsmap or {}).items() if value != XHTML_NS}
    if isinstance(root.tag, str) and etree.QName(root).namespace == XHTML_NS:
        nsmap[None] = XHTML_NS
    nsmap["epub"] = EPUB_NS
    new_root = etree.Element(root.tag, nsmap=nsmap)
    for key, value in root.attrib.items():
        new_root.set(key, value)
    new_root.text = root.text
    new_root.tail = root.tail
    for child in list(root):
        new_root.append(child)
    return new_root


def ensure_xhtml_document_namespace(root: etree._Element) -> etree._Element:
    if not isinstance(root.tag, str) or etree.QName(root).localname != "html":
        return root
    for elem in root.iter():
        if not isinstance(elem.tag, str):
            continue
        qname = etree.QName(elem)
        if not qname.namespace:
            elem.tag = f"{{{XHTML_NS}}}{qname.localname}"
    return add_epub_namespace(root)


def sanitize_namespace_declarations(data: str) -> str:
    data = data.replace("clasＶs=", "class=")
    data = re.sub(
        r"""xmlns=(['"])https?://www\.w3\.org/[^'"]*xhtml\1""",
        'xmlns="%s"' % XHTML_NS,
        data,
        flags=re.IGNORECASE,
    )
    replacements = {
        'xmlns="https://www.w3.org/1999/xhtml"': 'xmlns="%s"' % XHTML_NS,
        'xmlns="http://www.w3.org/1999/xhtml/epub"': 'xmlns="%s"' % XHTML_NS,
        'xmlns="https://www.idpf.org/2007/opf"': 'xmlns="%s"' % OPF_NS,
        'xmlns="http://www.idpf.org/2007/opf/v3"': 'xmlns="%s"' % OPF_NS,
        'xmlns:dc="http://purl.org/dc/elements/1.0/"': 'xmlns:dc="%s"' % DC_NS,
    }
    for old, new in replacements.items():
        data = data.replace(old, new)
    data = re.sub(r"<？xml[^>]*>", "", data, flags=re.IGNORECASE)
    data = re.sub(r"""\s+xmlns:xmlns\s*=\s*(['"]).*?\1""", "", data)
    data = re.sub(r"""\s+xmlns:xml\s*=\s*(['"])(?!http://www\.w3\.org/XML/1998/namespace).*?\1""", "", data)

    def dedupe_xmlns(match: re.Match[str]) -> str:
        seen: set[str] = set()

        def keep_first(attr_match: re.Match[str]) -> str:
            name = attr_match.group(1)
            if name in seen:
                return ""
            seen.add(name)
            return attr_match.group(0)

        return re.sub(r"""\s+(xmlns(?::[A-Za-z_][\w.-]*)?)\s*=\s*(['"])[^'"]*\2""", keep_first, match.group(0))

    return re.sub(r"<(?![!?/])[^<>]+>", dedupe_xmlns, data)


def parse_xml_recovering(data: str) -> etree._Element:
    data = sanitize_namespace_declarations(data)
    data = re.sub(r"<([\u3400-\u9fff][^<>\s/]*)\s*/>", r"&lt;\1/&gt;", data)
    try:
        return etree.fromstring(data.encode("utf-8"), XML_PARSER)
    except etree.XMLSyntaxError:
        return etree.fromstring(data.encode("utf-8"), RECOVER_XML_PARSER)


def make_xml_id(candidate: str, used: set[str]) -> str:
    candidate = re.sub(r"[^A-Za-z0-9_.:-]", "_", candidate or "id")
    if not re.match(r"^[A-Za-z_]", candidate):
        candidate = "id_" + candidate
    value = candidate or "id"
    counter = 2
    while value in used:
        value = "%s_%d" % (candidate, counter)
        counter += 1
    used.add(value)
    return value


def append_style(elem: etree._Element, declaration: str) -> None:
    style = elem.get("style", "").strip()
    if style and not style.endswith(";"):
        style += ";"
    elem.set("style", (style + " " + declaration).strip())


def sanitize_style_value(value: str) -> str:
    parts: List[str] = []
    for decl in value.split(";"):
        decl = decl.strip()
        if not decl:
            continue
        if "url(" in decl and ")" not in decl:
            decl += ")"
        if ":" not in decl:
            continue
        prop, val = decl.split(":", 1)
        prop = prop.strip()
        if not re.fullmatch(r"-?[A-Za-z][A-Za-z0-9_-]*", prop):
            continue
        val = val.strip()
        if not val:
            continue
        if re.search(r"url\(\s*(['\"]?)(?:https?://|file:|res:/)[^)]+\)", val, flags=re.IGNORECASE):
            continue
        parts.append("%s: %s" % (prop, val))
    return "; ".join(parts)


def normalize_language_tag(value: str) -> str:
    value = (value or "").strip().replace("—", "-").replace("–", "-").replace("－", "-")
    if not value:
        return "zh-Hant"
    if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", value):
        parts = value.split("-")
        return "-".join([parts[0].lower(), *parts[1:]])
    return "zh-Hant"


def legacy_length_to_css(value: str) -> Optional[str]:
    value = value.strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return "%spx" % value
    if re.fullmatch(r"\d+(?:\.\d+)?(?:%|px|em|rem|pt|pc|cm|mm|in|ex|ch|vw|vh|vmin|vmax)", value):
        return value
    if value.lower() == "auto":
        return "auto"
    return None


def fix_package_relative_href(value: str, book_href: str) -> str:
    if not value:
        return value
    base, frag = split_href(value)
    parts = urlsplit(base)
    if parts.scheme or parts.netloc or base.startswith("data:") or not base:
        return value
    doc_dir = posixpath.dirname(book_href) or "."
    if doc_dir == ".":
        return value
    first_segment = book_href.split("/", 1)[0]
    if first_segment and base.startswith(first_segment + "/") and not base.startswith(doc_dir + "/"):
        return posixpath.relpath(posixpath.normpath(base), start=doc_dir) + frag
    return value


def normalize_element_ids(root: etree._Element) -> None:
    seen: set[str] = set()
    for elem in root.iter():
        if not isinstance(elem.tag, str):
            continue
        value = elem.get("id")
        if value is not None and not value.strip():
            elem.attrib.pop("id", None)
            continue
        if not value:
            continue
        if XML_ID_RE.match(value) and value not in seen:
            seen.add(value)
        else:
            elem.set("id", make_xml_id(value, seen))


def wrap_body_bare_text(root: etree._Element) -> None:
    for body in root.xpath("//*[local-name()='body']"):
        children = [child for child in body if isinstance(child.tag, str)]
        if body.text and body.text.strip():
            p = body.makeelement(f"{{{XHTML_NS}}}p")
            p.text = body.text.strip()
            body.text = "\n  "
            p.tail = "\n  " if children else "\n"
            body.insert(0, p)
            children.insert(0, p)
        for child in list(children):
            if child.tail and child.tail.strip():
                p = body.makeelement(f"{{{XHTML_NS}}}p")
                p.text = child.tail.strip()
                child.tail = "\n  "
                p.tail = "\n  "
                body.insert(body.index(child) + 1, p)


def normalize_definition_lists(root: etree._Element) -> None:
    for dl in root.xpath(".//*[local-name()='dl']"):
        if dl.text and dl.text.strip():
            dd = dl.makeelement(f"{{{XHTML_NS}}}dd")
            dd.text = dl.text.strip()
            dl.text = "\n  "
            dd.tail = "\n  "
            dl.insert(0, dd)
        for child in list(dl):
            if not isinstance(child.tag, str):
                continue
            qname = etree.QName(child)
            local = qname.localname
            if qname.namespace == XHTML_NS and local not in {"dt", "dd"}:
                child.tag = f"{{{XHTML_NS}}}dd"
                local = "dd"
            if qname.namespace == XHTML_NS and local == "dd":
                previous_terms = [
                    sibling for sibling in child.itersiblings(preceding=True)
                    if isinstance(sibling.tag, str) and etree.QName(sibling).localname == "dt"
                ]
                if not previous_terms:
                    child.tag = f"{{{XHTML_NS}}}div"
            if child.tail and child.tail.strip():
                dd = dl.makeelement(f"{{{XHTML_NS}}}dd")
                dd.text = child.tail.strip()
                child.tail = "\n  "
                dd.tail = "\n  "
                dl.insert(dl.index(child) + 1, dd)
        seen_dt = False
        for child in list(dl):
            if not isinstance(child.tag, str) or etree.QName(child).namespace != XHTML_NS:
                continue
            local = etree.QName(child).localname
            if local == "dt":
                seen_dt = True
            elif local == "dd" and not seen_dt:
                child.tag = f"{{{XHTML_NS}}}div"
        if any(
            isinstance(child.tag, str) and etree.QName(child).localname not in {"dt", "dd"}
            for child in dl
        ):
            dl.tag = f"{{{XHTML_NS}}}div"
            for child in dl:
                if isinstance(child.tag, str) and etree.QName(child).localname in {"dt", "dd"}:
                    child.tag = f"{{{XHTML_NS}}}div"


def normalize_ruby_fallbacks(root: etree._Element) -> None:
    def flatten_ruby(ruby: etree._Element) -> None:
        ruby.tag = f"{{{XHTML_NS}}}span"
        for child in ruby.xpath(".//*[local-name()='rp' or local-name()='rt']"):
            parent = child.getparent()
            if parent is not None:
                if child.tail:
                    previous = child.getprevious()
                    if previous is not None:
                        previous.tail = (previous.tail or "") + child.tail
                    else:
                        parent.text = (parent.text or "") + child.tail
                parent.remove(child)

    for ruby in root.xpath(".//*[local-name()='ruby']"):
        if any(
            isinstance(child.tag, str) and etree.QName(child).localname == "rt" and not "".join(child.itertext()).strip()
            for child in ruby
        ) or any(
            isinstance(child.tag, str) and etree.QName(child).localname == "rt" and child.tail and child.tail.strip()
            for child in ruby
        ):
            flatten_ruby(ruby)
            continue
        for child in list(ruby):
            if not isinstance(child.tag, str) or etree.QName(child).localname != "rt":
                continue
            index = ruby.index(child)
            before = ruby[index - 1] if index > 0 else None
            if before is None or not isinstance(before.tag, str) or etree.QName(before).localname != "rp":
                rp_open = ruby.makeelement(f"{{{XHTML_NS}}}rp")
                rp_open.text = "("
                ruby.insert(index, rp_open)
                index += 1
            after = ruby[index + 1] if index + 1 < len(ruby) else None
            if after is None or not isinstance(after.tag, str) or etree.QName(after).localname != "rp":
                rp_close = ruby.makeelement(f"{{{XHTML_NS}}}rp")
                rp_close.text = ")"
                ruby.insert(index + 1, rp_close)


def normalize_head_text(root: etree._Element) -> None:
    allowed = {"base", "link", "meta", "script", "style", "template", "title"}
    for head in root.xpath(".//*[local-name()='head']"):
        if head.text:
            head.text = "\n"
        for child in list(head):
            child_local = etree.QName(child).localname if isinstance(child.tag, str) else ""
            if child_local == "span" and not head.xpath("./*[local-name()='title']") and "".join(child.itertext()).strip():
                child.tag = f"{{{XHTML_NS}}}title"
                child.attrib.clear()
                child.text = "".join(child.itertext()).strip()
                child[:] = []
                child.tail = "\n"
                continue
            if isinstance(child.tag, str) and child_local not in allowed:
                if child.tail:
                    previous = child.getprevious()
                    if previous is not None:
                        previous.tail = (previous.tail or "") + child.tail
                head.remove(child)
                continue
            if child.tail:
                child.tail = "\n"


def normalize_head_meta_children(root: etree._Element) -> None:
    for head in root.xpath(".//*[local-name()='head']"):
        for meta in list(head.xpath("./*[local-name()='meta']")):
            insert_at = head.index(meta) + 1
            for child in list(meta):
                meta.remove(child)
                child.tail = "\n"
                head.insert(insert_at, child)
                insert_at += 1
            meta.text = None


def normalize_html_root_structure(root: etree._Element) -> None:
    if not isinstance(root.tag, str) or etree.QName(root).localname != "html":
        return
    head = next((child for child in root if isinstance(child.tag, str) and etree.QName(child).localname == "head"), None)
    body = next((child for child in root if isinstance(child.tag, str) and etree.QName(child).localname == "body"), None)
    if body is None:
        body = root.makeelement(f"{{{XHTML_NS}}}body")
        if head is not None:
            root.insert(root.index(head) + 1, body)
        else:
            root.append(body)
    for child in list(root):
        if not isinstance(child.tag, str):
            continue
        local = etree.QName(child).localname
        if local in {"head", "body"}:
            continue
        root.remove(child)
        body.append(child)
    if body.tail and body.tail.strip():
        p = body.makeelement(f"{{{XHTML_NS}}}p")
        p.text = body.tail.strip()
        body.tail = "\n"
        body.append(p)


def normalize_list_structures(root: etree._Element) -> None:
    for list_elem in root.xpath(".//*[local-name()='ul' or local-name()='ol' or local-name()='menu']"):
        if list_elem.text and list_elem.text.strip():
            li = list_elem.makeelement(f"{{{XHTML_NS}}}li")
            li.text = list_elem.text.strip()
            list_elem.text = "\n  "
            li.tail = "\n  "
            list_elem.insert(0, li)
        for child in list(list_elem):
            if not isinstance(child.tag, str):
                continue
            qname = etree.QName(child)
            if qname.namespace == XHTML_NS and qname.localname not in {"li", "script", "template"}:
                child.tag = f"{{{XHTML_NS}}}li"
            if child.tail and child.tail.strip():
                li = list_elem.makeelement(f"{{{XHTML_NS}}}li")
                li.text = child.tail.strip()
                child.tail = "\n  "
                li.tail = "\n  "
                list_elem.insert(list_elem.index(child) + 1, li)


def normalize_table_structures(root: etree._Element) -> None:
    allowed_table_children = {"caption", "colgroup", "script", "tbody", "template", "tfoot", "thead", "tr"}
    for table in root.xpath(".//*[local-name()='table']"):
        for child in list(table):
            if not isinstance(child.tag, str):
                continue
            qname = etree.QName(child)
            if qname.namespace == XHTML_NS and qname.localname == "span" and not "".join(child.itertext()).strip() and len(child) == 0:
                if child.tail and child.tail.strip():
                    previous = child.getprevious()
                    if previous is not None:
                        previous.tail = (previous.tail or "") + child.tail
                    else:
                        table.text = (table.text or "") + child.tail
                table.remove(child)
        direct_children = [child for child in table if isinstance(child.tag, str)]
        if any(
            etree.QName(child).namespace == XHTML_NS and etree.QName(child).localname not in allowed_table_children | {"col"}
            for child in direct_children
        ):
            table.tag = f"{{{XHTML_NS}}}div"
            continue
        current_colgroup: Optional[etree._Element] = None
        for child in list(table):
            if not isinstance(child.tag, str) or etree.QName(child).namespace != XHTML_NS:
                continue
            local = etree.QName(child).localname
            if local == "col":
                if current_colgroup is None or current_colgroup.getparent() is not table:
                    current_colgroup = table.makeelement(f"{{{XHTML_NS}}}colgroup")
                    table.insert(table.index(child), current_colgroup)
                table.remove(child)
                current_colgroup.append(child)
            elif local != "colgroup":
                current_colgroup = None


def normalize_epubcheck_xhtml(root: etree._Element, book_href: str = "") -> None:
    normalize_element_ids(root)
    normalize_html_root_structure(root)
    normalize_head_meta_children(root)
    normalize_head_text(root)
    wrap_body_bare_text(root)
    normalize_definition_lists(root)
    normalize_list_structures(root)
    normalize_ruby_fallbacks(root)
    normalize_table_structures(root)
    for elem in list(root.iter()):
        if not isinstance(elem.tag, str):
            continue
        qname = etree.QName(elem)
        local = qname.localname
        namespace = qname.namespace
        renamed_from_fake_tag = False
        if local.lower() in {"switch", "case", "default", "defaultcase"}:
            elem.tag = f"{{{XHTML_NS}}}div"
            local = "div"
            namespace = XHTML_NS
            renamed_from_fake_tag = True
        elif namespace == XHTML_NS:
            normalized_local = XHTML_TAG_RENAMES.get(local.lower(), local.lower())
            if normalized_local == local and local.lower().startswith("title_"):
                normalized_local = "div"
            if normalized_local == local and re.fullmatch(r"[a-z]_{2,}", local.lower()):
                normalized_local = "span"
            if normalized_local != local:
                elem.tag = f"{{{XHTML_NS}}}{normalized_local}"
                local = normalized_local
                renamed_from_fake_tag = True

        if namespace == XHTML_NS and local == "html":
            lang = elem.get("{http://www.w3.org/XML/1998/namespace}lang") or elem.get("lang")
            lang = normalize_language_tag(lang)
            if lang:
                elem.set("lang", lang)
                elem.set("{http://www.w3.org/XML/1998/namespace}lang", lang)

        if namespace == XHTML_NS and local == "script":
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
            continue

        if namespace == XHTML_NS and local == "base":
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
            continue

        parent = elem.getparent()
        parent_local = etree.QName(parent).localname if parent is not None and isinstance(parent.tag, str) else ""
        if namespace == XHTML_NS and local in {"form", "button", "input", "select", "textarea"}:
            if parent is not None:
                if elem.tail:
                    previous = elem.getprevious()
                    if previous is not None:
                        previous.tail = (previous.tail or "") + elem.tail
                    else:
                        parent.text = (parent.text or "") + elem.tail
                parent.remove(elem)
            continue
        if namespace == XHTML_NS and local == "source" and (parent_local not in {"audio", "picture", "video"} or not elem.get("src")):
            if parent is not None:
                parent.remove(elem)
            continue
        if namespace == XHTML_NS and local == "iframe":
            src_base = split_href(elem.get("src", ""))[0] if elem.get("src") else ""
            src_parts = urlsplit(src_base)
            if src_parts.scheme or src_parts.netloc or not src_base:
                if parent is not None:
                    parent.remove(elem)
                continue
        if local == "span" and parent_local in {"table", "tbody", "thead", "tfoot", "tr"}:
            if not (elem.text or "").strip() and len(elem) == 0:
                if elem.tail and elem.tail.strip():
                    previous = elem.getprevious()
                    if previous is not None:
                        previous.tail = (previous.tail or "") + elem.tail
                    elif parent is not None:
                        parent.text = (parent.text or "") + elem.tail
                if parent is not None:
                    parent.remove(elem)
                continue

        if namespace == XHTML_NS and parent_local != "head" and local in {"meta", "style"}:
            if elem.tail:
                elem.tail = (elem.text or "") + elem.tail
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
            continue

        if namespace == XHTML_NS and parent_local == "head" and local == "style" and elem.text:
            elem.text = sanitize_css(elem.text)

        if namespace == XHTML_NS and parent_local != "head" and local == "title":
            elem.tag = f"{{{XHTML_NS}}}span"
            local = "span"

        if namespace == XHTML_NS and local == "br" and elem.text:
            elem.tail = (elem.text or "") + (elem.tail or "")
            elem.text = None

        if namespace == XHTML_NS and local == "img" and not elem.get("src"):
            haystack = " ".join(part for part in (elem.text, elem.tail) if part)
            match = re.search(r"([A-Za-z0-9_./%:-]+\.(?:jpe?g|png|gif|webp|svg))", haystack, flags=re.IGNORECASE)
            if match:
                elem.set("src", match.group(1))
                if elem.tail:
                    elem.tail = elem.tail.replace(match.group(0), "").replace("/>", "").replace("/&gt;", "")
            else:
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)
                continue

        if local == "meta":
            http_equiv = elem.get("http-equiv")
            if http_equiv and http_equiv.lower() not in HTML5_HTTP_EQUIV:
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)
                continue
            name = elem.get("name", "").lower()
            if http_equiv and http_equiv.lower() == "content-type" and not elem.get("content"):
                elem.attrib.clear()
                elem.set("charset", "utf-8")
            elif name == "viewport" and not elem.get("content"):
                content = elem.attrib.pop("content", "") or elem.attrib.pop("value", "") or elem.attrib.pop("width", "")
                if content:
                    elem.set("content", content if re.match(r"\s*[\w-]+\s*=", content) else "width=%s" % content)
            if not any(elem.get(attr) for attr in ("charset", "http-equiv", "name")):
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)
                continue
            if (elem.get("http-equiv") or elem.get("name")) and not elem.get("content"):
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

        if namespace == XHTML_NS and local == "strike":
            elem.tag = f"{{{XHTML_NS}}}s"
            local = "s"

        if namespace == XHTML_NS and local == "hr":
            size = elem.attrib.pop("size", "")
            css_size = legacy_length_to_css(size) if size else None
            if css_size:
                append_style(elem, "height: %s" % css_size)
                append_style(elem, "border: none")
                append_style(elem, "background-color: black")
            if parent_local in PHRASING_PARENT_ELEMENTS:
                elem.tag = f"{{{XHTML_NS}}}span"
                append_style(elem, "display: block")
                append_style(elem, "border-top: 1px solid black")
                local = "span"

        if namespace == XHTML_NS and local in {"col", "colgroup"}:
            if (local == "col" and parent_local != "colgroup") or (local == "colgroup" and parent_local != "table"):
                if parent is not None:
                    if elem.tail:
                        previous = elem.getprevious()
                        if previous is not None:
                            previous.tail = (previous.tail or "") + elem.tail
                        else:
                            parent.text = (parent.text or "") + elem.tail
                    parent.remove(elem)
                continue

        if namespace == XHTML_NS and local in {"tbody", "thead", "tfoot", "tr", "td", "th"}:
            valid_parent = {
                "tbody": {"table"},
                "thead": {"table"},
                "tfoot": {"table"},
                "tr": {"table", "tbody", "thead", "tfoot"},
                "td": {"tr"},
                "th": {"tr"},
            }
            if parent_local not in valid_parent.get(local, set()):
                elem.tag = f"{{{XHTML_NS}}}{'span' if parent_local in PHRASING_PARENT_ELEMENTS else 'div'}"
                local = etree.QName(elem).localname

        if parent is not None and namespace == XHTML_NS and local in BLOCK_TO_INLINE_ELEMENTS:
            if parent_local == "p":
                parent.tag = f"{{{XHTML_NS}}}div"
            elif parent_local in PHRASING_PARENT_ELEMENTS or parent_local == "pre":
                elem.tag = f"{{{XHTML_NS}}}span"
                local = "span"
            elif local == "li" and parent_local not in LIST_CONTAINER_ELEMENTS:
                elem.tag = f"{{{XHTML_NS}}}p"
                local = "p"

        if namespace == XHTML_NS and local == "img" and Path(unquote(split_href(elem.get("src", ""))[0])).suffix.lower() in FOREIGN_IMAGE_SUFFIXES:
            parent = elem.getparent()
            if parent is not None:
                if elem.tail:
                    previous = elem.getprevious()
                    if previous is not None:
                        previous.tail = (previous.tail or "") + elem.tail
                    else:
                        parent.text = (parent.text or "") + elem.tail
                parent.remove(elem)
            continue

        if namespace == XHTML_NS and local == "a":
            has_ancestor_anchor = any(
                isinstance(ancestor.tag, str) and etree.QName(ancestor).namespace == XHTML_NS and etree.QName(ancestor).localname == "a"
                for ancestor in elem.iterancestors()
            )
            href_base = split_href(elem.get("href", ""))[0] if elem.get("href") else ""
            if has_ancestor_anchor or not elem.get("href") or resource_kind(href_base) == "image":
                elem.attrib.pop("href", None)
                elem.tag = f"{{{XHTML_NS}}}span"
                local = "span"

        for attr in list(elem.attrib):
            attr_local = etree.QName(attr).localname if attr.startswith("{") else attr
            attr_lower = attr_local.lower()
            if attr_lower.startswith("data-amznremoved"):
                del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower.startswith("v-"):
                del elem.attrib[attr]
            elif renamed_from_fake_tag and namespace == XHTML_NS and attr_lower not in SAFE_RENAMED_TAG_ATTRS:
                del elem.attrib[attr]
            elif attr_lower.startswith("on"):
                del elem.attrib[attr]
            elif attr_lower.startswith("zy-") or attr_lower == "_" or (
                attr_lower == "value" and local not in {"button", "data", "input", "meter", "option", "progress"}
            ):
                del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower == "a":
                del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower == "summary":
                del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower == "cite":
                del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower == "body":
                del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower in {"times", "new", "roman", "serif", "tooltip"}:
                del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower == "download":
                del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower in {"colspan", "rowspan"} and local not in {"td", "th"}:
                del elem.attrib[attr]
            elif attr_lower == "gallery":
                del elem.attrib[attr]
            elif attr_lower == "required-namespace":
                del elem.attrib[attr]
            elif namespace == XHTML_NS and "_" in attr_lower:
                del elem.attrib[attr]
            elif attr_lower in {"activestate", "bgcolor", "border", "cellpadding", "cellspacing", "cid", "clear", "frame", "frameborder", "marginheight", "marginwidth", "page-progression-direction", "rules", "toc", "valign"}:
                del elem.attrib[attr]
            elif attr_lower == "placeholder" and local not in {"input", "textarea"}:
                del elem.attrib[attr]
            elif attr_lower == "target":
                del elem.attrib[attr]
            elif attr_lower == "style":
                style = sanitize_style_value(elem.attrib[attr])
                if style:
                    elem.attrib[attr] = style
                else:
                    del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower == "name" and local not in HTML5_NAME_ELEMENTS:
                del elem.attrib[attr]
            elif attr_lower in {"lang", "xml:lang"} and not elem.attrib[attr].strip():
                del elem.attrib[attr]
            elif not attr.startswith("{") and namespace == XHTML_NS and attr_lower == "type" and local not in {"button", "embed", "input", "link", "object", "script", "source", "style", "track"}:
                del elem.attrib[attr]
            elif attr_lower == "align":
                value = elem.attrib.pop(attr, "").lower()
                if namespace == XHTML_NS and local == "hr" and value == "center":
                    append_style(elem, "margin: 0 auto")
                elif value in {"left", "right", "center", "justify"}:
                    append_style(elem, "text-align: %s" % value)
            elif attr_lower == "size":
                del elem.attrib[attr]
            elif namespace == XHTML_NS and attr_lower in {"height", "width"}:
                value = elem.attrib[attr].strip()
                if local in HTML5_DIMENSION_ELEMENTS and re.fullmatch(r"\d+", value):
                    continue
                css_value = legacy_length_to_css(elem.attrib.pop(attr, ""))
                if css_value:
                    append_style(elem, "%s: %s" % (attr_lower, css_value))
            elif attr_lower in {"href", "src"}:
                base, _frag = split_href(elem.attrib[attr])
                if re.fullmatch(r"X{8,}", base):
                    del elem.attrib[attr]
                    continue
                elem.attrib[attr] = encode_local_href(fix_package_relative_href(elem.attrib[attr], book_href))

        if namespace == XHTML_NS and local == "link":
            link_type = elem.get("type", "")
            if link_type == "application/vnd.adobe-page-template+xml":
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)


def collect_doc_features(root: etree._Element, book_href: str) -> Tuple[str, List[str], List[str], List[Tuple[str, str, str]]]:
    ns = {"x": XHTML_NS, "epub": EPUB_NS}
    root = ensure_xhtml_document_namespace(root)

    normalize_epubcheck_xhtml(root, book_href)

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
    ).decode("utf-8")
    output = re.sub(r"</br\s*>", "<br/>", output, flags=re.IGNORECASE)
    output = re.sub(r"<br([^>/]*?)>", r"<br\1/>", output, flags=re.IGNORECASE)
    return output, manifest_properties, spine_properties, epub_types


def convert_xhtml_file(src_path: Path, book_href: str) -> Tuple[str, List[str], List[str], List[Tuple[str, str, str]]]:
    raw = convert_named_entities(read_text_file(src_path))
    root = parse_xml_recovering(raw)
    return collect_doc_features(root, book_href)


def normalize_all_xhtml_files(root_dir: Path) -> None:
    for path in root_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".htm", ".xhtml"}:
            continue
        rel = path.relative_to(root_dir).as_posix()
        try:
            data, _mprops, _sprops, _etypes = convert_xhtml_file(path, rel)
        except Exception:
            continue
        write_text_file(path, data)


def parse_ncx_file(src_path: Path, ncx_href: str) -> Tuple[Optional[str], List[TocNode], List[Tuple[str, str]]]:
    raw = convert_named_entities(read_text_file(src_path))
    root = parse_xml_recovering(raw)
    if root is None:
        return None, [], []
    ns = {"n": NCX_NS}

    for elem in root.iter():
        if not isinstance(elem.tag, str):
            continue
        local = etree.QName(elem).localname
        if local in {"doctitle", "docauthor", "navmap", "navpoint", "navlabel", "pagelist", "pagetarget", "playorder"}:
            pass

    doc_title_el = root.find(".//n:docTitle/n:text", namespaces=ns)
    doctitle = doc_title_el.text if doc_title_el is not None else None
    ncx_dir = posixpath.dirname(ncx_href) or "."

    def ncx_target_to_book_href(value: str) -> str:
        base, frag = split_href(value)
        parts = urlsplit(base)
        if parts.scheme or parts.netloc or not base:
            return value
        first_segment = ncx_href.split("/", 1)[0]
        if first_segment and base.startswith(first_segment + "/"):
            return posixpath.normpath(base) + frag
        return posixpath.normpath(posixpath.join(ncx_dir, base)) + frag

    def parse_navpoint(navpoint: etree._Element) -> TocNode:
        label = navpoint.findtext("n:navLabel/n:text", default="", namespaces=ns) or ""
        content = navpoint.find("n:content", namespaces=ns)
        href = ncx_target_to_book_href(content.get("src", "")) if content is not None else ""
        children = [parse_navpoint(child) for child in navpoint.findall("n:navPoint", namespaces=ns)]
        return TocNode(label=label, href=href, children=children)

    toc_nodes = [parse_navpoint(node) for node in root.findall(".//n:navMap/n:navPoint", namespaces=ns)]

    pagelist: List[Tuple[str, str]] = []
    current_page = None
    for elem in root.iter():
        if not isinstance(elem.tag, str):
            continue
        local = etree.QName(elem).localname
        if local == "pageTarget" and elem.get("value"):
            current_page = elem.get("value")
        elif local == "content" and current_page is not None and elem.get("src"):
            pagelist.append((current_page, ncx_target_to_book_href(elem.get("src"))))
            current_page = None

    uid_meta = root.xpath(".//*[local-name()='meta' and @name='dtb:uid']")
    uid = uid_meta[0].get("content", "") if uid_meta else ""
    write_ncx_file(src_path, ncx_href, doctitle, toc_nodes, uid)
    return doctitle, toc_nodes, pagelist


def write_ncx_file(src_path: Path, ncx_href: str, doctitle: Optional[str], toc_nodes: List[TocNode], uid: str = "") -> None:
    ncx_dir = posixpath.dirname(ncx_href) or "."
    out_root = etree.Element(f"{{{NCX_NS}}}ncx", nsmap={None: NCX_NS}, version="2005-1")
    head = etree.SubElement(out_root, f"{{{NCX_NS}}}head")
    etree.SubElement(head, f"{{{NCX_NS}}}meta", name="dtb:uid", content=uid)
    doc_title = etree.SubElement(out_root, f"{{{NCX_NS}}}docTitle")
    etree.SubElement(doc_title, f"{{{NCX_NS}}}text").text = doctitle or "Untitled"
    nav_map = etree.SubElement(out_root, f"{{{NCX_NS}}}navMap")
    counter = 1
    seen_targets: set[str] = set()

    def add_node(parent: etree._Element, node: TocNode) -> None:
        nonlocal counter
        if strip_fragment(node.href) in seen_targets:
            for child in node.children:
                add_node(parent, child)
            return
        seen_targets.add(strip_fragment(node.href))
        nav_point = etree.SubElement(parent, f"{{{NCX_NS}}}navPoint", id="navPoint-%d" % counter, playOrder=str(counter))
        counter += 1
        nav_label = etree.SubElement(nav_point, f"{{{NCX_NS}}}navLabel")
        etree.SubElement(nav_label, f"{{{NCX_NS}}}text").text = node.label.strip() or posixpath.basename(strip_fragment(node.href)) or "Untitled"
        base, _frag = split_href(node.href)
        src = posixpath.relpath(base, start=ncx_dir) if ncx_dir != "." else base
        etree.SubElement(nav_point, f"{{{NCX_NS}}}content", src=src)
        for child in node.children:
            add_node(nav_point, child)

    for node in toc_nodes:
        add_node(nav_map, node)

    write_text_file(src_path, etree.tostring(out_root, encoding="utf-8", xml_declaration=True, pretty_print=True).decode("utf-8"))


def sync_ncx_uid(src_path: Path, uid: str) -> None:
    if not uid or not src_path.exists():
        return
    raw = convert_named_entities(read_text_file(src_path))
    root = parse_xml_recovering(raw)
    ns = {"n": NCX_NS}
    meta = root.find(".//n:meta[@name='dtb:uid']", namespaces=ns)
    if meta is None:
        found = root.xpath(".//*[local-name()='meta' and @name='dtb:uid']")
        meta = found[0] if found else None
    if meta is None:
        head = root.find(".//n:head", namespaces=ns)
        if head is None:
            found_head = root.xpath(".//*[local-name()='head']")
            head = found_head[0] if found_head else None
        if head is None:
            head = etree.Element(f"{{{NCX_NS}}}head")
            root.insert(0, head)
        meta = etree.SubElement(head, f"{{{NCX_NS}}}meta", name="dtb:uid")
    if meta.get("content") == uid:
        return
    meta.set("content", uid)
    write_text_file(
        src_path,
        etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=False).decode("utf-8"),
    )


def opf_unique_identifier_value(src_path: Path) -> str:
    if not src_path.exists():
        return ""
    try:
        root = parse_xml_recovering(read_text_file(src_path))
    except Exception:
        return ""
    unique_id = root.get("unique-identifier", "")
    if not unique_id:
        return ""
    found = root.xpath(".//*[local-name()='identifier' and @id=$id]", id=unique_id)
    if not found:
        return ""
    return (found[0].text or "").strip()


def normalize_ncx_play_order(src_path: Path) -> None:
    if not src_path.exists():
        return
    raw = convert_named_entities(read_text_file(src_path))
    root = parse_xml_recovering(raw)
    if root is None:
        return
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
    data = "".join(ch for ch in data if ch in "\t\r\n" or ord(ch) >= 0x20)
    data = data.replace("％", "%")
    data = data.replace("：", ":")
    data = re.sub(r"(?im)^\s*@namespace\b[^\n]*(?:\n|$)", "", data)
    data = re.sub(r"/\*.*?\*/", "", data, flags=re.DOTALL)
    data = re.sub(r"(?m)^.*(?:/\*|\*/).*$", "", data)
    data = re.sub(r"//[^\n}]*}", "}", data)
    data = re.sub(r"(?m)(?<!:)//.*$", "", data)
    data = re.sub(r"\\\s*(?=[;}])", "", data)
    data = re.sub(r":\s*([^;{}]+);\s*!important", r": \1 !important", data, flags=re.IGNORECASE)
    data = re.sub(r";{2,}", ";", data)
    previous = None
    while previous != data:
        previous = data
        data = re.sub(r"(?im)(font-family\s*:\s*[^;\n{}]+);(?=\s*[^:\n{};]+;)", r"\1,", data)
    data = re.sub(r"(?i)(?<=[{;])\s*direction\s*:\s*[^;{}]+;?", "", data)
    data = re.sub(r"(?<=[{;])\s*\*([-\w]+\s*:)", r"\1", data)
    data = re.sub(r"(?s)(^|})\s*(?:[-\w]+\s*:\s*[^;{}]+;\s*)+\}\s*", r"\1", data)
    if "{" not in data:
        data = re.sub(r"(?m)^\s*}\s*$", "", data)
    elif data.count("{") > data.count("}"):
        data = data.rstrip() + "\n" + ("}" * (data.count("{") - data.count("}"))) + "\n"
    data = re.sub(r"(?m)^(\s*[-\w]+)\s*=\s*([^;{}]+);", r"\1: \2;", data)
    data = re.sub(r"(?m)([{\s;])([-\w]+)-(#(?:[0-9a-fA-F]{3,8})\s*;)", r"\1\2: \3", data)
    data = re.sub(r"(?m)^\s*[-\w]+\s*:\s*;", "", data)
    data = re.sub(r"(?im)^\s*[-\w]+\s*:\s*url\(\s*(['\"]?)data:[^\n)]*$", "", data)
    data = re.sub(r"url\(\s*(['\"]?)https?://[^)'\"]+\1\s*\)", "none", data, flags=re.IGNORECASE)
    data = re.sub(
        r"@font-face\s*\{.*?\}",
        "",
        data,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if "{" not in data:
        data = re.sub(r"(?m)^\s*}\s*$", "", data)
    data = re.sub(r"url\(\s*(['\"]?)(?:file:|res:/)[^)]+\)", "none", data, flags=re.IGNORECASE)
    data = re.sub(r"(^|\})\s*([^{}\n]+?)\s+\d+\s*\{", lambda m: "%s\n%s {" % (m.group(1), m.group(2).strip()), data)
    data = re.sub(r"(?m)(;\s*\n)(\s*[.#A-Za-z][^{}\n]+\{)", r"\1}\n\2", data)
    balanced: List[str] = []
    depth = 0
    for ch in data:
        if ch == "{":
            depth += 1
            balanced.append(ch)
        elif ch == "}":
            if depth == 0:
                continue
            depth -= 1
            balanced.append(ch)
        else:
            balanced.append(ch)
    data = "".join(balanced)
    if depth > 0:
        data = data.rstrip() + "\n" + ("}" * depth) + "\n"
    return data


def sanitize_all_css_files(root_dir: Path) -> None:
    for path in root_dir.rglob("*.css"):
        if path.is_file():
            write_text_file(path, sanitize_css(read_text_file(path)))


def resource_kind(path: str) -> str:
    suffix = Path(unquote(strip_fragment(path))).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff"}:
        return "image"
    if suffix == ".css":
        return "css"
    if suffix == ".js":
        return "script"
    if suffix in {".html", ".htm", ".xhtml"}:
        return "xhtml"
    return suffix.lstrip(".")


def build_resource_candidates(root_dir: Path) -> List[str]:
    return [path.relative_to(root_dir).as_posix() for path in root_dir.rglob("*") if path.is_file()]


def find_replacement_resource(requested: str, candidates: List[str]) -> Optional[str]:
    requested_base = unquote(strip_fragment(requested)).replace("\\", "/")
    requested_name = posixpath.basename(requested_base).lower()
    requested_stem = Path(requested_name).stem.lower()
    requested_suffix = Path(requested_name).suffix.lower()
    requested_kind = resource_kind(requested_base)
    if not requested_name or not requested_stem:
        return None

    ranked: List[Tuple[int, int, str]] = []
    for candidate in candidates:
        candidate_name = posixpath.basename(candidate).lower()
        candidate_stem = Path(candidate_name).stem.lower()
        candidate_suffix = Path(candidate_name).suffix.lower()
        candidate_kind = resource_kind(candidate)
        rank: Optional[int] = None
        if candidate_name == requested_name:
            rank = 0
        elif candidate_stem == requested_stem and candidate_kind == requested_kind:
            rank = 10
        elif candidate_stem == requested_stem and requested_suffix and candidate_suffix:
            rank = 20
        elif requested_stem in {"cover", "cov"} and candidate_stem in {"cover", "cov"} and candidate_kind == requested_kind:
            rank = 30
        if rank is not None:
            ranked.append((rank, len(candidate), candidate))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][2]


def relative_href(from_doc: str, target: str) -> str:
    doc_dir = posixpath.dirname(from_doc) or "."
    rel = posixpath.relpath(target, start=doc_dir)
    if rel == ".":
        rel = posixpath.basename(target)
    return quote(rel, safe="/%:@!$&'()*+,;=-._~")


def fix_case_mismatched_local_hrefs(root_dir: Path) -> None:
    actual_paths = {
        path.relative_to(root_dir).as_posix().lower(): path.relative_to(root_dir).as_posix()
        for path in root_dir.rglob("*")
        if path.is_file()
    }
    text_suffixes = {".css", ".html", ".htm", ".ncx", ".opf", ".xhtml", ".xml"}

    def rewrite(value: str, doc_rel: str) -> str:
        base, frag = split_href(value)
        parts = urlsplit(base)
        if parts.scheme or parts.netloc or base.startswith("data:") or not base:
            return value
        doc_dir = posixpath.dirname(doc_rel) or "."
        target = posixpath.normpath(posixpath.join(doc_dir, unquote(base)))
        actual = actual_paths.get(target.lower())
        if not actual or actual == target:
            return value
        rel = posixpath.relpath(actual, start=doc_dir)
        if rel == ".":
            rel = posixpath.basename(actual)
        return quote(rel, safe="/%:@!$&'()*+,;=-._~") + frag

    def attr_repl(match: re.Match[str]) -> str:
        attr, value = match.group(1), match.group(2)
        return '%s="%s"' % (attr, html.escape(rewrite(value, current_rel), quote=True))

    def css_repl(match: re.Match[str]) -> str:
        quote_char = match.group(1) or ""
        value = match.group(2)
        return "url(%s%s%s)" % (quote_char, rewrite(value, current_rel), quote_char)

    for path in root_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        current_rel = path.relative_to(root_dir).as_posix()
        data = read_text_file(path)
        updated = re.sub(r'\b(href|src)="([^"]+)"', attr_repl, data)
        updated = re.sub(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", css_repl, updated)
        if updated != data:
            write_text_file(path, updated)


def repair_missing_xhtml_references(root_dir: Path) -> None:
    actual_paths = {
        path.relative_to(root_dir).as_posix().lower(): path.relative_to(root_dir).as_posix()
        for path in root_dir.rglob("*")
        if path.is_file()
    }
    candidates = build_resource_candidates(root_dir)
    id_cache: Dict[str, set[str]] = {}

    def target_for(value: str, doc_rel: str) -> Tuple[str, str, Optional[str]]:
        base, frag = split_href(value)
        parts = urlsplit(base)
        if parts.scheme or parts.netloc or base.startswith("data:") or not base:
            return base, frag, None
        doc_dir = posixpath.dirname(doc_rel) or "."
        target = posixpath.normpath(posixpath.join(doc_dir, unquote(base)))
        actual = actual_paths.get(target.lower())
        return target, frag, actual

    def replacement_href(value: str, doc_rel: str) -> Optional[str]:
        base, frag = split_href(value)
        replacement = find_replacement_resource(base, candidates)
        if not replacement:
            return None
        return relative_href(doc_rel, replacement) + frag

    def ids_for(rel: str) -> set[str]:
        if rel in id_cache:
            return id_cache[rel]
        ids: set[str] = set()
        path = root_dir / Path(rel)
        try:
            root = parse_xml_recovering(read_text_file(path))
            for elem in root.iter():
                if isinstance(elem.tag, str) and elem.get("id"):
                    ids.add(elem.get("id"))
        except Exception:
            pass
        id_cache[rel] = ids
        return ids

    for path in root_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".htm", ".xhtml"}:
            continue
        doc_rel = path.relative_to(root_dir).as_posix()
        try:
            root = parse_xml_recovering(read_text_file(path))
        except Exception:
            continue
        changed = False
        for elem in list(root.iter()):
            if not isinstance(elem.tag, str):
                continue
            qname = etree.QName(elem)
            local = qname.localname
            image_attr = None
            if qname.namespace == XHTML_NS and local == "img" and elem.get("src"):
                image_attr = "src"
            elif local == "image":
                for attr in elem.attrib:
                    attr_qname = etree.QName(attr) if attr.startswith("{") else None
                    if attr == "href" or (attr_qname is not None and attr_qname.localname == "href"):
                        image_attr = attr
                        break
            if image_attr and elem.get(image_attr):
                _target, _frag, actual = target_for(elem.get(image_attr, ""), doc_rel)
                if actual is None:
                    repl = replacement_href(elem.get(image_attr, ""), doc_rel)
                    if repl:
                        elem.set(image_attr, repl)
                        changed = True
                    else:
                        parent = elem.getparent()
                        if parent is not None:
                            parent.remove(elem)
                            changed = True
            if qname.namespace == XHTML_NS and local in {"link", "script"} and elem.get("href" if local == "link" else "src"):
                attr = "href" if local == "link" else "src"
                _target, _frag, actual = target_for(elem.get(attr, ""), doc_rel)
                if actual is None:
                    repl = replacement_href(elem.get(attr, ""), doc_rel)
                    if repl:
                        elem.set(attr, repl)
                        changed = True
                    else:
                        parent = elem.getparent()
                        if parent is not None:
                            parent.remove(elem)
                            changed = True
            if qname.namespace == XHTML_NS and local == "a" and elem.get("href"):
                base, frag = split_href(elem.get("href", ""))
                if resource_kind(base) == "image":
                    del elem.attrib["href"]
                    elem.tag = f"{{{XHTML_NS}}}span"
                    changed = True
                    continue
                if not base and frag:
                    in_landmarks = any(
                        isinstance(parent.tag, str)
                        and etree.QName(parent).localname == "nav"
                        and (
                            parent.get("{%s}type" % EPUB_NS) == "landmarks"
                            or parent.get("epub:type") == "landmarks"
                            or parent.get("id") == "landmarks"
                        )
                        for parent in elem.iterancestors()
                    )
                    if in_landmarks:
                        del elem.attrib["href"]
                        elem.tag = f"{{{XHTML_NS}}}span"
                        changed = True
                        continue
                    anchor = frag[1:]
                    if anchor and anchor not in ids_for(doc_rel):
                        del elem.attrib["href"]
                        elem.tag = f"{{{XHTML_NS}}}span"
                        changed = True
                        continue
                _target, _frag, actual = target_for(elem.get("href", ""), doc_rel)
                if actual is None and base:
                    repl = replacement_href(elem.get("href", ""), doc_rel)
                    if repl:
                        elem.set("href", repl)
                    else:
                        del elem.attrib["href"]
                        elem.tag = f"{{{XHTML_NS}}}span"
                    changed = True
                elif actual is not None and frag:
                    anchor = frag[1:]
                    if anchor and anchor not in ids_for(actual):
                        elem.set("href", encode_local_href(posixpath.relpath(actual, start=posixpath.dirname(doc_rel) or ".")))
                        changed = True
        if changed:
            write_text_file(
                path,
                etree.tostring(
                    root,
                    encoding="utf-8",
                    xml_declaration=True,
                    doctype="<!DOCTYPE html>",
                    pretty_print=False,
                ).decode("utf-8"),
            )


def repair_missing_css_references(root_dir: Path) -> None:
    candidates = build_resource_candidates(root_dir)
    actual_paths = {
        path.relative_to(root_dir).as_posix().lower(): path.relative_to(root_dir).as_posix()
        for path in root_dir.rglob("*")
        if path.is_file()
    }

    def css_repl(match: re.Match[str]) -> str:
        quote_char = match.group(1) or ""
        value = match.group(2).strip()
        base, frag = split_href(value)
        parts = urlsplit(base)
        if parts.scheme or parts.netloc or base.startswith("data:") or not base:
            return match.group(0)
        doc_dir = posixpath.dirname(current_rel) or "."
        target = posixpath.normpath(posixpath.join(doc_dir, unquote(base)))
        if target.lower() in actual_paths:
            return match.group(0)
        replacement = find_replacement_resource(base, candidates)
        if replacement:
            rel = posixpath.relpath(replacement, start=doc_dir)
            if rel == ".":
                rel = posixpath.basename(replacement)
            return "url(%s%s%s)" % (quote_char, quote(rel, safe="/%:@!$&'()*+,;=-._~") + frag, quote_char)
        return "none"

    for path in root_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".css":
            continue
        current_rel = path.relative_to(root_dir).as_posix()
        data = read_text_file(path)
        updated = re.sub(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", css_repl, data)
        if updated != data:
            write_text_file(path, updated)


def convert_bmp_images(root_dir: Path) -> None:
    if Image is None:
        return
    replacements: Dict[str, str] = {}
    for path in sorted(root_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            is_bmp = path.suffix.lower() == ".bmp" or sniff_image_kind(path) == "bmp"
        except Exception:
            is_bmp = path.suffix.lower() == ".bmp"
        if not is_bmp:
            continue
        target = path.with_suffix(".png")
        try:
            with Image.open(path) as image:
                image.save(target, "PNG")
            old_rel = path.relative_to(root_dir).as_posix()
            new_rel = target.relative_to(root_dir).as_posix()
            replacements[old_rel] = new_rel
            replacements[quote(old_rel, safe="/%:@!$&'()*+,;=-._~")] = quote(new_rel, safe="/%:@!$&'()*+,;=-._~")
            replacements[posixpath.basename(old_rel)] = posixpath.basename(new_rel)
            path.unlink()
        except Exception:
            continue
    if not replacements:
        return
    text_suffixes = {".css", ".html", ".htm", ".ncx", ".opf", ".xhtml", ".xml"}
    for path in root_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        data = read_text_file(path)
        updated = data
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != data:
            write_text_file(path, updated)


def add_fixed_layout_viewports(root_dir: Path, opf_href: str) -> None:
    if Image is None:
        return
    opf_path = root_dir / Path(opf_href)
    if not opf_path.exists():
        return
    opf_dir = posixpath.dirname(opf_href) or "."
    try:
        opf_root = parse_xml_recovering(read_text_file(opf_path))
    except Exception:
        return
    has_global_fixed_layout = any(
        (meta.text or "").strip() == "pre-paginated"
        for meta in opf_root.xpath(".//*[local-name()='meta' and @property='rendition:layout']")
    )
    fixed_items: List[str] = []
    for item in opf_root.xpath(".//*[local-name()='manifest']/*[local-name()='item']"):
        href = item.get("href", "")
        if not href or item.get("media-type") != "application/xhtml+xml":
            continue
        properties = item.get("properties", "").split()
        if has_global_fixed_layout or "rendition:layout-pre-paginated" in properties or "layout-pre-paginated" in properties:
            fixed_items.append(posixpath.normpath(posixpath.join(opf_dir, unquote(href))))

    for rel in fixed_items:
        page_path = root_dir / Path(rel)
        if not page_path.exists():
            continue
        try:
            page_root = parse_xml_recovering(read_text_file(page_path))
        except Exception:
            continue
        if page_root.xpath(".//*[local-name()='head']/*[local-name()='meta' and translate(@name, 'VIEWPORT', 'viewport')='viewport']"):
            continue
        head_matches = page_root.xpath(".//*[local-name()='head']")
        img_matches = page_root.xpath(".//*[local-name()='img' and @src]")
        if not head_matches or not img_matches:
            continue
        img_src = img_matches[0].get("src", "")
        base, _frag = split_href(img_src)
        parts = urlsplit(base)
        if parts.scheme or parts.netloc or not base:
            continue
        page_dir = posixpath.dirname(rel) or "."
        image_rel = posixpath.normpath(posixpath.join(page_dir, unquote(base)))
        image_path = root_dir / Path(image_rel)
        if not image_path.exists():
            continue
        try:
            with Image.open(image_path) as image:
                width, height = image.size
        except Exception:
            continue
        if width <= 0 or height <= 0:
            continue
        head = head_matches[0]
        meta = etree.Element(f"{{{XHTML_NS}}}meta")
        meta.set("name", "viewport")
        meta.set("content", f"width={width}, height={height}")
        charset_metas = head.xpath("./*[local-name()='meta' and @charset]")
        if charset_metas:
            head.insert(head.index(charset_metas[-1]) + 1, meta)
        else:
            head.insert(0, meta)
        write_text_file(
            page_path,
            etree.tostring(
                page_root,
                encoding="utf-8",
                xml_declaration=True,
                doctype="<!DOCTYPE html>",
                pretty_print=False,
            ).decode("utf-8"),
        )


def strip_links_from_legacy_toc_files(root_dir: Path, opf_href: str) -> None:
    opf_path = root_dir / Path(opf_href)
    if not opf_path.exists():
        return
    opf_dir = posixpath.dirname(opf_href) or "."
    official_nav = ""
    try:
        opf_root = parse_xml_recovering(read_text_file(opf_path))
        for item in opf_root.findall(f".//{{{OPF_NS}}}item"):
            if "nav" in item.get("properties", "").split() and item.get("href"):
                official_nav = posixpath.normpath(posixpath.join(opf_dir, unquote(item.get("href", ""))))
                break
    except Exception:
        return

    for path in root_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".htm", ".xhtml"}:
            continue
        rel = path.relative_to(root_dir).as_posix()
        if rel == official_nav:
            continue
        lower_name = path.name.lower()
        data = read_text_file(path)
        if lower_name not in {"nav.html", "nav.xhtml", "toc.html", "toc.xhtml"} and "<nav" not in data.lower():
            continue
        try:
            root = parse_xml_recovering(data)
        except Exception:
            continue
        changed = False
        for elem in root.iter():
            if isinstance(elem.tag, str) and etree.QName(elem).localname == "a" and elem.get("href"):
                del elem.attrib["href"]
                changed = True
        if changed:
            write_text_file(
                path,
                etree.tostring(
                    root,
                    encoding="utf-8",
                    xml_declaration=True,
                    doctype="<!DOCTYPE html>",
                    pretty_print=False,
                ).decode("utf-8"),
            )


def cleanup_nav_leaf_spans(root_dir: Path, opf_href: str) -> None:
    opf_path = root_dir / Path(opf_href)
    if not opf_path.exists():
        return
    opf_dir = posixpath.dirname(opf_href) or "."
    try:
        opf_root = parse_xml_recovering(read_text_file(opf_path))
    except Exception:
        return
    nav_rel = ""
    for item in opf_root.xpath(".//*[local-name()='item']"):
        if "nav" in item.get("properties", "").split() and item.get("href"):
            nav_rel = posixpath.normpath(posixpath.join(opf_dir, unquote(item.get("href", ""))))
            break
    if not nav_rel:
        return
    nav_path = root_dir / Path(nav_rel)
    if not nav_path.exists():
        return
    try:
        root = parse_xml_recovering(read_text_file(nav_path))
    except Exception:
        return
    changed = False
    manifest_hrefs: Dict[str, str] = {}
    for item in opf_root.xpath(".//*[local-name()='manifest']/*[local-name()='item']"):
        item_id = item.get("id", "")
        href = item.get("href", "")
        if item_id and href:
            manifest_hrefs[item_id] = posixpath.normpath(posixpath.join(opf_dir, unquote(href)))
    spine_href_list = [
        manifest_hrefs[itemref.get("idref", "")]
        for itemref in opf_root.xpath(".//*[local-name()='spine']/*[local-name()='itemref']")
        if manifest_hrefs.get(itemref.get("idref", ""))
    ]
    spine_hrefs = set(spine_href_list)
    nav_dir = posixpath.dirname(nav_rel) or "."
    if spine_hrefs:
        for anchor in list(root.xpath(".//*[local-name()='nav']//*[local-name()='a'][@href]")):
            base, _frag = split_href(anchor.get("href", ""))
            parts = urlsplit(base)
            if parts.scheme or parts.netloc or not base:
                continue
            target = posixpath.normpath(posixpath.join(nav_dir, unquote(base)))
            if target not in spine_hrefs and Path(target).suffix.lower() in {".html", ".htm", ".xhtml"}:
                anchor.attrib.pop("href", None)
                anchor.tag = f"{{{XHTML_NS}}}span"
                changed = True
    for ol in list(root.xpath(".//*[local-name()='nav']//*[local-name()='ol']")):
        if not any(isinstance(child.tag, str) and etree.QName(child).localname == "li" for child in ol):
            parent = ol.getparent()
            if parent is not None:
                parent.remove(ol)
                changed = True
    for li in list(root.xpath(".//*[local-name()='nav']//*[local-name()='li']")):
        has_child_ol = any(
            isinstance(child.tag, str) and etree.QName(child).localname == "ol"
            and any(isinstance(grandchild.tag, str) and etree.QName(grandchild).localname == "li" for grandchild in child)
            for child in li
        )
        has_href_anchor = any(
            isinstance(desc.tag, str) and etree.QName(desc).localname == "a" and desc.get("href")
            for desc in li.iterdescendants()
        )
        if not has_child_ol and not has_href_anchor:
            parent = li.getparent()
            if parent is not None:
                parent.remove(li)
                changed = True
    for nav in list(root.xpath(".//*[local-name()='nav']")):
        if nav.xpath(".//*[local-name()='li']"):
            continue
        epub_type = " ".join(
            part for part in (nav.get("{%s}type" % EPUB_NS, ""), nav.get("type", "")) if part
        )
        if "toc" not in epub_type.split():
            parent = nav.getparent()
            if parent is not None:
                parent.remove(nav)
                changed = True
            continue
        ol = next(
            (child for child in nav if isinstance(child.tag, str) and etree.QName(child).localname == "ol"),
            None,
        )
        if ol is None:
            ol = etree.SubElement(nav, f"{{{XHTML_NS}}}ol")
        li = etree.SubElement(ol, f"{{{XHTML_NS}}}li")
        first_spine_href = spine_href_list[0] if spine_href_list else ""
        if first_spine_href:
            anchor = etree.SubElement(li, f"{{{XHTML_NS}}}a")
            anchor.set("href", posixpath.relpath(first_spine_href, start=nav_dir))
            anchor.text = posixpath.basename(strip_fragment(first_spine_href)) or "Start"
        else:
            span = etree.SubElement(li, f"{{{XHTML_NS}}}span")
            span.text = "Start"
        changed = True
    if changed:
        write_text_file(
            nav_path,
            etree.tostring(
                root,
                encoding="utf-8",
                xml_declaration=True,
                doctype="<!DOCTYPE html>",
                pretty_print=False,
            ).decode("utf-8"),
        )


def media_type_for_path(path: Path) -> str:
    kind = sniff_image_kind(path)
    if kind:
        return {
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "tiff": "image/tiff",
            "bmp": "image/bmp",
        }.get(kind, "image/%s" % kind)
    guessed, _encoding = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def extension_media_type(path: str) -> Optional[str]:
    suffix = Path(path).suffix.lower()
    return {
        ".css": "text/css",
        ".gif": "image/gif",
        ".htm": "application/xhtml+xml",
        ".html": "application/xhtml+xml",
        ".jpeg": "image/jpeg",
        ".jpg": "image/jpeg",
        ".js": "application/javascript",
        ".ncx": "application/x-dtbncx+xml",
        ".otf": "application/vnd.ms-opentype",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".ttf": "application/vnd.ms-opentype",
        ".webp": "image/webp",
        ".xhtml": "application/xhtml+xml",
    }.get(suffix)


def sniff_image_kind(path: Path) -> Optional[str]:
    try:
        header = path.read_bytes()[:32]
    except OSError:
        return None
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if header.startswith(b"BM"):
        return "bmp"
    if header.startswith((b"II*\x00", b"MM\x00*")):
        return "tiff"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def manifest_media_type_for_path(path: Path, href: str) -> str:
    detected = media_type_for_path(path)
    if detected.startswith("image/"):
        return detected
    return extension_media_type(href) or detected


def is_calibre_bookmark_path(path: str) -> bool:
    return posixpath.normpath(unquote(path)).replace("\\", "/").lower() in CALIBRE_BOOKMARKS


def is_javascript_resource(href: str, media_type: str = "") -> bool:
    return Path(unquote(href)).suffix.lower() == ".js" or media_type.lower() in JAVASCRIPT_MEDIA_TYPES


def is_invalid_svg_resource(path: Path) -> bool:
    if path.suffix.lower() != ".svg":
        return False
    try:
        data = read_text_file(path)
    except Exception:
        return True
    return not data.strip() or "<svg" not in data.lower()


PRIVATE_OPF_PROPERTY_TOKENS = {"duokan-page-fitwindow", "duokan-page-fullscreen"}
PUBLICATION_RESOURCE_SUFFIXES = {
    ".css",
    ".gif",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".otf",
    ".png",
    ".svg",
    ".ttf",
    ".webp",
    ".xhtml",
}


def cleanup_opf_manifest(root_dir: Path, opf_href: str) -> None:
    opf_path = root_dir / Path(opf_href)
    if not opf_path.exists():
        return
    for path in root_dir.rglob("*"):
        rel = path.relative_to(root_dir).as_posix()
        if path.is_file() and (path.suffix.lower() in {".js", ".ncx"} or is_calibre_bookmark_path(rel)):
            try:
                path.unlink()
            except OSError:
                pass
    opf_dir = posixpath.dirname(opf_href) or "."
    try:
        root = parse_xml_recovering(read_text_file(opf_path))
    except Exception:
        return
    manifest = root.find(f".//{{{OPF_NS}}}manifest")
    spine = root.find(f".//{{{OPF_NS}}}spine")
    metadata = root.find(f".//{{{OPF_NS}}}metadata")
    if manifest is None:
        return
    def manifest_items() -> List[etree._Element]:
        return list(manifest.xpath("./*[local-name()='item']"))

    def spine_itemrefs() -> List[etree._Element]:
        if spine is None:
            return []
        return list(spine.xpath("./*[local-name()='itemref']"))

    changed = False
    for misplaced_spine in list(manifest.xpath("./*[local-name()='spine']")):
        manifest.remove(misplaced_spine)
        if spine is None or spine is misplaced_spine:
            spine = misplaced_spine
            root.insert(root.index(manifest) + 1, spine)
        elif not spine_itemrefs():
            for itemref in misplaced_spine.xpath("./*[local-name()='itemref']"):
                spine.append(itemref)
        changed = True
    for guide in root.xpath(".//*[local-name()='guide']"):
        parent = guide.getparent()
        if parent is not None:
            parent.remove(guide)
            changed = True
    candidates = build_resource_candidates(root_dir)
    removed_ids: set[str] = set()
    removed_files: set[Path] = set()
    id_renames: Dict[str, str] = {}
    cover_meta_ids = set()
    if metadata is not None:
        cover_meta_ids = {
            meta.get("content", "")
            for meta in metadata.xpath(".//*[local-name()='meta' and translate(@name, 'COVER', 'cover')='cover']")
            if meta.get("content")
        }

    def duplicate_manifest_priority(item: etree._Element) -> int:
        score = 0
        if item.get("id", "") in cover_meta_ids:
            score += 4
        if "cover-image" in item.get("properties", "").split():
            score += 2
        if item.get("id", "").lower() == "cover":
            score += 1
        return score

    nav_seen = False
    has_generated_nav = any(
        posixpath.basename(item.get("href", "")) == "nav.xhtml"
        for item in manifest_items()
    )
    used_ids: set[str] = set()
    for item in manifest_items():
        item_id = item.get("id", "")
        href = item.get("href", "")
        if not item_id or not XML_ID_RE.match(item_id):
            new_id = make_xml_id(item_id or posixpath.basename(href) or "item", used_ids)
            if item_id:
                id_renames[item_id] = new_id
            item.set("id", new_id)
            changed = True
        elif item_id in used_ids:
            item.set("id", make_xml_id(item_id, used_ids))
            changed = True
        else:
            used_ids.add(item_id)

    declared_package_hrefs = {
        posixpath.normpath(posixpath.join(opf_dir, unquote(item.get("href", "")))).lower()
        for item in manifest_items()
        if item.get("href")
    }
    for path in sorted(root_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root_dir).as_posix()
        rel_lower = rel.lower()
        if (
            rel_lower == "mimetype"
            or rel_lower.startswith("meta-inf/")
            or rel_lower == posixpath.normpath(opf_href).lower()
            or is_calibre_bookmark_path(rel)
            or path.suffix.lower() not in PUBLICATION_RESOURCE_SUFFIXES
        ):
            continue
        if rel_lower in declared_package_hrefs:
            continue
        href = posixpath.relpath(rel, start=opf_dir)
        if href == ".":
            href = posixpath.basename(rel)
        item = etree.SubElement(manifest, f"{{{OPF_NS}}}item")
        item.set("id", make_xml_id(Path(rel).stem or "item", used_ids))
        item.set("href", quote(href, safe="/%:@!$&'()*+,;=-._~"))
        item.set("media-type", manifest_media_type_for_path(path, href))
        declared_package_hrefs.add(rel_lower)
        changed = True

    seen_hrefs: Dict[str, etree._Element] = {}
    for item in manifest_items():
        for attr in list(item.attrib):
            attr_local = etree.QName(attr).localname if attr.startswith("{") else attr
            if attr_local in PRIVATE_OPF_PROPERTY_TOKENS:
                item.attrib.pop(attr, None)
                changed = True
        item_id = item.get("id", "")
        href = item.get("href", "")
        item_path = posixpath.normpath(posixpath.join(opf_dir, unquote(href))) if href else ""
        if href and (
            is_javascript_resource(href, item.get("media-type", ""))
            or is_calibre_bookmark_path(item_path)
            or Path(unquote(href)).suffix.lower() in FOREIGN_IMAGE_SUFFIXES
            or is_invalid_svg_resource(root_dir / Path(item_path))
            or Path(unquote(href)).suffix.lower() == ".ncx"
            or item.get("media-type") == "application/x-dtbncx+xml"
        ):
            manifest.remove(item)
            if item_id:
                removed_ids.add(item_id)
            removed_files.add(root_dir / Path(item_path))
            changed = True
            continue
        if not href:
            manifest.remove(item)
            if item_id:
                removed_ids.add(item_id)
            changed = True
            continue
        decoded_href = unquote(href)
        if opf_dir != "." and posixpath.normpath(decoded_href).startswith(opf_dir + "/"):
            fixed_href = posixpath.relpath(posixpath.normpath(decoded_href), start=opf_dir)
            href = quote(fixed_href, safe="/%:@!$&'()*+,;=-._~")
            item.set("href", href)
            changed = True
        normalized_href = posixpath.normpath(posixpath.join(opf_dir, unquote(href))).lower()
        previous_item = seen_hrefs.get(normalized_href)
        if previous_item is not None:
            previous_id = previous_item.get("id", "")
            if duplicate_manifest_priority(item) > duplicate_manifest_priority(previous_item):
                manifest.remove(previous_item)
                if previous_id:
                    removed_ids.add(previous_id)
                seen_hrefs[normalized_href] = item
                changed = True
            else:
                manifest.remove(item)
                if item_id:
                    removed_ids.add(item_id)
                changed = True
                continue
        else:
            seen_hrefs[normalized_href] = item
        if href:
            target = root_dir / Path(posixpath.normpath(posixpath.join(opf_dir, unquote(href))))
            if not target.exists():
                replacement = find_replacement_resource(href, candidates)
                if replacement:
                    new_href = posixpath.relpath(replacement, start=opf_dir)
                    if new_href == ".":
                        new_href = posixpath.basename(replacement)
                    href = quote(new_href, safe="/%:@!$&'()*+,;=-._~")
                    item.set("href", href)
                    target = root_dir / Path(replacement)
                    changed = True
                else:
                    manifest.remove(item)
                    if item_id:
                        removed_ids.add(item_id)
                    changed = True
                    continue
            media_type = manifest_media_type_for_path(target, href)
            if media_type and item.get("media-type") != media_type:
                item.set("media-type", media_type)
                changed = True
        props = item.get("properties", "")
        tokens = props.split()
        if any(token in PRIVATE_OPF_PROPERTY_TOKENS for token in tokens):
            tokens = [token for token in tokens if token not in PRIVATE_OPF_PROPERTY_TOKENS]
            if tokens:
                item.set("properties", " ".join(tokens))
            else:
                item.attrib.pop("properties", None)
            props = item.get("properties", "")
            tokens = props.split()
            changed = True
        if "scripted" in tokens and (posixpath.basename(href) == "nav.xhtml" or item.get("media-type") != "application/xhtml+xml"):
            tokens = [token for token in tokens if token != "scripted"]
            if tokens:
                item.set("properties", " ".join(tokens))
            else:
                item.attrib.pop("properties", None)
            props = item.get("properties", "")
            tokens = props.split()
            changed = True
        if "nav" in tokens:
            is_generated_nav = posixpath.basename(href) == "nav.xhtml"
            if has_generated_nav and not is_generated_nav:
                tokens = [token for token in tokens if token != "nav"]
                if tokens:
                    item.set("properties", " ".join(tokens))
                else:
                    item.attrib.pop("properties", None)
                changed = True
            elif not nav_seen:
                nav_seen = True
            else:
                tokens = [token for token in tokens if token != "nav"]
                if tokens:
                    item.set("properties", " ".join(tokens))
                else:
                    item.attrib.pop("properties", None)
                changed = True
    if spine is None:
        spine = etree.Element(f"{{{OPF_NS}}}spine")
        root.insert(root.index(manifest) + 1, spine)
        changed = True
    if not spine_itemrefs():
        for item in manifest_items():
            href = item.get("href", "")
            if item.get("media-type") != "application/xhtml+xml":
                continue
            if posixpath.basename(unquote(href)).lower() in {"nav.html", "nav.xhtml"}:
                continue
            itemref = etree.SubElement(spine, f"{{{OPF_NS}}}itemref")
            itemref.set("idref", item.get("id", ""))
            changed = True
    manifest_ids = {item.get("id", "") for item in manifest_items()}
    if spine is not None:
        if spine.get("toc"):
            spine.attrib.pop("toc", None)
            changed = True
        seen_idrefs: set[str] = set()
        for itemref in spine_itemrefs():
            for attr in list(itemref.attrib):
                attr_local = etree.QName(attr).localname if attr.startswith("{") else attr
                if attr_local in PRIVATE_OPF_PROPERTY_TOKENS:
                    itemref.attrib.pop(attr, None)
                    changed = True
            idref = itemref.get("idref", "")
            if idref in id_renames:
                idref = id_renames[idref]
                itemref.set("idref", idref)
                changed = True
            linear_type = itemref.attrib.pop("linear-type", None)
            if linear_type is not None:
                if linear_type in {"yes", "no"} and "linear" not in itemref.attrib:
                    itemref.set("linear", linear_type)
                changed = True
            if itemref.get("linear") not in {None, "yes", "no"}:
                itemref.attrib.pop("linear", None)
                changed = True
            props = itemref.get("properties", "")
            if any(token in PRIVATE_OPF_PROPERTY_TOKENS for token in props.split()):
                tokens = [token for token in props.split() if token not in PRIVATE_OPF_PROPERTY_TOKENS]
                if tokens:
                    itemref.set("properties", " ".join(tokens))
                else:
                    itemref.attrib.pop("properties", None)
                changed = True
            if idref in removed_ids or idref not in manifest_ids or idref in seen_idrefs:
                spine.remove(itemref)
                changed = True
                continue
            seen_idrefs.add(idref)
            manifest_matches = manifest.xpath("./*[local-name()='item' and @id=$idref]", idref=idref)
            manifest_item = manifest_matches[0] if manifest_matches else None
            if manifest_item is not None:
                href = manifest_item.get("href", "")
                if posixpath.basename(unquote(href)).lower() in {"nav.html", "nav.xhtml"}:
                    spine.remove(itemref)
                    changed = True
                    continue
                if Path(unquote(href)).suffix.lower() in {".html", ".htm", ".xhtml"} and manifest_item.get("media-type") != "application/xhtml+xml":
                    manifest_item.set("media-type", "application/xhtml+xml")
                    changed = True
                basename = posixpath.basename(unquote(href)).lower()
                item_id_lower = idref.lower()
                if itemref.get("linear") == "no" and (
                    basename in {"cover.html", "cover.xhtml", "cover_page.html", "cover_page.xhtml", "titlepage.html", "titlepage.xhtml"}
                    or item_id_lower in {"cover", "cover_page", "titlepage", "cover.xhtml", "cover_page.xhtml", "titlepage.xhtml"}
                ):
                    itemref.attrib.pop("linear", None)
                    changed = True

    if metadata is None:
        metadata = etree.Element(f"{{{OPF_NS}}}metadata", nsmap={"dc": DC_NS})
        root.insert(0, metadata)
        changed = True
    for elem in list(metadata):
        if isinstance(elem.tag, str) and etree.QName(elem).namespace == DC_NS and etree.QName(elem).localname not in DC_METADATA_ELEMENTS and etree.QName(elem).localname != "meta":
            metadata.remove(elem)
            changed = True
            continue
        if isinstance(elem.tag, str) and etree.QName(elem).namespace == DC_NS and etree.QName(elem).localname != "meta":
            for attr in list(elem.attrib):
                attr_local = etree.QName(attr).localname if attr.startswith("{") else attr
                if attr_local not in {"dir", "id", "lang"} and attr != "{http://www.w3.org/XML/1998/namespace}lang":
                    elem.attrib.pop(attr, None)
                    changed = True
    for meta in metadata.xpath(".//*[local-name()='meta']"):
        if not isinstance(meta.tag, str):
            continue
        if etree.QName(meta).namespace == DC_NS:
            meta.tag = f"{{{OPF_NS}}}meta"
            changed = True
        if etree.QName(meta).namespace == OPF_NS and not meta.attrib and (meta.text or "").strip():
            text = (meta.text or "").strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[^\\s]+)?Z?", text):
                meta.set("property", "dcterms:modified")
                changed = True
            else:
                metadata.remove(meta)
                changed = True
                continue
        if meta.get("property", "").startswith("ibooks:") and not (meta.text or "").strip():
            metadata.remove(meta)
            changed = True
            continue
        if meta.get("property") == "role" and not (meta.text or "").strip():
            metadata.remove(meta)
            changed = True
            continue
        for attr in list(meta.attrib):
            if attr.startswith("{%s}" % OPF_NS):
                meta.set(etree.QName(attr).localname, meta.attrib.pop(attr))
                changed = True
        if meta.get("scheme") is not None:
            meta.attrib.pop("scheme", None)
            changed = True
    metadata_ids = {
        elem.get("id")
        for elem in metadata.xpath(".//*[@id]")
        if isinstance(elem.tag, str) and elem.get("id")
    }
    property_by_id = {
        elem.get("id"): elem.get("property", "")
        for elem in metadata.xpath(".//*[local-name()='meta' and @id]")
        if isinstance(elem.tag, str)
    }
    seen_refines_properties: set[tuple[str, str]] = set()
    for meta in list(metadata.xpath(".//*[local-name()='meta']")):
        if not isinstance(meta.tag, str):
            continue
        prop = meta.get("property", "")
        text = (meta.text or "").strip()
        content = (meta.get("content") or "").strip()
        if prop == "dcterms:modified":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text):
                meta.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                changed = True
            continue
        refines = meta.get("refines", "")
        if prop and not text and not content:
            metadata.remove(meta)
            changed = True
            continue
        if refines.startswith("#") and refines[1:] not in metadata_ids:
            metadata.remove(meta)
            changed = True
            continue
        if refines and prop:
            key = (refines, prop)
            if key in seen_refines_properties:
                metadata.remove(meta)
                changed = True
                continue
            seen_refines_properties.add(key)
        if prop == "collection-type" and property_by_id.get(refines.lstrip("#")) != "belongs-to-collection":
            metadata.remove(meta)
            changed = True
            continue
    modified_seen = False
    for meta in list(metadata.xpath(".//*[local-name()='meta' and @property='dcterms:modified']")):
        if modified_seen:
            metadata.remove(meta)
            changed = True
        else:
            modified_seen = True
    titles = list(metadata.findall(f"{{{DC_NS}}}title"))
    if not any((title.text or "").strip() for title in titles):
        title = titles[0] if titles else etree.SubElement(metadata, f"{{{DC_NS}}}title")
        title.text = "Untitled"
        changed = True
    languages = list(metadata.findall(f"{{{DC_NS}}}language"))
    if not any((language.text or "").strip() for language in languages):
        language = languages[0] if languages else etree.SubElement(metadata, f"{{{DC_NS}}}language")
        language.text = "zh-Hant"
        changed = True
    identifiers = list(metadata.findall(f"{{{DC_NS}}}identifier"))
    for ident in list(identifiers):
        if not (ident.text or "").strip():
            metadata.remove(ident)
            identifiers.remove(ident)
            changed = True
    unique_id = root.get("unique-identifier", "")
    if not unique_id or not any(ident.get("id") == unique_id for ident in identifiers):
        replacement = next((ident for ident in identifiers if ident.get("id") and (ident.text or "").strip()), None)
        if replacement is None:
            unique_id = "uid"
            used = {ident.get("id", "") for ident in identifiers}
            unique_id = make_xml_id(unique_id, used)
            replacement = etree.SubElement(metadata, f"{{{DC_NS}}}identifier")
            replacement.set("id", unique_id)
            replacement.text = "urn:uuid:%s" % uuid.uuid4()
            changed = True
        root.set("unique-identifier", replacement.get("id"))
        changed = True
    if changed:
        etree.cleanup_namespaces(root, top_nsmap={None: OPF_NS, "dc": DC_NS})
        for path in removed_files:
            try:
                if path.is_file():
                    path.unlink()
            except OSError:
                pass
        write_text_file(
            opf_path,
            etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=True).decode("utf-8"),
        )


def add_missing_manifest_items(root_dir: Path, opf_href: str) -> None:
    opf_path = root_dir / Path(opf_href)
    if not opf_path.exists():
        return
    actual_paths = {
        path.relative_to(root_dir).as_posix().lower(): path.relative_to(root_dir).as_posix()
        for path in root_dir.rglob("*")
        if path.is_file()
    }
    opf_dir = posixpath.dirname(opf_href) or "."
    try:
        root = parse_xml_recovering(read_text_file(opf_path))
    except Exception:
        return
    manifest = root.find(f".//{{{OPF_NS}}}manifest")
    if manifest is None:
        return

    declared = set()
    used_ids = {item.get("id", "") for item in manifest.findall(f"{{{OPF_NS}}}item")}
    for item in manifest.findall(f"{{{OPF_NS}}}item"):
        href = item.get("href")
        if href:
            declared.add(posixpath.normpath(posixpath.join(opf_dir, unquote(href))).lower())

    refs: set[str] = set()
    text_suffixes = {".css", ".html", ".htm", ".xhtml"}
    attr_re = re.compile(r"""\b(?:href|src|poster|data|xlink:href)\s*=\s*(['"])(.*?)\1""")
    css_re = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)")
    import_re = re.compile(r"""@import\s+(?:url\(\s*)?(['"])(.*?)\1""")
    for path in root_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        doc_rel = path.relative_to(root_dir).as_posix()
        doc_dir = posixpath.dirname(doc_rel) or "."
        data = read_text_file(path)
        values = [m.group(2) for m in attr_re.finditer(data)]
        for srcset in re.finditer(r"""\bsrcset\s*=\s*(['"])(.*?)\1""", data):
            values.extend(part.strip().split()[0] for part in srcset.group(2).split(",") if part.strip())
        values.extend(m.group(2) for m in css_re.finditer(data))
        values.extend(m.group(2) for m in import_re.finditer(data))
        for value in values:
            base, _frag = split_href(value)
            parts = urlsplit(base)
            if parts.scheme or parts.netloc or base.startswith("data:") or not base:
                continue
            target = posixpath.normpath(posixpath.join(doc_dir, unquote(base)))
            actual = actual_paths.get(target.lower())
            if actual and actual.lower() not in declared:
                refs.add(actual)

    counter = 1
    changed = False
    for rel in sorted(refs):
        while "auto-%d" % counter in used_ids:
            counter += 1
        item_id = "auto-%d" % counter
        used_ids.add(item_id)
        counter += 1
        href = posixpath.relpath(rel, start=opf_dir)
        if href == ".":
            href = posixpath.basename(rel)
        item = etree.SubElement(manifest, f"{{{OPF_NS}}}item")
        item.set("id", item_id)
        item.set("href", quote(href, safe="/%:@!$&'()*+,;=-._~"))
        item.set("media-type", media_type_for_path(root_dir / Path(rel)))
        declared.add(rel.lower())
        changed = True

    if changed:
        write_text_file(
            opf_path,
            etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=True).decode("utf-8"),
        )


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
    fallback_href: str = "",
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
    if not flat_toc:
        fallback = fallback_href or ""
        if fallback:
            lines.append(
                '        <li><a href="%s">%s</a></li>\n'
                % (html.escape(href_for(fallback), quote=True), html.escape(posixpath.basename(strip_fragment(fallback)) or "Start"))
            )
        lines.append("      </ol>\n")
        lines.append("    </nav>\n")
    else:
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


def filter_toc_to_spine(toc_nodes: List[TocNode], spine_hrefs: Iterable[str]) -> List[TocNode]:
    resolved_spine_hrefs = list(spine_hrefs)

    def resolve(value: str) -> Optional[str]:
        base, frag = split_href(value)
        norm_base = posixpath.normpath(unquote(base))
        spine_map = {posixpath.normpath(unquote(href)).lower(): href for href in resolved_spine_hrefs}
        direct = spine_map.get(norm_base.lower())
        if direct:
            return direct
        replacement = find_replacement_resource(base, resolved_spine_hrefs)
        if replacement and posixpath.normpath(unquote(replacement)).lower() in spine_map:
            return replacement
        return None

    def keep(nodes: List[TocNode]) -> List[TocNode]:
        result: List[TocNode] = []
        for node in nodes:
            children = keep(node.children)
            href = resolve(node.href)
            if href:
                result.append(TocNode(node.label, href, children))
            else:
                result.extend(children)
        return result

    return keep(toc_nodes)


def filter_pagelist_to_spine(pagelist: List[Tuple[str, str]], spine_hrefs: Iterable[str]) -> List[Tuple[str, str]]:
    toc_nodes = [TocNode(page, href, []) for page, href in pagelist]
    return [(node.label, node.href) for node in filter_toc_to_spine(toc_nodes, spine_hrefs)]


def filter_guide_to_spine(guide_info: List[Tuple[str, str, str]], spine_hrefs: Iterable[str]) -> List[Tuple[str, str, str]]:
    filtered: List[Tuple[str, str, str]] = []
    for gtyp, gtitle, ghref in guide_info:
        resolved = filter_toc_to_spine([TocNode(gtitle, ghref, [])], spine_hrefs)
        if resolved:
            filtered.append((gtyp, gtitle, strip_fragment(resolved[0].href)))
    return filtered


def final_spine_hrefs_for_nav(spine_hrefs: Iterable[str]) -> List[str]:
    return [
        href for href in spine_hrefs
        if posixpath.basename(strip_fragment(href)).lower() not in {"nav.xhtml", "nav.html"}
    ]


def remove_nav_spine_itemref(opf_text: str) -> str:
    return re.sub(
        r"\n?\s*<itemref[^>]*idref=\"[^\"]*nav[^\"]*\"[^>]*/>\s*",
        "\n",
        opf_text,
        flags=re.IGNORECASE,
    )


def sniff_manifest_media_types(book: EpubBookAdapter, manifest_items: List[Tuple[str, str, str]]) -> Dict[str, str]:
    mapping = {
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "tiff": "image/tiff",
        "bmp": "image/bmp",
    }
    overrides: Dict[str, str] = {}
    for mid, _href, media_type in manifest_items:
        ext_media_type = extension_media_type(_href)
        if ext_media_type and ext_media_type != media_type:
            overrides[mid] = ext_media_type
            continue
        if not media_type.startswith("image/"):
            continue
        try:
            path = book.resolve_bookpath(book.id_to_bookpath(mid))
            kind = sniff_image_kind(path)
        except Exception:
            continue
        detected = mapping.get(kind or "")
        if detected and detected != media_type:
            overrides[mid] = detected
    return overrides


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

        convert_bmp_images(book.root_dir)
        fix_case_mismatched_local_hrefs(book.root_dir)
        opf_text = sanitize_namespace_declarations(book.readotherfile(opf_href))

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
        final_spine_hrefs = final_spine_hrefs_for_nav(spine_hrefs)
        toc_nodes = filter_toc_to_spine(toc_nodes, final_spine_hrefs)
        pagelist = filter_pagelist_to_spine(pagelist, final_spine_hrefs)
        if ncx_path.exists():
            write_ncx_file(ncx_path, ncx_href, doctitle, toc_nodes, uid="")

        man_ids = [mid for mid, _, _ in manifest_items if mid]
        media_type_overrides = sniff_manifest_media_types(book, manifest_items)
        opfconv = Opf_Converter(opf_text, spine_properties, manifest_properties, {}, man_ids, media_type_overrides)
        lang = opfconv.get_lang()
        uid = opfconv.get_uid()
        if ncx_path.exists():
            sync_ncx_uid(ncx_path, uid)
            normalize_ncx_play_order(ncx_path)
        opf3 = opfconv.get_opf3()
        # In the standalone tool, keep nav.xhtml out of the spine so epubCheck
        # does not treat it as non-linear reachable content.
        opf3 = remove_nav_spine_itemref(opf3)
        guide = filter_guide_to_spine(opfconv.get_guide(), final_spine_hrefs)

        opf3_path = opf_path
        write_text_file(opf3_path, opf3)

        nav_href = book.build_bookpath("nav.xhtml", opf_dir)
        nav_path = book.resolve_bookpath(nav_href)
        print("..creating:", nav_href)
        navdata = build_nav(nav_href, doctitle, toc_nodes, pagelist, guide, opf_dir, final_spine_hrefs[0] if final_spine_hrefs else "")
        write_text_file(nav_path, navdata)
        repair_missing_xhtml_references(book.root_dir)
        repair_missing_css_references(book.root_dir)
        add_missing_manifest_items(book.root_dir, opf_href)
        cleanup_opf_manifest(book.root_dir, opf_href)
        final_uid = opf_unique_identifier_value(opf3_path)
        if ncx_path.exists() and final_uid:
            sync_ncx_uid(ncx_path, final_uid)
        strip_links_from_legacy_toc_files(book.root_dir, opf_href)
        cleanup_nav_leaf_spans(book.root_dir, opf_href)
        normalize_all_xhtml_files(book.root_dir)
        add_fixed_layout_viewports(book.root_dir, opf_href)
        repair_missing_xhtml_references(book.root_dir)
        repair_missing_css_references(book.root_dir)
        add_missing_manifest_items(book.root_dir, opf_href)
        cleanup_opf_manifest(book.root_dir, opf_href)
        cleanup_nav_leaf_spans(book.root_dir, opf_href)
        sanitize_all_css_files(book.root_dir)

        mimetype_path = book.root_dir / "mimetype"
        write_text_file(mimetype_path, "application/epub+zip")

        print("..creating: epub3")
        zip_epub(book.root_dir, output_path)

    return output_path
