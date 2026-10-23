from lxml import etree
from epub3itizer.repair import repair_body_fragment_links

NS = 'http://www.w3.org/1999/xhtml'


def page(body, head=''):
    return f'<html xmlns="{NS}"><head><title>測試</title>{head}</head>{body}</html>'


def test_body_links_preserve_content_and_other_targets(tmp_path):
    folder = tmp_path / 'Text'
    folder.mkdir()
    chapter = folder / '中 文.xhtml'
    chapter.write_text(page('<body id="start"><p id="p">正文不能刪</p></body>'), encoding='utf-8')
    nav = tmp_path / 'nav.xhtml'
    links = ['Text/%E4%B8%AD%20%E6%96%87.xhtml#start',
             'Text/%E4%B8%AD%20%E6%96%87.xhtml#p', 'missing.xhtml#start',
             'https://example.org/Text/a.xhtml#start', 'Text/中 文.xhtml?q=1#start',
             '../outside.xhtml#start']
    nav.write_text(page('<body>' + ''.join(f'<a href="{v}">{i}</a>' for i,v in enumerate(links)) + '</body>'), encoding='utf-8')
    ncx = tmp_path / 'toc.ncx'
    ncx.write_text('<ncx><content src="Text/%E4%B8%AD%20%E6%96%87.xhtml#start"/></ncx>', encoding='utf-8')
    before = chapter.read_bytes()
    repair_body_fragment_links(tmp_path)
    actual = etree.parse(str(nav)).xpath('//@href')
    assert actual == [links[0].split('#')[0], *links[1:]]
    assert etree.parse(str(ncx)).xpath('//@src') == [links[0].split('#')[0]]
    assert chapter.read_bytes() == before
    snapshot = {p: p.read_bytes() for p in (nav, ncx, chapter)}
    repair_body_fragment_links(tmp_path)
    assert all(p.read_bytes() == data for p, data in snapshot.items())


def test_same_page_body_link(tmp_path):
    p = tmp_path / 'chapter.xhtml'
    p.write_text(page('<body id="body"><a href="#body">頁首</a><a href="#note">註</a><p id="note">正文</p></body>'), encoding='utf-8')
    repair_body_fragment_links(tmp_path)
    assert etree.parse(str(p)).xpath('//@href') == ['chapter.xhtml', '#note']
    assert etree.parse(str(p)).xpath('//@id') == ['body', 'note']


def test_ambiguous_ids_and_base_or_invalid_documents_unchanged(tmp_path):
    cases = {
        'duplicate.xhtml': page('<body id="body"><p id="body"/><a href="#body">正文</a></body>'),
        'xmlbase.xhtml': page('<body xml:base="other/" id="body"><a href="#body">正文</a></body>'),
        'base.xhtml': page('<body id="body"><a href="#body">正文</a></body>', '<base href="other/"/>'),
        'invalid.xhtml': '<html><body id="body"><a href="#body">正文',
    }
    for name, data in cases.items():
        (tmp_path / name).write_text(data, encoding='utf-8')
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    repair_body_fragment_links(tmp_path)
    assert all(p.read_bytes() == data for p, data in before.items())


def test_shared_pipeline_body_links(tmp_path):
    from epub3itizer.repair import repair_epub
    from epub3itizer.conversion import convert_epub2_to_epub3
    import zipfile

    for version, processor in [('2.0', convert_epub2_to_epub3), ('3.0', repair_epub)]:
        source = tmp_path / ('input-' + version)
        source.mkdir()
        (source / 'META-INF').mkdir()
        (source / 'mimetype').write_text('application/epub+zip', encoding='utf-8')
        (source / 'META-INF/container.xml').write_text('<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>', encoding='utf-8')
        (source / 'book.opf').write_text(f'''<package xmlns="http://www.idpf.org/2007/opf" version="{version}" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier><dc:title>測試</dc:title><dc:language>zh-Hant</dc:language><meta property="dcterms:modified">2026-10-16T00:00:00Z</meta></metadata><manifest><item id="c" href="chapter.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="c"/></spine></package>''', encoding='utf-8')
        (source / 'chapter.xhtml').write_text(page('<body id="start"><p>正文不能刪</p></body>'), encoding='utf-8')
        (source / 'nav.xhtml').write_text(page('<body><nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc"><ol><li><a href="chapter.xhtml#start">章節</a></li></ol></nav></body>'), encoding='utf-8')
        output = tmp_path / ('output-' + version + '.epub')
        processor(source, output)
        with zipfile.ZipFile(output) as archive:
            assert archive.testzip() is None
            nav = etree.fromstring(archive.read('nav.xhtml'))
            assert nav.xpath('//@href') == ['chapter.xhtml']
            chapter = etree.fromstring(archive.read('chapter.xhtml'))
            assert chapter.xpath('string(//*[local-name()="p"])') == '正文不能刪'
