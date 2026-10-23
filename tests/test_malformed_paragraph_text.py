from lxml import etree
from epub3itizer.conversion import parse_xml_recovering
from epub3itizer.chinese import convert_chinese_document

def test_orphan_and_unclosed_paragraphs_keep_all_text_and_anchors():
    raw = '''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>書</title></head><body><p>開頭</p>中間</p>尾段</p><p id="a">作者備註<p id="b">結尾</body></html>'''
    root = parse_xml_recovering(raw)
    assert ''.join(root.find('.//{*}body').itertext()) == '開頭中間尾段作者備註結尾'
    assert root.find('.//{*}p[@id="a"]').text == '作者備註'
    assert root.find('.//{*}p[@id="b"]').text == '結尾'
    converted = convert_chinese_document(raw, 's2tw')
    assert '作者備註' in converted and '結尾' in converted
    assert convert_chinese_document(converted, 's2tw') == converted

def test_valid_xhtml_with_quoted_tags_comments_svg_is_not_repaired():
    raw = '''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>書</title></head><body><!-- </p> --><p title="&lt;p&gt;">引文&lt;/p&gt;<em>尾</em></p><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text>圖</text></svg></body></html>'''
    assert etree.tostring(parse_xml_recovering(raw)) == etree.tostring(etree.fromstring(raw.encode()))
