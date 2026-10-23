from lxml import etree
from epub3itizer.conversion import remove_known_source_ad_paragraphs


def test_exact_forum_reader_pitch_keeps_credits_quotes_anchors_and_tail():
    root = etree.fromstring('''<html xmlns="http://www.w3.org/1999/xhtml"><body>
<p>https://www.lightnovel.fun</p><p>作者：平坂読</p><p>翻譯：1cho</p>
<p>本文僅供個人學習交流使用，禁作商業用途</p>
<p>如需轉載請經過翻譯本人同意並保留所有信息</p><p>如需轉載請經過本人同意</p>
<p>推薦使用『多看閱讀』</p><p>「推薦使用『多看閱讀』」</p>
<p id="keep">推薦使用『多看閱讀』</p><p><a href="#keep">推薦使用『多看閱讀』</a></p>
<p>推薦使用『多看閱讀』</p>相鄰尾文
<p>作者後記：她推薦使用『多看閱讀』，但他不同意。</p>
</body></html>'''.encode())
    remove_known_source_ad_paragraphs(root)
    text=''.join(root.itertext())
    assert '本文僅供' not in text and '如需轉載' not in text
    assert '作者：平坂読' in text and '翻譯：1cho' in text
    assert len(root.xpath('//*[local-name()="p"][text()="推薦使用『多看閱讀』"]')) == 2
    assert '「推薦使用『多看閱讀』」' in text and '作者後記' in text and '相鄰尾文' in text
    assert root.xpath('//*[@id="keep"]') and root.xpath('//*[@href="#keep"]')
    once=etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root)==once


def test_reader_recommendation_without_forum_context_is_not_removed():
    root=etree.fromstring('<html xmlns="http://www.w3.org/1999/xhtml"><body><p>推薦使用『多看閱讀』</p></body></html>'.encode())
    before=etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root)==before
