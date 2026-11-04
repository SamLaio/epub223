from __future__ import annotations

from pathlib import Path
from typing import Optional

from .chinese import convert_chinese_in_package
from . import conversion as conv
from .compat import EpubBookAdapter

__all__ = [
    "repair_epub",
    "repair_epub_contents",
    "restore_verified_chapter_headings",
]


def restore_verified_chapter_headings(root_dir: Path, headings: dict[str, str], toc_paths: list[str]) -> None:
    """依人工核對的完整文字恢復章標，並在指定 XHTML 目錄補入錨點。"""
    import copy
    import hashlib
    import posixpath
    import re
    from urllib.parse import unquote, urlsplit
    from lxml import etree

    root_dir = root_dir.resolve()
    documents = {}

    def document(relative):
        path = (root_dir / relative).resolve()
        if not path.is_relative_to(root_dir) or path == root_dir:
            raise ValueError('章標修復路徑超出工作目錄')
        if path not in documents:
            documents[path] = etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True))
        return documents[path]

    for relative, original in headings.items():
        match = re.fullmatch(r'(第[零〇一二三四五六七八九十百千兩两0-9]+)\s+(.{1,100})', original)
        if not match:
            raise ValueError('須提供缺少章字的完整已核對章標')
        label = f'{match[1]}章 {match[2]}'
        doc = document(relative)
        matches = doc.xpath('//*[local-name()="p" and normalize-space(.)=$label]', label=original)
        if len(matches) != 1 or len(matches[0]) or set(matches[0].attrib) - {'class'}:
            raise ValueError(f'章標不唯一、已修復或含錨點：{relative}')
        node = matches[0]
        following = node.getnext()
        if following is None or not ''.join(following.itertext()).strip():
            raise ValueError(f'章標後無正文：{relative}')
        anchor_id = 'restored-chapter-' + hashlib.sha256(original.encode('utf-8')).hexdigest()[:12]
        if doc.xpath('//*[@id=$value]', value=anchor_id):
            raise ValueError('章標錨點重複')
        node.tag = f'{{{conv.XHTML_NS}}}h2'
        node.set('id', anchor_id)
        node.text = label
        for toc_relative in toc_paths:
            toc = document(toc_relative)
            anchors = []
            for a in toc.xpath('//*[local-name()="a"][@href]'):
                url = urlsplit(a.get('href'))
                target = posixpath.normpath(posixpath.join(posixpath.dirname(toc_relative), unquote(url.path)))
                if not url.scheme and not url.netloc and not url.fragment and target == relative:
                    anchors.append(a)
            if len(anchors) != 1 or etree.QName(anchors[0].getparent()).localname != 'li':
                raise ValueError(f'目錄入口不唯一：{toc_relative} / {relative}')
            old = anchors[0]
            entry = copy.deepcopy(old.getparent())
            if len(entry) != 1 or entry[0].get('id') or entry.get('id'):
                raise ValueError('目錄項目含複雜結構或既有錨點')
            entry[0].clear()
            entry[0].set('href', old.get('href') + '#' + anchor_id)
            entry[0].text = label
            old.getparent().addnext(entry)
    # 完整計畫通過才開始寫入；呼叫端仍須於工作副本執行並重跑格式驗證。
    for path, doc in documents.items():
        path.write_bytes(etree.tostring(doc, encoding='utf-8', xml_declaration=True))


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
    repair_missing_numbered_nav_entry(root_dir, opf_href)
    repair_body_fragment_links(root_dir)
    repair_media_overlays(root_dir, opf_href)


