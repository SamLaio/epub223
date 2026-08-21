import re
import sys
import uuid
import zipfile
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
    convert_named_entities,
    convert_bmp_images,
    collect_hyperlinked_xhtml_targets,
    filter_guide_to_spine,
    filter_toc_to_spine,
    fix_case_mismatched_local_hrefs,
    flatten_pathological_single_chain_nav,
    normalize_all_xhtml_files,
    normalize_epubcheck_xhtml,
    normalize_ncx_play_order,
    parse_ncx_file,
    parse_xml_recovering,
    read_text_file,
    repair_missing_css_references,
    repair_missing_xhtml_references,
    required_manifest_properties_for_xhtml,
    sanitize_all_css_files,
    sanitize_css,
    sanitize_style_value,
    sync_ncx_uid,
    normalize_language_tag,
)
from epub3itizer.chinese import convert_chinese_document, to_traditional  # noqa: E402
from epub3itizer.cli import parse_args  # noqa: E402
from epub3itizer.repair import repair_epub  # noqa: E402


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


def test_opf_package_prefix_includes_calibre_when_needed():
    opf2 = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
<dc:title>Sample</dc:title>
<dc:language>en</dc:language>
<dc:identifier id="uid">123</dc:identifier>
</metadata>
<manifest>
<item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml" properties="calibre:title-page" />
</manifest>
<spine><itemref idref="titlepage" /></spine>
</package>
"""
    opf3 = Opf_Converter(opf2, {}, {}, {}, ["titlepage"]).get_opf3()

    assert 'prefix="rendition: http://www.idpf.org/vocab/rendition/# calibre: http://calibre.kovidgoyal.net/2009/metadata"' in opf3
    assert 'properties="calibre:title-page"' in opf3
    etree.fromstring(opf3.encode("utf-8"))


def test_read_text_file_falls_back_to_cp950(tmp_path):
    source = tmp_path / "legacy.xhtml"
    source.write_bytes('<?xml version="1.0" encoding="big5"?><html>繁體中文</html>'.encode("cp950"))

    assert "繁體中文" in read_text_file(source)


def _write_case_mismatch_epub(epub_path: Path) -> None:
    container_xml = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Sample</dc:title>
    <dc:language>zh-Hant</dc:language>
    <dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>
  </metadata>
  <manifest>
    <item id="chap" href="ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="cover" href="Images/cover.jpg" media-type="image/jpeg"/>
  </manifest>
  <spine>
    <itemref idref="chap"/>
  </spine>
</package>
"""
    xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Sample</title></head>
  <body><p><img src="Images/COVER.JPG" alt="cover"/></p></body>
</html>
"""
    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OPS/package.opf", opf)
        zf.writestr("OPS/ch1.xhtml", xhtml)
        zf.writestr("OPS/Images/cover.jpg", b"\xff\xd8\xff\xd9")


def test_repair_only_fixes_case_mismatched_local_hrefs(tmp_path):
    source = tmp_path / "sample.epub"
    output = tmp_path / "sample_repaired.epub"
    _write_case_mismatch_epub(source)

    result = repair_epub(source, output)

    assert result == output
    with zipfile.ZipFile(output) as zf:
        data = zf.read("OPS/ch1.xhtml").decode("utf-8")
    assert "Images/cover.jpg" in data
    assert "COVER.JPG" not in data


def test_repair_only_adds_svg_manifest_property(tmp_path):
    source = tmp_path / "svg-cover.epub"
    output = tmp_path / "svg-cover-repaired.epub"
    container_xml = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Sample</dc:title>
    <dc:language>zh-Hant</dc:language>
    <dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>
  </metadata>
  <manifest>
    <item id="cover-page" href="Text/cover.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap" href="Text/ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="cover-image" href="Images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>
  </manifest>
  <spine>
    <itemref idref="cover-page"/>
    <itemref idref="chap"/>
  </spine>
</package>
"""
    cover = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Cover</title></head>
