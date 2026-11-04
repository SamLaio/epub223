from lxml import etree
from epub3itizer.conversion import remove_known_inline_source_ads, XHTML_NS

PITCH = '{記住本站網址，，方便下次閱讀，或且百度輸入「52」，就能進入本站}8'


def test_exact_suffix_keeps_story_and_tail_and_is_idempotent():
    root=etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p class="a">他的身影已經不見。{PITCH}</p>尾文</body></html>')
    remove_known_inline_source_ads(root)
    assert ''.join(root.itertext())=='他的身影已經不見。尾文'
    before=etree.tostring(root)
    remove_known_inline_source_ads(root)
    assert etree.tostring(root)==before


def test_unknown_suffix_quotes_code_and_anchors_are_preserved():
    root=etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p id="keep">正文{PITCH}</p><p>「{PITCH}」</p><p>正文{PITCH[:-1]}</p><p>正文{PITCH}後文</p><blockquote><p>{PITCH}</p></blockquote><pre><p>{PITCH}</p></pre></body></html>')
    before=etree.tostring(root)
    remove_known_inline_source_ads(root)
    assert etree.tostring(root)==before
