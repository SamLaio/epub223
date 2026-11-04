from lxml import etree
from epub3itizer.conversion import remove_known_source_ad_paragraphs, XHTML_NS


def test_source_pitches_keep_story_tail_and_are_idempotent():
    marker = r'【鳳\/凰\/ 更新快 無彈窗 請搜尋f/h/xiao/shuo/c/o/m】'
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>前文{marker}後文</p><p>天才一秒記住本站地址：.。手機版閱讀網址：m.</p>尾文<p>故事新八一中文網首發</p><p>廣告之後，馬上回來</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert ''.join(root.itertext()) == '前文後文尾文故事廣告之後，馬上回來'
    before = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == before


def test_exact_pitches_keep_quotes_anchors_unknown_variants_and_code():
    pitch = '佰度搜尋 噺八壹中文網 м. 無廣告詞'
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>{pitch}</p><p>「{pitch}」</p><p id="keep">{pitch}</p><p>{pitch}正文</p><blockquote><p>{pitch}</p></blockquote><pre><p>{pitch}</p></pre><p>宋書航說這是廣告。</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert ''.join(root.itertext()).count(pitch) == 5
    assert root.xpath('//*[@id="keep"]')


def test_inline_site_variants_preserve_sentences_and_story_mentions():
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>天才3秒記住本站網址【筆迷閣 .】為什麼會出現？</p><p>他很謹慎。 .更新最快</p><p>只有宋書航。品書網</p><p>書客居閱讀網址：</p><p>故事中的品書網不能猜刪。</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert ''.join(root.itertext()) == '為什麼會出現？他很謹慎。只有宋書航。故事中的品書網不能猜刪。'


def test_mobile_label_requires_complete_source_footer():
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>手機閱讀</p><p>正文</p><p>本書來自 品書網 https:百度搜尋品.書,網更新最快的站！</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert ''.join(root.itertext()) == '正文'
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>手機閱讀</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert ''.join(root.itertext()) == '手機閱讀'


def test_exact_truncated_mobile_pitches_preserve_story_and_quotes():
    pitches = ['。樂文手機版更新最快網址：13', '手機版更新最快網址：7']
    body = ''.join(f'<p>{p}</p>尾文<p>「{p}」</p><p id="keep{i}">{p}</p>' for i,p in enumerate(pitches))
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body>正文{body}<p>手機版更新最快網址：8</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    text = ''.join(root.itertext())
    assert text.startswith('正文尾文') and text.count('尾文') == 2
    assert all(text.count(p) == 2 for p in pitches)
    assert '手機版更新最快網址：8' in text
    before = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == before
