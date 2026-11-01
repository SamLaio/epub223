from lxml import etree
from epub3itizer.conversion import XHTML_NS, remove_known_source_ad_paragraphs


def test_rabbit_terminal_credit_is_exact_and_idempotent():
    def doc(value):
        return etree.fromstring(f'<html xmlns="{XHTML_NS}"><body>{value}</body></html>')
    root=doc('<p>正文</p><p class="calibre2">END</p><p class="calibre2">兔子家族製作</p>')
    remove_known_source_ad_paragraphs(root)
    assert ''.join(root.itertext())=='正文END'
    before=etree.tostring(root);remove_known_source_ad_paragraphs(root);assert etree.tostring(root)==before
    for value in ['<p>兔子家族製作</p>', '<p>END</p><p id="x">兔子家族製作</p>', '<p>END</p><p>兔子家族製作</p><p>後記</p>', '<p>END</p><p>「兔子家族製作」</p>', '<p>END</p><p>封面製作：兔子家族</p>', '<p>END</p><p>兔子家族製作</p>正文尾文']:
        root=doc(value);before=etree.tostring(root);remove_known_source_ad_paragraphs(root);assert etree.tostring(root)==before
