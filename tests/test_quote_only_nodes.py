from lxml import etree as E
from epub3itizer.chinese import convert_chinese_document
from epub3itizer.cli import parse_args
import pytest


def test_quote_only_mode_preserves_simplified_words_and_language():
    source = '<html lang="zh-Hans"><body><p>他说：“？” 此后。</p><p>皇后帶回祕密。</p><p lang="ja">“国会”</p><code>"中文"</code></body></html>'
    output = convert_chinese_document(source, 'quotes')
    root = E.fromstring(output)
    assert root.get('lang') == 'zh-Hans'
    assert root.xpath('//p/text()') == ['他说：「？」 此后。','皇后帶回祕密。','“国会”']
    assert root.find('.//code').text == '"中文"'
    assert convert_chinese_document(output, 'quotes') == output
    assert parse_args(['a.epub','--normalize-quotes']).normalize_quotes
    with pytest.raises(SystemExit):
        parse_args(['a.epub','--normalize-quotes','--convert-chinese','s2tw'])


def test_quotes_do_not_require_simplified_characters():
    source = '<html lang="zh-Hant"><body><p>“？”</p><p>“……”</p><p>她說：“好。”</p><p>皇后帶回祕密。</p><p>&quot;你好&quot;</p><p>‘是’</p></body></html>'
    result = convert_chinese_document(source, 's2tw')
    doc = E.fromstring(result)
    assert doc.xpath('//p/text()') == ['「？」','「……」','她說：「好。」','皇后帶回祕密。','「你好」','『是』']
    assert convert_chinese_document(result, 's2tw') == result


def test_markup_paths_code_japanese_and_english_apostrophes_are_preserved():
    source = '''<html><body><p>“<em>好</em>。”</p><p>I'm fine.</p><a href='x.xhtml?key="中文"' id="source" title="“？”">“是”</a><code>"中文" “？”</code><pre>“……”</pre><script>"中文"</script><style>p{content:"中文"}</style><p translate="no">“？”</p><p lang="ja">“国会”</p>“？”</body></html>'''
    doc = E.fromstring(convert_chinese_document(source, 's2tw'))
    assert ''.join(doc.find('.//p').itertext()) == '「好。」'
    assert doc.findall('.//p')[1].text == "I'm fine."
    assert doc.find('.//a').attrib == {'href':'x.xhtml?key="中文"','id':'source','title':'「？」'}
    for tag, text in [('code','"中文" “？”'),('pre','“……”'),('script','"中文"'),('style','p{content:"中文"}')]:
        assert doc.find('.//'+tag).text == text
    assert doc.xpath('//p[@translate]/text()') == ['“？”']
    assert doc.xpath('//p[@lang]/text()') == ['“国会”']
    assert doc.xpath('//p[@lang]/following-sibling::text()') == ['「？」']
