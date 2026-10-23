from lxml import etree
from epub3itizer.conversion import normalize_epubcheck_xhtml


def test_empty_invalid_epub_footnote_preserves_links_and_semantics():
    root = etree.fromstring(b'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Notes</title></head><body><a href="notes.xhtml#n1" epub:footnote="" epub:type="noteref">1</a><aside id="n1" epub:type="footnote">Note</aside><a href="#n1" epub:footnote="unknown">2</a></body></html>')
    text = ''.join(root.itertext())
    normalize_epubcheck_xhtml(root)
    ns={'epub':'http://www.idpf.org/2007/ops'}
    assert root.xpath('//*[local-name()="a"]/@href') == ['notes.xhtml#n1', '#n1']
    assert root.xpath('//@epub:footnote', namespaces=ns) == ['unknown']
    assert root.xpath('//@epub:type', namespaces=ns) == ['noteref', 'footnote']
    assert ''.join(root.itertext()) == text
    once=etree.tostring(root)
    normalize_epubcheck_xhtml(root)
    assert etree.tostring(root)==once
