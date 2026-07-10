import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from opf_converter import Opf_Converter  # noqa: E402
from epub3itizer.conversion import (  # noqa: E402
    build_nav,
    collect_doc_features,
    normalize_ncx_play_order,
    sanitize_css,
    sync_ncx_uid,
)


def test_opf_metadata_attrs_are_epub3_safe():
    opf2 = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
<dc:title>Sample</dc:title>
<dc:creator xmlns:ns0="http://www.idpf.org/2007/opf" ns0:role="aut" ns0:file-as="Author, A">A Author</dc:creator>
<dc:identifier id="uid" xmlns:ns1="http://www.idpf.org/2007/opf" ns1:scheme="ISBN">123</dc:identifier>
<dc:language>zh-Hant</dc:language>
</metadata>
<manifest><item id="chap" href="chap.xhtml" media-type="application/xhtml+xml" /></manifest>
<spine><itemref idref="chap" /></spine>
</package>
"""
    opf3 = Opf_Converter(opf2, {}, {}, {}, ["chap"]).get_opf3()

    assert '<package xmlns="http://www.idpf.org/2007/opf" version="3.0"' in opf3
    assert "ns0:" not in opf3
    assert "ns1:" not in opf3
    assert "xmlns:ns" not in opf3
    assert 'property="role" scheme="marc:relators">aut</meta>' in opf3
    assert 'property="file-as">Author, A</meta>' in opf3
    assert '<dc:identifier id="uid">urn:isbn:123</dc:identifier>' in opf3
    etree.fromstring(opf3.encode("utf-8"))


def test_empty_xhtml_title_is_filled_from_href():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>   </title></head>
<body><p>body</p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "<title>chapter01.xhtml</title>" in output


def test_xhtml_legacy_markup_is_epubcheck_safe():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Style-Type" content="text/css"/>
<title>Title</title>
</head>
<body>
<center><font size="7" color="red">x</font></center>
<p width="2em" height="1em" align="center">body</p>
<h2><div>heading</div></h2>
<link rel="stylesheet" type="application/vnd.adobe-page-template+xml" href="page-template.xpgt"/>
<img src="a.jpg" data-AmznRemoved="mobi7" data-AmznRemoved-M8="x"/>
</body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "Content-Style-Type" not in output
    assert "<center" not in output
    assert "<font" not in output
    assert "data-AmznRemoved" not in output
    assert 'width="2em"' not in output
    assert 'height="1em"' not in output
    assert "text-align: center" in output
    assert "page-template.xpgt" not in output
    assert "<h2><span>heading</span></h2>" in output


def test_invalid_spine_properties_are_dropped():
    opf2 = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>en</dc:language></metadata>
<manifest><item id="chap" href="chap file.xhtml" media-type="application/xhtml+xml" /></manifest>
<spine><itemref idref="chap" properties="viewport-width=1410, height=2000 page-spread-left" /></spine>
</package>
"""

    opf3 = Opf_Converter(opf2, {}, {}, {}, ["chap"]).get_opf3()

    assert 'href="chap_file.xhtml"' in opf3
    assert "viewport-width" not in opf3
    assert "height=2000" not in opf3
    assert 'properties="page-spread-left"' in opf3
    etree.fromstring(opf3.encode("utf-8"))


def test_ncx_uid_is_synced_to_opf_uid(tmp_path):
    ncx = tmp_path / "toc.ncx"
    ncx.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="plain-uuid"/></head>
</ncx>""",
        encoding="utf-8",
    )

    sync_ncx_uid(ncx, "urn:uuid:plain-uuid")

    assert 'content="urn:uuid:plain-uuid"' in ncx.read_text(encoding="utf-8")


def test_ncx_play_order_is_renumbered(tmp_path):
    ncx = tmp_path / "toc.ncx"
    ncx.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<navMap>
<navPoint id="a" playOrder="2"><navLabel><text>A</text></navLabel><content src="a.xhtml"/></navPoint>
<navPoint id="b" playOrder="2"><navLabel><text>B</text></navLabel><content src="b.xhtml"/></navPoint>
</navMap>
</ncx>""",
        encoding="utf-8",
    )

    normalize_ncx_play_order(ncx)

    data = ncx.read_text(encoding="utf-8")
    assert 'playOrder="1"' in data
    assert 'playOrder="2"' in data


def test_external_device_font_css_is_removed():
    css = """@font-face {
font-family: "zw";
src: local("Songti"), url(file:///mnt/us/fonts/zw.ttf), url(res:///fonts/zw.ttf);
}
p { color: black; }"""

    output = sanitize_css(css)

    assert "file:///" not in output
    assert "res:///" not in output
    assert "@font-face" not in output
    assert "p { color: black; }" in output


def test_empty_landmarks_nav_is_omitted():
    nav = build_nav("nav.xhtml", None, [], [], [], ".")

    assert 'epub:type="landmarks"' not in nav


def test_empty_landmark_label_uses_href_fallback():
    nav = build_nav("nav.xhtml", None, [], [], [("cover", "", "Text/cover.html")], ".")

    assert '>cover.html</a>' in nav


def test_empty_toc_label_uses_href_fallback():
    nav = build_nav("nav.xhtml", None, [type("Node", (), {"label": "", "href": "Text/a.xhtml", "children": []})()], [], [], ".")

    assert '>a.xhtml</a>' in nav