<body>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <image href="../Images/cover.jpg" width="100" height="100"/>
</svg>
</body>
</html>
"""
    chapter = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter</title></head>
<body><p>Text</p></body>
</html>
"""
    with zipfile.ZipFile(source, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OPS/package.opf", opf)
        zf.writestr("OPS/Text/cover.xhtml", cover)
        zf.writestr("OPS/Text/ch1.xhtml", chapter)
        zf.writestr("OPS/Images/cover.jpg", b"\xff\xd8\xff\xd9")

    repair_epub(source, output)

    with zipfile.ZipFile(output) as zf:
        opf_root = etree.fromstring(zf.read("OPS/package.opf"))
    cover_item = opf_root.xpath(".//*[local-name()='item' and @id='cover-page']")[0]
    assert "svg" in cover_item.get("properties", "").split()


def test_repair_only_removes_stale_svg_manifest_property(tmp_path):
    source = tmp_path / "stale-svg-cover.epub"
    output = tmp_path / "stale-svg-cover-repaired.epub"
    container_xml = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Sample</dc:title>
    <dc:language>zh-Hant</dc:language>
    <dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>
  </metadata>
  <manifest>
    <item id="cover-page" href="Text/cover.xhtml" media-type="application/xhtml+xml" properties="svg"/>
    <item id="cover-image" href="Images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>
  </manifest>
  <spine>
    <itemref idref="cover-page"/>
  </spine>
</package>
"""
    cover = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Cover</title></head>
<body><div><img alt="cover" src="../Images/cover.jpg"/></div></body>
</html>
"""
    with zipfile.ZipFile(source, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OPS/package.opf", opf)
        zf.writestr("OPS/Text/cover.xhtml", cover)
        zf.writestr("OPS/Images/cover.jpg", b"\xff\xd8\xff\xd9")

    repair_epub(source, output)

    with zipfile.ZipFile(output) as zf:
        opf_root = etree.fromstring(zf.read("OPS/package.opf"))
    cover_item = opf_root.xpath(".//*[local-name()='item' and @id='cover-page']")[0]
    assert "svg" not in cover_item.get("properties", "").split()


def test_repair_only_removes_stale_scripted_manifest_property(tmp_path):
    source = tmp_path / "stale-scripted.epub"
    output = tmp_path / "stale-scripted-repaired.epub"
    container_xml = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Sample</dc:title>
    <dc:language>zh-Hant</dc:language>
    <dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>
  </metadata>
  <manifest>
    <item id="chap" href="Text/ch1.xhtml" media-type="application/xhtml+xml" properties="scripted"/>
  </manifest>
  <spine>
    <itemref idref="chap"/>
  </spine>
</package>
"""
    xhtml = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter</title></head>
<body><p>No active content remains.</p></body>
</html>
"""
    with zipfile.ZipFile(source, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OPS/package.opf", opf)
        zf.writestr("OPS/Text/ch1.xhtml", xhtml)

    repair_epub(source, output)

    with zipfile.ZipFile(output) as zf:
        opf_root = etree.fromstring(zf.read("OPS/package.opf"))
    item = opf_root.xpath(".//*[local-name()='item' and @id='chap']")[0]
    assert "scripted" not in item.get("properties", "").split()


def test_convert_chinese_document_converts_readable_text_quotes_not_links():
    source = """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>“汉字” ‘中国’</title><meta name="description" content="“实时”"/></head>
<body><p title="‘三民书局’">“汉字”<script>var name = "“汉字”";</script><a href="Text/汉字.xhtml" id="汉字">链接</a><img src="Images/汉字.jpg" alt="“中国”"/></p></body>
</html>"""

    output = convert_chinese_document(source, "s2tw")

    assert "「漢字」 『中國』" in output
    assert 'content="「即時」"' in output
    assert 'title="『三民書局』"' in output
    assert 'alt="「中國」"' in output
    assert 'href="Text/汉字.xhtml"' in output
    assert 'src="Images/汉字.jpg"' in output
    assert 'id="汉字"' in output
    assert 'var name = "“汉字”";' in output


def test_convert_chinese_cli_option_is_explicit():
    args = parse_args(["input.epub", "-o", "output.epub", "--convert-chinese", "s2tw"])

    assert args.convert_chinese == "s2tw"


def test_to_traditional_uses_opencc_and_custom_replacements():
    assert to_traditional("“汉字” ‘中国’ 实时 信息") == "「漢字」 『中國』 即時 資訊"


def test_empty_xhtml_title_is_filled_from_href():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>   </title></head>
<body><p>body</p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "<title>chapter01.xhtml</title>" in output


def test_known_source_ad_paragraph_is_removed():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body>
<p>這一段是正文，更多精彩也可能只是正常語句。</p>
<p class="a">更多精彩，更多好書，盡在請看小說網http://Www.qinkan.net</p>
<p>下一段正文。</p>
</body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "qinkan.net" not in output
    assert "請看小說網" not in output
    assert "這一段是正文" in output
    assert "下一段正文" in output


def test_yanqingtu_source_ad_paragraphs_are_removed():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body>
<p>正文也可能提到更多精彩，不應該被刪。</p>
<p>聲明：EPUB電子書內容由言情兔(yanqingtu.com)網友整理分享，下載24小時內刪除，請購買正版閱讀。</p>
<p>《獵愛狂夫》全本完結，更多精彩言情小說請訪問言情兔<span>www.yanqingtu.com</span>免費下載。</p>
<p>下一段正文。</p>
</body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "yanqingtu.com" not in output
    assert "言情兔" not in output
    assert "正版閱讀" not in output
    assert "正文也可能提到更多精彩" in output
    assert "下一段正文" in output


def test_known_inline_source_ads_are_removed_without_dropping_text():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head>
<body>
<p>三老[www.qinkan.net請看小說網]爺去也得去。</p>
<p>那些[請看小說網·電子書下載樂園—wＷw.QiＳuu.cＯm］伺候的人。</p>
</body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert "qinkan.net" not in output
    assert "請看小說網" not in output
    assert "QiＳuu" not in output
    assert "三老爺去也得去" in output
    assert "那些伺候的人" in output


def test_empty_definition_list_toc_becomes_ordered_list():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Table Of Contents</title></head>
<body>
<div class="toc"><dl class="toc">
<dt class="tocl2"><a href="chapter0001.xhtml">第一章</a></dt><dd></dd>
<dt class="tocl2"><a href="chapter0002.xhtml">第二章</a></dt><dd></dd>
<dt class="tocl2"><a href="chapter0003.xhtml">第三章</a></dt><dd></dd>
</dl></div>
</body>
</html>""".encode("utf-8")
    )

    output, _, _, _ = collect_doc_features(root, "Text/book-toc.xhtml")

    assert "<dl" not in output
    assert "<dd" not in output
    assert "<ol" in output
    assert output.count("<li") == 3
    assert 'href="chapter0001.xhtml"' in output


def test_pathological_single_chain_nav_is_flattened():
    root = etree.fromstring(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Nav</title></head>
<body><nav epub:type="toc"><ol>
<li><a href="chapter0001.xhtml">第一章</a><ol>
<li><a href="chapter0002.xhtml">第二章</a><ol>
<li><a href="chapter0003.xhtml">第三章</a><ol>
<li><a href="chapter0004.xhtml">第四章</a><ol>
<li><a href="chapter0005.xhtml">第五章</a></li>
<li><a href="chapter0006.xhtml">第六章</a></li>
</ol></li></ol></li></ol></li></ol></li>
</ol></nav></body></html>""".encode("utf-8")
    )

    changed = flatten_pathological_single_chain_nav(root)
    output = etree.tostring(root, encoding="unicode")

    assert changed is True
    assert output.count("<ol") == 1
    assert output.count("<li") == 6
    assert 'href="chapter0001.xhtml"' in output
    assert 'href="chapter0006.xhtml"' in output


def test_abnormal_namespace_declarations_are_sanitized_for_xhtml():
    root = parse_xml_recovering(
        """<html xmlns="https://www.w3.org/1999/xhtml" xmlns:xmlns="bad">
<head><title>Title</title></head>
<body><p>body</p></body>
</html>"""
    )

    assert etree.QName(root).namespace == "http://www.w3.org/1999/xhtml"
    assert "xmlns" not in root.nsmap


def test_plain_text_xhtml_is_wrapped_before_parse():
    root = parse_xml_recovering("Welcome")
    output = etree.tostring(root, encoding="unicode")

    assert etree.QName(root).localname == "html"
    assert "Welcome" in output
    assert root.xpath("//*[local-name()='body']")


def test_ocr_fake_text_tag_with_many_empty_attrs_is_flattened():
    root = parse_xml_recovering(
        """<html xmlns="http://www.w3.org/1999/xhtml"><body>
<p>few drin]<s at="" bar="" drake="" sensed="" the="" sad="" predatory="" face="" expected:=""/></p>
</body></html>"""
    )

    normalize_epubcheck_xhtml(root)
    output = etree.tostring(root, encoding="unicode")

    assert "<s " not in output
    assert "s at bar drake sensed the sad predatory face expected:" in output
    etree.fromstring(output.encode("utf-8"))


def test_content_link_back_to_nav_is_demoted_to_span():
    root = parse_xml_recovering(
        """<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1><a href="nav.xhtml#n1"><span>Chapter</span></a></h1>
</body></html>"""
    )

    normalize_epubcheck_xhtml(root, "Chapter.xhtml")
    output = etree.tostring(root, encoding="unicode")

    assert 'href="nav.xhtml#n1"' not in output
    assert "<span>Chapter</span>" in output


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


def test_named_entity_missing_semicolon_before_attribute_quote_is_repaired():
    fixed = convert_named_entities('<div style="font-family: &quot" data-id="x"/>')

    assert "&quot\"" not in fixed
    assert "&#34;\"" in fixed
    etree.fromstring(fixed.encode("utf-8"))


def test_html_missing_body_gets_empty_body():
    root = parse_xml_recovering(
        """<html><head><title>Only Head</title></head></html>"""
    )

    output, _, _, _ = collect_doc_features(root, "OPS/empty.html")
    out_root = etree.fromstring(output.encode("utf-8"))

    assert out_root.xpath("//*[local-name()='head']")
    assert out_root.xpath("//*[local-name()='body']")


def test_repair_missing_xhtml_references_skips_unparseable_empty_xhtml(tmp_path):
    (tmp_path / "Text").mkdir()
    (tmp_path / "Text" / "empty.xhtml").write_text("", encoding="utf-8")

    repair_missing_xhtml_references(tmp_path)


def test_required_manifest_properties_skips_unparseable_empty_xhtml(tmp_path):
    empty = tmp_path / "empty.xhtml"
    empty.write_text("", encoding="utf-8")

    assert required_manifest_properties_for_xhtml(empty) == []


def test_collect_hyperlinked_targets_skips_unparseable_empty_xhtml(tmp_path):
    (tmp_path / "empty.xhtml").write_text("", encoding="utf-8")

    assert collect_hyperlinked_xhtml_targets(tmp_path, ".") == set()


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
    fixed_uid = re.search(r"<dc:identifier[^>]*>(urn:uuid:[^<]+)</dc:identifier>", output).group(1)
    uuid.UUID(fixed_uid.split(":", 2)[2])
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


def test_nav_parent_anchor_before_child_links_is_demoted(tmp_path):
    (tmp_path / "content.opf").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>T</dc:title><dc:language>zh-Hant</dc:language><dc:identifier id="uid">urn:uuid:x</dc:identifier></metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>
<item id="chap1" href="index_split_000.html" media-type="application/xhtml+xml"/>
<item id="chap2" href="index_split_001.html" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="titlepage"/><itemref idref="chap1"/><itemref idref="chap2"/></spine>
</package>""",
        encoding="utf-8",
    )
    (tmp_path / "nav.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>nav</title></head><body><nav epub:type="toc"><ol><li>
<a href="index_split_000.html">Book</a>
<ol>
<li><a href="index_split_000.html#page_5">序章</a></li>
<li><a href="index_split_000.html">第1章</a></li>
<li><a href="index_split_001.html#page_148">版權頁</a></li>
</ol>
</li></ol></nav></body></html>""",
        encoding="utf-8",
    )

    cleanup_nav_leaf_spans(tmp_path, "content.opf")
    output = (tmp_path / "nav.xhtml").read_text(encoding="utf-8")

    assert '<span>Book</span>' in output
    assert 'href="index_split_000.html">Book</a>' not in output
    assert "第1章" not in output
    assert 'href="index_split_000.html">第1章</a>' not in output
    assert 'href="index_split_000.html#page_5"' in output
    assert 'href="index_split_001.html#page_148"' in output


def test_nav_parent_anchor_after_earlier_child_links_is_demoted(tmp_path):
    (tmp_path / "Text").mkdir()
    (tmp_path / "content.opf").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>T</dc:title><dc:language>zh-Hant</dc:language><dc:identifier id="uid">urn:uuid:x</dc:identifier></metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="chap1" href="Text/chapter_136.html" media-type="application/xhtml+xml"/>
<item id="chap2" href="Text/chapter_137.html" media-type="application/xhtml+xml"/>
<item id="chap3" href="Text/chapter_140.html" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="chap1"/><itemref idref="chap2"/><itemref idref="chap3"/></spine>
</package>""",
        encoding="utf-8",
    )
    (tmp_path / "nav.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>nav</title></head><body><nav epub:type="toc"><ol><li>
<a href="Text/chapter_140.html">卷標題</a>
<ol>
<li><a href="Text/chapter_136.html">第137章</a></li>
<li><a href="Text/chapter_137.html">第138章</a></li>
<li><a href="Text/chapter_140.html">第141章</a></li>
</ol>
</li></ol></nav></body></html>""",
        encoding="utf-8",
    )

    cleanup_nav_leaf_spans(tmp_path, "content.opf")
    output = (tmp_path / "nav.xhtml").read_text(encoding="utf-8")

    assert "<span>卷標題</span>" in output
    assert 'href="Text/chapter_140.html">卷標題</a>' not in output
    assert 'href="Text/chapter_136.html"' in output
    assert 'href="Text/chapter_137.html"' in output
    assert 'href="Text/chapter_140.html">第141章</a>' in output


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


def test_cleanup_opf_removes_spine_page_map_and_stale_switch_manifest_property(tmp_path):
    root = tmp_path
    (root / "OEBPS" / "Text").mkdir(parents=True)
    (root / "OEBPS" / "Text" / "chap.xhtml").write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body><div id="svgswitch0"><p>ok</p></div></body></html>',
        encoding="utf-8",
    )
    opf = root / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>x</dc:title><dc:language>zh-Hant</dc:language></metadata>
