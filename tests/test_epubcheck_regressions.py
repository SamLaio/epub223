import re
import sys
import uuid
import zipfile
from pathlib import Path

import pytest
from lxml import etree


@pytest.mark.parametrize("advert", ["下载器购买请联系作者QQxxxxxx或者微信xxxxxxx", "下載器購買請聯絡作者QQxxxxxx或者微信xxxxxxx"])
def test_downloader_placeholder_ad_is_removed_only_from_head(advert):
    from epub3itizer.conversion import normalize_head_meta_children
    root = etree.fromstring(f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{advert}</title><meta name="author" content="{advert}"/><meta name="generator" content="pdftohtml 0.36"/><meta name="author" content="楊若暉"/></head><body><p>{advert}</p><img src="page.png"/></body></html>'.encode())
    body = etree.tostring(root.find('{http://www.w3.org/1999/xhtml}body'))
    normalize_head_meta_children(root)
    assert root.xpath('string(//*[local-name()="title"])') == '正文'
    assert root.xpath('//*[local-name()="meta"]/@content') == ['pdftohtml 0.36', '楊若暉']
    assert etree.tostring(root.find('{http://www.w3.org/1999/xhtml}body')) == body
    once = etree.tostring(root)
    normalize_head_meta_children(root)
    assert etree.tostring(root) == once

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
    normalize_raster_image_extensions,
    normalize_ncx_play_order,
    parse_ncx_file,
    parse_xml_recovering,
    read_text_file,
    repair_missing_css_references,
    repair_missing_xhtml_references,
    required_manifest_properties_for_xhtml,
    sanitize_all_css_files,
    sanitize_css,
    sanitize_package_filenames,
    sanitize_style_value,
    sync_ncx_uid,
    normalize_language_tag,
)
from epub3itizer.chinese import convert_chinese_document, to_traditional  # noqa: E402
from epub3itizer.cli import parse_args  # noqa: E402
from epub3itizer.repair import repair_epub  # noqa: E402


def test_pubu_ploc_becomes_span_without_losing_text_anchor_or_foreign_elements():
    root = etree.fromstring('<html xmlns="http://www.w3.org/1999/xhtml" xmlns:x="urn:private"><head><title>測試</title></head><body><p>前<ploc id="pos34" class="position">34<b>註記</b></ploc>後</p><x:ploc>外部</x:ploc></body></html>')
    prior = ''.join(root.itertext())
    normalize_epubcheck_xhtml(root)
    assert ''.join(root.itertext()) == prior
    span = root.find('.//{http://www.w3.org/1999/xhtml}span')
    assert span.get('id') == 'pos34' and span.get('class') == 'position'
    assert root.find('.//{urn:private}ploc') is not None
    once = etree.tostring(root)
    normalize_epubcheck_xhtml(root)
    assert etree.tostring(root) == once


def test_missing_xhtml_never_falls_back_to_same_stem_stylesheet(tmp_path):
    from epub3itizer.conversion import find_replacement_resource
    assert find_replacement_resource('Text/Copyright.xhtml', ['Styles/Copyright.css']) is None
    assert find_replacement_resource('Text/Copyright.xhtml', ['Styles/Copyright.css', 'Other/Copyright.html']) == 'Other/Copyright.html'
    (tmp_path/'Copyright.css').write_text('p { color: black; }', encoding='utf-8')
    page=tmp_path/'toc.xhtml'
    page.write_text('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>目錄</title></head><body><a href="Copyright.xhtml">版權頁</a></body></html>', encoding='utf-8')
    repair_missing_xhtml_references(tmp_path)
    root=etree.parse(str(page)).getroot()
    assert root.find('.//{http://www.w3.org/1999/xhtml}span').text == '版權頁'
    once=page.read_bytes()
    repair_missing_xhtml_references(tmp_path)
    assert page.read_bytes()==once


def test_legacy_toc_keeps_valid_spine_anchor_but_removes_nav_or_missing_targets(tmp_path):
    from epub3itizer.conversion import strip_links_from_legacy_toc_files
    (tmp_path/'content.opf').write_text('<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="official.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="chapter"/></spine></package>',encoding='utf-8')
    (tmp_path/'chapter.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><body><h1 id="chapter-start">正文</h1></body></html>',encoding='utf-8')
    (tmp_path/'official.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><body/></html>',encoding='utf-8')
    page=tmp_path/'nav.xhtml'
    page.write_text('<html xmlns="http://www.w3.org/1999/xhtml"><body><nav><a href="chapter.xhtml#chapter-start">有效章節</a><a href="official.xhtml">重複導覽</a><a href="missing.xhtml">缺頁</a></nav></body></html>',encoding='utf-8')
    strip_links_from_legacy_toc_files(tmp_path,'content.opf')
    links=etree.parse(str(page)).xpath('//*[local-name()="a"]')
    assert [a.get('href') for a in links]==['chapter.xhtml#chapter-start',None,None]
    assert [a.text for a in links]==['有效章節','重複導覽','缺頁']
    once=page.read_bytes()
    strip_links_from_legacy_toc_files(tmp_path,'content.opf')
    assert page.read_bytes()==once


