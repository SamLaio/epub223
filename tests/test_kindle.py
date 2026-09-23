import zipfile
from io import BytesIO

import pytest
from lxml import etree
from PIL import Image

from epub3itizer.kindle import horizontal_css, kindle_reflowable, _unwrap_image
from epub3itizer.repair import repair_epub


def test_horizontal_css_preserves_values_and_rejects_positioning():
    css = '@media screen{.vrtl{writing-mode:vertical-rl;width:50%;margin:2em;content:"writing-mode:vertical-rl"}}'
    result = horizontal_css(css)
    assert 'writing-mode:horizontal-tb' in result
    assert 'content:"writing-mode:vertical-rl"' in result
    assert 'width:50%;margin:2em' in result
    assert horizontal_css(result) == result
    with pytest.raises(ValueError, match="絕對定位"):
        horizontal_css('p{position:absolute}')


def test_complex_or_cropped_svg_is_not_flattened():
    for child in ('<text>不可刪除</text>', '<image href="x.png" width="50" height="200"/>'):
        root = etree.fromstring(f'<div xmlns="http://www.w3.org/1999/xhtml"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 200">{child}</svg></div>')
        before = etree.tostring(root)
        with pytest.raises(ValueError):
            _unwrap_image(root[0])
        assert etree.tostring(root) == before


def test_opt_in_reflowable_copy_preserves_text_and_images(tmp_path):
    source, normal, output = [tmp_path / name for name in ('source.epub', 'normal.epub', 'kindle.epub')]
    buffer = BytesIO()
    Image.new('RGB', (100, 200)).save(buffer, format='JPEG')
    image_bytes = buffer.getvalue()
    with zipfile.ZipFile(source, 'w') as z:
        z.writestr('mimetype', 'application/epub+zip')
        z.writestr('META-INF/container.xml', '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr('content.opf', '''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">test</dc:identifier><dc:title>測試</dc:title><dc:language>zh-Hant</dc:language><meta property="rendition:layout">reflowable</meta></metadata><manifest><item id="page" href="page.xhtml" media-type="application/xhtml+xml" properties="svg"/><item id="img" href="image.jpg" media-type="image/jpeg"/></manifest><spine page-progression-direction="rtl"><itemref idref="page" properties="rendition:layout-pre-paginated rendition:spread-none"/></spine></package>''')
        z.writestr('page.xhtml', '''<html xmlns="http://www.w3.org/1999/xhtml" lang="en"><head><title>測試</title><meta name="viewport" content="width=100,height=200"/><style>.vrtl{writing-mode:vertical-rl}</style></head><body><p id="chapter" style="writing-mode:vertical-rl">保留<em>全部</em>文字。</p><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 200"><image xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="image.jpg" width="100" height="200"/></svg></body></html>''')
        z.writestr('image.jpg', image_bytes)
    repair_epub(source, normal)
    with zipfile.ZipFile(normal) as z:
        assert b'vertical-rl' in z.read('page.xhtml')
        assert b'pre-paginated' in z.read('content.opf')
    before = source.read_bytes()
    kindle_reflowable(source, output, 'zh-Hant')
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert z.read('image.jpg') == image_bytes
        page = etree.fromstring(z.read('page.xhtml'))
        assert page.get('lang') == 'zh-Hant'
        assert ''.join(page.xpath('//*[local-name()="p"]')[0].itertext()) == '保留全部文字。'
        assert page.xpath('//*[@id="chapter"]')
        assert page.xpath('//*[local-name()="img"]')[0].get('src') == 'image.jpg'
        assert b'vertical-rl' not in z.read('page.xhtml')
        assert b'pre-paginated' not in z.read('content.opf')
    assert source.read_bytes() == before
    with pytest.raises(ValueError, match="不可覆寫"):
        kindle_reflowable(source, source)
    with zipfile.ZipFile(source) as z:
        # Replace the package globally instead of attempting to flatten a comic.
        opf = z.read('content.opf').replace(b'>reflowable<', b'>pre-paginated<')
    fixed = tmp_path / 'fixed.epub'
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(fixed, 'w') as zout:
        for name in zin.namelist():
            zout.writestr(name, opf if name == 'content.opf' else zin.read(name))
    with pytest.raises(ValueError, match="全書固定"):
        kindle_reflowable(fixed, output)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
