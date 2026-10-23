import pytest
from lxml import etree
from PIL import Image
from epub3itizer.conversion import cleanup_opf_manifest


@pytest.mark.parametrize('with_image', [False, True])
def test_cover_page_flag_removed_without_deleting_page_or_image(tmp_path, with_image):
    page = '<html xmlns="http://www.w3.org/1999/xhtml"><body><p>封面與正文保留</p></body></html>'
    (tmp_path/'cover.xhtml').write_text(page, encoding='utf-8')
    Image.new('RGB', (2, 2), 'red').save(tmp_path/'cover.jpg')
    image = (tmp_path/'cover.jpg').read_bytes()
    image_item = '<item id="image" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>' if with_image else ''
    opf = tmp_path/'content.opf'
    opf.write_text(f'''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">test</dc:identifier><dc:title>測試</dc:title><dc:language>zh-Hant</dc:language></metadata>
    <manifest><item id="page" href="cover.xhtml" media-type="application/xhtml+xml" properties="cover-image remote-resources"/>{image_item}</manifest>
    <spine><itemref idref="page"/></spine></package>''', encoding='utf-8')
    cleanup_opf_manifest(tmp_path, 'content.opf')
    doc = etree.parse(str(opf))
    assert doc.xpath('//*[local-name()="item" and @id="page"]/@properties') == ['remote-resources']
    assert doc.xpath('//*[local-name()="item" and contains(@properties,"cover-image")]/@id') == (['image'] if with_image else [])
    assert doc.xpath('//*[local-name()="itemref"]/@idref') == ['page']
    assert (tmp_path/'cover.xhtml').read_text(encoding='utf-8') == page
    assert (tmp_path/'cover.jpg').read_bytes() == image
    before = opf.read_bytes()
    cleanup_opf_manifest(tmp_path, 'content.opf')
    assert opf.read_bytes() == before