<manifest><item id="chap" href="Text/chap.xhtml" media-type="application/xhtml+xml" properties="switch"/></manifest>
<spine page-map="_page_map_"><itemref idref="chap"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(root, "OEBPS/content.opf")
    output = opf.read_text(encoding="utf-8")

    assert "page-map" not in output
    assert "switch" not in output


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


def test_missing_css_import_is_removed_when_no_replacement_exists(tmp_path):
    (tmp_path / "OEBPS" / "css").mkdir(parents=True)
    css = tmp_path / "OEBPS" / "css" / "book-style.css"
    css.write_text(
        '@import "style-bc-kadokawa.css";\nbody { color: black; }\n',
        encoding="utf-8",
    )

    repair_missing_css_references(tmp_path)

    output = css.read_text(encoding="utf-8")
    assert "style-bc-kadokawa.css" not in output
    assert "body { color: black; }" in output


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
    (tmp_path / "OEBPS" / "Misc" / "Provider.txt").write_text("provider", encoding="utf-8")
    (tmp_path / "META-INF").mkdir()
    (tmp_path / "META-INF" / "calibre_bookmarks.txt").write_text("bookmark", encoding="utf-8")
    (tmp_path / "OEBPS" / "nav.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="js" href="Misc/note.js" media-type="application/xhtml+xml"/>
<item id="provider" href="Misc/Provider.txt" media-type="text/plain"/>
<item id="bookmark" href="../META-INF/calibre_bookmarks.txt" media-type="text/plain"/>
<item id="missing" href="Images/missing.jpg" media-type="image/jpeg"/>
<item id="nav1" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="nav2" href="othernav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
</manifest>
<spine><itemref idref="missing"/><itemref idref="js"/><itemref idref="provider"/><itemref idref="bookmark"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'id="missing"' not in data
    assert 'idref="missing"' not in data
    assert 'id="js"' not in data
    assert 'idref="js"' not in data
    assert 'Provider.txt' not in data
    assert 'idref="provider"' not in data
    assert 'calibre_bookmarks.txt' not in data
    assert not (tmp_path / "OEBPS" / "Misc" / "note.js").exists()
    assert not (tmp_path / "OEBPS" / "Misc" / "Provider.txt").exists()
    assert not (tmp_path / "META-INF" / "calibre_bookmarks.txt").exists()
    assert data.count('properties="nav"') == 1


def test_cleanup_opf_removes_unmanifested_nested_cover_copy(tmp_path):
    (tmp_path / "OEBPS" / "OEBPS").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "cover.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    (tmp_path / "OEBPS" / "OEBPS" / "cover.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="cover-image" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>
<item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="chapter"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'href="cover.jpg"' in data
    assert "OEBPS/cover.jpg" not in data
    assert not (tmp_path / "OEBPS" / "OEBPS" / "cover.jpg").exists()


def test_cleanup_opf_renames_metadata_id_conflicting_with_manifest(tmp_path):
    (tmp_path / "OEBPS").mkdir()
    (tmp_path / "OEBPS" / "title.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0" unique-identifier="bookid">
<metadata>
<dc:title id="title">書名</dc:title>
<meta refines="#title" property="title-type">main</meta>
<dc:language>zh-Hant</dc:language>
<dc:identifier id="bookid">urn:uuid:x</dc:identifier>
<meta property="dcterms:modified">2026-08-01T00:00:00Z</meta>
</metadata>
<manifest><item id="title" href="title.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="title"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")
    output = opf.read_text(encoding="utf-8")

    assert 'item id="title"' in output
    assert 'dc:title id="meta-title"' in output
    assert 'refines="#meta-title"' in output
    assert output.count('id="title"') == 1


def test_cleanup_nav_wraps_plain_toc_list_in_epub_nav(tmp_path):
    (tmp_path / "EPUB").mkdir()
    (tmp_path / "EPUB" / "chap_001.xhtml").write_text("<html/>", encoding="utf-8")
    (tmp_path / "EPUB" / "content.opf").write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="toc" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="chap1" href="chap_001.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="chap1"/></spine>
</package>""",
        encoding="utf-8",
    )
    (tmp_path / "EPUB" / "toc.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>目錄</title></head>
<body><div class="toc"><h1>目錄</h1><ul><li><a href="chap_001.xhtml">第一章</a></li></ul></div></body>
</html>""",
        encoding="utf-8",
    )

    cleanup_nav_leaf_spans(tmp_path, "EPUB/content.opf")

    output = (tmp_path / "EPUB" / "toc.xhtml").read_text(encoding="utf-8")
    assert output.count('epub:type="toc"') == 1
    assert "<ol>" in output
    assert "<ul>" not in output


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
<meta property="hdf">0401000000000160f8203861</meta>
<meta property="ebpaj:guide-version">1.1</meta>
<meta lic="菜鳥丹丹製作，歡迎指教" ver="20200115" name="TenGo_Utility" url="https://github.com/danleetw/ebook"/>
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
    assert 'idref="id_1bad" linear="no"' not in data
    assert 'linear="maybe"' not in data
    assert 'duokan-page-fullscreen' not in data
    assert 'property="hdf"' not in data
    assert "ebpaj:guide-version" not in data
    assert "TenGo_Utility" not in data
    assert "lic=" not in data
    assert "ver=" not in data
    assert "url=" not in data
    assert "<opf:meta" not in data
    assert data.count('property="dcterms:modified"') == 1
    assert data.count('properties="nav"') == 1
    assert (tmp_path / "OEBPS" / "nav.xhtml").exists()
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
    fixed_uid = root.xpath("string(//*[local-name()='identifier'])")
    assert fixed_uid.startswith("urn:uuid:")
    uuid.UUID(fixed_uid.split(":", 2)[2])
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


