"""僅依人工核對清單補入段落章標目錄，不自動猜測正文。"""
from pathlib import Path
import posixpath
from lxml import etree as E


def append_verified_paragraph_toc(root_dir: Path, entries: list[tuple[str, str]], nav_href: str, ncx_href: str | None = None) -> None:
    """保留原本單一入口，為已核對且唯一的純文字段落新增 nav／NCX。"""
    root_dir = root_dir.resolve()
    documents = {}

    def document(relative):
        path = (root_dir / relative).resolve()
        if not path.is_relative_to(root_dir) or path == root_dir:
            raise ValueError('目錄修復路徑超出工作目錄')
        if path not in documents:
            documents[path] = E.parse(str(path), E.XMLParser(resolve_entities=False, no_network=True))
        return documents[path]

    if not entries or len(set(entries)) != len(entries):
        raise ValueError('須提供不重複的已核對章標清單')
    nav = document(nav_href)
    ncx = document(ncx_href) if ncx_href else None
    lists = nav.xpath('//*[local-name()="nav" and @*[local-name()="type"]="toc"]/*[local-name()="ol"]')
    maps = ncx.xpath('//*[local-name()="navMap"]') if ncx is not None else []
    if len(lists) != 1 or len(lists[0]) != 1 or ncx is not None and (len(maps) != 1 or len(maps[0]) != 1):
        raise ValueError('只允許補入原本只有單一入口的目錄')
    if len(lists[0].xpath('.//*[local-name()="a"]')) != 1 or maps and len(maps[0].xpath('.//*[local-name()="navPoint"]')) != 1:
        raise ValueError('目錄含額外分組，須人工確認')
    xns = '{http://www.w3.org/1999/xhtml}'
    nns = '{http://www.daisy.org/z3986/2005/ncx/}'
    for number, (href, label) in enumerate(entries, 1):
        doc = document(href)
        nodes = doc.xpath('//*[local-name()="body"]//*[local-name()="p" and normalize-space(.)=$label]', label=label)
        if len(nodes) != 1 or len(nodes[0]) or set(nodes[0].attrib) - {'class'}:
            raise ValueError(f'章標不唯一或含既有結構：{href} / {label}')
        node = nodes[0]
        if node.getnext() is None or not ''.join(node.getnext().itertext()).strip():
            raise ValueError(f'章標後無正文：{label}')
        anchor = f'verified-chapter-{number}'
        if doc.xpath('//*[@id=$v]', v=anchor) or ncx is not None and ncx.xpath('//*[@id=$v]', v=anchor):
            raise ValueError('章標錨點衝突')
        node.set('id', anchor)
        li = E.SubElement(lists[0], xns + 'li')
        E.SubElement(li, xns + 'a', href=posixpath.relpath(href, posixpath.dirname(nav_href) or '.') + '#' + anchor).text = label
        if maps:
            point = E.SubElement(maps[0], nns + 'navPoint', id=anchor)
            E.SubElement(E.SubElement(point, nns + 'navLabel'), nns + 'text').text = label
            E.SubElement(point, nns + 'content', src=posixpath.relpath(href, posixpath.dirname(ncx_href) or '.') + '#' + anchor)
    if maps:
        for number, point in enumerate(maps[0], 1):
            point.set('playOrder', str(number))
    for path, doc in documents.items():
        path.write_bytes(E.tostring(doc, encoding='utf-8', xml_declaration=True))
