import pytest
from lxml import etree as E
from epub3itizer.verified_toc import append_verified_paragraph_toc


def fixture(tmp_path):
    for name, text in {
        'chapter.xhtml':'<html xmlns="http://www.w3.org/1999/xhtml"><body><p class="c">第001章</p><p>正文不變。</p><p>第002章 完</p><p>尾文。</p></body></html>',
        'nav.xhtml':'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="chapter.xhtml">開始</a></li></ol></nav></body></html>',
        'toc.ncx':'<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap><navPoint id="start"><navLabel><text>開始</text></navLabel><content src="chapter.xhtml"/></navPoint></navMap></ncx>',
    }.items():
        (tmp_path/name).write_text(text, encoding='utf8')


def test_verified_entries_preserve_text_and_start(tmp_path):
    fixture(tmp_path)
    before = ''.join(E.parse(str(tmp_path/'chapter.xhtml')).getroot().itertext())
    append_verified_paragraph_toc(tmp_path, [('chapter.xhtml','第001章'),('chapter.xhtml','第002章 完')], 'nav.xhtml', 'toc.ncx')
    assert ''.join(E.parse(str(tmp_path/'chapter.xhtml')).getroot().itertext()) == before
    assert E.parse(str(tmp_path/'nav.xhtml')).xpath('//*[local-name()="a"]/text()') == ['開始','第001章','第002章 完']
    assert E.parse(str(tmp_path/'toc.ncx')).xpath('//*[local-name()="content"]/@src') == ['chapter.xhtml','chapter.xhtml#verified-chapter-1','chapter.xhtml#verified-chapter-2']


def test_epub3_without_ncx_only_updates_nav(tmp_path):
    fixture(tmp_path)
    original = (tmp_path/'toc.ncx').read_bytes()
    append_verified_paragraph_toc(tmp_path, [('chapter.xhtml','第001章')], 'nav.xhtml')
    assert len(E.parse(str(tmp_path/'nav.xhtml')).xpath('//*[local-name()="a"]')) == 2
    assert (tmp_path/'toc.ncx').read_bytes() == original


@pytest.mark.parametrize('entries', [[('chapter.xhtml','第001章'),('chapter.xhtml','不存在')], [('../outside.xhtml','章標')], [('chapter.xhtml','第001章')]*2])
def test_invalid_plan_writes_nothing(tmp_path, entries):
    fixture(tmp_path)
    before = {p:p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises((ValueError, OSError)):
        append_verified_paragraph_toc(tmp_path, entries, 'nav.xhtml', 'toc.ncx')
    assert all(p.read_bytes()==data for p,data in before.items())