def test_css_text_combine_horizontal_all_is_removed():
    output = sanitize_css(
        """.tcy {
    writing-mode: vertical-rl;
    text-combine-horizontal: all;
    text-combine: horizontal;
    text-align: center;
}"""
    )

    assert "text-combine-horizontal" not in output
    assert "text-combine:" not in output
    assert "writing-mode: vertical-rl" in output
    assert "text-align: center" in output


def test_css_duokan_text_indent_is_removed():
    output = sanitize_css(
        """.chapter {
    duokan-text-indent: 0;
    text-indent: 2em;
}"""
    )

    assert "duokan-text-indent" not in output
    assert "text-indent: 2em" in output


def test_css_text_spacing_trim_start_is_removed():
    output = sanitize_css(
        """.chapter {
    text-spacing-trim: trim-start;
    text-indent: 2em;
}"""
    )

    assert "text-spacing-trim" not in output
    assert "text-indent: 2em" in output


def test_css_directional_properties_with_spaces_are_hyphenated():
    output = sanitize_css(
        """h1 {
    padding top: 1cm;
    padding bottom: 1cm;
    margin left: 2em;
    border right: 1px solid black;
}"""
    )

    assert "padding-top: 1cm" in output
    assert "padding-bottom: 1cm" in output
    assert "margin-left: 2em" in output
    assert "border-right: 1px solid black" in output
    assert "padding top" not in output
    assert "padding bottom" not in output


