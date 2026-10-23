from lxml import etree
from epub3itizer.repair import repair_ncx_placeholder_titles
import pytest


@pytest.mark.parametrize('text', ['[此处填写标题]', '[此處填寫標題]', '保留的正式書名'])
def test_only_explicit_placeholder_changes(tmp_path, text):
    (tmp_path/'book.opf').write_text('''<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>製造文明</dc:title></metadata><manifest><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest></package>''', encoding='utf-8')
    ncx=tmp_path/'toc.ncx'
    ncx.write_text(f'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><docTitle><text>{text}</text></docTitle><navMap><navPoint id="n"><navLabel><text>此處是正文引用</text></navLabel><content src="a.xhtml#p"/></navPoint></navMap></ncx>',encoding='utf-8')
    repair_ncx_placeholder_titles(tmp_path,'book.opf')
    first=ncx.read_bytes();doc=etree.fromstring(first)
    assert doc.xpath('string(//*[local-name()="docTitle"])')==('製造文明' if text.startswith('[') else text)
    assert doc.xpath('string(//*[local-name()="navLabel"])')=='此處是正文引用'
    assert doc.xpath('string(//*[local-name()="content"]/@src)')=='a.xhtml#p'
    repair_ncx_placeholder_titles(tmp_path,'book.opf')
    assert ncx.read_bytes()==first


def test_exact_vote_pitch_keeps_quoted_story():
    from epub3itizer.conversion import remove_known_source_ad_paragraphs, XHTML_NS
    pitch='姊妹們，請支持《九重紫》進前十，在首頁的榜單上做做廣告！謝謝大家。O（∩_∩）O～'
    doc=etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>正文前</p><p>{pitch}</p><p>「{pitch}」</p><p>正文後</p></body></html>')
    remove_known_source_ad_paragraphs(doc)
    assert ''.join(doc.itertext())=='正文前「'+pitch+'」正文後'
    prior=etree.tostring(doc);remove_known_source_ad_paragraphs(doc)
    assert etree.tostring(doc)==prior
