#!/usr/bin/env python3
from __future__ import annotations

import json
import posixpath
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple
from html import unescape
from urllib.parse import quote, unquote

from lxml import etree

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from html_namedentities import named_entities

XHTML_NS = "http://www.w3.org/1999/xhtml"
OPF_NS = "http://www.idpf.org/2007/opf"
CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
NCX_MIME = "application/x-dtbncx+xml"
XHTML_MIME = "application/xhtml+xml"

XML_PARSER = etree.XMLParser(
    remove_blank_text=False,
    resolve_entities=False,
    load_dtd=False,
    no_network=True,
    huge_tree=True,
)


@dataclass(frozen=True)
class ManifestItem:
    id: str
    href: str
    media_type: str
    properties: str = ""


def convert_named_entities(text: str) -> str:
    import re

    entity_re = re.compile(r"(&\w+;)")
    pieces = entity_re.split(text)
    for i in range(1, len(pieces), 2):
        piece = pieces[i]
        sval = named_entities.get(piece[1:], "")
        if sval:
            pieces[i] = "&#%d;" % ord(sval)
    return "".join(pieces)


def _read_text_file(path: Path) -> str:
    data = path.read_bytes()
    declared = re.search(br"""encoding\s*=\s*["']([^"']+)["']""", data[:256], re.IGNORECASE)
    encodings = ["utf-8", "utf-8-sig"]
    if declared:
        try:
            encodings.insert(0, declared.group(1).decode("ascii", errors="ignore"))
        except Exception:
            pass
    encodings.extend(["cp950", "big5", "gb18030"])
    seen: set[str] = set()
    for encoding in encodings:
        normalized = encoding.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="strict")


