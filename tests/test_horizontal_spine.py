from pathlib import Path
import zipfile

from lxml import etree
import pytest

from epub3itizer.repair import repair_epub, repair_horizontal_spine_direction
from epub3itizer.conversion import convert_epub2_to_epub3


def package(root: Path, css: str, body: str = '<p>正文內容</p>', direction: str = 'rtl') -> None:
    (root / 'content.opf').write_text(
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
        '<manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest>'
        f'<spine page-progression-direction="{direction}"><itemref idref="chapter"/></spine></package>',
        encoding='utf-8',
    )
    (root / 'chapter.xhtml').write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><head>'
        '<link rel="stylesheet" href="style.css"/></head>'
        f'<body class="horizontal">{body}</body></html>', encoding='utf-8',
    )
    (root / 'style.css').write_text(css, encoding='utf-8')


def direction(root: Path):
    return etree.parse(str(root / 'content.opf')).find(
        '{http://www.idpf.org/2007/opf}spine'
    ).get('page-progression-direction')


@pytest.mark.parametrize('css', [
    'body {writing-mode: horizontal-tb}',
    '.horizontal {-epub-writing-mode: horizontal-tb}',
    'html, body.horizontal {-webkit-writing-mode: lr-tb}',
    'body {writing-mode: horizontal-tb; content: "writing-mode: vertical-rl"}',
    '/* writing-mode: vertical-rl */ body {writing-mode: horizontal-tb}',
])
def test_horizontal_removes_only_direction(tmp_path, css):
    package(tmp_path, css)
    originals = {name: (tmp_path / name).read_bytes() for name in ('chapter.xhtml', 'style.css')}
    repair_horizontal_spine_direction(tmp_path, 'content.opf')
    assert direction(tmp_path) is None
    for name, original in originals.items():
        assert (tmp_path / name).read_bytes() == original
    first = (tmp_path / 'content.opf').read_bytes()
    repair_horizontal_spine_direction(tmp_path, 'content.opf')
    assert (tmp_path / 'content.opf').read_bytes() == first


@pytest.mark.parametrize('css,body', [
    ('body {writing-mode: vertical-rl}', '<p>正文</p>'),
    ('body {writing-mode: horizontal-tb} p {writing-mode: vertical-rl}', '<p>正文</p>'),
    ('p {writing-mode: horizontal-tb}', '<p>正文</p>'),
    ('body {color: black}', '<p>正文</p>'),
    ('@media print {body {writing-mode: horizontal-tb}}', '<p>正文</p>'),
    ('body {writing-mode: horizontal-tb}', '<p dir="rtl">正文</p>'),
    ('body {writing-mode: horizontal-tb}', '<img src="cover.jpg"/>'),
    ('@import "missing.css"; body {writing-mode: horizontal-tb}', '<p>正文</p>'),
    ('@import "https://example.com/style.css"; body {writing-mode: horizontal-tb}', '<p>正文</p>'),
    ('body {writing-mode: var(--mode)}', '<p>正文</p>'),
])
def test_uncertain_or_vertical_keeps_direction(tmp_path, css, body):
    package(tmp_path, css, body)
    original = (tmp_path / 'content.opf').read_bytes()
    repair_horizontal_spine_direction(tmp_path, 'content.opf')
    assert (tmp_path / 'content.opf').read_bytes() == original


def test_import_and_inline_modes(tmp_path):
    package(tmp_path, '@import "layout.css";')
    (tmp_path / 'layout.css').write_text('body {writing-mode: horizontal-tb}', encoding='utf-8')
    repair_horizontal_spine_direction(tmp_path, 'content.opf')
    assert direction(tmp_path) is None
    package(tmp_path, '', '<p style="writing-mode: vertical-rl">正文</p>')
    repair_horizontal_spine_direction(tmp_path, 'content.opf')
    assert direction(tmp_path) == 'rtl'


def test_ltr_is_unchanged(tmp_path):
    package(tmp_path, 'body {writing-mode: horizontal-tb}', direction='ltr')
    original = (tmp_path / 'content.opf').read_bytes()
    repair_horizontal_spine_direction(tmp_path, 'content.opf')
    assert (tmp_path / 'content.opf').read_bytes() == original


@pytest.mark.parametrize('version,repair', [('2.0', convert_epub2_to_epub3), ('3.0', repair_epub)])
def test_shared_pipeline_removes_horizontal_rtl(tmp_path, version, repair):
    package(tmp_path, 'body {writing-mode: horizontal-tb}')
    opf = etree.parse(str(tmp_path / 'content.opf')).getroot()
    opf.set('version', version)
    opf.set('unique-identifier', 'uid')
    metadata = etree.Element('{http://www.idpf.org/2007/opf}metadata')
    for key, value in [('title', '橫排測試'), ('language', 'zh-Hant'), ('identifier', 'urn:uuid:12345678-1234-1234-1234-123456789abc')]:
        node = etree.SubElement(metadata, '{http://purl.org/dc/elements/1.1/}' + key)
        node.text = value
        if key == 'identifier':
            node.set('id', 'uid')
    opf.insert(0, metadata)
    source, output = tmp_path / 'source.epub', tmp_path / 'output.epub'
    with zipfile.ZipFile(source, 'w') as z:
        z.writestr('mimetype', 'application/epub+zip')
        z.writestr('META-INF/container.xml', '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr('content.opf', etree.tostring(opf))
        for name in ('chapter.xhtml', 'style.css'):
            z.writestr(name, (tmp_path / name).read_bytes())
    repair(source, output)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        spine = etree.fromstring(z.read('content.opf')).find('{http://www.idpf.org/2007/opf}spine')
        assert spine.get('page-progression-direction') is None
        assert [e.get('idref') for e in spine] == ['chapter']
        assert '正文內容' in z.read('chapter.xhtml').decode('utf-8')
