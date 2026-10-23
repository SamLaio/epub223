from lxml import etree

from epub3itizer.conversion import XHTML_NS, remove_known_source_ad_paragraphs


FOOTER = '請收藏本站：https://.bg60。筆趣閣手機版：https://m.bg60'


def test_bg60_exact_footer_removal_preserves_tail_and_is_idempotent():
    root = etree.fromstring(f'''<html xmlns="{XHTML_NS}"><body>
<p>前方正文。</p><p>{FOOTER}</p>保留尾文
<p>请收藏本站：https://.bg60。笔趣阁手机版：https://m.bg60</p>
<p>請收藏本站：<span>https://.bg60</span>。筆趣閣手機版：https://m.bg60</p>
<p>後方正文。</p></body></html>''')
    remove_known_source_ad_paragraphs(root)
    text = ''.join(root.itertext())
    assert 'bg60' not in text
    assert all(x in text for x in ('前方正文。', '保留尾文', '後方正文。'))
    previous = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == previous


def test_bg60_quotes_story_other_hosts_and_anchors_are_not_removed():
    root = etree.fromstring(f'''<html xmlns="{XHTML_NS}"><body>
<p>她在畫面上看見「{FOOTER}」，並未理會。</p>
<p>「{FOOTER}」</p>
<p>請收藏本站：https://example.com。筆趣閣手機版：https://m.example.com</p>
<p>請收藏本站：https://.bg60</p>
<p id="source-anchor"><span>{FOOTER}</span></p>
<p><a href="#source-anchor">{FOOTER}</a></p>
</body></html>''')
    previous = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == previous
