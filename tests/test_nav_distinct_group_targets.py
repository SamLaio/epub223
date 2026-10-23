"""同檔案不代表同目錄入口；保留分組標題的有效章內錨點。"""
from lxml import etree
from epub3itizer.conversion import cleanup_nav_leaf_spans


def test_distinct_parent_fragment_and_children_survive(tmp_path):
    (tmp_path / 'content.opf').write_text('''<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><manifest>
<item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/>
<item id="c" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c"/></spine></package>''', encoding='utf-8')
    (tmp_path / 'chapter.xhtml').write_text('''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>章</title></head><body><h1 id="group">藤之香</h1><h2 id="one">一</h2><p>正文</p><h2 id="two">二</h2><p>後文</p></body></html>''', encoding='utf-8')
    (tmp_path / 'nav.xhtml').write_text('''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>目錄</title></head><body><nav epub:type="toc"><ol><li><a href="chapter.xhtml#group">藤之香</a><ol><li><a href="chapter.xhtml#one">一</a></li><li><a href="chapter.xhtml#two">二</a></li></ol></li></ol></nav></body></html>''', encoding='utf-8')
    cleanup_nav_leaf_spans(tmp_path, 'content.opf')
    first = (tmp_path / 'nav.xhtml').read_bytes()
    doc = etree.fromstring(first)
    assert [(x.get('href'), x.text) for x in doc.findall('.//{*}a')] == [('chapter.xhtml#group', '藤之香'), ('chapter.xhtml#one', '一'), ('chapter.xhtml#two', '二')]
    cleanup_nav_leaf_spans(tmp_path, 'content.opf')
    assert (tmp_path / 'nav.xhtml').read_bytes() == first
