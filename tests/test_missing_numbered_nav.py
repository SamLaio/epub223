from pathlib import Path

import pytest
from lxml import etree

from epub3itizer import repair


def package(tmp_path: Path, titles=('第一章 起', '第二章 中', '第三章 終')):
    (tmp_path / 'Text').mkdir()
    opf = '<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><manifest><item id="nav" href="Text/nav.xhtml" properties="nav" media-type="application/xhtml+xml"/>'
    opf += ''.join(f'<item id="c{i}" href="Text/{i}.xhtml" media-type="application/xhtml+xml"/>' for i in range(3))
    opf += '</manifest><spine>' + ''.join(f'<itemref idref="c{i}"/>' for i in range(3)) + '</spine></package>'
    (tmp_path / 'content.opf').write_text(opf, encoding='utf-8')
    for i, title in enumerate(titles):
        (tmp_path / f'Text/{i}.xhtml').write_text(f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>未知</title></head><body><p><br/></p><p>{title}</p><p>正文{i}，不可改動。</p></body></html>', encoding='utf-8')
    nav = '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol>'
    nav += f'<li><a href="0.xhtml">{titles[0]}</a></li><li><a href="2.xhtml">{titles[2]}</a></li>'
    (tmp_path / 'Text/nav.xhtml').write_text(nav + '</ol></nav></body></html>', encoding='utf-8')
    return tmp_path / 'Text/nav.xhtml'


@pytest.mark.parametrize('titles', [('第一章 起', '第二章 中', '第三章 終'), ('第21章 起', '第22章 中', '第23章 終')])
def test_add_only_existing_numbered_chapter_between_consecutive_neighbours(tmp_path, titles):
    nav = package(tmp_path, titles)
    originals = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file() and p != nav}
    repair.repair_missing_numbered_nav_entry(tmp_path, 'content.opf')
    tree = etree.fromstring(nav.read_bytes())
    links = tree.xpath('//*[local-name()="a"]')
    assert [a.get('href') for a in links] == ['0.xhtml', '1.xhtml', '2.xhtml']
    assert [a.text for a in links] == list(titles)
    assert all(p.read_bytes() == content for p, content in originals.items())
    first = nav.read_bytes()
    repair.repair_missing_numbered_nav_entry(tmp_path, 'content.opf')
    assert nav.read_bytes() == first


@pytest.mark.parametrize('case', ['nonchapter', 'nonconsecutive', 'empty', 'missing', 'fragment', 'different_parent', 'ncx', 'nonlinear', 'mixed_number', 'represented_fragment'])
def test_ambiguous_or_incomplete_navigation_stays_unchanged(tmp_path, case):
    titles = ('第一章 起', '版權頁', '第三章 終') if case == 'nonchapter' else ('第一章 起', '第二章 中', '第四章 終') if case == 'nonconsecutive' else ('第一章 起', '第二章 中', '第三章 終')
    nav = package(tmp_path, titles)
    if case == 'mixed_number':
        p = tmp_path / 'Text/1.xhtml'
        p.write_text(p.read_text(encoding='utf-8').replace('第二章', '第1二章'), encoding='utf-8')
    elif case == 'represented_fragment':
        nav.write_text(nav.read_text(encoding='utf-8').replace('</nav>', '<ol><li><a href="1.xhtml#part">第二章章內節點</a></li></ol></nav>'), encoding='utf-8')
    elif case == 'empty':
        p = tmp_path / 'Text/1.xhtml'
        p.write_text(p.read_text(encoding='utf-8').replace('<p>正文1，不可改動。</p>', ''), encoding='utf-8')
    elif case == 'missing':
        (tmp_path / 'Text/1.xhtml').unlink()
    elif case == 'fragment':
        nav.write_text(nav.read_text(encoding='utf-8').replace('2.xhtml', '2.xhtml#section'), encoding='utf-8')
    elif case == 'different_parent':
        nav.write_text(nav.read_text(encoding='utf-8').replace('</a></li><li>', '</a></li></ol><ol><li>'), encoding='utf-8')
    elif case in ('ncx', 'nonlinear'):
        p = tmp_path / 'content.opf'
        text = p.read_text(encoding='utf-8')
        text = text.replace('</manifest>', '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest>') if case == 'ncx' else text.replace('idref="c1"', 'idref="c1" linear="no"')
        p.write_text(text, encoding='utf-8')
    original = nav.read_bytes()
    repair.repair_missing_numbered_nav_entry(tmp_path, 'content.opf')
    assert nav.read_bytes() == original
