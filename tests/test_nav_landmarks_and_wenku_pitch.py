import pytest
from lxml import etree
from epub3itizer.conversion import cleanup_nav_leaf_spans, remove_known_source_ad_paragraphs, XHTML_NS


def test_toc_fragment_does_not_remove_landmark_or_page_list(tmp_path):
    (tmp_path/'content.opf').write_text('''<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><manifest>
<item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/>
<item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>
</manifest><spine><itemref idref="chapter"/></spine></package>''',encoding='utf-8')
    path=tmp_path/'nav.xhtml'
    path.write_text(f'''<html xmlns="{XHTML_NS}" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>目錄</title></head><body>
<nav epub:type="toc"><ol><li><a href="chapter.xhtml#start">楔子</a></li></ol></nav>
<nav epub:type="landmarks"><ol><li><a epub:type="bodymatter" href="chapter.xhtml">本文</a></li></ol></nav>
<nav epub:type="page-list"><ol><li><a href="chapter.xhtml">1</a></li></ol></nav>
</body></html>''',encoding='utf-8')
    cleanup_nav_leaf_spans(tmp_path,'content.opf')
    doc=etree.fromstring(path.read_bytes())
    assert doc.xpath('//*[local-name()="a"]/@href')==['chapter.xhtml#start','chapter.xhtml','chapter.xhtml']
    assert '本文' in ''.join(doc.itertext())
    prior=path.read_bytes();cleanup_nav_leaf_spans(tmp_path,'content.opf');assert path.read_bytes()==prior


@pytest.mark.parametrize('pitch',[
 '更多精彩熱門日本輕小說、動漫小說，輕小說文庫(http://www.wenku8.com) 為你一網打盡！',
 '更多精彩热门日本轻小说、动漫小说，轻小说文库(https://www.wenku8.cn)为你一网打尽！',
])
def test_exact_wenku_pitch_preserves_quotes_anchors_mentions_and_tail(pitch):
    doc=etree.fromstring(f'''<html xmlns="{XHTML_NS}"><body>
<p>{pitch}</p>保留尾文
<p>「{pitch}」</p><p>他想看更多精彩的小說，也提到wenku8.com。</p>
<p id="anchor">{pitch}</p><p><a href="chapter.xhtml">{pitch}</a></p>
<p>錄入：小明</p><p>更多精彩熱門日本輕小說</p></body></html>''')
    remove_known_source_ad_paragraphs(doc)
    assert len(doc.findall('.//{*}p'))==6
    assert '保留尾文' in ''.join(doc.itertext())and '錄入：小明' in ''.join(doc.itertext())
    assert doc.xpath('//*[@id="anchor"]')and doc.xpath('//*[local-name()="a"]/@href')==['chapter.xhtml']
    prior=etree.tostring(doc);remove_known_source_ad_paragraphs(doc);assert etree.tostring(doc)==prior