def test_inline_style_duplicate_properties_keep_last_value():
    output = sanitize_style_value(
        "font-weight: normal; border-top: 1px solid black; font-weight: bold; "
        "border-top: none; border-bottom: 1px solid black; border-bottom: none"
    )

    assert output.count("font-weight") == 1
    assert output.count("border-top") == 1
    assert output.count("border-bottom") == 1
    assert "font-weight: bold" in output
    assert "border-top: none" in output
    assert "border-bottom: none" in output


def test_inline_style_duokan_text_indent_is_removed():
    output = sanitize_style_value("duokan-text-indent: 0; text-indent: 2em; color: black")

    assert "duokan-text-indent" not in output
    assert "text-indent: 2em" in output
    assert "color: black" in output


def test_inline_style_text_spacing_trim_is_removed():
    output = sanitize_style_value("text-spacing-trim: trim-start; text-indent: 2em; color: black")

    assert "text-spacing-trim" not in output
    assert "text-indent: 2em" in output
    assert "color: black" in output


def test_css_duplicate_properties_keep_last_value_in_rule_blocks():
    output = sanitize_css(
        """.dupe {
    font-weight: normal;
    font-weight: bold;
    border-left: 1px solid black;
    border-left: none;
}"""
    )

    assert output.count("font-weight") == 1
    assert output.count("border-left") == 1
    assert "font-weight: bold" in output
    assert "border-left: none" in output


