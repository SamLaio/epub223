from lxml import etree
from epub3itizer.conversion import remove_known_source_ad_paragraphs, XHTML_NS


def test_browser_pitch_exact_only_keeps_story_anchors_quotes_and_tail():
    text='原版未篡改内容请移至 #官!网。如已在，请，关闭广告拦截功能并且退出浏览器阅读模式'
    root=etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>{text}</p>尾文<p id="keep">{text}</p><p>「{text}」</p><p>守衛軍不再攔截。</p><p>廣告攔截功能</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    visible=''.join(root.itertext())
    assert visible.count(text)==2 and '尾文' in visible and '守衛軍不再攔截。' in visible
    assert root.xpath('//*[@id="keep"]') and '廣告攔截功能' in visible
    before=etree.tostring(root);remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root)==before