def _write_text_file(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8", newline="\n")


def _split_href(href: str) -> Tuple[str, str]:
    base, frag = href.split("#", 1) if "#" in href else (href, "")
    return base, ("#" + frag) if frag else ""


def _normalize_bookpath(href: str) -> str:
    if not href:
        return ""
    href = href.replace("\\", "/")
    base, frag = _split_href(href)
    parts = posixpath.normpath(base)
    if parts == ".":
        parts = ""
    return parts + frag


def _extract_epub_archive(zf: zipfile.ZipFile, root: Path) -> None:
    """在解壓前改名，避免 Windows extractall 的清理造成章節互相覆蓋。"""
    files = [item for item in zf.infolist() if not item.is_dir()]
    names = [item.filename for item in files]
    if len(set(names)) != len(names):
        raise ValueError("EPUB ZIP 含重複資源名稱，無法安全決定引用目標")
    canonical = {}
    for name in names:
        parts = name.split("/")
        target = posixpath.normpath(name)
        if name.startswith("/") or any(part in {"", "."} for part in parts) or target in {".", ".."} or target.startswith("../"):
            raise ValueError("EPUB ZIP 含不安全路徑：" + name)
        canonical[name] = target
    changed_paths = {name for name in names if canonical[name] != name}
    for name in changed_paths:
        aliases = [other for other in names if canonical[other].casefold() == canonical[name].casefold()]
        if len(aliases) > 1 and (
            Path(canonical[name]).suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}
            or len({zf.read(other) for other in aliases}) != 1
        ):
            raise ValueError("EPUB ZIP 正規化後資源名稱衝突，無法安全決定引用目標")
    invalid = re.compile(r'[<>:"\\|?*\x00-\x1f]')
    device = re.compile(r'^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', re.I)
    mapping: Dict[str, str] = {}
    used: set[str] = set()
    reserved = {canonical[name].casefold() for name in names}
    for index, item in enumerate(files):
        original = item.filename
        name = canonical[original]
        parts = name.split("/")
        if name.startswith("/") or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("EPUB ZIP 含不安全路徑：" + name)
        # ponytail: 不安全目錄名稱先拒絕；需要支援時再加目錄與引用的完整映射。
        if any(invalid.search(part) or device.match(part) or part.endswith((".", " ")) for part in parts[:-1]):
            raise ValueError("EPUB ZIP 含不安全目錄名稱：" + name)
        filename = parts[-1]
        target = name
        if invalid.search(filename) or device.match(filename) or filename.endswith((".", " ")) or name.casefold() in used:
            suffix = Path(filename).suffix
            if invalid.search(suffix):
                raise ValueError("EPUB ZIP 含無法安全辨識的副檔名：" + name)
            number = index
            while True:
                target = posixpath.join(posixpath.dirname(name), f"epub3itizer_resource_{number}{suffix}")
                if target.casefold() not in reserved | used:
                    break
                number += 1
            mapping[name] = target
        if original != target:
            mapping[original] = target
            if original in changed_paths:
                mapping[name] = target
        used.add(target.casefold())
        path = root / target
        path.resolve().relative_to(root.resolve())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(zf.read(item))
    if not mapping:
        return
    for item in files:
        original = item.filename
        path = root / mapping.get(original, original)
        if path.suffix.lower() not in {".css", ".html", ".htm", ".ncx", ".opf", ".xhtml", ".xml"}:
            continue
        try:
            text = _read_text_file(path)
        except UnicodeDecodeError:
            continue
        def rewrite(value: str, full_path: bool = False) -> str:
            base, fragment = _split_href(unescape(value))
            source = posixpath.normpath(posixpath.join("" if full_path else posixpath.dirname(original), unquote(base)))
            if source not in mapping:
                return value
            target = mapping[source] if full_path else posixpath.relpath(mapping[source], posixpath.dirname(mapping.get(original, original)) or ".")
            return quote(target, safe="/-._~") + fragment
        text = re.sub(r'((?:\b|:)href|\bsrc|\bposter|\bdata|\bfull-path)(\s*=\s*)([\'"])(.*?)\3', lambda m: m[1]+m[2]+m[3]+rewrite(m[4], m[1] == "full-path")+m[3], text, flags=re.I)
        text = re.sub(r'url\(\s*([\'"]?)(.*?)\1\s*\)', lambda m: 'url('+m[1]+rewrite(m[2])+m[1]+')', text, flags=re.I)
        text = re.sub(r'(@import\s+)([\'"])(.*?)\2', lambda m: m[1]+m[2]+rewrite(m[3])+m[2], text, flags=re.I)
        text = re.sub(r'(<\?xml[^>]*encoding\s*=\s*)([\'"])[^\'"]+\2', r'\1\2utf-8\2', text, flags=re.I)
        _write_text_file(path, text)


