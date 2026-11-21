from lxml import etree

from epub3itizer.conversion import normalize_epubcheck_xhtml, sanitize_css


def test_shizuku_marker_and_hiding_rule_are_removed():
    doc = etree.fromstring(b'<html xmlns="http://www.w3.org/1999/xhtml"><body shizuku666="url"><p id="text" shizuku666="url">text</p></body></html>')
    normalize_epubcheck_xhtml(doc)
    assert not doc.xpath('//@shizuku666')
    assert doc.xpath('//*[@id="text"]')[0].text == "text"
    css = '@import "base.css";body:not([shizuku666]),p:not([shizuku666]){display:none}p{color:red}'
    clean = sanitize_css(css)
    assert "shizuku666" not in clean and "base.css" in clean and "color:red" in clean
    assert sanitize_css(clean) == clean