def test_css_trailing_chinese_note_after_rule_is_removed():
    output = sanitize_css('.textItalic { font-style: normal; }（加標識"I"）\n.next { color: black; }')

    assert "加標識" not in output
    assert ".textItalic" in output
    assert ".next" in output


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


def test_fixed_layout_spine_itemref_gets_viewport_from_first_image(tmp_path):
    pil_image = pytest.importorskip("PIL.Image")
    (tmp_path / "OEBPS" / "image").mkdir(parents=True)
    pil_image.new("RGB", (900, 1200)).save(tmp_path / "OEBPS" / "image" / "cover.jpg")
    (tmp_path / "OEBPS" / "cover.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Cover</title></head>
<body><div><img src="image/cover.jpg" alt="cover" style="height: 100%"/></div></body>
</html>""",
        encoding="utf-8",
    )
    (tmp_path / "OEBPS" / "content.opf").write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata/>
<manifest><item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="cover" properties="rendition:layout-pre-paginated rendition:spread-none"/></spine>
</package>""",
        encoding="utf-8",
    )

    add_fixed_layout_viewports(tmp_path, "OEBPS/content.opf")

    output = (tmp_path / "OEBPS" / "cover.xhtml").read_text(encoding="utf-8")
    assert 'name="viewport"' in output
    assert 'content="width=900, height=1200"' in output


