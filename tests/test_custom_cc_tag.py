from lxml import etree
from epub3itizer.conversion import normalize_epubcheck_xhtml, preserve_custom_cc_css, XHTML_NS


def test_custom_cc_preserves_text_anchor_class_style_and_foreign_tag():
    doc=etree.fromstring(f'<html xmlns="{XHTML_NS}" xmlns:x="urn:foreign"><head><title>卷頁</title></head><body><h1><cc id="volume" class="old" style="color:red">卷名<b>後日談</b></cc>尾文</h1><x:cc>外部</x:cc></body></html>')
    before=''.join(doc.itertext());normalize_epubcheck_xhtml(doc)
    node=doc.xpath('//*[@id="volume"]')[0]
    assert node.tag==f'{{{XHTML_NS}}}span' and node.get('class')=='old epub223-cc'
    assert 'color' in node.get('style') and ''.join(doc.itertext())==before
    assert doc.find('.//{urn:foreign}cc') is not None
    once=etree.tostring(doc);normalize_epubcheck_xhtml(doc);assert etree.tostring(doc)==once


def test_cc_css_type_selector_only_and_nested_rules():
    css='cc, h1>CC.old:not(cc){color:#cc0000;content:"cc"} .cc,#cc,[cc="cc"],x|cc,cc|x,:lang(cc){color:red}@media screen{cc{font-size:150%}}'
    result=preserve_custom_cc_css(css)
    assert 'span.epub223-cc, h1>span.epub223-cc.old:not(span.epub223-cc)' in result
    assert '.cc,#cc,[cc="cc"],x|cc,cc|x,:lang(cc)' in result
    assert 'color:#cc0000;content:"cc"' in result and '@media screen{span.epub223-cc{font-size:150%}}' in result
    assert preserve_custom_cc_css(result)==result
