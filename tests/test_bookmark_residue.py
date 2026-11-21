import pytest
from lxml import etree
from epub3itizer.conversion import cleanup_opf_manifest


@pytest.mark.parametrize('name', ['calibre_bookmarks.txt', 'META-INF/calibre_bookmarks.txt', 'OEBPS/Misc/CALIBRE_BOOKMARKS.TXT'])
@pytest.mark.parametrize('manifested', [True, False])
def test_bookmark_residue_removed_at_any_location(tmp_path, name, manifested):
    target=tmp_path/name
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('private bookmark',encoding='utf-8')
    (tmp_path/'bookmarks.txt').write_text('正文附錄',encoding='utf-8')
    (tmp_path/'chapter.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>正文</title></head><body><p>保留正文</p></body></html>',encoding='utf-8')
    item=f'<item id="bookmark" href="{name}" media-type="text/plain"/>' if manifested else ''
    ref='<itemref idref="bookmark"/>' if manifested else ''
    opf=tmp_path/'content.opf'
    opf.write_text(f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>{item}</manifest><spine><itemref idref="chapter"/>{ref}</spine></package>',encoding='utf-8')
    cleanup_opf_manifest(tmp_path,'content.opf')
    assert not target.exists()
    assert (tmp_path/'bookmarks.txt').read_text(encoding='utf-8')=='正文附錄'
    doc=etree.parse(str(opf))
    assert 'chapter' in doc.xpath('//*[local-name()="item"]/@id')
    assert not doc.xpath('//*[@id="bookmark" or @idref="bookmark"]')
    assert doc.xpath('//*[local-name()="itemref"]/@idref')==['chapter']
