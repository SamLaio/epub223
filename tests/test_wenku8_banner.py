from lxml import etree
from epub3itizer.conversion import XHTML_NS, remove_known_source_ad_paragraphs


def test_exact_wenku8_domains_keep_translation_and_story():
    for domain in ('cn', 'com'):
        root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>★☆輕小說文庫(Www.WenKu8.{domain})☆★</p><p>翻譯：cleverchm</p><p>正文提到 Wenku8.com，不是宣傳。</p></body></html>'.encode())
        remove_known_source_ad_paragraphs(root)
        assert list(root.itertext()) == ['翻譯：cleverchm', '正文提到 Wenku8.com，不是宣傳。']