def test_archive_invalid_filename_collisions_keep_every_resource_and_reference(tmp_path):
    from epub3itizer.compat import EpubBookAdapter
    archive = tmp_path / "collision.epub"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("META-INF/container.xml", '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="content.opf"/></rootfiles></container>')
        z.writestr("content.opf", '<package xmlns="http://www.idpf.org/2007/opf" version="2.0"><metadata/><manifest><item id="a" href="Text/a*b.xhtml" media-type="application/xhtml+xml"/><item id="b" href="Text/a:b.xhtml" media-type="application/xhtml+xml"/><item id="c" href="Text/ab.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="a"/><itemref idref="b"/><itemref idref="c"/></spine></package>')
        for name, text in [("a*b", "第一章"), ("a:b", "第二章"), ("ab", "第三章")]:
            z.writestr(f"Text/{name}.xhtml", f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{text}</title></head><body><p>{text}</p><a href="a%3Ab.xhtml#target">下一章</a></body></html>')
        z.writestr("style.css", 'p{background:url("Text/a*b.xhtml")}')
        z.writestr("toc.ncx", '<navMap><navPoint><content src="Text/a:b.xhtml#target"/></navPoint></navMap>')
    with EpubBookAdapter.open(archive) as book:
        paths = [book.id_to_bookpath(key) for key in ["a", "b", "c"]]
        assert len(set(paths)) == 3
        assert all(not re.search(r'[<>:"\\|?*]', path) for path in paths)
        for path, text in zip(paths, ["第一章", "第二章", "第三章"]):
            data = (book.root_dir / path).read_text(encoding="utf-8")
            assert text in data
            assert Path(paths[1]).name + "#target" in data
        assert paths[0] in (book.root_dir / "style.css").read_text(encoding="utf-8")
        assert paths[1] + "#target" in (book.root_dir / "toc.ncx").read_text(encoding="utf-8")


def test_archive_path_traversal_is_rejected_before_extraction(tmp_path):
    from epub3itizer.compat import EpubBookAdapter
    archive = tmp_path / "unsafe.epub"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../escape.xhtml", "not safe")
    with pytest.raises(ValueError, match="不安全路徑"):
        EpubBookAdapter.open(archive)


@pytest.mark.parametrize("titles,expected", [
    ("<title>製作說明</title><title/>", "製作說明"),
    ("<title/><title>原有標題</title>", "原有標題"),
    ("<title/><title> </title>", "chapter.xhtml"),
])
def test_duplicate_xhtml_titles_keep_nonempty_title_and_body(titles, expected):
    root = etree.fromstring(f'<html xmlns="http://www.w3.org/1999/xhtml"><head>{titles}</head><body><p>正文保留</p></body></html>')
    output, _, _, _ = collect_doc_features(root, "Text/chapter.xhtml")
    document = etree.fromstring(output.encode("utf-8"))
    kept = document.xpath('//*[local-name()="head"]/*[local-name()="title"]')
    assert len(kept) == 1 and kept[0].text == expected
    assert document.xpath('string(//*[local-name()="body"])') == "正文保留"
    again, _, _, _ = collect_doc_features(document, "Text/chapter.xhtml")
    assert etree.tostring(etree.fromstring(again.encode("utf-8")), method="c14n") == etree.tostring(etree.fromstring(output.encode("utf-8")), method="c14n")


@pytest.mark.parametrize("declared", ["second", "", "first,second"])
def test_duplicate_cover_flags_require_unambiguous_metadata(tmp_path, declared):
    from PIL import Image
    (tmp_path / "chapter.xhtml").write_text('<html xmlns="http://www.w3.org/1999/xhtml"><body><p>Text</p></body></html>', encoding="utf-8")
    for name, color in (("first", "red"), ("second", "blue")):
        Image.new("RGB", (2, 2), color).save(tmp_path / (name + ".jpg"))
    image_before = (tmp_path / "first.jpg").read_bytes()
    second_before = (tmp_path / "second.jpg").read_bytes()
    cover_meta = "".join(f'<meta name="cover" content="{name}"/>' for name in declared.split(",") if name)
    opf = tmp_path / "content.opf"
    opf.write_text(f'''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>en</dc:language><dc:identifier id="uid">urn:uuid:1</dc:identifier>{cover_meta}</metadata>
<manifest><item id="first" href="first.jpg" media-type="image/jpeg" properties="cover-image svg"/><item id="second" href="second.jpg" media-type="image/jpeg" properties="cover-image"/><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="chapter"/></spine></package>''', encoding="utf-8")
    cleanup_opf_manifest(tmp_path, "content.opf")
    root = etree.parse(str(opf))
    covers = root.xpath('//*[local-name()="item" and contains(@properties,"cover-image")]/@id')
    assert covers == (["second"] if declared == "second" else ["first", "second"])
    assert "svg" in root.xpath('//*[local-name()="item" and @id="first"]')[0].get("properties", "")
    assert (tmp_path / "first.jpg").read_bytes() == image_before
    assert (tmp_path / "second.jpg").read_bytes() == second_before
    first_pass = opf.read_bytes()
    cleanup_opf_manifest(tmp_path, "content.opf")
    assert opf.read_bytes() == first_pass


@pytest.mark.parametrize("declared", ["", "first,second"])
def test_duplicate_cover_flags_with_identical_images_preserve_resources(tmp_path, declared):
    from PIL import Image
    (tmp_path / "Images").mkdir()
    Image.new("RGB", (2, 2), "red").save(tmp_path / "Images/first.jpg")
    image = (tmp_path / "Images/first.jpg").read_bytes()
    (tmp_path / "Images/second.jpg").write_bytes(image)
    chapter = '<html xmlns="http://www.w3.org/1999/xhtml"><body><p>正文不變</p><img src="Images/second.jpg"/></body></html>'
    (tmp_path / "chapter.xhtml").write_text(chapter, encoding="utf-8")
    cover_meta = "".join(f'<meta name="cover" content="{name}"/>' for name in declared.split(",") if name)
    opf = tmp_path / "content.opf"
    opf.write_text(f'''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>zh-Hant</dc:language><dc:identifier id="uid">urn:uuid:1</dc:identifier>{cover_meta}</metadata>
<manifest><item id="first" href="Images/first.jpg" media-type="image/jpeg" properties="cover-image svg"/><item id="second" href="Images/second.jpg" media-type="image/jpeg" properties="cover-image"/><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="chapter"/></spine></package>''', encoding="utf-8")
    cleanup_opf_manifest(tmp_path, "content.opf")
    root = etree.parse(str(opf))
    assert root.xpath('//*[local-name()="item" and contains(@properties,"cover-image")]/@id') == ["first"]
    assert "svg" in root.xpath('//*[local-name()="item" and @id="first"]')[0].get("properties", "")
    assert root.xpath('//*[local-name()="item"]/@href')[:2] == ["Images/first.jpg", "Images/second.jpg"]
    assert (tmp_path / "Images/first.jpg").read_bytes() == (tmp_path / "Images/second.jpg").read_bytes() == image
    assert (tmp_path / "chapter.xhtml").read_text(encoding="utf-8") == chapter
    first_pass = opf.read_bytes()
    cleanup_opf_manifest(tmp_path, "content.opf")
    assert opf.read_bytes() == first_pass


def test_stylesheet_link_with_path_in_type_is_normalized_to_css_mime_type():
    root = parse_xml_recovering(
        '''<html xmlns="http://www.w3.org/1999/xhtml"><head>
        <link rel="stylesheet" href="../Styles/book.css" type="../Text/css"/>
        </head><body><p>text</p></body></html>'''
    )

    normalize_epubcheck_xhtml(root)

    link = root.xpath(".//*[local-name()='link']")[0]
    assert link.get("type") == "text/css"


def test_xhtml_image_element_is_renamed_to_img():
    root = parse_xml_recovering(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body><image src="cover.jpg"/></body></html>'
    )

    normalize_epubcheck_xhtml(root)

    assert root.xpath(".//*[local-name()='img']")
    assert not root.xpath(".//*[local-name()='image']")


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


def test_opf_comment_without_space_does_not_capture_manifest_or_spine():
    opf2 = """<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>zh-Hant</dc:language><dc:identifier id="uid">123</dc:identifier><!--accessibility options--></metadata>
<manifest><item id="chap" href="chap.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="chap"/></spine></package>"""

    root = etree.fromstring(Opf_Converter(opf2, {}, {}, {}, ["chap"]).get_opf3().encode("utf-8"))

    assert len(root.xpath("./*[local-name()='metadata']/*[local-name()='manifest' or local-name()='spine']")) == 0
    assert len(root.xpath("./*[local-name()='manifest']")) == 1
    assert len(root.xpath("./*[local-name()='spine']/*[local-name()='itemref']")) == 2


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


def test_chinese_fields_keep_traditional_body_and_japanese_quote():
    source = '<html><head><title>夜莺别墅</title></head><body><p>皇后于此說話，「卑しい人间、万死に値する。」</p><p>这本书。</p></body></html>'
    output = convert_chinese_document(source, 's2tw')
    assert '<title>夜鶯別墅</title>' in output
    assert '皇后于此說話，「卑しい人间、万死に値する。」' in output
    assert '這本書。' in output


def test_chinese_fields_respect_explicit_literal_glyphs_and_nested_tails():
    source='<div><span translate="no" title="龙"><i>几内亚</i>与龙</span>这本书<img alt="汉字" src="汉字.png"/></div>'
    output=convert_chinese_document(source,'s2tw')
    assert 'title="龙"' in output and '<i>几内亚</i>与龙' in output
    assert '這本書' in output and 'alt="漢字"' in output and 'src="汉字.png"' in output


def test_chinese_fields_convert_publisher_and_short_footnotes_only(tmp_path):
    from epub3itizer.chinese import convert_chinese_in_package
    page=tmp_path/'mixed.xhtml'
    page.write_text('<html><body><p>帶回伙伴，祕密。</p><p>机の上。</p><p>机械工业出版社</p><p>北京日报出版社</p><p>普奇报告。</p><p>《斯图加特报》</p><img alt="《新自由报》" src="报.png"/><a href="日报.xhtml">正體連結</a></body></html>',encoding='utf-8')
    convert_chinese_in_package(tmp_path,'s2tw')
    value=page.read_text(encoding='utf-8')
    assert all(x in value for x in ('帶回伙伴，祕密。','机の上。','機械工業出版社','北京日報出版社','普奇報告。','斯圖加特報','日报.xhtml','alt="《新自由報》"','src="报.png"'))
    convert_chinese_in_package(tmp_path,'s2tw')
    assert page.read_text(encoding='utf-8')==value


def test_chinese_fields_convert_short_title_author_without_changing_paths():
    text='<html><head><title>催妆</title></head><body><p>赏饭罚饿</p><p>帶回伙伴，祕密。机の上。</p><img alt="催妆" src="催妆.png"/></body></html>'
    output=convert_chinese_document(text,'s2tw')
    assert '<title>催妝</title>' in output and '<p>賞飯罰餓</p>' in output
    assert '帶回伙伴，祕密。机の上。' in output
    assert 'alt="催妝"' in output and 'src="催妆.png"' in output
    names=convert_chinese_document('<div><p>萧枕</p><p>孙相</p><p>圆满</p><a href="萧.xhtml">蕭枕</a></div>','s2tw')
    assert '<p>蕭枕</p><p>孫相</p><p>圓滿</p>' in names and 'href="萧.xhtml"' in names
    assert convert_chinese_document(output,'s2tw')==output


def test_chinese_fields_keep_japanese_bibliographic_brackets():
    quote = '〈台湾史の誕生－－『台湾人四百年史』の書誌学的考察〉、（餃子の王将）、《台湾の文学》'
    output = convert_chinese_document('<p>' + quote + '。这本书。</p>', 's2tw')
    assert quote in output
    assert '這本書。' in output


def test_chinese_short_nodes_cover_body_navigation_names_and_attributes():
    source = '<div><h2>军代表吴峥嵘</h2><p>项桓</p><p>顾虑</p><p>怎么</p><a href="军.xhtml">张陈归宿</a><img alt="视线" src="陈.png"/><p>病灶，雇用，佳肴，皇后，干涉。帶回伙伴，祕密。</p></div>'
    output = convert_chinese_document(source, 's2tw')
    assert all(text in output for text in ('軍代表吳崢嶸', '<p>項桓</p>', '<p>顧慮</p>', '<p>怎麼</p>', '張陳歸宿', 'alt="視線"', 'href="军.xhtml"', 'src="陈.png"', '病灶，雇用，佳肴，皇后，干涉。帶回伙伴，祕密。'))
    assert convert_chinese_document(output, 's2tw') == output
    assert '軍代表吳崢嶸' in convert_chinese_document('<ncx><navLabel><text>军代表吴峥嵘</text></navLabel></ncx>', 's2tw')


def test_required_chinese_conversion_does_not_hide_converter_failure(monkeypatch):
    import pytest
    from epub3itizer import chinese
    monkeypatch.setattr(chinese, '_converter', False)
    with pytest.raises(RuntimeError, match='無法載入'):
        chinese.convert_chinese_document('<p>军</p>', 's2tw')
    class BrokenConverter:
        def convert(self, text):
            raise RuntimeError('轉換例外')
    monkeypatch.setattr(chinese, '_converter', BrokenConverter())
    with pytest.raises(RuntimeError, match='轉換例外'):
        chinese.convert_chinese_document('<p>军</p>', 's2tw')


def test_without_chinese_conversion_does_not_load_optional_dictionary(monkeypatch,tmp_path):
    import pytest
    from epub3itizer import chinese
    monkeypatch.setattr(chinese,'simplified_pattern',lambda *a:pytest.fail('未要求簡轉正，不應讀取可選字典'))
    monkeypatch.setattr(chinese,'_converter',False)
    assert chinese.convert_chinese_document('<p>军</p>',None)=='<p>军</p>'
    chinese.convert_chinese_in_package(tmp_path,None)


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


def test_epubw_full_ad_removed_without_touching_quoted_narrative():
    root = etree.fromstring('''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>測試</title></head><body>
<div><p>正文保留。</p><p>本书由“<a href="https://epubw.com">ePUBw.COM</a>”整理，ePUBw.COM 提供最新最全的优质电子书下载！！！</p>後接正文。</div>
<p>本書由「ePUBw.COM」整理，ePUBw.COM 提供最新最全的優質電子書下載！！！</p>
<p>他讀到本書由 ePUBw.COM 整理的字樣。</p>
</body></html>'''.encode())
    output, _, _, _ = collect_doc_features(root, "chapter.xhtml")
    assert "提供最新最全" not in output
    assert "正文保留。" in output and "後接正文。" in output
    assert "他讀到本書由 ePUBw.COM 整理的字樣。" in output


def test_exact_download_disclaimers_and_payment_pitches_preserve_body():
    root = etree.fromstring('''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>前言</title></head><body>
<p>本電子書內容收集於網絡，本書僅供個人學習排版之用，請於下載二十四小時內刪除，不得用作任何商業用途。如有喜歡，請支持正版。</p>
<p>如果你不知道讀什麼書或者想獲得更多免費電子書請加小編QQ：2338856113，http://www.ireadweek.com，如果打不開，可以qq聯繫我</p>
<p>説明：文中需掃碼閲讀的請掃此付費二維碼。</p>
<p>掃碼下載「湛廬閱讀」App，搜索「鞋狗」，獲取更多本書信息。</p>
<p>譯者：毛大慶。</p><p>課程練習請掃碼閱讀出版社補充教材。</p>
<p>他說：如果你不知道讀什麼書，請到圖書館。</p><p>本書討論免費電子書、QQ及付費二維碼。</p>
</body></html>'''.encode())
    output, _, _, _ = collect_doc_features(root, "preface.xhtml")
    assert "二十四小時" not in output and "2338856113" not in output
    assert "説明" not in output and "獲取更多本書信息" not in output
    assert "譯者：毛大慶" in output and "出版社補充教材" in output
    assert "請到圖書館" in output and "本書討論免費電子書" in output


def test_forum_disclaimers_preserve_translator_and_afterword():
    root = etree.fromstring('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>後記</title></head><body><p>譯者：梁恩嘉</p><p>輕之國度：http://www.lightnovel.cn</p><p>下載後請在24小時內刪除，LK不負擔任何責任</p><p>轉載請保留信息</p><p>我是作者，這是正文與後記。</p><p>他在論壇看到 lightnovel.cn 的討論，並說：禁止轉載SF小說頻道。</p></body></html>'.encode())
    output, _, _, _ = collect_doc_features(root, "afterword.xhtml")
    assert "24小時" not in output and "轉載請" not in output
    assert "譯者：梁恩嘉" in output and "這是正文與後記" in output and "他在論壇看到" in output


def test_lightnovel_new_domains_and_joined_disclaimers_keep_afterword():
    from epub3itizer.conversion import remove_known_source_ad_paragraphs
    root = etree.fromstring('''<html xmlns="http://www.w3.org/1999/xhtml"><body>
<p>作者：三田誠</p><p>譯者：周庭旭</p><p>輕之國度：https://www.lightnovel.fun</p>
<p>輕書架：https://www.lightnovel.app</p><p>輕書架：https://www.lightnovel.life</p>
<p>下載後請在24小時內刪除，天使動漫與輕書架不負擔任何責任</p>
<p>下載後請在24小時内删除，LK不負擔任何責任 <br/>請體諒圖源、錄入、校對的辛勤勞動 <br/>不可修改文本檔，轉載請務必保留資訊</p>
<p>下載後請在24小時内删除，輕之國度不負擔任何責任 <br/>請尊重掃圖、錄入、修圖、校對的辛勤勞動，轉載請保留信息 <br/>本文特别嚴禁轉載至SF輕小說頻道和輕小說文庫</p>
<p>僅供個人學習交流使用，禁作商業用途 <br/>下載後請在24小時内删除，輕之國度不負擔任何責任</p>
<p>本文特别嚴禁轉載至SF輕小說頻道和輕小說文庫 <br/>所錄入的每一本書裡，掃圖者有很大一部分功勞！</p>
<p>作者後記：謝謝讀者。他曾在 lightnovel.app 看見討論。</p>
<p>下載後請在24小時內刪除，LK不負擔任何責任。這是正文引用。</p>
</body></html>'''.encode())
    remove_known_source_ad_paragraphs(root)
    once=etree.tostring(root)
    text=''.join(root.itertext())
    assert '三田誠' in text and '周庭旭' in text and '作者後記' in text
    assert '正文引用' in text and '看見討論' in text
    assert '輕書架：https' not in text and '辛勤勞動' not in text and '商業用途' not in text
    assert 'SF輕小說' not in text and '天使動漫' not in text
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root)==once