class BookPrefs(dict):
    def __init__(self, store_path: Optional[Path] = None):
        super().__init__()
        self.defaults: Dict[str, object] = {}
        self.store_path = store_path or (Path.home() / ".epub3itizer_prefs.json")
        self._load()

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(payload, dict):
            super().update(payload)

    def __getitem__(self, key):  # type: ignore[override]
        if key in self.keys():
            return super().__getitem__(key)
        if key in self.defaults:
            return self.defaults[key]
        raise KeyError(key)

    def get(self, key, default=None):  # type: ignore[override]
        if key in self.keys():
            return super().get(key, default)
        if key in self.defaults:
            return self.defaults[key]
        return default

    def save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps(dict(self), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


class EpubBookAdapter:
    """
    Small compatibility layer that mimics the subset of Sigil's bk object used
    by the EPUB2 -> EPUB3 conversion logic.
    """

    def __init__(
        self,
        root_dir: Path,
        *,
        source_path: Optional[Path] = None,
        tempdir: Optional[tempfile.TemporaryDirectory] = None,
        prefs_path: Optional[Path] = None,
    ):
        self.root_dir = Path(root_dir).resolve()
        self.source_path = Path(source_path).resolve() if source_path is not None else self.root_dir
        self._tempdir = tempdir
        self._prefs = BookPrefs(prefs_path)
        self._opf_href = ""
        self._opf_path = Path()
        self._opf_dir = "."
        self._opf_version = "2.0"
        self._manifest_items: List[ManifestItem] = []
        self._manifest_by_id: Dict[str, ManifestItem] = {}
        self._spine_items: List[Tuple[str, str, str]] = []
        self._guide_items: List[Tuple[str, str, str]] = []
        self._load()

    @classmethod
    def open(cls, input_path: Path, prefs_path: Optional[Path] = None) -> "EpubBookAdapter":
        input_path = Path(input_path)
        if input_path.is_dir():
            return cls(input_path, source_path=input_path, prefs_path=prefs_path)

        tempdir = tempfile.TemporaryDirectory(prefix="epub3itizer_source_")
        try:
            with zipfile.ZipFile(input_path, "r") as zf:
                _extract_epub_archive(zf, Path(tempdir.name))
            return cls(Path(tempdir.name), source_path=input_path, tempdir=tempdir, prefs_path=prefs_path)
        except Exception:
            tempdir.cleanup()
            raise

    def __enter__(self) -> "EpubBookAdapter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._tempdir is not None:
            self._tempdir.cleanup()
            self._tempdir = None

    def _load(self) -> None:
        self._opf_href = self._find_container_rootfile()
        self._opf_path = self.resolve_bookpath(self._opf_href)
        self._opf_dir = posixpath.dirname(self._opf_href) or "."
        self._opf_version = self._detect_epub_version()
        self._manifest_items, self._spine_items, self._guide_items = self._parse_opf(self.readotherfile(self._opf_href))
        self._manifest_by_id = {item.id: item for item in self._manifest_items if item.id}
        self._spine_items = [
            (idref, linear, self.id_to_bookpath(idref) if idref in self._manifest_by_id else "")
            for idref, linear, _ in self._spine_items
        ]

    def _find_container_rootfile(self) -> str:
        container_path = self.root_dir / "META-INF" / "container.xml"
        if not container_path.exists():
            opf_candidates = sorted(self.root_dir.rglob("*.opf"))
            if not opf_candidates:
                raise FileNotFoundError("Could not find container.xml or any .opf file")
            return opf_candidates[0].relative_to(self.root_dir).as_posix()

        root = etree.fromstring(container_path.read_bytes(), XML_PARSER)
        rootfile = root.find(f".//{{{CONTAINER_NS}}}rootfile")
        if rootfile is None:
            raise ValueError("container.xml does not contain a rootfile entry")
        full_path = rootfile.get("full-path")
        if not full_path:
            raise ValueError("container.xml rootfile is missing full-path")
        return _normalize_bookpath(full_path)

    def _detect_epub_version(self) -> str:
        try:
            opf_data = self.readotherfile(self._opf_href)
            root = etree.fromstring(convert_named_entities(opf_data).encode("utf-8"), XML_PARSER)
            return root.get("version", "2.0")
        except Exception:
            return "2.0"

    def _parse_opf(self, opf_text: str) -> Tuple[List[ManifestItem], List[Tuple[str, str, str]], List[Tuple[str, str, str]]]:
        raw = convert_named_entities(opf_text)
        root = etree.fromstring(raw.encode("utf-8"), XML_PARSER)
        ns = {"opf": OPF_NS}
        manifest: List[ManifestItem] = []
        for item in root.xpath("./opf:manifest/opf:item", namespaces=ns):
            manifest.append(
                ManifestItem(
                    id=item.get("id", ""),
                    href=item.get("href", ""),
                    media_type=item.get("media-type", ""),
                    properties=item.get("properties", ""),
                )
            )

        spine: List[Tuple[str, str, str]] = []
        for itemref in root.xpath("./opf:spine/opf:itemref", namespaces=ns):
            idref = itemref.get("idref", "")
            linear = itemref.get("linear", "yes")
            spine.append((idref, linear, ""))

        guide: List[Tuple[str, str, str]] = []
        for ref in root.xpath("./opf:guide/opf:reference", namespaces=ns):
            guide.append((ref.get("type", ""), ref.get("title", ""), ref.get("href", "")))
        return manifest, spine, guide

    def resolve_bookpath(self, bookhref: str) -> Path:
        base, _frag = _split_href(bookhref)
        normalized = _normalize_bookpath(base)
        if normalized == "":
            return self.root_dir
        return (self.root_dir / Path(normalized)).resolve()

    def launcher_version(self) -> int:
        return 99999999

    def epub_version(self) -> str:
        return self._opf_version

    def getPrefs(self) -> BookPrefs:
        return self._prefs

    def savePrefs(self, prefs: BookPrefs) -> None:
        prefs.save()

    def copy_book_contents_to(self, dest: str | Path) -> None:
        shutil.copytree(self.root_dir, dest, dirs_exist_ok=True)

    def readfile(self, mid: str) -> str:
        item = self._manifest_by_id.get(mid)
        if item is None:
            raise KeyError(mid)
        return _read_text_file(self.resolve_bookpath(self.id_to_bookpath(mid)))

    def readotherfile(self, bookhref: str) -> str:
        return _read_text_file(self.resolve_bookpath(bookhref))

    def writeotherfile(self, bookhref: str, data: str) -> None:
        _write_text_file(self.resolve_bookpath(bookhref), data)

    def text_iter(self) -> Iterator[Tuple[str, str]]:
        seen = set()
        for idref, _linear, href in self._spine_items:
            item = self._manifest_by_id.get(idref)
            if item is not None and item.media_type == XHTML_MIME:
                seen.add(item.id)
                yield item.id, item.href
        for item in self._manifest_items:
            if item.media_type == XHTML_MIME and item.id not in seen:
                yield item.id, item.href

    def manifest_iter(self) -> Iterator[Tuple[str, str, str]]:
        for item in sorted(self._manifest_items, key=lambda entry: entry.id):
            yield item.id, item.href, item.media_type

    def spine_iter(self) -> Iterator[Tuple[str, str, str]]:
        for idref, linear, _href in self._spine_items:
            item = self._manifest_by_id.get(idref)
            yield idref, linear, item.href if item is not None else ""

    def gettocid(self) -> str:
        for item in self._manifest_items:
            if item.media_type == NCX_MIME:
                return item.id
        raise KeyError("No NCX manifest item found")

    def get_opfbookpath(self) -> str:
        return self._opf_href

    def id_to_bookpath(self, mid: str) -> str:
        item = self._manifest_by_id.get(mid)
        if item is None:
            raise KeyError(mid)
        href = item.href.replace("\\", "/")
        if not self._opf_dir or self._opf_dir == ".":
            return _normalize_bookpath(href)
        return _normalize_bookpath(posixpath.join(self._opf_dir, href))

    def build_bookpath(self, href: str, base: str) -> str:
        href = href.replace("\\", "/")
        base = base.replace("\\", "/")
        if not base or base == ".":
            return _normalize_bookpath(href)
        return _normalize_bookpath(posixpath.join(base, href))

    def get_startingdir(self, bookhref: str) -> str:
        base, _frag = _split_href(bookhref)
        return posixpath.dirname(base) or "."

    def get_relativepath(self, from_href: str, target_href: str) -> str:
        from_base, _from_frag = _split_href(from_href)
        target_base, target_frag = _split_href(target_href)
        if not target_base:
            return target_href
        if posixpath.dirname(from_base) in ("", "."):
            rel = posixpath.relpath(posixpath.normpath(target_base), start=".")
        else:
            rel = posixpath.relpath(posixpath.normpath(target_base), start=posixpath.dirname(from_base))
        if rel == ".":
            rel = posixpath.basename(target_base)
        return rel + target_frag

    def basename_to_id(self, href: str) -> Optional[str]:
        base = posixpath.basename(_split_href(href)[0])
        for item in self._manifest_items:
            if item.href == href or posixpath.basename(item.href) == base:
                return item.id
        return None

    def get_guide(self) -> List[Tuple[str, str, str]]:
        return list(self._guide_items)
