from lxml import etree

from epub3itizer.conversion import XHTML_NS, remove_known_source_ad_paragraphs


def test_exact_ireadweek_pitch_preserves_paragraph_with_story_text():
    pitch = (
        "本書由「行行」整理，如果你不知道讀什麼書或者想獲得更多免費電子書請加小編微信或QQ：491256034 "
        "小編也和結交一些喜歡讀書的朋友 或者關注小編個人微信公眾號id：d716-716 "
        "為了方便書友朋友找書和看書，小編自己做了一個電子書下載網站，網址：www.ireadweek.com QQ群：550338315"
    )
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>{pitch}</p><p>故事引述：{pitch}</p></body></html>'.encode())
    remove_known_source_ad_paragraphs(root)
    assert root.xpath('//*[local-name()="p"]/text()') == ["故事引述：" + pitch]