def repair_media_overlays(root_dir: Path, opf_href: str) -> None:
    """依既有 SMIL 補齊 MIME 與缺少時長，保留音訊、同步點及正文。"""
    from decimal import Decimal
    import re
    from urllib.parse import unquote, urlsplit
    from lxml import etree

    def seconds(value):
        if value is None:
            raise ValueError("SMIL 缺少 clipEnd，無法安全推算同步朗讀時長")
        if re.fullmatch(r"\d+(?:\.\d+)?(?:h|min|s|ms)?", value):
            match = re.fullmatch(r"(\d+(?:\.\d+)?)(h|min|s|ms)?", value)
            return Decimal(match[1]) * {None: 1, 'h': 3600, 'min': 60, 's': 1, 'ms': Decimal('.001')}[match[2]]
        if re.fullmatch(r"(?:\d+:)?[0-5]?\d:[0-5]?\d(?:\.\d+)?", value):
            result = Decimal(0)
            for part in value.split(':'):
                result = result * 60 + Decimal(part)
            return result
        raise ValueError(f"無法安全解析 SMIL 時間：{value}")

    opf = root_dir / opf_href
    package = etree.fromstring(opf.read_bytes())
    ns = f'{{{conv.OPF_NS}}}'
    items = {i.get('id'): i for i in package.findall(f'{ns}manifest/{ns}item')}
    overlay_ids = dict.fromkeys(i.get('media-overlay') for i in items.values() if i.get('media-overlay'))
    if not overlay_ids:
        return
    metadata = package.find(f'{ns}metadata')
    durations = {m.get('refines'): m for m in metadata.findall(f'{ns}meta') if m.get('property') == 'media:duration'}
    total = Decimal(0)
    for identifier in overlay_ids:
        item = items.get(identifier)
        if item is None:
            raise ValueError(f"同步朗讀指向不存在的 manifest ID：{identifier}")
        url = urlsplit(item.get('href', ''))
        if url.scheme or url.netloc:
            raise ValueError("同步朗讀必須是包內 SMIL")
        path = (opf.parent / unquote(url.path)).resolve()
        path.relative_to(root_dir.resolve())
        smil = etree.fromstring(path.read_bytes())
        if smil.tag != '{http://www.w3.org/ns/SMIL}smil':
            raise ValueError(f"同步朗讀文件不是 SMIL：{item.get('href')}")
        item.set('media-type', 'application/smil+xml')
        refinement = '#' + identifier
        if refinement not in durations:
            audio = smil.findall('.//{http://www.w3.org/ns/SMIL}audio')
            if not audio:
                raise ValueError("SMIL 沒有音訊片段，無法安全推算時長")
            duration = Decimal(0)
            for clip in audio:
                length = seconds(clip.get('clipEnd')) - seconds(clip.get('clipBegin', '0'))
                if length < 0:
                    raise ValueError("SMIL clipEnd 早於 clipBegin")
                duration += length
            elem = etree.SubElement(metadata, f'{ns}meta', property='media:duration', refines=refinement)
            elem.text = f'{duration:f}s'
            durations[refinement] = elem
        total += seconds(durations[refinement].text)
    if None not in durations:
        durations[None] = etree.SubElement(metadata, f'{ns}meta', property='media:duration')
    if not durations[None].text or seconds(durations[None].text) != total:
        durations[None].text = f'{total:f}s'
    data = etree.tostring(package, encoding='utf-8', xml_declaration=True)
    if opf.read_bytes() != data:
        opf.write_bytes(data)



def repair_body_fragment_links(root_dir: Path) -> None:
    """將指向唯一 body ID 的本機連結改連至頁面，保留其他錨點與正文。"""
    from urllib.parse import unquote, urlsplit, urlunsplit
    from lxml import etree

    root_dir = root_dir.resolve()
    documents = {}
    bodies = {}
    for path in root_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".xhtml", ".html", ".htm", ".ncx"}:
            continue
        path = path.resolve()
        if not path.is_relative_to(root_dir):
            continue
        try:
            tree = etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True))
        except etree.XMLSyntaxError:
            continue
        # xml:base 會改變連結基準；無法依檔案位置安全判定時保留。
        if tree.xpath("//@xml:base", namespaces={"xml": "http://www.w3.org/XML/1998/namespace"}):
            continue
        if tree.find(f".//{{{conv.XHTML_NS}}}base") is not None:
            continue
        documents[path] = tree
        body = tree.find(f"{{{conv.XHTML_NS}}}body")
        if body is not None and body.get("id"):
            body_id = body.get("id")
            if len(tree.xpath("//*[@id=$value]", value=body_id)) == 1:
                bodies[path] = body_id

    for path, tree in documents.items():
        changed = False
        for node in tree.iter():
            for attribute in ("href", "src"):
                href = node.get(attribute)
                if not href:
                    continue
                try:
                    url = urlsplit(href)
                except ValueError:
                    continue
                if url.scheme or url.netloc or url.query or not url.fragment:
                    continue
                target = (path.parent / unquote(url.path)).resolve() if url.path else path
                if bodies.get(target) != unquote(url.fragment):
                    continue
                node.set(attribute, urlunsplit(("", "", url.path or path.name, "", "")))
                changed = True
        if changed:
            tree.write(str(path), encoding="utf-8", xml_declaration=True)


