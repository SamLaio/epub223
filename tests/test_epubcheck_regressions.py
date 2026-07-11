import re
import sys
from pathlib import Path

import pytest
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from opf_converter import Opf_Converter  # noqa: E402
from epub3itizer.conversion import (  # noqa: E402
    add_fixed_layout_viewports,
    add_missing_manifest_items,
    build_nav,
    cleanup_nav_leaf_spans,
    cleanup_opf_manifest,
    collect_doc_features,
    convert_bmp_images,
    filter_guide_to_spine,
    filter_toc_to_spine,
    fix_case_mismatched_local_hrefs,
    normalize_all_xhtml_files,
    normalize_ncx_play_order,
    parse_ncx_file,
    parse_xml_recovering,
    repair_missing_css_references,
    repair_missing_xhtml_references,
    sanitize_all_css_files,
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


def test_abnormal_namespace_declarations_are_sanitized_for_xhtml():
    root = parse_xml_recovering(
        """<html xmlns="https://www.w3.org/1999/xhtml" xmlns:xmlns="bad">
<head><title>Title</title></head>
<body><p>body</p></body>
</html>"""
    )

    assert etree.QName(root).namespace == "http://www.w3.org/1999/xhtml"
    assert "xmlns" not in root.nsmap


def test_corrupted_xhtml_namespace_year_is_sanitized():
    root = parse_xml_recovering(
        """<html xmlns="http://www.w3.org/十九99/xhtml">
<head><title>Title</title></head>
<body><p>body</p></body>
</html>"""
    )

    assert etree.QName(root).namespace == "http://www.w3.org/1999/xhtml"


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
    assert "width: 2em" in output
    assert "height: 1em" in output
    assert "text-align: center" in output
    assert "page-template.xpgt" not in output
    assert "<h2><span>heading</span></h2>" in output


def test_epub_switch_and_legacy_media_markup_are_flattened():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN" xml:lang="zh-TW">
<head><title>Title</title><style>@font-face { src: url(res:///fonts/a.ttf); }</style></head>
<body>
<epub:switch><epub:case><svg xmlns="http://www.w3.org/2000/svg"/></epub:case><epub:default><p>fallback</p></epub:default></epub:switch>
<switch><case><p>case</p></case><default><p>default</p></default></switch>
<iframe marginwidth="0" marginheight="0" frameborder="0" src="http://example.invalid/ad.html"/>
<audio activestate="a.png" placeholder="b.png" title="music"/>
<audio title="music"/><source type="audio/mpeg"/>
<pre><h1>Heading</h1></pre>
<p><img src="images/a.emf" alt="bad"/>text</p>
</body>
</html>""".encode("utf-8")
    )

    output, manifest_props, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "epub:switch" not in output
    assert "<switch" not in output
    assert "required-namespace" not in output
    assert "marginwidth" not in output
    assert "frameborder" not in output
    assert "example.invalid" not in output
    assert "activestate" not in output
    assert "placeholder" not in output
    assert "<source" not in output
    assert "<pre><span>Heading</span></pre>" in output
    assert "a.emf" not in output
    assert 'lang="zh-TW"' in output
    assert 'xml:lang="zh-TW"' in output
    assert "res:///" not in output
    assert "switch" not in manifest_props


def test_invalid_ruby_with_empty_rt_is_flattened():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p><ruby>印<rp>(</rp><rt>營多麵</rt>尼<rp>)</rp><rt/>泡<rp>)</rp><rt/></ruby></p></body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "<ruby" not in output
    assert "<rt" not in output
    assert "<rp" not in output
    assert "印尼泡" in output


def test_malformed_ruby_with_text_between_rt_and_rp_is_flattened():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p><ruby>覚<rp>(</rp><rt>おぼ</rt>束<rp>)</rp><rt>つか</rt>無<rp>)</rp></ruby></p></body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "<ruby" not in output
    assert "<rt" not in output
    assert "<rp" not in output
    assert "覚束無" in output


def test_empty_ids_bad_language_and_unknown_inline_tags_are_repaired():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml" lang="zh—CN" xml:lang="zh—CN">
<head><title>Title</title></head>
<body><p><span id="">x</span><r>wrong</r><spine page-progression-direction="rtl" toc="ncx">old</spine></p></body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert 'id=""' not in output
    assert 'lang="zh-CN"' in output
    assert 'xml:lang="zh-CN"' in output
    assert "<r>" not in output
    assert "<spine>" not in output
    assert "page-progression-direction" not in output
    assert 'toc="ncx"' not in output
    assert "wrong" in output


def test_html_without_namespace_is_promoted_to_xhtml():
    root = etree.fromstring(
        b"""<html><head><title>Title</title></head><body><p>body</p></body></html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    out_root = etree.fromstring(output.encode("utf-8"))
    assert etree.QName(out_root).namespace == "http://www.w3.org/1999/xhtml"
    assert out_root.xpath("//*[local-name()='p']")


def test_head_children_wrapped_by_broken_meta_are_restored():
    root = parse_xml_recovering(
        """<html><head><meta charset="UTF-8">
<link rel="stylesheet" href="style.css"/>
<title>Broken</title>
</meta></head><body/></html>"""
    )

    output, _, _, _ = collect_doc_features(root, "OPS/1.html")
    out_root = etree.fromstring(output.encode("utf-8"))
    head_children = [etree.QName(child).localname for child in out_root.xpath("//*[local-name()='head']/*")]

    assert head_children == ["meta", "link", "title"]
    assert out_root.xpath("string(//*[local-name()='title'])") == "Broken"
    assert not out_root.xpath("//*[local-name()='meta']/*")


def test_malformed_class_attribute_name_is_repaired_before_parse():
    root = parse_xml_recovering(
        """<html><head><title>T</title></head><body><span clasＶs="bold">x</span></body></html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert 'class="bold"' in output
    assert "clasＶs" not in output


def test_html_missing_body_gets_empty_body():
    root = parse_xml_recovering(
        """<html><head><title>Only Head</title></head></html>"""
    )

    output, _, _, _ = collect_doc_features(root, "OPS/empty.html")
    out_root = etree.fromstring(output.encode("utf-8"))

    assert out_root.xpath("//*[local-name()='head']")
    assert out_root.xpath("//*[local-name()='body']")


def test_invalid_head_block_element_is_removed():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><div style="page-break-after:always"/><title>Title</title></head>
<body><p>body</p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")

    assert "<head><title>Title</title>" in output


def test_css_line_comments_font_family_semicolon_and_orphan_brace_are_repaired():
    css = """.box{page-break-after: always; // old comment}
.box:last-of-type{ page-break-after: auto; // old comment }
.CI { text-align:center; }
li.note { color-#b49c84; }
}
p { font-family: "zw","Song";sans-serif; }
p.jy { font-family: "kt","Kai";"zw", serif; }
"""

    output = sanitize_css(css)

    assert "//" not in output
    assert output.count("{") == output.count("}")
    assert '"Song",sans-serif' in output
    assert '"Kai","zw", serif' in output
    assert "color: #b49c84;" in output
    assert ".CI" in output


def test_forms_bad_a_attribute_unknown_tag_and_hr_in_heading_are_repaired():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body>
<debagame><p>body</p></debagame>
<title_______________________________><p>custom title</p></title_______________________________>
<blockquote body="" class="x"/>
<span><tt>mono</tt><tr><td><p>menu</p></td></tr></span>
<p><order of="" the="" zenith="">OZ</order><do>bad</do><mi><so>note</so></mi><a___>a</a___><b___>b</b___></p>
<p><span times="" new="" roman="" serif="" tooltip="Tip" colspan="2">bad attrs</span></p>
<pre v-pre="" data-lang="json"><code>{}</code></pre>
<p><a href="asset.bin" download="">download</a></p>
<p><a a="" href="chap.xhtml">note</a></p>
<blockquote cite="輸入url"><p>quote</p></blockquote>
<h1><span>Title<hr size="2"/></span></h1>
<table summary="legacy"><tr><td>cell</td></tr></table>
<form><input id="cfi_fragment" type="hidden" value="/6/2"/></form>
</body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "<debagame" not in output
    assert "<title_______________________________" not in output
    assert 'body=""' not in output
    assert "<tt" not in output
    assert "<order" not in output
    assert "<do" not in output
    assert "<mi" not in output
    assert "<so" not in output
    assert "<a___" not in output
    assert "<b___" not in output
    assert 'of=""' not in output
    assert 'the=""' not in output
    assert 'zenith=""' not in output
    assert 'times=""' not in output
    assert 'tooltip=' not in output
    assert 'colspan="2">bad attrs' not in output
    assert "v-pre" not in output
    assert "download=" not in output
    assert "<span>mono</span><span><span><span>menu</span></span></span>" in output
    assert "<form" not in output
    assert "<input" not in output
    assert ' a=""' not in output
    assert 'cite="輸入url"' not in output
    assert 'summary="legacy"' not in output
    assert "<hr" not in output
    assert "border-top: 1px solid black" in output


def test_table_col_and_broken_table_structures_are_repaired():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body>
<table><col style="width: 50%"/><col style="width: 50%"/><tr><td colspan="2">ok</td></tr></table>
<table><div><colgroup><col/></colgroup><div>broken</div></div></table>
</body></html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/table.xhtml")

    assert "<colgroup><col" in output
    assert output.count("<table") == 1
    assert "<table><div" not in output
    assert "<colgroup><col/></colgroup><div>broken</div>" not in output
    assert "broken" in output


def test_inline_file_url_styles_are_removed():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body style="background-image: url(file:///C:/Temp/OEBPS/Images/back.png); background-color: rgb(255,255,255)">
<p>body</p>
</body></html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/page.xhtml")

    assert "file:///" not in output
    assert "background-image" not in output
    assert "background-color: rgb(255,255,255)" in output


def test_cjk_pseudo_self_closing_tag_is_escaped_before_parse():
    root = parse_xml_recovering(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p>推薦 <我在明末有套房/></p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter.xhtml")

    assert "<我在明末有套房" not in output
    assert "&lt;我在明末有套房/&gt;" in output


def test_nav_empty_toc_gets_first_spine_fallback_and_empty_landmarks_removed(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "content.opf").write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="chap" href="Text/a.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="chap"/></spine>
</package>""",
        encoding="utf-8",
    )
    nav = tmp_path / "OEBPS" / "nav.xhtml"
    nav.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>N</title></head>
<body>
<nav epub:type="toc"><ol></ol></nav>
<nav epub:type="landmarks"><h2>Guide</h2></nav>
</body></html>""",
        encoding="utf-8",
    )

    cleanup_nav_leaf_spans(tmp_path, "OEBPS/content.opf")
    output = nav.read_text(encoding="utf-8")

    assert 'href="Text/a.xhtml"' in output
    assert "landmarks" not in output


def test_sanitize_all_css_files_cleans_late_added_external_font_urls(tmp_path):
    css = tmp_path / "late.css"
    css.write_text(
        """@font-face {
  font-family: "h2";
  src: url('res:///system/fonts/h2.ttf'), url('file:///mnt/us/fonts/h2.ttf');
}
.body { font-family: "h2"; }""",
        encoding="utf-8",
    )

    sanitize_all_css_files(tmp_path)
    output = css.read_text(encoding="utf-8")

    assert "res:///" not in output
    assert "file:///" not in output
    assert "@font-face" not in output


def test_css_fullwidth_colon_is_normalized():
    output = sanitize_css("@page {padding：0pt; margin:0pt}\nbody { text-align：center; }")

    assert "padding:0pt" in output
    assert "text-align:center" in output


def test_opf_cleanup_removes_old_attrs_private_tokens_and_fills_empty_spine(tmp_path):
    (tmp_path / "Text").mkdir()
    (tmp_path / "Text" / "chap.xhtml").write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>T</title></head><body/></html>',
        encoding="utf-8",
    )
    opf = tmp_path / "content.opf"
    opf.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0" unique-identifier="uid">
<metadata>
<dc:title id="title1">Title</dc:title>
<dc:creator id="creator" role="aut">Author</dc:creator>
<meta refines="#creator" property="role" scheme="marc:relators">aut</meta>
<dc:identifier id="uid" scheme="uuid">urn:uuid:abc</dc:identifier>
<dc:language>zh-Hant</dc:language>
</metadata>
<manifest>
<spine></spine>
<item id="navid" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="chap" href="Text/chap.xhtml" media-type="application/xhtml+xml"/>
</manifest>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "content.opf")
    output = opf.read_text(encoding="utf-8")

    assert 'scheme="uuid"' not in output
    assert 'scheme="marc:relators"' not in output
    assert 'role="aut"' not in output
    assert "<spine>" in output
    assert 'idref="chap"' in output


def test_opf_cleanup_removes_empty_svg_and_makes_cover_page_linear(tmp_path):
    (tmp_path / "Text").mkdir()
    (tmp_path / "Images").mkdir()
    (tmp_path / "Text" / "cover_page.xhtml").write_text("<html/>", encoding="utf-8")
    (tmp_path / "Text" / "chap.xhtml").write_text("<html/>", encoding="utf-8")
    (tmp_path / "Images" / "bad.svg").write_text("", encoding="utf-8")
    opf = tmp_path / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>T</dc:title><dc:language>zh-Hant</dc:language><dc:identifier id="uid">urn:uuid:x</dc:identifier></metadata>
<manifest>
<item id="cover" href="Text/cover_page.xhtml" media-type="application/xhtml+xml"/>
<item id="chap" href="Text/chap.xhtml" media-type="application/xhtml+xml"/>
<item id="badsvg" href="Images/bad.svg" media-type="image/svg+xml"/>
</manifest>
<spine><itemref idref="cover" linear="no"/><itemref idref="chap"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "content.opf")
    output = opf.read_text(encoding="utf-8")

    assert "bad.svg" not in output
    assert 'linear="no"' not in output


def test_nav_links_to_non_spine_items_are_demoted(tmp_path):
    (tmp_path / "Text").mkdir()
    (tmp_path / "Text" / "001.xhtml").write_text("", encoding="utf-8")
    (tmp_path / "Text" / "002.xhtml").write_text("", encoding="utf-8")
    (tmp_path / "content.opf").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>T</dc:title><dc:language>zh-Hant</dc:language><dc:identifier id="uid">urn:uuid:x</dc:identifier></metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="chap1" href="Text/001.xhtml" media-type="application/xhtml+xml"/>
<item id="chap2" href="Text/002.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="chap1"/></spine>
</package>""",
        encoding="utf-8",
    )
    (tmp_path / "nav.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>nav</title></head><body><nav epub:type="toc"><ol>
<li><a href="Text/001.xhtml">keep</a></li>
<li><a href="Text/002.xhtml">drop</a><ol></ol></li>
</ol></nav></body></html>""",
        encoding="utf-8",
    )

    cleanup_nav_leaf_spans(tmp_path, "content.opf")
    output = (tmp_path / "nav.xhtml").read_text(encoding="utf-8")

    assert 'href="Text/001.xhtml"' in output
    assert 'href="Text/002.xhtml"' not in output
    assert "drop" not in output
    assert "<ol/>" not in output
    assert "page-break-after" not in output


def test_invalid_body_metadata_and_list_items_are_normalized():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head>　<title>Title</title>　</head>
<body>
<div><li>orphan list item</li></div>
<ul>bare<li>ok</li><div>wrong child</div></ul>
<p><title>body title</title><meta name="cover" content="true"/><style>p {}</style></p>
</body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "<li>orphan list item</li>" not in output
    assert "<p>orphan list item</p>" in output
    assert "<li>bare</li>" in output
    assert "<li>ok</li>" in output
    assert "<li>wrong child</li>" in output
    assert "<title>body title</title>" not in output
    assert "<span>body title</span>" in output
    assert 'name="cover"' not in output
    assert "<style" not in output


def test_legacy_width_number_becomes_px_style():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p width="600">body</p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert 'width="600"' not in output
    assert "width: 600px" in output


def test_xhtml_meta_without_required_content_is_repaired_or_removed():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta name="author"/>
<meta name="viewport" width="device-width, initial-scale=1.0"/>
<meta http-equiv="Content-Type"/>
<title>Title</title>
</head>
<body><p>body</p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert 'name="author"' not in output
    out_root = etree.fromstring(output.encode("utf-8"))
    viewport = out_root.xpath("//*[local-name()='meta' and @name='viewport']")
    assert len(viewport) == 1
    assert viewport[0].get("content") == "width=device-width, initial-scale=1.0"
    assert viewport[0].get("width") is None
    assert '<meta charset="utf-8"/>' in output
    assert 'http-equiv="Content-Type"' not in output


def test_invalid_dl_children_are_wrapped_as_dd():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><dl>intro<p>bad paragraph</p>tail<dt>Term</dt><dd>Definition</dd></dl></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")
    out_root = etree.fromstring(output.encode("utf-8"))
    assert not out_root.xpath("//*[local-name()='dl']")
    container = out_root.xpath("//*[local-name()='body']/*[local-name()='div']")[0]

    assert [etree.QName(child).localname for child in container if isinstance(child.tag, str)] == ["div", "div", "div", "div", "div"]
    assert "bad paragraph" in output
    assert "intro" in output
    assert "tail" in output


def test_valid_dl_structure_is_preserved():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><dl><dt>Term</dt><dd>Definition</dd></dl></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")
    out_root = etree.fromstring(output.encode("utf-8"))
    dl = out_root.xpath("//*[local-name()='dl']")[0]

    assert [etree.QName(child).localname for child in dl if isinstance(child.tag, str)] == ["dt", "dd"]


def test_ruby_missing_rp_fallbacks_are_added():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p><ruby>漢字<rt>hàn zì</rt></ruby></p></body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")
    out_root = etree.fromstring(output.encode("utf-8"))
    ruby = out_root.xpath("//*[local-name()='ruby']")[0]
    ruby_children = [etree.QName(child).localname for child in ruby if isinstance(child.tag, str)]

    assert ruby_children == ["rp", "rt", "rp"]
    assert [child.text for child in ruby if etree.QName(child).localname == "rp"] == ["(", ")"]


def test_ruby_existing_rp_fallbacks_are_not_duplicated():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p><ruby>漢字<rp>(</rp><rt>hàn zì</rt><rp>)</rp></ruby></p></body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")
    out_root = etree.fromstring(output.encode("utf-8"))
    ruby = out_root.xpath("//*[local-name()='ruby']")[0]
    ruby_children = [etree.QName(child).localname for child in ruby if isinstance(child.tag, str)]

    assert ruby_children == ["rp", "rt", "rp"]


def test_legacy_strike_tag_becomes_s():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p><strike>刪除線</strike></p></body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "<strike" not in output
    assert "<s>刪除線</s>" in output


def test_nonstandard_xhtml_tags_and_anchor_shapes_are_normalized():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title><base href="https://example.invalid/"/></head>
<body>
<P><PUBU>vendor</PUBU><spen>typo</spen></P>
<p><a href="a.xhtml">outer <a>inner</a></a><a>empty href</a></p>
</body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "<base" not in output
    assert "<P>" not in output
    assert "<PUBU" not in output
    assert "<spen" not in output
    assert "<div>vendor</div>" in output
    assert "<span>typo</span>" in output
    assert '<a href="a.xhtml">outer <span>inner</span></a>' in output
    assert "<span>empty href</span>" in output


def test_switch_case_fragment_is_normalized_to_safe_div():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><case required-namespace="http://www.w3.org/2000/svg"><svg xmlns="http://www.w3.org/2000/svg"/></case></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")

    assert "<case" not in output
    assert "required-namespace" not in output
    assert "<div><svg" in output


def test_empty_span_between_table_rows_is_removed():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><table><tr><td>A</td></tr><span/><tr><td>B</td></tr></table></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")
    out_root = etree.fromstring(output.encode("utf-8"))

    assert not out_root.xpath("//*[local-name()='table']/*[local-name()='span']")
    assert len(out_root.xpath("//*[local-name()='table']/*[local-name()='tr']")) == 2


def test_empty_span_between_non_namespace_table_rows_is_removed():
    root = etree.fromstring(
        b"""<html>
<head><title>Title</title></head>
<body><table><tr><td>A</td></tr><span/><tr><td>B</td></tr></table></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")
    out_root = etree.fromstring(output.encode("utf-8"))

    assert not out_root.xpath("//*[local-name()='table']/*[local-name()='span']")
    assert len(out_root.xpath("//*[local-name()='table']/*[local-name()='tr']")) == 2


def test_final_xhtml_normalization_cleans_table_span(tmp_path):
    page = tmp_path / "index_split_008.html"
    page.write_text(
        """<html><head><title>T</title></head><body><table><tr><td>A</td></tr><span/><tr><td>B</td></tr></table></body></html>""",
        encoding="utf-8",
    )

    normalize_all_xhtml_files(tmp_path)

    output = page.read_text(encoding="utf-8")
    assert "<span" not in output
    assert output.count("<tr") == 2


def test_final_xhtml_normalization_preserves_nav_epub_type(tmp_path):
    page = tmp_path / "nav.xhtml"
    page.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>N</title></head><body><nav epub:type="toc"><ol><li><a href="a.xhtml">A</a></li></ol></nav></body></html>""",
        encoding="utf-8",
    )

    normalize_all_xhtml_files(tmp_path)

    assert 'epub:type="toc"' in page.read_text(encoding="utf-8")


def test_invalid_xhtml_attrs_are_removed_or_moved_to_style():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p name="old" cid="bad" value="1">x</p><div gallery="image">g</div><img src="a.jpg" width="100%" height="20"/></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert 'name="old"' not in output
    assert 'cid="bad"' not in output
    assert 'value="1"' not in output
    assert 'gallery="image"' not in output
    assert 'width="100%"' not in output
    assert 'style="width: 100%"' in output
    assert 'height="20"' in output


def test_hr_legacy_size_and_align_become_css():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><hr size="2" align="center" style="width:50%"/></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert 'size="2"' not in output
    assert 'align="center"' not in output
    assert "width: 50%" in output
    assert "height: 2px" in output
    assert "border: none" in output
    assert "background-color: black" in output
    assert "margin: 0 auto" in output


def test_hr_legacy_size_keeps_em_unit():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><hr size="1.5em"/></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert 'size="1.5em"' not in output
    assert "height: 1.5em" in output


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


def test_itemref_linear_type_is_renamed_to_linear():
    opf2 = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>en</dc:language></metadata>
<manifest><item id="appendix" href="appendix.xhtml" media-type="application/xhtml+xml" /></manifest>
<spine><itemref idref="appendix" linear-type="no" /></spine>
</package>
"""

    opf3 = Opf_Converter(opf2, {}, {}, {}, ["appendix"]).get_opf3()

    assert "linear-type" not in opf3
    root = etree.fromstring(opf3.encode("utf-8"))
    itemref = root.xpath("//*[local-name()='itemref' and @idref='appendix']")[0]
    assert itemref.get("linear") == "no"


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


def test_ncx_uid_is_created_when_missing(tmp_path):
    ncx = tmp_path / "toc.ncx"
    ncx.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><navMap/></ncx>""",
        encoding="utf-8",
    )

    sync_ncx_uid(ncx, "urn:uuid:new-book-id")

    data = ncx.read_text(encoding="utf-8")
    assert 'name="dtb:uid"' in data
    assert 'content="urn:uuid:new-book-id"' in data


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


def test_css_control_characters_are_removed():
    output = sanitize_css("\x16.calibre { color: black; }")

    assert output.startswith(".calibre")


def test_css_stray_backslash_before_declaration_end_is_removed():
    output = sanitize_css("h2 { border-bottom: 1px solid #767572;\\\n}")

    assert "\\\n}" not in output
    assert "border-bottom: 1px solid #767572;" in output


def test_css_invalid_comment_semicolon_equals_empty_and_remote_url_are_repaired():
    output = sanitize_css(
        """.text span {
/* standard body font */;
width=100%;
font-family: ;
background-image: url(https://example.invalid/cover.jpg);
}"""
    )

    assert "*/;" not in output
    assert "width: 100%;" in output
    assert "font-family: ;" not in output
    assert "https://example.invalid" not in output
    assert "background-image: none" in output


def test_css_orphan_declaration_block_at_file_start_is_removed():
    output = sanitize_css("\n\n    font-weight: bold;\n}\n.FA-text { margin: 0; }")

    assert "font-weight: bold" not in output
    assert output.lstrip().startswith(".FA-text")


def test_empty_landmarks_nav_is_omitted():
    nav = build_nav("nav.xhtml", None, [], [], [], ".")

    assert 'epub:type="landmarks"' not in nav


def test_empty_landmark_label_uses_href_fallback():
    nav = build_nav("nav.xhtml", None, [], [], [("cover", "", "Text/cover.html")], ".")

    assert '>cover.html</a>' in nav


def test_empty_toc_label_uses_href_fallback():
    nav = build_nav("nav.xhtml", None, [type("Node", (), {"label": "", "href": "Text/a.xhtml", "children": []})()], [], [], ".")

    assert '>a.xhtml</a>' in nav


def test_manifest_and_spine_ids_are_xml_name_safe():
    opf2 = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>en</dc:language></metadata>
<manifest><item id="000.xhtml" href="000.xhtml" media-type="application/xhtml+xml" /></manifest>
<spine><itemref idref="000.xhtml" /></spine>
</package>
"""

    opf3 = Opf_Converter(opf2, {}, {}, {}, ["000.xhtml"]).get_opf3()

    assert 'id="id_000.xhtml"' in opf3
    assert 'idref="id_000.xhtml"' in opf3
    etree.fromstring(opf3.encode("utf-8"))


def test_manifest_media_type_override_is_applied():
    opf2 = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>en</dc:language></metadata>
<manifest><item id="img" href="image.jpeg" media-type="image/jpeg" /></manifest>
<spine />
</package>
"""

    opf3 = Opf_Converter(opf2, {}, {}, {}, ["img"], {"img": "image/png"}).get_opf3()

    assert 'media-type="image/png"' in opf3


def test_legacy_body_nav_and_anchor_type_are_removed():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body type="frontmatter"><nav type="toc"><ol><li><a href="a.xhtml" type="toc">A</a></li></ol></nav></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/nav.xhtml")

    assert '<body type="frontmatter"' not in output
    assert '<nav type="toc"' not in output
    assert '<a href="a.xhtml" type="toc"' not in output
    assert 'epub:type="frontmatter"' not in output
    assert 'epub:type="toc"' not in output


def test_package_relative_image_href_is_made_document_relative():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><img src="OEBPS/Images/cover.jpg"/></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "OEBPS/Text/Cover.xhtml")

    assert 'src="../Images/cover.jpg"' in output


def test_duplicate_element_ids_are_made_unique():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p id="dup">A</p><p id="dup">B</p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")

    assert 'id="dup"' in output
    assert 'id="dup_2"' in output


def test_invalid_element_ids_are_made_xml_name_safe():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p id="123 bad">A</p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")

    assert 'id="id_123_bad"' in output


def test_bare_body_text_is_wrapped_in_paragraphs():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body>Intro<div>Block</div>Tail</body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")

    assert "<p>Intro</p>" in output
    assert "<p>Tail</p>" in output


def test_toc_entries_outside_spine_are_dropped_or_promoted():
    child = type("Node", (), {"label": "Child", "href": "Text/chapter.xhtml", "children": []})()
    parent = type("Node", (), {"label": "Cover", "href": "Text/cover.xhtml", "children": [child]})()

    filtered = filter_toc_to_spine([parent], ["Text/chapter.xhtml"])

    assert len(filtered) == 1
    assert filtered[0].label == "Child"
    assert filtered[0].href == "Text/chapter.xhtml"


def test_toc_target_wrong_folder_is_resolved_to_spine_item():
    node = type("Node", (), {"label": "Chapter", "href": "OEBPS/Text/chapter.xhtml", "children": []})()

    filtered = filter_toc_to_spine([node], ["Text/chapter.xhtml"])

    assert len(filtered) == 1
    assert filtered[0].href == "Text/chapter.xhtml"


def test_toc_target_html_extension_is_resolved_to_xhtml_spine_item():
    node = type("Node", (), {"label": "Chapter", "href": "Text/chapter.html#p1", "children": []})()

    filtered = filter_toc_to_spine([node], ["OEBPS/Text/chapter.xhtml"])

    assert len(filtered) == 1
    assert filtered[0].href == "OEBPS/Text/chapter.xhtml"


def test_guide_nav_document_is_dropped_when_not_in_final_spine():
    guide = [("toc", "Table of Contents", "OEBPS/Text/nav.xhtml"), ("text", "Start", "OEBPS/Text/chapter.html")]

    filtered = filter_guide_to_spine(guide, ["OEBPS/Text/chapter.xhtml"])

    assert filtered == [("text", "Start", "OEBPS/Text/chapter.xhtml")]


def test_ncx_ids_are_xml_name_safe(tmp_path):
    ncx = tmp_path / "toc.ncx"
    ncx.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<navMap>
<navPoint id="000.xhtml" playOrder="1"><navLabel><text>A</text></navLabel><content src="a.xhtml"/></navPoint>
</navMap>
</ncx>""",
        encoding="utf-8",
    )

    parse_ncx_file(ncx, "toc.ncx")

    assert 'id="navPoint-1"' in ncx.read_text(encoding="utf-8")


def test_broken_br_text_is_moved_to_tail():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p>A<br>B</br></p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")

    assert "<br/>B" in output


def test_script_elements_are_removed_instead_of_marked_scripted():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title><script src="../js/app.js"/></head>
<body><p>A</p><script>alert(1)</script></body>
</html>"""
    )

    output, manifest_properties, _, _ = collect_doc_features(root, "Text/a.xhtml")

    assert "<script" not in output
    assert "scripted" not in manifest_properties


def test_empty_img_src_is_recovered_from_tail():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p><img/>../Images/cover.jpg /&gt;</p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")

    assert 'src="../Images/cover.jpg"' in output


def test_block_list_inside_paragraph_turns_parent_into_div():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body><p><span>Outline</span><ul><li>A</li></ul></p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/a.xhtml")

    assert "<p><span>Outline</span><ul>" not in output
    assert "<div><span>Outline</span><ul>" in output


def test_case_mismatched_local_hrefs_are_rewritten(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "style").mkdir(parents=True)
    (tmp_path / "OEBPS" / "style" / "book.css").write_text("p {}", encoding="utf-8")
    page = tmp_path / "OEBPS" / "Text" / "a.xhtml"
    page.write_text('<link href="../Style/book.css" rel="stylesheet"/>', encoding="utf-8")

    fix_case_mismatched_local_hrefs(tmp_path)

    assert 'href="../style/book.css"' in page.read_text(encoding="utf-8")


def test_case_mismatched_opf_hrefs_are_rewritten(tmp_path):
    (tmp_path / "OEBPS" / "Style").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Style" / "book.css").write_text("p {}", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text('<item href="style/book.css" media-type="text/css"/>', encoding="utf-8")

    fix_case_mismatched_local_hrefs(tmp_path)

    assert 'href="Style/book.css"' in opf.read_text(encoding="utf-8")


def test_missing_image_and_anchor_references_are_repaired(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    page = tmp_path / "OEBPS" / "Text" / "a.xhtml"
    page.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>A</title></head>
<body><p><img src="../Images/missing.jpg"/><a href="b.xhtml#missing">B</a><a href="missing.xhtml">Missing</a></p></body>
</html>""",
        encoding="utf-8",
    )
    (tmp_path / "OEBPS" / "Text" / "b.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>B</title></head><body><p id="exists">B</p></body>
</html>""",
        encoding="utf-8",
    )

    repair_missing_xhtml_references(tmp_path)

    output = page.read_text(encoding="utf-8")
    assert "<img" not in output
    assert 'href="b.xhtml"' in output
    assert 'href="missing.xhtml"' not in output


def test_image_links_are_converted_to_spans(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Images").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Images" / "chapter-01.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
    page = tmp_path / "OEBPS" / "Text" / "a.xhtml"
    page.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>A</title></head>
<body><p><a href="../Images/chapter-01.jpg">第一章</a></p><div><a href="../Images/chapter-01.jpg"><img src="../Images/chapter-01.jpg"/></a></div></body>
</html>""",
        encoding="utf-8",
    )

    repair_missing_xhtml_references(tmp_path)

    output = page.read_text(encoding="utf-8")
    assert 'href="../Images/chapter-01.jpg"' not in output
    assert "<span>第一章</span>" in output
    assert '<span><img src="../Images/chapter-01.jpg"/></span>' in output


def test_missing_cover_reference_uses_actual_cover_file(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "cover.jpeg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
    page = tmp_path / "OEBPS" / "Text" / "cover.xhtml"
    page.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Cover</title></head>
<body><img src="OEBPS/Images/cover.jpg"/></body>
</html>""",
        encoding="utf-8",
    )

    repair_missing_xhtml_references(tmp_path)

    assert 'src="../../cover.jpeg"' in page.read_text(encoding="utf-8")


def test_missing_svg_cover_reference_uses_actual_cover_file(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "cover.jpeg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
    page = tmp_path / "OEBPS" / "Text" / "cover.xhtml"
    page.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Cover</title></head>
<body><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><image xlink:href="../Images/cover.jpg"/></svg></body>
</html>""",
        encoding="utf-8",
    )

    repair_missing_xhtml_references(tmp_path)

    assert 'href="../../cover.jpeg"' in page.read_text(encoding="utf-8")


def test_missing_stylesheet_reference_uses_actual_css_location(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "styles").mkdir()
    (tmp_path / "styles" / "book.css").write_text("p {}", encoding="utf-8")
    page = tmp_path / "OEBPS" / "Text" / "a.xhtml"
    page.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>A</title><link href="../Styles/book.css" rel="stylesheet"/></head>
<body><p>A</p></body>
</html>""",
        encoding="utf-8",
    )

    repair_missing_xhtml_references(tmp_path)

    assert 'href="../../styles/book.css"' in page.read_text(encoding="utf-8")


def test_missing_stylesheet_and_same_page_fragment_are_repaired(tmp_path):
    (tmp_path / "OEBPS").mkdir()
    page = tmp_path / "OEBPS" / "a.xhtml"
    page.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>A</title><link href="missing.css" rel="stylesheet"/></head>
<body><a href="#missing">Missing</a></body>
</html>""",
        encoding="utf-8",
    )

    repair_missing_xhtml_references(tmp_path)

    output = page.read_text(encoding="utf-8")
    assert "<link" not in output
    assert 'href="#missing"' not in output


def test_missing_css_url_is_removed_when_no_replacement_exists(tmp_path):
    (tmp_path / "OEBPS" / "Styles").mkdir(parents=True)
    css = tmp_path / "OEBPS" / "Styles" / "style.css"
    css.write_text("blockquote { background: rgba(0,0,0,.2) url('../css/Images/missing.jpg'); }", encoding="utf-8")

    repair_missing_css_references(tmp_path)

    output = css.read_text(encoding="utf-8")
    assert "missing.jpg" not in output
    assert "background: rgba(0,0,0,.2) none" in output


def test_missing_css_url_uses_matching_existing_resource(tmp_path):
    (tmp_path / "OEBPS" / "Styles").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Images").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Images" / "Old-paper2.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
    css = tmp_path / "OEBPS" / "Styles" / "style.css"
    css.write_text("blockquote { background: url('../css/Images/Old-paper2.jpg'); }", encoding="utf-8")

    repair_missing_css_references(tmp_path)

    assert "../Images/Old-paper2.jpg" in css.read_text(encoding="utf-8")


def test_bmp_images_are_converted_to_png_and_references_rewritten(tmp_path):
    if convert_bmp_images.__globals__.get("Image") is None:
        return
    from PIL import Image as PILImage

    (tmp_path / "OEBPS").mkdir()
    bmp = tmp_path / "OEBPS" / "cover.bmp"
    PILImage.new("RGB", (1, 1), (255, 0, 0)).save(bmp, "BMP")
    page = tmp_path / "OEBPS" / "coverpage.xhtml"
    page.write_text('<img src="cover.bmp" alt="cover"/>', encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text('<item href="cover.bmp" media-type="image/bmp"/>', encoding="utf-8")

    convert_bmp_images(tmp_path)

    assert not bmp.exists()
    assert (tmp_path / "OEBPS" / "cover.png").exists()
    assert 'src="cover.png"' in page.read_text(encoding="utf-8")
    assert 'href="cover.png"' in opf.read_text(encoding="utf-8")


def test_bmp_content_with_wrong_extension_is_converted(tmp_path):
    if convert_bmp_images.__globals__.get("Image") is None:
        return
    from PIL import Image as PILImage

    (tmp_path / "OPS" / "images").mkdir(parents=True)
    image = tmp_path / "OPS" / "images" / "wrong.jpg"
    PILImage.new("RGB", (1, 1), (255, 0, 0)).save(image, "BMP")
    page = tmp_path / "OPS" / "chapter.xhtml"
    page.write_text('<img src="images/wrong.jpg" alt="cover"/>', encoding="utf-8")

    convert_bmp_images(tmp_path)

    assert not image.exists()
    assert (tmp_path / "OPS" / "images" / "wrong.png").exists()
    assert 'src="images/wrong.png"' in page.read_text(encoding="utf-8")


def test_ncx_is_rebuilt_with_valid_navmap(tmp_path):
    ncx = tmp_path / "toc.ncx"
    ncx.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="u"/></head>
<docTitle><text>Book</text></docTitle>
<navMap><navPoint id="bad.id" playOrder="1"><navLabel><text>A</text></navLabel><content src="a.xhtml"/>
<navMap><navPoint id="nested.bad" playOrder="2"><navLabel><text>B</text></navLabel><content src="b.xhtml"/></navPoint></navMap>
</navPoint></navMap>
</ncx>""",
        encoding="utf-8",
    )

    parse_ncx_file(ncx, "toc.ncx")
    etree.fromstring(ncx.read_bytes())

    data = ncx.read_text(encoding="utf-8")
    assert "<navMap>" in data
    assert 'id="navPoint-1"' in data


def test_ncx_rebuild_skips_duplicate_targets(tmp_path):
    ncx = tmp_path / "toc.ncx"
    ncx.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<navMap>
<navPoint id="a" playOrder="1"><navLabel><text>A</text></navLabel><content src="same.xhtml"/></navPoint>
<navPoint id="b" playOrder="2"><navLabel><text>B</text></navLabel><content src="same.xhtml"/></navPoint>
</navMap>
</ncx>""",
        encoding="utf-8",
    )

    parse_ncx_file(ncx, "toc.ncx")

    assert ncx.read_text(encoding="utf-8").count("<navPoint") == 1


def test_ncx_relative_targets_are_resolved_from_ncx_folder(tmp_path):
    ncx = tmp_path / "OEBPS" / "toc.ncx"
    ncx.parent.mkdir()
    ncx.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<navMap><navPoint id="a" playOrder="1"><navLabel><text>A</text></navLabel><content src="Text/a.xhtml"/></navPoint></navMap>
</ncx>""",
        encoding="utf-8",
    )

    _title, nodes, _pages = parse_ncx_file(ncx, "OEBPS/toc.ncx")

    assert nodes[0].href == "OEBPS/Text/a.xhtml"


def test_landmarks_self_fragment_href_is_removed(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    page = tmp_path / "OEBPS" / "Text" / "nav.xhtml"
    page.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>N</title></head>
<body><nav epub:type="landmarks"><ol><li><a epub:type="toc" href="#toc">TOC</a></li></ol></nav><nav id="toc"/></body>
</html>""",
        encoding="utf-8",
    )

    repair_missing_xhtml_references(tmp_path)

    assert 'href="#toc"' not in page.read_text(encoding="utf-8")


def test_existing_referenced_files_are_added_to_manifest(tmp_path):
    (tmp_path / "text").mkdir()
    (tmp_path / "img").mkdir()
    (tmp_path / "styles").mkdir()
    (tmp_path / "fonts").mkdir()
    (tmp_path / "img" / "pic.jpeg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
    (tmp_path / "img" / "poster.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
    (tmp_path / "img" / "wide.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
    (tmp_path / "styles" / "book.css").write_text("@import '../styles/theme.css';\n@font-face { src: url('../fonts/body.otf'); }", encoding="utf-8")
    (tmp_path / "styles" / "theme.css").write_text("p {}", encoding="utf-8")
    (tmp_path / "fonts" / "body.otf").write_bytes(b"OTTO" + b"0" * 20)
    (tmp_path / "text" / "chapter.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink">
<head><link rel="stylesheet" href="../styles/book.css"/></head>
<body>
<img src="../img/pic.jpeg" srcset="../img/wide.png 2x"/>
<video poster="../img/poster.png"/>
<svg><image xlink:href="../img/pic.jpeg"/></svg>
</body></html>""",
        encoding="utf-8",
    )
    opf = tmp_path / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest><item id="chap" href="text/chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="chap"/></spine>
</package>""",
        encoding="utf-8",
    )

    add_missing_manifest_items(tmp_path, "content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'href="img/pic.jpeg"' in data
    assert 'media-type="image/jpeg"' in data
    assert 'href="img/poster.png"' in data
    assert 'href="img/wide.png"' in data
    assert 'href="styles/book.css"' in data
    assert 'href="styles/theme.css"' in data
    assert 'href="fonts/body.otf"' in data


def test_cleanup_opf_removes_missing_items_js_bookmarks_and_dedupes_nav(tmp_path):
    (tmp_path / "OEBPS" / "Misc").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Misc" / "note.js").write_text("alert(1)", encoding="utf-8")
    (tmp_path / "META-INF").mkdir()
    (tmp_path / "META-INF" / "calibre_bookmarks.txt").write_text("bookmark", encoding="utf-8")
    (tmp_path / "OEBPS" / "nav.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="js" href="Misc/note.js" media-type="application/xhtml+xml"/>
<item id="bookmark" href="../META-INF/calibre_bookmarks.txt" media-type="text/plain"/>
<item id="missing" href="Images/missing.jpg" media-type="image/jpeg"/>
<item id="nav1" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="nav2" href="othernav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
</manifest>
<spine><itemref idref="missing"/><itemref idref="js"/><itemref idref="bookmark"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'id="missing"' not in data
    assert 'idref="missing"' not in data
    assert 'id="js"' not in data
    assert 'idref="js"' not in data
    assert 'calibre_bookmarks.txt' not in data
    assert not (tmp_path / "OEBPS" / "Misc" / "note.js").exists()
    assert not (tmp_path / "META-INF" / "calibre_bookmarks.txt").exists()
    assert data.count('properties="nav"') == 1


def test_cleanup_opf_applies_calibre_style_structural_fixes(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "a.xhtml").write_text("<html/>", encoding="utf-8")
    (tmp_path / "OEBPS" / "Text" / "b.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="missing">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
<dc:identifier id="empty"> </dc:identifier>
<dc:meta property="dcterms:modified">2026-07-11T12:00:00Z</dc:meta>
<dc:meta opf:name="cover" content="cover-image"/>
<opf:meta>2026-07-11T12:00:00Z</opf:meta>
</metadata>
<manifest>
<item id="1bad" href="Text/a.xhtml" media-type="text/plain" duokan-page-fullscreen="true" properties="duokan-page-fullscreen"/>
<item id="dup" href="Text/b.xhtml" media-type="application/xhtml+xml"/>
<item id="dup2" href="Text/b.xhtml" media-type="application/xhtml+xml"/>
<item id="nohref" media-type="text/css"/>
</manifest>
<spine><itemref idref="1bad" linear-type="no" properties="duokan-page-fullscreen"/><itemref idref="dup" linear="maybe"/><itemref idref="dup"/><itemref idref="nohref"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'id="id_1bad"' in data
    assert 'idref="id_1bad"' in data
    assert 'media-type="application/xhtml+xml"' in data
    assert 'linear-type=' not in data
    assert 'idref="id_1bad" linear="no"' in data
    assert 'linear="maybe"' not in data
    assert 'duokan-page-fullscreen' not in data
    assert "<opf:meta" not in data
    assert data.count('property="dcterms:modified"') == 1
    assert 'id="nohref"' not in data
    assert data.count('href="Text/b.xhtml"') == 1
    assert data.count('idref="dup"') == 1
    assert 'unique-identifier="uid"' in data
    assert "urn:uuid:" in data
    assert 'id="empty"' not in data
    assert "<dc:meta" not in data
    assert '<meta property="dcterms:modified">2026-07-11T12:00:00Z</meta>' in data
    root = etree.fromstring(data.encode("utf-8"))
    cover_meta = root.xpath("//*[local-name()='meta' and @name='cover']")
    assert len(cover_meta) == 1
    assert cover_meta[0].get("content") == "cover-image"
    assert root.xpath("string(//*[local-name()='title'])") == "Untitled"
    assert root.xpath("string(//*[local-name()='language'])") == "zh-Hant"


def test_cleanup_opf_removes_nonstandard_dc_metadata(tmp_path):
    (tmp_path / "OPS").mkdir()
    opf = tmp_path / "OPS" / "fb.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0">
<metadata><dc:title>Sample</dc:title><dc:language>zh-TW</dc:language><dc:builder>epubBuilder</dc:builder><dc:builder_version>1</dc:builder_version></metadata>
<manifest/>
<spine/>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OPS/fb.opf")

    data = opf.read_text(encoding="utf-8")
    assert "dc:builder" not in data
    assert "builder_version" not in data


def test_cleanup_opf_removes_empty_undeclared_ibooks_meta(tmp_path):
    opf = tmp_path / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>zh-TW</dc:language><meta property="ibooks:version"/><meta property="ibooks:specified-fonts"/></metadata>
<manifest/>
<spine/>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "content.opf")

    data = opf.read_text(encoding="utf-8")
    assert "ibooks:" not in data


def test_cleanup_opf_removes_empty_role_meta(tmp_path):
    opf = tmp_path / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>zh-TW</dc:language><meta refines="#creator2" property="role" scheme="marc:relators"/></metadata>
<manifest/>
<spine/>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "content.opf")

    assert 'property="role"' not in opf.read_text(encoding="utf-8")


def test_cleanup_opf_removes_empty_epubmerge_meta_and_repairs_modified(tmp_path):
    opf = tmp_path / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title id="title1">Sample</dc:title>
<meta refines="#title1" property="title-type">main</meta>
<meta refines="#title1" property="title-type"/>
<dc:creator id="creator1">Author</dc:creator>
<meta refines="#creator1" property="file-as"/>
<dc:identifier id="uid">urn:uuid:test</dc:identifier>
<dc:language>zh-TW</dc:language>
<meta property="belongs-to-collection"/>
<meta refines="#series" property="collection-type"/>
<meta refines="#series" property="group-position"/>
<meta property="dcterms:modified"/>
</metadata>
<manifest/>
<spine/>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "content.opf")

    data = opf.read_text(encoding="utf-8")
    assert data.count('property="title-type"') == 1
    assert 'property="file-as"' not in data
    assert 'property="belongs-to-collection"' not in data
    assert 'refines="#series"' not in data
    assert re.search(r'<meta property="dcterms:modified">\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z</meta>', data)


def test_cleanup_opf_repoints_missing_manifest_item_to_actual_file(tmp_path):
    (tmp_path / "OEBPS").mkdir()
    (tmp_path / "cover.jpeg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest><item id="cover" href="Images/cover.jpg" media-type="image/jpeg"/></manifest>
<spine/>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    assert 'href="../cover.jpeg"' in opf.read_text(encoding="utf-8")


def test_cleanup_opf_normalizes_package_prefixed_duplicate_hrefs(tmp_path):
    (tmp_path / "OEBPS").mkdir()
    (tmp_path / "OEBPS" / "cover.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata><meta name="cover" content="cover"/></metadata>
<manifest>
<item id="cover.jpg" href="OEBPS/cover.jpg" media-type="image/jpeg"/>
<item id="cover" href="OEBPS/cover.jpg" media-type="image/jpeg" properties="cover-image"/>
</manifest>
<spine/>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'href="cover.jpg"' in data
    assert "OEBPS/cover.jpg" not in data
    assert data.count('href="cover.jpg"') == 1


def test_nav_leaf_spans_without_links_are_removed(tmp_path):
    (tmp_path / "OEBPS").mkdir()
    nav = tmp_path / "OEBPS" / "nav.xhtml"
    nav.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>N</title></head>
<body><nav epub:type="toc"><ol><li><a href="Text/a.xhtml">A</a></li><li><span>Missing</span></li><li><span>Part</span><ol><li><a href="Text/b.xhtml">B</a></li></ol></li></ol></nav></body>
</html>""",
        encoding="utf-8",
    )
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>
<spine/>
</package>""",
        encoding="utf-8",
    )

    cleanup_nav_leaf_spans(tmp_path, "OEBPS/content.opf")

    output = nav.read_text(encoding="utf-8")
    assert "Missing" not in output
    assert "Part" in output
    assert 'href="Text/a.xhtml"' in output


def test_cleanup_opf_sanitizes_abnormal_namespaces(tmp_path):
    (tmp_path / "OEBPS").mkdir()
    (tmp_path / "OEBPS" / "a.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf/v3" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.0/"><dc:identifier id="uid">urn:uuid:test</dc:identifier></metadata>
<manifest><item id="chap" href="a.xhtml" media-type="text/plain"/></manifest>
<spine><itemref idref="chap"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    root = etree.fromstring(data.encode("utf-8"))
    assert etree.QName(root).namespace == "http://www.idpf.org/2007/opf"
    assert root.xpath("string(//*[local-name()='identifier'])") == "urn:uuid:test"
    assert root.xpath("string(//*[local-name()='language'])") == "zh-Hant"
    assert 'media-type="application/xhtml+xml"' in data


def test_cleanup_opf_uses_sniffed_image_media_type(tmp_path):
    (tmp_path / "OEBPS" / "Images").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Images" / "wrong.jpg").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"0" * 20
    )
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest><item id="img" href="Images/wrong.jpg" media-type="image/jpeg"/></manifest>
<spine/>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    assert 'media-type="image/png"' in opf.read_text(encoding="utf-8")


def test_ncx_parser_ignores_comments_and_processing_instructions(tmp_path):
    ncx = tmp_path / "toc.ncx"
    ncx.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">
<head><?legacy value?><meta name="dtb:uid" content="urn:uuid:test"/></head>
<docTitle><text>Sample</text></docTitle>
<navMap><!-- generated by old tool --><navPoint id="n1" playOrder="1"><navLabel><text>Start</text></navLabel><content src="Text/a.xhtml"/></navPoint></navMap>
</ncx>""",
        encoding="utf-8",
    )

    _title, nodes, _pages = parse_ncx_file(ncx, "toc.ncx")

    assert nodes[0].href == "Text/a.xhtml"


def test_empty_ncx_is_treated_as_missing_toc(tmp_path):
    ncx = tmp_path / "toc.ncx"
    ncx.write_text('<?xml version="1.0" encoding="utf-8"?>', encoding="utf-8")

    title, nodes, pages = parse_ncx_file(ncx, "toc.ncx")
    normalize_ncx_play_order(ncx)

    assert title is None
    assert nodes == []
    assert pages == []


def test_css_direction_and_star_hacks_are_removed():
    output = sanitize_css(
        """input,textarea,select{*font-size:100%;}
.calibre {
    -webkit-writing-mode: vertical-rl;
    direction: rtl;
    writing-mode: tb-rl
}"""
    )

    assert "*font-size" not in output
    assert "font-size:100%" in output
    assert "direction:" not in output
    assert "writing-mode: tb-rl" in output


def test_css_fullwidth_percent_is_normalized():
    output = sanitize_css(".cover { width: 100％; margin-left: 12.5％; }")

    assert "100%" in output
    assert "12.5%" in output
    assert "％" not in output


def test_css_malformed_comments_important_and_extra_semicolons_are_repaired():
    output = sanitize_css(
        """@namespace h "http:
p {
color:green; !important;
overflow:hidden;;
}
/* broken heading
blockquote {
   /*
background:#F9F0C9 none;
*/
background-size:100% 100%;
       border-radius: 5px;
}
.ok { color: red; }"""
    )

    assert "color: green !important" in output
    assert "overflow:hidden;" in output
    assert "@namespace" not in output
    assert ";;" not in output
    assert "background-size:100% 100%" not in output
    assert ".ok { color: red; }" in output


def test_css_truncated_data_url_declaration_is_removed():
    output = sanitize_css(
        """.reader_footer_note {
  background-color: black;
  background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAm
  background-repeat: no-repeat;
}"""
    )

    assert "background-image" not in output
    assert "data:image" not in output
    assert "background-repeat: no-repeat" in output


def test_css_unbalanced_and_orphan_braces_are_repaired():
    assert sanitize_css("}") == ""
    assert sanitize_css("@font-face { src: url(a.ttf); }\n}") == ""
    output = sanitize_css(".zzvu {\n\tmargin-left: 30%; text-indent: 0; ")
    assert output.rstrip().endswith("}")


def test_fixed_layout_pages_get_viewport_from_first_image(tmp_path):
    pil_image = pytest.importorskip("PIL.Image")
    (tmp_path / "OEBPS" / "html").mkdir(parents=True)
    (tmp_path / "OEBPS" / "image").mkdir(parents=True)
    pil_image.new("RGB", (640, 960)).save(tmp_path / "OEBPS" / "image" / "cover.jpg")
    (tmp_path / "OEBPS" / "html" / "cover.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Cover</title><meta charset="utf-8"/></head>
<body><img src="../image/cover.jpg" alt="cover"/></body>
</html>""",
        encoding="utf-8",
    )
    (tmp_path / "OEBPS" / "content.opf").write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata><meta property="rendition:layout">pre-paginated</meta></metadata>
<manifest><item id="cover" href="html/cover.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="cover"/></spine>
</package>""",
        encoding="utf-8",
    )

    add_fixed_layout_viewports(tmp_path, "OEBPS/content.opf")

    output = (tmp_path / "OEBPS" / "html" / "cover.xhtml").read_text(encoding="utf-8")
    assert 'name="viewport"' in output
    assert 'content="width=640, height=960"' in output


def test_cleanup_opf_makes_cover_xhtml_linear_by_default(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "cover.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest><item id="cover.xhtml" href="Text/cover.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="cover.xhtml" linear="no"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'idref="cover.xhtml"' in data
    assert 'linear="no"' not in data


def test_cleanup_opf_removes_nav_itemref_even_when_id_is_toc(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "nav.xhtml").write_text("<html/>", encoding="utf-8")
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="toc" href="Text/nav.xhtml" media-type="application/xhtml+xml"/>
<item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="chapter"/><itemref idref="toc" linear="no"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'idref="chapter"' in data
    assert 'idref="toc"' not in data
