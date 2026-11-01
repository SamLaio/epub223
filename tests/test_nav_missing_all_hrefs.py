from pathlib import Path
from lxml import etree
import pytest
from epub3itizer.conversion import cleanup_nav_leaf_spans


def package(tmp_path, ambiguity=False, reverse=False, linked=False):
    (tmp_path/'content.opf').write_text('<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="nav" href="nav.xhtml" properties="nav"/><item id="a" href="a.xhtml"/><item id="b" href="b.xhtml"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>',encoding='utf-8')
    (tmp_path/'a.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>A</h1><p>正文A</p></body></html>',encoding='utf-8')
    (tmp_path/'b.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><body><h2>B</h2><h'+('1' if ambiguity else '3')+'>A</h'+('1' if ambiguity else '3')+'><p>正文B</p></body></html>',encoding='utf-8')
    titles=['B','A'] if reverse else ['A','B']
    href=' href="a.xhtml"' if linked else ''
    (tmp_path/'nav.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol>'+''.join(f'<li><a{href}>{t}</a></li>' for t in titles)+'</ol></nav></body></html>',encoding='utf-8')


def test_complete_unique_headings_restore_links_and_keep_reference_repeat(tmp_path):
    package(tmp_path)
    cleanup_nav_leaf_spans(tmp_path,'content.opf')
    nav=etree.parse(str(tmp_path/'nav.xhtml'))
    assert nav.xpath('//*[local-name()="a"]/@href')==['a.xhtml#recovered-toc-1','b.xhtml#recovered-toc-2']
    assert '正文A' in (tmp_path/'a.xhtml').read_text(encoding='utf-8')
    first={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    cleanup_nav_leaf_spans(tmp_path,'content.opf')
    assert first=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize('option',['ambiguity','reverse','linked'])
def test_no_guess_for_ambiguous_out_of_order_or_linked_toc(tmp_path,option):
    package(tmp_path,**{option:True})
    before={n:(tmp_path/n).read_bytes() for n in ['a.xhtml','b.xhtml']}
    cleanup_nav_leaf_spans(tmp_path,'content.opf')
    assert before=={n:(tmp_path/n).read_bytes() for n in before}
    assert 'recovered-toc' not in (tmp_path/'nav.xhtml').read_text(encoding='utf-8')