def test_text_pages_remove_stale_global_fixed_layout_when_viewport_cannot_be_inferred(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter</title></head>
<body><p>一般文字頁，不應被全域固定版面宣告要求 viewport。</p></body>
</html>""",
        encoding="utf-8",
    )
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata><meta property="rendition:layout">pre-paginated</meta></metadata>
<manifest><item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="chapter"/></spine>
</package>""",
        encoding="utf-8",
    )

    add_fixed_layout_viewports(tmp_path, "OEBPS/content.opf")

    opf_output = opf.read_text(encoding="utf-8")
    page_output = (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").read_text(encoding="utf-8")
    assert "pre-paginated" not in opf_output
    assert 'name="viewport"' not in page_output


def test_non_table_caption_is_rewritten_to_figcaption():
    root = parse_xml_recovering(
        """<html xmlns="http://www.w3.org/1999/xhtml"><body><figure><img src="a.jpg"/><caption><p>Caption</p></caption></figure></body></html>"""
    )

    normalize_epubcheck_xhtml(root)

    assert root.xpath(".//*[local-name()='figcaption']")
    assert not root.xpath(".//*[local-name()='caption']")


def test_cleanup_opf_removes_invalid_spine_property_tokens(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>zh-Hant</dc:language></metadata>
<manifest><item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="chapter" properties="viewport-width=1514, height=2048"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    output = opf.read_text(encoding="utf-8")
    assert "viewport-width" not in output
    assert "height=2048" not in output
    assert '<itemref idref="chapter"/>' in output
    assert 'properties="nav"' in output


def test_cleanup_opf_and_nav_remove_image_spine_and_image_nav_link(tmp_path):
    (tmp_path / "EPUB").mkdir()
    (tmp_path / "EPUB" / "cover.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
    (tmp_path / "EPUB" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    (tmp_path / "EPUB" / "nav.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body><nav epub:type="toc"><h2/><ol><li><a href="cover.jpg">cover.jpg</a></li></ol></nav></body></html>""",
        encoding="utf-8",
    )
    opf = tmp_path / "EPUB" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>zh-Hant</dc:language></metadata>
<manifest>
<item id="cover" href="cover.jpg" media-type="image/jpeg"/>
<item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
</manifest>
<spine><itemref idref="cover"/><itemref idref="chapter"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "EPUB/content.opf")
    cleanup_nav_leaf_spans(tmp_path, "EPUB/content.opf")

    opf_output = opf.read_text(encoding="utf-8")
    nav_output = (tmp_path / "EPUB" / "nav.xhtml").read_text(encoding="utf-8")
    assert 'idref="cover"' not in opf_output
    assert 'href="cover.jpg"' not in nav_output
    assert "Table of Contents" in nav_output
    assert 'href="chapter.xhtml"' in nav_output


def test_cleanup_nav_sorts_toc_links_by_spine_order(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    for name in ("nav.xhtml", "ch1.xhtml", "ch2.xhtml", "ch3.xhtml"):
        (tmp_path / "OEBPS" / "Text" / name).write_text("<html/>", encoding="utf-8")
    (tmp_path / "OEBPS" / "content.opf").write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="nav" href="Text/nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="ch1" href="Text/ch1.xhtml" media-type="application/xhtml+xml"/>
<item id="ch2" href="Text/ch2.xhtml" media-type="application/xhtml+xml"/>
<item id="ch3" href="Text/ch3.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="ch1"/><itemref idref="ch2"/><itemref idref="ch3"/></spine>
</package>""",
        encoding="utf-8",
    )
    (tmp_path / "OEBPS" / "Text" / "nav.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body><nav epub:type="toc"><ol>
<li><a href="ch3.xhtml">Three</a></li>
<li><a href="ch1.xhtml">One</a></li>
<li><a href="ch2.xhtml">Two</a></li>
</ol></nav></body></html>""",
        encoding="utf-8",
    )

    cleanup_nav_leaf_spans(tmp_path, "OEBPS/content.opf")

    output = (tmp_path / "OEBPS" / "Text" / "nav.xhtml").read_text(encoding="utf-8")
    assert output.index("ch1.xhtml") < output.index("ch2.xhtml") < output.index("ch3.xhtml")


def test_cleanup_nav_removes_empty_span_and_anchor_entries(tmp_path):
    (tmp_path / "OEBPS").mkdir()
    for name in ("nav.xhtml", "ch1.xhtml", "ch2.xhtml"):
        (tmp_path / "OEBPS" / name).write_text("<html/>", encoding="utf-8")
    (tmp_path / "OEBPS" / "content.opf").write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
<item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="ch1"/><itemref idref="ch2"/></spine>
</package>""",
        encoding="utf-8",
    )
    (tmp_path / "OEBPS" / "nav.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body><nav epub:type="toc"><ol>
<li><a href="ch1.xhtml">One</a><span id="GBS.1"/><ol><li><a href="ch2.xhtml">Two</a></li></ol></li>
<div style="display: none"/><div style="display: none"></div>
<li><a href="ch2.xhtml"/></li>
</ol></nav></body></html>""",
        encoding="utf-8",
    )

    cleanup_nav_leaf_spans(tmp_path, "OEBPS/content.opf")

    output = (tmp_path / "OEBPS" / "nav.xhtml").read_text(encoding="utf-8")
    assert 'id="GBS.1"' not in output
    assert '<a href="ch2.xhtml"/>' not in output
    assert 'display: none' not in output
    assert "One" in output
    assert "Two" in output


def test_cleanup_nav_converts_nested_unordered_lists_to_ordered_lists(tmp_path):
    (tmp_path / "OEBPS").mkdir()
    for name in ("nav.xhtml", "ch1.xhtml", "ch2.xhtml", "ch3.xhtml"):
        (tmp_path / "OEBPS" / name).write_text("<html/>", encoding="utf-8")
    (tmp_path / "OEBPS" / "content.opf").write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
<item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
<item id="ch3" href="ch3.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="ch1"/><itemref idref="ch2"/><itemref idref="ch3"/></spine>
</package>""",
        encoding="utf-8",
    )
    (tmp_path / "OEBPS" / "nav.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body><nav epub:type="toc"><ol>
<li><a href="ch1.xhtml">Part 1</a><ul><li><a href="ch2.xhtml">Chapter 2</a></li></ul></li>
<li><a href="ch3.xhtml">Part 2</a><menu><li><a href="ch3.xhtml#s1">Section</a></li></menu></li>
</ol></nav></body></html>""",
        encoding="utf-8",
    )

    cleanup_nav_leaf_spans(tmp_path, "OEBPS/content.opf")

    output = (tmp_path / "OEBPS" / "nav.xhtml").read_text(encoding="utf-8")
    assert "<ul" not in output
    assert "<menu" not in output
    assert output.count("<ol") >= 3
    assert "Chapter 2" in output
    assert "Section" in output


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


def test_cleanup_opf_makes_unreachable_non_linear_xhtml_linear(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    (tmp_path / "OEBPS" / "Text" / "appendix.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/>
<item id="appendix" href="Text/appendix.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="chapter"/><itemref idref="appendix" linear="no"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'idref="appendix"' in data
    assert 'linear="no"' not in data


def test_cleanup_opf_preserves_reachable_non_linear_xhtml(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body><a href="appendix.xhtml">附錄</a></body></html>',
        encoding="utf-8",
    )
    (tmp_path / "OEBPS" / "Text" / "appendix.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/>
<item id="appendix" href="Text/appendix.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine><itemref idref="chapter"/><itemref idref="appendix" linear="no"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'idref="appendix" linear="no"' in data


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


def test_language_tag_underscore_is_normalized():
    assert normalize_language_tag("zh_TW") == "zh-TW"
    assert normalize_language_tag("zh_Hant") == "zh-Hant"


def test_cleanup_opf_normalizes_existing_dc_language(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Sample</dc:title>
<dc:language>zh_TW</dc:language>
<dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>
</metadata>
<manifest><item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="chapter"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert "<dc:language>zh-TW</dc:language>" in data
    assert "zh_TW" not in data