def repair_missing_numbered_nav_entry(root_dir: Path, opf_href: str) -> None:
    """只補入兩個連號同層目錄之間、已有完整正文的單一漏列章節。"""
    import posixpath
    import re
    from urllib.parse import quote, unquote, urlsplit
    from lxml import etree

    root_dir = root_dir.resolve()
    opf = root_dir / opf_href
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    package = etree.fromstring(opf.read_bytes(), parser)
    items = package.findall(f'{{{conv.OPF_NS}}}manifest/{{{conv.OPF_NS}}}item')
    navs = [e for e in items if 'nav' in e.get('properties', '').split()]
    if len(navs) != 1 or any(e.get('media-type') == 'application/x-dtbncx+xml' for e in items):
        return

    def local(base: Path, href: str) -> Optional[Path]:
        url = urlsplit(href)
        if url.scheme or url.netloc or url.fragment or url.query or not url.path:
            return None
        path = (base / unquote(url.path)).resolve()
        try:
            path.relative_to(root_dir)
        except ValueError:
            return None
        return path if path.is_file() else None

    def ordinal(label: str):
        match = re.match(r'^第\s*([0-9０-９零〇一二三四五六七八九十百千兩两]+)\s*([章回])', label)
        if not match:
            return None
        text = match[1].translate(str.maketrans('０１２３４５６７８９兩两〇', '0123456789二二零'))
        if text.isdigit():
            return int(text), match[2]
        digits = dict(zip('零一二三四五六七八九', range(10)))
        units = {'十': 10, '百': 100, '千': 1000}
        if any(c not in digits and c not in units for c in text):
            return None
        if not any(c in units for c in text):
            return int(''.join(str(digits[c]) for c in text)), match[2]
        total = current = 0
        for char in text:
            if char in digits:
                current = digits[char]
            elif char in units:
                total += (current or 1) * units[char]
                current = 0
            else:
                return None
        return total + current, match[2]

    nav_path = local(opf.parent, navs[0].get('href', ''))
    if nav_path is None:
        return
    tree = etree.fromstring(nav_path.read_bytes(), parser)
    tocs = tree.xpath('//*[local-name()="nav" and contains(concat(" ", @epub:type, " "), " toc ")]', namespaces={'epub': conv.EPUB_NS})
    if len(tocs) != 1:
        return
    by_id = {e.get('id'): e for e in items}
    spine = []
    for ref in package.findall(f'{{{conv.OPF_NS}}}spine/{{{conv.OPF_NS}}}itemref'):
        item = by_id.get(ref.get('idref'))
        if item is not None and ref.get('linear') != 'no' and item.get('media-type') == 'application/xhtml+xml':
            path = local(opf.parent, item.get('href', ''))
            if path is not None:
                spine.append(path)
    if len(spine) != len(set(spine)):
        return
    links = {}
    represented = set()
    for anchor in tocs[0].iter(f'{{{conv.XHTML_NS}}}a'):
        url = urlsplit(anchor.get('href', ''))
        represented_path = local(nav_path.parent, url._replace(fragment='').geturl())
        if represented_path is not None:
            represented.add(represented_path)
        path = local(nav_path.parent, anchor.get('href', ''))
        if path is not None:
            links.setdefault(path, []).append(anchor)
    changed = False
    for index, path in enumerate(spine[1:-1], 1):
        if path in represented or len(links.get(spine[index - 1], [])) != 1 or len(links.get(spine[index + 1], [])) != 1:
            continue
        left, right = links[spine[index - 1]][0], links[spine[index + 1]][0]
        a, c = ordinal(''.join(left.itertext()).strip()), ordinal(''.join(right.itertext()).strip())
        li, next_li = left.getparent(), right.getparent()
        if not a or not c or a[1] != c[1] or c[0] != a[0] + 2 or li.tag != f'{{{conv.XHTML_NS}}}li' or li.getnext() is not next_li or li.getparent().tag != f'{{{conv.XHTML_NS}}}ol':
            continue
        doc = etree.fromstring(path.read_bytes(), parser)
        body = doc.find(f'{{{conv.XHTML_NS}}}body')
        blocks = [] if body is None else [e for e in body.iter() if isinstance(e.tag, str) and etree.QName(e).localname in {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'} and ''.join(e.itertext()).strip()]
        if not blocks:
            continue
        label = ''.join(blocks[0].itertext()).strip()
        text = ''.join(body.itertext()).strip()
        if len(label) > 120 or ordinal(label) != (a[0] + 1, a[1]) or not text.startswith(label) or not text[len(label):].strip():
            continue
        entry = etree.Element(f'{{{conv.XHTML_NS}}}li')
        href = quote(posixpath.relpath(path.as_posix(), nav_path.parent.as_posix()), safe='/-._~')
        etree.SubElement(entry, f'{{{conv.XHTML_NS}}}a', href=href).text = label
        next_li.addprevious(entry)
        changed = True
    if changed:
        nav_path.write_bytes(etree.tostring(tree, encoding='utf-8', xml_declaration=True))


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
