from __future__ import annotations

from pathlib import Path
from typing import Optional

from .chinese import convert_chinese_in_package
from . import conversion as conv
from .compat import EpubBookAdapter

__all__ = [
    "repair_epub",
    "repair_epub_contents",
]


def repair_epub_contents(root_dir: Path, opf_href: str) -> None:
    """Run the reusable EPUB repair pipeline in-place."""
    conv.convert_bmp_images(root_dir)
    conv.normalize_raster_image_extensions(root_dir)
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
    repair_obfuscated_font_media_types(root_dir, opf_href)
    repair_ncx_placeholder_titles(root_dir, opf_href)
    repair_horizontal_spine_direction(root_dir, opf_href)


def repair_horizontal_spine_direction(root_dir: Path, opf_href: str) -> None:
    """確認正文根元素為橫排後，只移除過時的 spine RTL 宣告。"""
    import re
    from urllib.parse import unquote, urlsplit
    from lxml import etree
    import tinycss2

    opf = root_dir / opf_href
    package = etree.fromstring(opf.read_bytes())
    spine = package.find(f'{{{conv.OPF_NS}}}spine')
    if spine is None or spine.get('page-progression-direction') != 'rtl':
        return
    manifest = {e.get('id'): e for e in package.findall(f'{{{conv.OPF_NS}}}manifest/{{{conv.OPF_NS}}}item')}
    horizontal = {'horizontal-tb', 'lr-tb', 'rl-tb'}
    found_body = False

    def local_path(base: Path, href: str) -> Path:
        url = urlsplit(href)
        if url.scheme or url.netloc:
            raise ValueError('外部樣式無法確認')
        path = (base / unquote(url.path)).resolve()
        path.relative_to(root_dir.resolve())
        return path

    def root_selector(selector: str, roots: list) -> bool:
        # 只認可可明確匹配 html／body 的簡單選擇器，不猜測複雜 CSS cascade。
        for part in selector.split(','):
            match = re.fullmatch(r'\s*(html|body|\*)?((?:[.#][\w-]+)*)\s*', part)
            if not match or not part.strip():
                continue
            for elem in roots:
                if match[1] not in (None, '*', etree.QName(elem).localname):
                    continue
                tokens = re.findall(r'([.#])([\w-]+)', match[2])
                if all(value in elem.get('class', '').split() if prefix == '.' else value == elem.get('id') for prefix, value in tokens):
                    return True
        return False

    try:
        for ref in spine:
            item = manifest.get(ref.get('idref'))
            if item is None or item.get('media-type') != 'application/xhtml+xml' or 'nav' in item.get('properties', '').split():
                continue
            path = local_path(opf.parent, item.get('href', ''))
            doc = etree.fromstring(path.read_bytes())
            body = doc.find(f'{{{conv.XHTML_NS}}}body')
            if body is None or not ''.join(body.itertext()).strip():
                continue
            if any(e.get('dir', '').lower() == 'rtl' for e in doc.iter() if isinstance(e.tag, str)):
                return
            roots = [doc, body]
            confirmed = False
            visited = set()

            def declarations(content, applies: bool) -> None:
                nonlocal confirmed
                for node in tinycss2.parse_declaration_list(content, skip_comments=True, skip_whitespace=True):
                    if node.type == 'error':
                        raise ValueError('樣式無法確認')
                    if node.type == 'declaration' and node.lower_name in ('writing-mode', '-epub-writing-mode', '-webkit-writing-mode'):
                        mode = tinycss2.serialize(node.value).strip().lower()
                        if mode not in horizontal:
                            raise ValueError('直排、混合或未知排版')
                        confirmed |= applies

            def stylesheet(content, base: Path, unconditional: bool = True) -> None:
                for node in tinycss2.parse_stylesheet(content, skip_comments=True, skip_whitespace=True):
                    if node.type == 'error':
                        raise ValueError('樣式無法確認')
                    if node.type == 'qualified-rule':
                        declarations(node.content, unconditional and root_selector(tinycss2.serialize(node.prelude), roots))
                    elif node.type == 'at-rule' and node.lower_at_keyword == 'import':
                        tokens = [t for t in node.prelude if t.type not in ('whitespace', 'comment')]
                        token = tokens[0]
                        href = token.value if token.type in ('string', 'url') else tinycss2.serialize(token.arguments).strip().strip('\"\'') if token.type == 'function' and token.lower_name == 'url' else ''
                        if not href:
                            raise ValueError('匯入樣式無法確認')
                        linked = local_path(base, href)
                        if linked not in visited:
                            visited.add(linked)
                            stylesheet(linked.read_text(encoding='utf-8-sig'), linked.parent, unconditional and len(tokens) == 1)
                    elif node.type == 'at-rule' and node.content is not None and node.lower_at_keyword not in ('font-face', 'page'):
                        stylesheet(node.content, base, False)

            for elem in doc.iter():
                if not isinstance(elem.tag, str):
                    continue
                declarations(elem.get('style', ''), elem in roots)
                if elem.tag == f'{{{conv.XHTML_NS}}}style':
                    stylesheet(elem.text or '', path.parent)
                elif elem.tag == f'{{{conv.XHTML_NS}}}link' and 'stylesheet' in elem.get('rel', '').split():
                    linked = local_path(path.parent, elem.get('href', ''))
                    stylesheet(linked.read_text(encoding='utf-8-sig'), linked.parent)
            if not confirmed:
                return
            found_body = True
    except (ValueError, OSError, etree.XMLSyntaxError, IndexError):
        return
    if found_body:
        del spine.attrib['page-progression-direction']
        opf.write_bytes(etree.tostring(package, encoding='utf-8', xml_declaration=True))


