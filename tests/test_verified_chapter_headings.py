import pytest
import hashlib
from lxml import etree
from epub3itizer.repair import restore_verified_chapter_headings


def package(tmp_path):
    ns = 'http://www.w3.org/1999/xhtml'
    (tmp_path/'chapter.xhtml').write_text(f'<html xmlns="{ns}"><body><h2>第九十九章 前章</h2><p>前文</p><p class="a">第一百 粉絲見面會</p><p>完整正文</p></body></html>',encoding='utf-8')
    for name in ['nav.xhtml','toc.xhtml']:
        (tmp_path/name).write_text(f'<html xmlns="{ns}"><body><ol><li><a href="chapter.xhtml">第九十九章 前章</a></li></ol></body></html>',encoding='utf-8')


def test_verified_plan_keeps_body_and_updates_both_tocs(tmp_path):
    package(tmp_path)
    restore_verified_chapter_headings(tmp_path, {'chapter.xhtml':'第一百 粉絲見面會'}, ['nav.xhtml','toc.xhtml'])
    doc=etree.parse(str(tmp_path/'chapter.xhtml'))
    assert doc.xpath('//*[local-name()="h2"]/text()') == ['第九十九章 前章','第一百章 粉絲見面會']
    assert doc.xpath('//*[local-name()="p"]/text()') == ['前文','完整正文']
    for name in ['nav.xhtml','toc.xhtml']:
        anchor = hashlib.sha256('第一百 粉絲見面會'.encode('utf-8')).hexdigest()[:12]
        assert etree.parse(str(tmp_path/name)).xpath('//*[local-name()="a"]/@href') == ['chapter.xhtml','chapter.xhtml#restored-chapter-'+anchor]


def test_bad_plan_writes_nothing_and_cannot_escape_root(tmp_path):
    package(tmp_path)
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises((ValueError, OSError)):
        restore_verified_chapter_headings(tmp_path, {'chapter.xhtml':'第一百 粉絲見面會'}, ['missing.xhtml'])
    assert before == {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError):
        restore_verified_chapter_headings(tmp_path, {'../outside.xhtml':'第一百 標題'}, [])
