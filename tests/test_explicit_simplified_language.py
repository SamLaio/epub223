from lxml import etree as E
from epub3itizer.chinese import convert_chinese_document


def test_explicit_simplified_source_converts_ambiguous_short_nodes_and_parent_tails():
    source = '<html lang="zh-Hans"><body><p>此后更甚。</p><p>一帘之隔。</p><p>沈云娥知道。万一……她先前哪里懂。</p><p lang="zh-Hant">帶回祕密</p>此后<p lang="ja">国会の机</p>此后<p translate="no">此后</p><a href="云.xhtml" title="一帘">云</a></body></html>'
    output = convert_chinese_document(source, 's2tw')
    root = E.fromstring(output)
    assert root.get('lang') == 'zh-Hant'
    assert root.xpath('//p/text()') == ['此後更甚。', '一簾之隔。', '沈雲娥知道。萬一……她先前哪裡懂。', '帶回祕密', '国会の机', '此后']
    assert root.xpath('//p[@lang]/following-sibling::text()')[:2] == ['此後', '此後']
    assert root.find('.//a').attrib == {'href':'云.xhtml', 'title':'一簾'}
    assert convert_chinese_document(output, 's2tw') == output


def test_unspecified_source_keeps_ambiguous_traditional_text():
    source = '<p>皇后帶回祕密</p>'
    assert '皇后帶回祕密' in convert_chinese_document(source, 's2tw')
    protected = '<html lang="zh-Hans"><body><script lang="zh-Hans">此后</script><p translate="no" lang="zh-Hans">此后</p></body></html>'
    root = E.fromstring(convert_chinese_document(protected, 's2tw'))
    assert root.find('.//script').get('lang') == 'zh-Hans'
    assert root.find('.//script').text == '此后'
    assert root.find('.//p').get('lang') == 'zh-Hans'