def repair_obfuscated_font_media_types(root_dir: Path, opf_href: str) -> None:
    """僅修 IDPF 字型混淆清單的 MIME，保留資源位元組與混淆設定。"""
    from urllib.parse import unquote
    from lxml import etree

    encryption = root_dir / 'META-INF/encryption.xml'
    if not encryption.exists():
        return
    encrypted = etree.fromstring(encryption.read_bytes())
    ns = {'enc': 'http://www.w3.org/2001/04/xmlenc#'}
    fonts = set()
    for node in encrypted.findall('.//enc:EncryptedData', ns):
        method = node.find('enc:EncryptionMethod', ns)
        ref = node.find('enc:CipherData/enc:CipherReference', ns)
        if method is not None and method.get('Algorithm') == 'http://www.idpf.org/2008/embedding' and ref is not None:
            path = (root_dir / unquote(ref.get('URI', ''))).resolve()
            path.relative_to(root_dir.resolve())
            if path.is_file():
                fonts.add(path)
    opf = root_dir / opf_href
    package = etree.fromstring(opf.read_bytes())
    changed = False
    for item in package.findall(f'.//{{{conv.OPF_NS}}}manifest/{{{conv.OPF_NS}}}item'):
        path = (opf.parent / unquote(item.get('href', ''))).resolve()
        if path in fonts and item.get('media-type') in {'application/octet-stream', 'chemical/x-mopac-input'}:
            item.set('media-type', 'application/vnd.ms-opentype')
            changed = True
    if changed:
        opf.write_bytes(etree.tostring(package, encoding='utf-8', xml_declaration=True))


def repair_ncx_placeholder_titles(root_dir: Path, opf_href: str) -> None:
    """只以正式書名補明確占位標題，不改章節或有效目錄標題。"""
    from urllib.parse import unquote
    from lxml import etree

    opf_path = root_dir / opf_href
    package = etree.fromstring(opf_path.read_bytes())
    title = package.find(f".//{{{conv.DC_NS}}}title")
    if title is None or not (title.text or "").strip():
        return
    for item in package.findall(f".//{{{conv.OPF_NS}}}manifest/{{{conv.OPF_NS}}}item"):
        if item.get("media-type") != "application/x-dtbncx+xml":
            continue
        path = (opf_path.parent / unquote(item.get("href", ""))).resolve()
        path.relative_to(root_dir.resolve())
        if not path.is_file():
            continue
        doc = etree.fromstring(path.read_bytes())
        node = doc.find(f"{{{conv.NCX_NS}}}docTitle/{{{conv.NCX_NS}}}text")
        if node is not None and (node.text or "").strip() in {"[此处填写标题]", "[此處填寫標題]"}:
            node.text = title.text
            path.write_bytes(etree.tostring(doc, encoding="utf-8", xml_declaration=True))


def _default_repair_output_path(input_path: Path) -> Path:
    if input_path.is_dir():
        return input_path.with_name(f"{input_path.name}_repaired.epub")
    return input_path.with_name(f"{input_path.stem}_repaired.epub")


def repair_epub(input_path: Path, output_path: Optional[Path] = None, convert_chinese: Optional[str] = None) -> Path:
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
        convert_chinese_in_package(book.root_dir, convert_chinese)
        mimetype_path = book.root_dir / "mimetype"
        conv.write_text_file(mimetype_path, "application/epub+zip")
        conv.zip_epub(book.root_dir, output_path)

    return output_path