def test_tsdm_yidm_and_xuanshu_precise_ads_keep_body_and_credits():
    root = etree.fromstring('''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>後記</title></head><body>
<p>作者：あし</p><p>譯者：某Y</p><p>天使動漫：www.tsdm39.net</p>
<p>下載後請在24小時內刪除，LK與TSDM不負擔任何責任</p>
<p>1、如果你喜歡該輕小說，請支援作者正版;</p>
<p>本小說由迷糊輕小說(www.yidm.com)提供閱讀和下載;</p>
<p>更多精彩，更多好書，盡在選書網—http://Www.xuanshu.Com</p>
<p>Txt,Epub,Mobi  www.qinkan.net</p>
<p>正文與後記保留。他說「更多精彩」，又談到 tsdm39.net 的事情。</p>
</body></html>'''.encode())
    output, _, _, _ = collect_doc_features(root, "afterword.xhtml")
    assert "譯者：某Y" in output and "作者：あし" in output
    assert "正文與後記保留" in output and "又談到 tsdm39.net" in output
    assert "24小時" not in output and "提供閱讀和下載" not in output
    assert "xuanshu.Com" not in output and "qinkan.net" not in output


def test_677txt_exact_source_pitch_is_removed_but_mentions_are_preserved():
    for pitch, following in [("推荐一个小说下载必备网址：www.677txt.com", "每天更新，喜欢的去看看。"), ("推薦一個小說下載必備網址：www.677txt.com", "每天更新，喜歡的去看看。")]:
        root = etree.fromstring(f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>前言</title></head><body><p>{pitch}</p><p>{following}</p><p>本書作者：鹿燈燈</p><p>正文提及 www.677txt.com，保留引用。</p><p>每天更新，喜歡的去看看。</p></body></html>'.encode())
        output, _, _, _ = collect_doc_features(root, "preface.xhtml")
        assert "必備網址" not in output and "必备网址" not in output
        assert "本書作者：鹿燈燈" in output and "正文提及 www.677txt.com" in output
        assert output.count("每天更新") == 1


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


def test_cleanup_opf_manifest_removes_zero_byte_xhtml_and_nav_link(tmp_path):
    oebps = tmp_path / "OEBPS"
    text = oebps / "Text"
    text.mkdir(parents=True)
    (text / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    empty = text / "empty.xhtml"
    empty.write_bytes(b"")
    (oebps / "nav.xhtml").write_text(
        '''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="Text/chapter.xhtml">Chapter</a></li><li><a href="Text/empty.xhtml">Empty</a></li></ol></nav></body></html>''',
        encoding="utf-8",
    )
    opf = oebps / "content.opf"
    opf.write_text(
        '''<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/><item id="empty" href="Text/empty.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="chapter"/><itemref idref="empty"/></spine></package>''',
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")
    cleanup_nav_leaf_spans(tmp_path, "OEBPS/content.opf")

    output = opf.read_text(encoding="utf-8")
    assert 'id="empty"' not in output
    assert 'idref="empty"' not in output
    assert not empty.exists()
    assert "empty.xhtml" not in (oebps / "nav.xhtml").read_text(encoding="utf-8")


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
<div div="" i="" class="calibre2">same-name attr</div>
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
    assert 'div=""' not in output
    assert 'i=""' not in output
    assert '<div class="calibre2">same-name attr</div>' in output
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


def test_duplicate_charset_meta_is_deduped():
    root = etree.fromstring(
        b"""<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8"/>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<title>Title</title>
</head>
<body><p>body</p></body>
</html>"""
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")
    out_root = etree.fromstring(output.encode("utf-8"))
    charset_metas = out_root.xpath("//*[local-name()='head']/*[local-name()='meta' and @charset]")

    assert len(charset_metas) == 1
    assert "http-equiv" not in output


def test_filename_sanitizer_skips_unreadable_legacy_ncx(tmp_path):
    (tmp_path / "META-INF").mkdir()
    (tmp_path / "META-INF" / "container.xml").write_text("container", encoding="utf-8")
    (tmp_path / "toc bad.ncx").write_bytes(b":\xe4Il\x1c)Z\xb6]\xa6\xa2\x90")
    page = tmp_path / "chapter one.xhtml"
    page.write_text('<a href="chapter one.xhtml">chapter</a>', encoding="utf-8")

    sanitize_package_filenames(tmp_path)

    assert (tmp_path / "toc_bad.ncx").exists()
    assert (tmp_path / "chapter_one.xhtml").exists()


def test_case_mismatch_repair_skips_unreadable_legacy_ncx(tmp_path):
    (tmp_path / "toc.ncx").write_bytes(b":\xe4Il\x1c)Z\xb6]\xa6\xa2\x90")
    (tmp_path / "Images").mkdir()
    (tmp_path / "Images" / "Cover.jpg").write_bytes(b"image")
    page = tmp_path / "chapter.xhtml"
    page.write_text('<img src="images/cover.jpg" alt="cover"/>', encoding="utf-8")

    fix_case_mismatched_local_hrefs(tmp_path)

    assert 'src="Images/Cover.jpg"' in page.read_text(encoding="utf-8")


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


def test_xhtml_normalization_removes_deprecated_doc_roles_but_keeps_epub_type():
    root = etree.fromstring(
        b'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Title</title></head><body>
<div epub:type="footnotes" role="doc-endnotes"><div epub:type="footnote" role="doc-endnote">Note <a role="doc-backlink" href="#ref">back</a></div></div>
<aside role="note doc-endnote">Retain the non-document role.</aside>
</body></html>'''
    )

    output, _, _, _ = collect_doc_features(root, "Text/notes.xhtml")

    assert 'epub:type="footnotes"' in output
    assert 'epub:type="footnote"' in output
    assert "doc-endnote" not in output
    assert "doc-endnotes" not in output
    assert "doc-backlink" not in output
    assert 'role="note"' in output


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


def test_stylesheet_link_src_is_moved_to_href():
    root = etree.fromstring(
        b'''<html xmlns="http://www.w3.org/1999/xhtml"><head>
        <title>Title</title><link rel="stylesheet" type="text/css" src="../styles/book.css"/>
        </head><body><p>Text</p></body></html>'''
    )

    output, _, _, _ = collect_doc_features(root, "Text/chapter01.xhtml")

    assert 'href="../styles/book.css"' in output
    assert '<link src=' not in output


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
    assert filtered[0].href == "OEBPS/Text/chapter.xhtml#p1"


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


def test_transparent_links_preserve_blocks_and_respect_surrounding_context():
    root = etree.fromstring(b'''<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Title</title></head><body>
<div><a href="chapter.xhtml"><p id="heading">Title</p><p class="summary">Summary</p><hr/></a></div>
<div><ins><del><p id="change">Change</p></del></ins></div>
<p id="outer"><a href="chapter.xhtml"><p id="inner">Nested</p></a></p>
<span><a href="chapter.xhtml"><div id="inline">Inline</div></a></span>
</body></html>''')
    output, _, _, _ = collect_doc_features(root, "Text/toc.xhtml")
    parsed = etree.fromstring(output.encode())
    ns = {"h": "http://www.w3.org/1999/xhtml"}
    assert parsed.xpath('count(//h:div/h:a/h:p)', namespaces=ns) == 3
    assert parsed.xpath('//h:a/h:hr', namespaces=ns)
    assert parsed.xpath('//h:ins/h:del/h:p[@id="change"]', namespaces=ns)
    assert parsed.xpath('//h:div[@id="outer"]/h:a/h:p[@id="inner"]', namespaces=ns)
    assert parsed.xpath('//h:span/h:a/h:span[@id="inline"]', namespaces=ns)
    assert parsed.xpath('//h:p[@class="summary"]/text()', namespaces=ns) == ["Summary"]


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


def test_missing_aria_references_preserve_valid_labels_and_body(tmp_path):
    page = tmp_path / "chapter.xhtml"
    page.write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>章</title></head>'
        '<body><h2 id="heading">章名</h2><p id="description">說明</p>'
        '<section aria-labelledby="heading missing" aria-describedby="missing description">正文</section>'
        '<div aria-labelledby="other-page" aria-describedby="missing" aria-label="原標籤">保留</div>'
        '<aside aria-labelledby="heading" aria-describedby="description">附註</aside></body></html>',
        encoding="utf-8",
    )
    (tmp_path / "other.xhtml").write_text('<html><body id="other-page"/></html>', encoding="utf-8")
    original_text = ''.join(etree.fromstring(page.read_bytes()).itertext())

    repair_missing_xhtml_references(tmp_path)

    root = etree.fromstring(page.read_bytes())
    section = root.find('.//{http://www.w3.org/1999/xhtml}section')
    assert section.get('aria-labelledby') == 'heading'
    assert section.get('aria-describedby') == 'description'
    div = root.find('.//{http://www.w3.org/1999/xhtml}div')
    assert div.attrib == {'aria-label': '原標籤'}
    aside = root.find('.//{http://www.w3.org/1999/xhtml}aside')
    assert aside.attrib == {'aria-labelledby': 'heading', 'aria-describedby': 'description'}
    assert ''.join(root.itertext()) == original_text
    once = page.read_bytes()
    repair_missing_xhtml_references(tmp_path)
    assert page.read_bytes() == once


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


def test_missing_svg_anchor_reference_uses_actual_xhtml_file(tmp_path):
    (tmp_path / "item" / "xhtml").mkdir(parents=True)
    page = tmp_path / "item" / "xhtml" / "p-004.xhtml"
    page.write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml"><body>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<a xlink:href="xhtml/p-005.xhtml"><rect/></a>
</svg></body></html>""",
        encoding="utf-8",
    )
    (tmp_path / "item" / "xhtml" / "p-005.xhtml").write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body/></html>', encoding="utf-8"
    )

    repair_missing_xhtml_references(tmp_path)

    assert 'href="p-005.xhtml"' in page.read_text(encoding="utf-8")


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


def test_embedded_css_resources_use_document_relative_paths_and_preserve_body(tmp_path):
    (tmp_path / "OEBPS" / "Images").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Images" / "existing.png").write_bytes(b"image")
    page = tmp_path / "OEBPS" / "chapter.xhtml"
    page.write_text('''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>A</title>
<style>.list {list-style-image:url(../Images/missing.png)}
.ok {background:url(../Images/existing.png)}
.remote {background:url(https://example.org/image.png)}</style></head>
<body><p id="keep" style="background:url(Images/missing.png);color:black">正文 &amp; 引用 url(Images/missing.png)</p>
<img src="Images/existing.png"/></body></html>''', encoding="utf-8")
    repair_missing_css_references(tmp_path)
    output = page.read_text(encoding="utf-8")
    assert "list-style-image:none" in output
    assert "background:url(Images/existing.png)" in output
    assert "https://example.org/image.png" in output
    assert 'style="background:none;color:black"' in output
    assert 'id="keep"' in output and "正文 &amp; 引用 url(Images/missing.png)" in output
    assert 'src="Images/existing.png"' in output
    repair_missing_css_references(tmp_path)
    assert page.read_text(encoding="utf-8") == output


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


def test_mislabeled_jpeg_is_renamed_and_referenced(tmp_path):
    (tmp_path / "OEBPS" / "Images").mkdir(parents=True)
    image = tmp_path / "OEBPS" / "Images" / "002.png"
    image.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 32)
    page = tmp_path / "OEBPS" / "chapter.xhtml"
    page.write_text('<img src="Images/002.png" alt=""/>', encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text('<item href="Images/002.png" media-type="image/png"/>', encoding="utf-8")

    normalize_raster_image_extensions(tmp_path)

    assert not image.exists()
    assert (tmp_path / "OEBPS" / "Images" / "002.jpg").exists()
    assert 'Images/002.jpg' in page.read_text(encoding="utf-8")
    assert 'Images/002.jpg' in opf.read_text(encoding="utf-8")


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


def test_cleanup_opf_removes_only_empty_author_link_cache(tmp_path):
    opf = tmp_path / "content.opf"
    opf.write_text('''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" prefix="calibre: https://calibre-ebook.com">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>書名</dc:title><dc:creator>樊文禮</dc:creator><dc:identifier id="uid">urn:uuid:test</dc:identifier><dc:language>zh-Hant</dc:language>
<meta property="calibre:author_link_map">{"樊文礼":""}</meta>
<meta name="calibre:author_link_map" content="{}"/>
<meta property="calibre:author_link_map">{"作者":"https://example.com/author"}</meta>
<meta property="calibre:author_link_map">not-json</meta>
</metadata><manifest/><spine/></package>''',encoding="utf-8")
    cleanup_opf_manifest(tmp_path, "content.opf")
    result = opf.read_text(encoding="utf-8")
    assert "樊文礼" not in result
    assert "樊文禮" in result
    assert "https://example.com/author" in result and "not-json" in result
    cleanup_opf_manifest(tmp_path, "content.opf")
    assert opf.read_text(encoding="utf-8") == result


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


def test_binary_pdf_misnamed_as_css_is_not_decoded(tmp_path):
    (tmp_path / "OEBPS").mkdir()
    fake_pdf = tmp_path / "OEBPS" / "residue.css"
    original = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    fake_pdf.write_bytes(original)
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        '''<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>測試</dc:title><dc:language>zh-Hant</dc:language></metadata>
<manifest><item id="residue" href="residue.css" media-type="text/css"/></manifest><spine/>
</package>''',
        encoding="utf-8",
    )

    add_missing_manifest_items(tmp_path, "OEBPS/content.opf")
    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")
    sanitize_all_css_files(tmp_path)

    assert fake_pdf.read_bytes() == original
    assert 'media-type="application/pdf"' in opf.read_text(encoding="utf-8")


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


def test_fixed_layout_svg_cover_gets_viewport_from_viewbox(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "cover.xhtml").write_text(
        """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Cover</title><meta charset="utf-8"/></head>
<body><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 874 1240" width="100%" height="100%">
<image width="874" height="1240" href="../Images/cover.jpg"/>
</svg></body>
</html>""",
        encoding="utf-8",
    )
    (tmp_path / "OEBPS" / "content.opf").write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata><meta property="rendition:layout">reflowable</meta></metadata>
<manifest><item id="cover" href="Text/cover.xhtml" media-type="application/xhtml+xml" properties="svg"/></manifest>
<spine><itemref idref="cover" properties="rendition:layout-pre-paginated rendition:spread-none"/></spine>
</package>""",
        encoding="utf-8",
    )

    add_fixed_layout_viewports(tmp_path, "OEBPS/content.opf")

    output = (tmp_path / "OEBPS" / "Text" / "cover.xhtml").read_text(encoding="utf-8")
    assert 'name="viewport"' in output
    assert 'content="width=874, height=1240"' in output


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


@pytest.mark.parametrize('props', ['layout-blank', 'page-spread-right layout-blank rendition:layout-pre-paginated custom:blank'])
def test_cleanup_opf_removes_only_private_blank_marker_preserving_page(tmp_path, props):
    page = tmp_path / 'page.xhtml'
    page.write_text('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>空頁</title></head><body><p>保留頁面</p></body></html>', encoding='utf-8')
    original = page.read_bytes()
    opf = tmp_path / 'content.opf'
    opf.write_text(f'''<package xmlns="http://www.idpf.org/2007/opf" version="3.0" prefix="custom: https://example.com/">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Sample</dc:title><dc:language>zh-Hant</dc:language></metadata>
<manifest><item id="page" href="page.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="page" properties="{props}"/></spine></package>''', encoding='utf-8')
    cleanup_opf_manifest(tmp_path, 'content.opf')
    root = etree.parse(str(opf))
    ref = root.xpath('//*[local-name()="itemref"]')[0]
    assert ref.get('idref') == 'page'
    assert ref.get('properties', '').split() == [p for p in props.split() if p != 'layout-blank']
    assert page.read_bytes() == original
    once = opf.read_bytes()
    cleanup_opf_manifest(tmp_path, 'content.opf')
    assert opf.read_bytes() == once


def test_cleanup_opf_removes_manifest_dimensions_not_image_content(tmp_path):
    image = pytest.importorskip('PIL.Image')
    image.new('RGB', (30, 40)).save(tmp_path / 'page.png')
    original_image = (tmp_path / 'page.png').read_bytes()
    page = tmp_path / 'page.xhtml'
    page.write_text('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>頁面</title></head><body><img src="page.png" width="30" height="40"/></body></html>', encoding='utf-8')
    original_page = page.read_bytes()
    opf = tmp_path / 'content.opf'
    opf.write_text('''<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata/>
<manifest><item id="page" href="page.xhtml" media-type="application/xhtml+xml"/>
<item id="image" href="page.png" media-type="image/png" width="30" height="40"/></manifest>
<spine><itemref idref="page"/></spine></package>''', encoding='utf-8')
    cleanup_opf_manifest(tmp_path, 'content.opf')
    node = etree.parse(str(opf)).xpath('//*[local-name()="item" and @id="image"]')[0]
    assert dict(node.attrib) == {'id':'image', 'href':'page.png', 'media-type':'image/png'}
    assert page.read_bytes() == original_page and (tmp_path / 'page.png').read_bytes() == original_image
    once = opf.read_bytes()
    cleanup_opf_manifest(tmp_path, 'content.opf')
    assert opf.read_bytes() == once


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


@pytest.mark.parametrize("formal_nav", [False, True])
@pytest.mark.parametrize("empty_spine", [False, True])
def test_cleanup_opf_only_removes_formal_nav_itemref(tmp_path, formal_nav, empty_spine):
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

    if formal_nav:
        opf.write_text(opf.read_text(encoding="utf-8").replace('id="toc" href=', 'id="toc" properties="nav" href='), encoding="utf-8")
    if empty_spine:
        opf.write_text(opf.read_text(encoding="utf-8").replace('<spine><itemref idref="chapter"/><itemref idref="toc" linear="no"/></spine>', '<spine/>'), encoding="utf-8")
    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'idref="chapter"' in data
    assert ('idref="toc"' in data) is not formal_nav


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


def test_cleanup_opf_normalizes_package_xml_lang(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="z">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Sample</dc:title>
<dc:language>zh-Hant</dc:language>
<dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>
</metadata>
<manifest><item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="chapter"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'xml:lang="zh-Hant"' in data
    assert 'xml:lang="z"' not in data


def test_cleanup_opf_removes_missing_manifest_fallback_id(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Images").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    (tmp_path / "OEBPS" / "Images" / "chapter.png").write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
        b"\x00\x01\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Sample</dc:title>
<dc:language>zh-Hant</dc:language>
<dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>
</metadata>
<manifest>
<item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/>
<item id="chapter-image" href="Images/chapter.png" media-type="image/png" fallback="chapter-image-placeholder"/>
</manifest>
<spine><itemref idref="chapter"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert 'id="chapter-image"' in data
    assert "chapter-image-placeholder" not in data
    assert "fallback=" not in data


def test_private_xhtml_attributes_are_removed():
    root = parse_xml_recovering(
        '''<html xmlns="http://www.w3.org/1999/xhtml"><body>
        <img src="cover.jpg" alt="cover" active="true" kmoetag="1" kimageraw="true" kmoe-marker="x" class="keep" />
        </body></html>'''
    )

    normalize_epubcheck_xhtml(root)

    data = etree.tostring(root, encoding="unicode")
    assert "active" not in data
    assert "kmoetag" not in data
    assert "kimageraw" not in data
    assert "kmoe-marker" not in data
    assert 'class="keep"' in data
    assert 'src="cover.jpg"' in data


def test_orphan_escaped_tag_fragments_are_removed_from_xhtml_text():
    root = parse_xml_recovering(
        '''<html xmlns="http://www.w3.org/1999/xhtml"
        xmlns:epub="http://www.idpf.org/2007/ops"><body>
        <div id="D1" class="calibre2">id="_idParaDest-3" class="ff_serif" aid="D2"&gt;<span>第四章</span></div>
        <div id="D2" class="calibre2">aDest-13" class="ff_serif" aid="D3"&gt;<span>第十三章</span></div>
        <p>d="footnote-133" class="_idFootnote" role="doc-footnote" epub:type="footnote" aid="167"&gt;</p>
        <p>ote-707" class="_idFootnote" role="doc-footnote" epub:type="footnote" aid="51B"&gt;</p>
        <p>[577note-605" class="_idFootnote" role="doc-footnote" epub:type="footnote" aid="4I7"&gt;</p>
        <p id="_idParaDest-19" aid="7J2">誌謝</p>
        <p>一加一 &gt; 一。</p>
        </body></html>'''
    )

    normalize_epubcheck_xhtml(root)
    from epub3itizer.conversion import remove_orphan_escaped_tag_fragments

    remove_orphan_escaped_tag_fragments(root)

    data = etree.tostring(root, encoding="unicode")
    assert 'id="_idParaDest-3" class=' not in data
    assert "_idFootnote" not in data
    assert "aid=" not in data
    assert 'id="_idParaDest-19"' in data
    assert "<span>第四章</span>" in data
    assert "<span>第十三章</span>" in data
    assert "[577</p>" in data
    assert ">誌謝</p>" in data
    assert "一加一 &gt; 一" in data


def test_orphan_cleanup_preserves_complete_escaped_markup_and_code_examples():
    from epub3itizer.conversion import remove_orphan_escaped_tag_fragments
    root = parse_xml_recovering('''<html xmlns="http://www.w3.org/1999/xhtml"><body>
      <p>那&lt;a id="_idTextAnchor000"&gt;&lt;/a&gt;兒。<span/>完整&lt;div aid="123"&gt;範例&lt;/div&gt;。</p>
      <pre>id="example"&gt;<code>d="snippet"&gt;</code> id="tail"&gt;</pre>
      <p><code>id="code"&gt;</code> id="orphan"&gt;正文保留。</p>
      <p id="actual">一加一 &gt; 一。</p>
    </body></html>''')
    texts = root.xpath('//*[local-name()="p"]/text()')
    output, *_ = collect_doc_features(root, 'chapter.xhtml')
    repaired = parse_xml_recovering(output)
    assert repaired.xpath('//*[local-name()="p"]/text()')[0] == texts[0]
    assert '完整<div aid="123">範例</div>。' in ''.join(repaired.itertext())
    assert repaired.xpath('string(//*[local-name()="pre"])') == 'id="example">d="snippet"> id="tail">'
    assert repaired.xpath('string(//*[local-name()="p"][*[local-name()="code"]])') == 'id="code"> 正文保留。'
    assert repaired.xpath('//*[local-name()="p"]/@id') == ['actual']
    once = etree.tostring(repaired)
    remove_orphan_escaped_tag_fragments(repaired)
    assert etree.tostring(repaired) == once


def test_cleanup_opf_removes_empty_dc_metadata_and_invalid_raster_images(tmp_path):
    (tmp_path / "OEBPS" / "Images").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Images" / "empty.jpg").write_bytes(b"")
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Sample</dc:title>
<dc:language>zh-Hant</dc:language>
<dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>
<dc:source></dc:source>
<dc:relation/>
<dc:coverage>  </dc:coverage>
<dc:rights/>
</metadata>
<manifest>
  <item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/>
  <item id="bad-image" href="Images/empty.jpg" media-type="image/jpeg"/>
</manifest>
<spine><itemref idref="chapter"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert "<dc:source" not in data
    assert "<dc:relation" not in data
    assert "<dc:coverage" not in data
    assert "<dc:rights" not in data
    assert "empty.jpg" not in data
    assert not (tmp_path / "OEBPS" / "Images" / "empty.jpg").exists()


def test_cleanup_opf_removes_kmoe_spine_private_attrs(tmp_path):
    (tmp_path / "OEBPS" / "Text").mkdir(parents=True)
    (tmp_path / "OEBPS" / "Text" / "chapter.xhtml").write_text("<html/>", encoding="utf-8")
    opf = tmp_path / "OEBPS" / "content.opf"
    opf.write_text(
        """<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Sample</dc:title>
<dc:language>zh-Hant</dc:language>
<dc:identifier id="uid">urn:uuid:12345678-1234-1234-1234-123456789abc</dc:identifier>
</metadata>
<manifest><item id="chapter" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine kmoe-pagedirect="rtl"><itemref idref="chapter" kmoe-pagedirect="rtl"/></spine>
</package>""",
        encoding="utf-8",
    )

    cleanup_opf_manifest(tmp_path, "OEBPS/content.opf")

    data = opf.read_text(encoding="utf-8")
    assert "kmoe-pagedirect" not in data
    assert "<spine>" in data
    assert 'idref="chapter"' in data


@pytest.mark.parametrize("body,cover,remove_page,remove_image", [
    ('<img src="arbitrary.png"/>', False, True, True),
    ('正文<img src="arbitrary.png"/>', False, False, False),
    ('<img src="arbitrary.png"/><img src="other.png"/>', False, False, False),
    ('<img src="arbitrary.png"/>', True, False, False),
    ('<p style="background:url(arbitrary.png)">正文</p>', False, False, False),
])
def test_known_image_promotions_preserve_content_and_cover(tmp_path, monkeypatch, body, cover, remove_page, remove_image):
    import hashlib
    from epub3itizer import conversion as conv
    from PIL import Image
    image = tmp_path / 'arbitrary.png'
    Image.new('RGB', (2, 2), 'white').save(image)
    Image.new('RGB', (2, 2), 'black').save(tmp_path / 'other.png')
    monkeypatch.setattr(conv, 'KNOWN_PROMOTIONAL_IMAGE_SHA256', {hashlib.sha256(image.read_bytes()).hexdigest()})
    (tmp_path / 'ad.xhtml').write_text(f'<html xmlns="{conv.XHTML_NS}"><head><title>頁面</title></head><body>{body}</body></html>', encoding='utf-8')
    (tmp_path / 'chapter.xhtml').write_text(f'<html xmlns="{conv.XHTML_NS}"><head><title>正文</title></head><body><p>正文內容</p></body></html>', encoding='utf-8')
    (tmp_path / 'nav.xhtml').write_text(f'<html xmlns="{conv.XHTML_NS}" xmlns:epub="{conv.EPUB_NS}"><head><title>目錄</title></head><body><nav epub:type="toc"><ol><li><a href="ad.xhtml">宣傳</a></li><li><a href="chapter.xhtml">正文</a></li></ol></nav></body></html>', encoding='utf-8')
    cover_property = ' properties="cover-image"' if cover else ''
    opf = tmp_path / 'content.opf'
    opf.write_text(f'<package xmlns="{conv.OPF_NS}" version="3.0"><metadata xmlns:dc="{conv.DC_NS}"><dc:title>測試</dc:title><dc:language>zh-Hant</dc:language></metadata><manifest><item id="ad" href="ad.xhtml" media-type="application/xhtml+xml"/><item id="image" href="arbitrary.png" media-type="image/png"{cover_property}/><item id="other" href="other.png" media-type="image/png"/><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="ad"/><itemref idref="chapter"/></spine></package>', encoding='utf-8')
    cleanup_opf_manifest(tmp_path, 'content.opf')
    cleanup_nav_leaf_spans(tmp_path, 'content.opf')
    assert (tmp_path / 'ad.xhtml').exists() != remove_page
    assert image.exists() != remove_image
    assert (tmp_path / 'other.png').exists()
    assert ('idref="ad"' in opf.read_text(encoding='utf-8')) != remove_page
    if remove_page:
        assert 'href="ad.xhtml"' not in (tmp_path / 'nav.xhtml').read_text(encoding='utf-8')
    snapshot = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    cleanup_opf_manifest(tmp_path, 'content.opf')
    cleanup_nav_leaf_spans(tmp_path, 'content.opf')
    assert snapshot == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_unknown_same_name_promotional_image_is_preserved(tmp_path):
    from epub3itizer.conversion import remove_known_image_only_promotions, OPF_NS
    image = tmp_path / 'theendinfo.png'
    image.write_bytes(b'not an approved promotional image')
    manifest = etree.Element(f'{{{OPF_NS}}}manifest')
    assert not remove_known_image_only_promotions(tmp_path, '.', manifest, set())
    assert image.exists()


def test_image_promotion_cleanup_preserves_manifest_comments(tmp_path):
    from epub3itizer.conversion import remove_known_image_only_promotions, OPF_NS
    manifest = etree.fromstring(f'<manifest xmlns="{OPF_NS}"><!--出版者註解--><item id="chapter" href="chapter.xhtml"/></manifest>')
    original = etree.tostring(manifest)
    assert not remove_known_image_only_promotions(tmp_path, '.', manifest, set())
    assert etree.tostring(manifest) == original


@pytest.mark.parametrize('ad', [
    '★☆★☆★☆輕小說文庫(Www.WenKu8.CN)☆★☆★☆★',
    '叉叉電子書（WWW.xxdzs2.com)免費TXT小說下載',
    '叉叉電子書(www.xxdzs2.com）txt電子書下載',
    '本電子書由叉叉電子書（www.xxdzs2.com）網友上傳分享，網址:http://www.xxdzs2.com',
    '叉叉電子書(www.xxdzs2.com)免費txt小說電子書下載網站，並支持支持在線閱讀！我們提供的均為全本，叉叉電子書（www.xxdzs2.com)提供最簡單直接的閱讀、下載方式,是讀者的寶藏',
    '宣告:本書由奇書網(www.qinkan.net)自網路收集整理製作,僅供交流學習使用,版權歸原作者和出版社所有,如果喜歡,請支援正版.',
])
def test_exact_xxdzs_qinkan_pitches_keep_quotes_and_story(ad):
    from epub3itizer.conversion import remove_known_source_ad_paragraphs, XHTML_NS
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>{ad}</p><p>正文內容</p><p>故事引用「{ad}」，不是獨立宣傳。</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert len(root.xpath("//*[local-name()='p']")) == 2
    assert '正文內容' in ''.join(root.itertext())
    assert '故事引用' in ''.join(root.itertext())
    snapshot=etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root)==snapshot


def test_qinkan_exact_inline_markers_restore_split_story_words():
    from epub3itizer.conversion import remove_known_inline_source_ads, XHTML_NS
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>戰☆奇書網のWww.qinkan.net★甲，一[WWW.qinkan.net奇`書`網]級，千**Www.qinkan.net**年。</p><p>作者後記提及 qinkan.net；普通星號 **重點**。</p></body></html>')
    remove_known_inline_source_ads(root)
    assert '戰甲，一級，千年。' in ''.join(root.itertext())
    assert 'qinkan.net' in ''.join(root.itertext())
    assert '**重點**' in ''.join(root.itertext())


@pytest.mark.parametrize('marker', ['（更d书f享搜索雅 书.YabooK）', '（更d書f享搜索雅書.YabooK）', '（此书更多分享搜索@雅书B）', '（此書更多分享搜索@雅書B）'])
def test_exact_yabook_pitch_preserves_caption_and_quotation(marker):
    from epub3itizer.conversion import remove_known_inline_source_ads, XHTML_NS
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>正文{marker}續文。</p><p>引用「{marker}」保留。</p><p>作者談 YabooK。</p></body></html>')
    remove_known_inline_source_ads(root)
    paragraphs = root.xpath("//*[local-name()='p']")
    assert ''.join(paragraphs[0].itertext()) == '正文續文。'
    assert marker in ''.join(paragraphs[1].itertext())
    assert ''.join(paragraphs[2].itertext()) == '作者談 YabooK。'
    snapshot = etree.tostring(root)
    remove_known_inline_source_ads(root)
    assert etree.tostring(root) == snapshot


def test_exact_freebook_caption_pitch_across_adjacent_paragraphs():
    from epub3itizer.conversion import remove_known_inline_source_ads, XHTML_NS
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p><span>圖說1916年。（Free书分</span></p><p><span>享更多搜雅书）</span></p><p>正文（Free書分享更多搜雅書）。</p><p>引用「（Free书分享更多搜雅书）」。</p><p>（Free书分</p><p>普通正文</p><p>享更多搜雅书）</p><!--保留註解--></body></html>')
    remove_known_inline_source_ads(root)
    paragraphs = root.xpath("//*[local-name()='p']")
    assert ''.join(paragraphs[0].itertext()) == '圖說1916年。'
    assert ''.join(paragraphs[1].itertext()) == ''
    assert ''.join(paragraphs[2].itertext()) == '正文。'
    assert 'Free书分享更多搜雅书' in ''.join(paragraphs[3].itertext())
    assert 'Free书分' in ''.join(paragraphs[4].itertext())
    assert ''.join(paragraphs[5].itertext()) == '普通正文'
    snapshot = etree.tostring(root)
    remove_known_inline_source_ads(root)
    assert etree.tostring(root) == snapshot


@pytest.mark.parametrize('marker', [
    '[最新電子書免費分享社群，群主V信 1107308023 新增備註電子書]',
    '[最新电子书免费分享社群，群主V信1107308023新增备注电子书]',
])
def test_exact_wechat_promotion_preserves_story_credits_and_quotes(marker):
    from epub3itizer.conversion import remove_known_inline_source_ads, XHTML_NS
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>第一段正文{marker}<b>續文</b>{marker}。</p><p>譯者：王小明。</p><p>引用「{marker}」應保留。</p><p>[最新電子書免費分享社群，群主V信999新增備註電子書]</p></body></html>')
    remove_known_inline_source_ads(root)
    paragraphs = root.xpath("//*[local-name()='p']")
    assert ''.join(paragraphs[0].itertext()) == '第一段正文續文。'
    assert '譯者：王小明' in ''.join(paragraphs[1].itertext())
    assert marker in ''.join(paragraphs[2].itertext())
    assert 'V信999' in ''.join(paragraphs[3].itertext())
    snapshot = etree.tostring(root)
    remove_known_inline_source_ads(root)
    assert etree.tostring(root) == snapshot


@pytest.mark.parametrize('simplified', [False, True])
def test_exact_manwu_pitch_preserves_credits_and_story(simplified):
    from epub3itizer.conversion import remove_known_source_ad_paragraphs, XHTML_NS
    ad = '本書由「滿屋書香」整理，如果你不知道讀什麼書或者想獲得更多免費電子書請加小編微信：sisijuan2012或QQ：151680600 小編也可以結交一些喜歡讀書的朋友。或者關注小編個人微信公眾號名稱：滿屋書香。 為了方便書友朋友找書和看書，小編自己還在簡書也開闢了一方樂土 ，簡書的網址：https://www.jianshu.com/u/0aea96a9af60'
    if simplified:
        ad = ad.translate(str.maketrans('書滿讀麼獲費電請編結歡關個眾號稱為還簡開闢樂網', '书满读么获费电请编结欢关个众号称为还简开辟乐网'))
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>署名</p><div><span>{ad}</span></div>後接正文<p>他引用「{ad}」</p><p>{ad.replace("151680600", "999")}</p><p>滿屋子都是煙。</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert not root.xpath("//*[local-name()='div']")
    assert len(root.xpath("//*[local-name()='p']")) == 4
    assert '後接正文' in ''.join(root.itertext())
    assert '滿屋子都是煙。' in ''.join(root.itertext())
    snapshot = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == snapshot


@pytest.mark.parametrize('extra,unknown,anchor,shared', [('',False,False,False),('正文',False,False,False),('',True,False,False),('',False,True,False),('',False,False,True)])
def test_promotional_suffix_preserves_notes_and_unmatched_blocks(tmp_path, monkeypatch, extra, unknown, anchor, shared):
    import hashlib
    from epub3itizer import conversion as conv
    image = tmp_path / 'qr.png'
    image.write_bytes(b'known ad image')
    text = '如果你不知道讀什麼書，完整已核准導流'
    monkeypatch.setattr(conv, 'KNOWN_PROMOTIONAL_SUFFIX_TEXT_SHA256', {hashlib.sha256(text.encode()).hexdigest()})
    monkeypatch.setattr(conv, 'KNOWN_PROMOTIONAL_IMAGE_SHA256', set() if unknown else {hashlib.sha256(image.read_bytes()).hexdigest()})
    id_attr = ' id="keep"' if anchor else ''
    page = tmp_path / 'notes.xhtml'
    page.write_text(f'<html xmlns="{conv.XHTML_NS}"><body><p><a id="note" href="chapter.xhtml#note">註解正文</a></p><p>如果你不知道讀什麼書，</p><p{id_attr}>完整已核准導流<img src="qr.png"/></p>{extra}</body></html>', encoding='utf-8')
    if shared:
        (tmp_path / 'chapter.xhtml').write_text(f'<html xmlns="{conv.XHTML_NS}"><body><p>正文</p><img src="qr.png"/></body></html>', encoding='utf-8')
    manifest = etree.fromstring(f'<manifest xmlns="{conv.OPF_NS}"><item id="notes" href="notes.xhtml"/><item id="qr" href="qr.png"/></manifest>')
    removed = not (extra or unknown or anchor)
    assert conv.remove_known_image_only_promotions(tmp_path, '', manifest, set()) == removed
    result = page.read_text(encoding='utf-8')
    assert '註解正文' in result and 'id="note"' in result
    assert ('完整已核准導流' not in result) == removed
    assert image.exists() == (not removed or shared)
    snapshot = page.read_bytes()
    assert not conv.remove_known_image_only_promotions(tmp_path, '', manifest, set())
    assert page.read_bytes() == snapshot


def test_exact_readweek_pitch_preserves_credits_and_story():
    from epub3itizer.conversion import remove_known_source_ad_paragraphs, XHTML_NS
    ad = '本書由「行行」整理，如果你不知道讀什麼書或者想獲得更多免費電子書請加小編微信或QQ：2338856113 小編也和結交一些喜歡讀書的朋友 或者關注小編個人微信公眾號名稱：幸福的味道 id：d716-716 為了方便書友朋友找書和看書，小編自己做了一個電子書下載網站，網站的名稱為：周讀 網址：http://www.ireadweek.com'
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>（美）布萊克著</p><p>姜文波譯</p><p>{ad}</p>後接正文<p>他引用「{ad}」</p><p>{ad.replace("2338856113","999")}</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert len(root.xpath("//*[local-name()='p']")) == 4
    assert '布萊克著' in ''.join(root.itertext()) and '姜文波譯' in ''.join(root.itertext())
    assert '後接正文' in ''.join(root.itertext()) and '他引用' in ''.join(root.itertext())
    snapshot = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == snapshot


@pytest.mark.parametrize('extra,shared,cover,remove_page,remove_image', [
    ('',False,False,True,True),
    ('',True,False,True,False),
    ('',False,True,False,False),
    ('<p>後記正文。</p>',False,False,False,False),
    ('<p>姜文波譯</p>',False,False,False,False),
    ('<img src="other.png"/>',False,False,False,False),
])
def test_readweek_full_page_requires_text_and_image_fingerprints(tmp_path,monkeypatch,extra,shared,cover,remove_page,remove_image):
    import hashlib
    from PIL import Image
    from epub3itizer import conversion as conv
    text = '如果你不知道讀什麼書，就關注這個微信號。微信公眾號名稱：幸福的味道加小編微信一起讀書小編微信號：2338856113【幸福的味道】已提供200個不同類型的書單1、歷屆茅盾文學獎獲獎作品2、每年豆瓣，噹噹，亞馬遜年度圖書銷售排行榜3、25歲前一定要讀的25本書4、有生之年，你一定要看的25部外國純文學名著5、有生之年，你一定要看的20部中國現當代名著6、美國亞馬遜編輯推薦的一生必讀書單100本7、30個領域30本不容錯過的入門書8、這20本書，是各領域的巔峰之作9、這7本書，教你如何高效讀書10、80萬書蟲力薦的「給五星都不夠」的30本書關注「幸福的味道」微信公眾號，即可查看對應書單和得到電子書也可以在我的網站（周讀）www.ireadweek.com自行下載'
    assert hashlib.sha256(text.encode()).hexdigest() in conv.KNOWN_PROMOTIONAL_DOCUMENT_TEXT_SHA256
    image=tmp_path/'qr.jpeg';Image.new('RGB',(2,2),'white').save(image)
    Image.new('RGB',(2,2),'black').save(tmp_path/'other.png')
    monkeypatch.setattr(conv,'KNOWN_PROMOTIONAL_IMAGE_SHA256',{hashlib.sha256(image.read_bytes()).hexdigest()})
    (tmp_path/'ad.xhtml').write_text(f'<html xmlns="{conv.XHTML_NS}"><head><title>宣傳</title></head><body><p>{text}</p><img src="qr.jpeg"/>{extra}</body></html>',encoding='utf-8')
    shared_image='<img src="qr.jpeg"/>' if shared else ''
    (tmp_path/'chapter.xhtml').write_text(f'<html xmlns="{conv.XHTML_NS}"><head><title>正文</title></head><body><p>原有正文</p>{shared_image}</body></html>',encoding='utf-8')
    (tmp_path/'nav.xhtml').write_text(f'<html xmlns="{conv.XHTML_NS}" xmlns:epub="{conv.EPUB_NS}"><head><title>目錄</title></head><body><nav epub:type="toc"><ol><li><a href="ad.xhtml">宣傳</a></li><li><a href="chapter.xhtml">正文</a></li></ol></nav></body></html>',encoding='utf-8')
    prop=' properties="cover-image"' if cover else ''
    opf=tmp_path/'content.opf'
    opf.write_text(f'<package xmlns="{conv.OPF_NS}" version="3.0"><metadata xmlns:dc="{conv.DC_NS}"><dc:title>測試</dc:title><dc:language>zh-Hant</dc:language></metadata><manifest><item id="ad" href="ad.xhtml" media-type="application/xhtml+xml"/><item id="image" href="qr.jpeg" media-type="image/jpeg"{prop}/><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="other" href="other.png" media-type="image/png"/></manifest><spine><itemref idref="ad"/><itemref idref="chapter"/></spine></package>',encoding='utf-8')
    conv.cleanup_opf_manifest(tmp_path,'content.opf');conv.cleanup_nav_leaf_spans(tmp_path,'content.opf')
    assert (tmp_path/'ad.xhtml').exists()!=remove_page
    assert image.exists()!=remove_image
    assert (tmp_path/'other.png').exists()
    assert ('idref="ad"' in opf.read_text(encoding='utf-8'))!=remove_page
    if remove_page:assert 'href="ad.xhtml"' not in (tmp_path/'nav.xhtml').read_text(encoding='utf-8')
    snapshot={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    conv.cleanup_opf_manifest(tmp_path,'content.opf');conv.cleanup_nav_leaf_spans(tmp_path,'content.opf')
    assert snapshot=={p.name:p.read_bytes() for p in tmp_path.iterdir()}
