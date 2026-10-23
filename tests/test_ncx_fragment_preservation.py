"""NCX、頁碼與轉換後目錄必須保留同檔案的不同小節入口。"""
from lxml import etree
import pytest
from epub3itizer.conversion import (
    TocNode, build_nav, cleanup_nav_leaf_spans, filter_pagelist_to_spine,
    filter_toc_to_spine, parse_ncx_file, write_ncx_file,
)


@pytest.mark.parametrize('href', ['Text/chapter.xhtml#part', 'text/CHAPTER.XHTML#part', 'Other/chapter.html#part'])
def test_spine_resolution_preserves_fragment(href):
    nodes = filter_toc_to_spine([TocNode('小節', href, [])], ['Text/chapter.xhtml'])
    assert nodes[0].href == 'Text/chapter.xhtml#part'
    assert filter_pagelist_to_spine([('1', href)], ['Text/chapter.xhtml']) == [('1', 'Text/chapter.xhtml#part')]


def test_ncx_roundtrip_keeps_distinct_fragments_and_deduplicates_exact_target(tmp_path):
    path = tmp_path / 'toc.ncx'
    nodes = [TocNode('第一節', 'Text/chapter.xhtml#one', []), TocNode('第二節', 'Text/chapter.xhtml#two', []), TocNode('重複', 'Text/chapter.xhtml#one', [])]
    write_ncx_file(path, 'OEBPS/toc.ncx', '書', nodes)
    expected = ['../Text/chapter.xhtml#one', '../Text/chapter.xhtml#two']
    assert etree.parse(str(path)).xpath('//*[local-name()="content"]/@src') == expected
    parse_ncx_file(path, 'OEBPS/toc.ncx')
    assert etree.parse(str(path)).xpath('//*[local-name()="content"]/@src') == expected


def test_converted_nav_keeps_parent_and_all_chapter_sections(tmp_path):
    (tmp_path / 'Text').mkdir()
    (tmp_path / 'Text/chapter.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>章</h1><h2 id="one">一</h2><p>正文</p><h2 id="two">二</h2></body></html>', encoding='utf-8')
    (tmp_path / 'content.opf').write_text('<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="c" href="Text/chapter.xhtml"/><item id="n" href="nav.xhtml" properties="nav"/></manifest><spine><itemref idref="c"/></spine></package>', encoding='utf-8')
    nodes = [TocNode('章', 'Text/chapter.xhtml', [TocNode('一', 'Text/chapter.xhtml#one', []), TocNode('二', 'Text/chapter.xhtml#two', [])])]
    nav = tmp_path / 'nav.xhtml'
    nav.write_text(build_nav('nav.xhtml', '書', filter_toc_to_spine(nodes, ['Text/chapter.xhtml']), [], [], '.'), encoding='utf-8')
    cleanup_nav_leaf_spans(tmp_path, 'content.opf')
    expected = ['Text/chapter.xhtml', 'Text/chapter.xhtml#one', 'Text/chapter.xhtml#two']
    assert etree.parse(str(nav)).xpath('//*[local-name()="a"]/@href') == expected
    first = nav.read_bytes()
    cleanup_nav_leaf_spans(tmp_path, 'content.opf')
    assert nav.read_bytes() == first
