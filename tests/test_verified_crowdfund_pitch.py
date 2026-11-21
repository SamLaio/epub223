from lxml import etree
from epub3itizer.conversion import remove_known_source_ad_paragraphs


def test_verified_group_pitch_preserves_credits_quotes_and_story():
    pitch = '本翻譯為眾籌付費翻譯。請喜歡的朋友入群支持翻譯持續進行。'
    root = etree.fromstring(f'<html xmlns="http://www.w3.org/1999/xhtml"><body><p>漢化組：眾籌吃土教導院</p><p>譯者：烏衣巷</p><p><span>QQ群630368941</span></p><p>僅供個人學習交流使用，禁作商業用途。<br/></p><p>下載後請在24小時內刪除，翻譯組不負擔任何責任。</p><p>{pitch}</p>尾文<blockquote><p>{pitch}</p></blockquote><p id="keep">{pitch}</p><p>正文提到{pitch}</p></body></html>'.encode())
    remove_known_source_ad_paragraphs(root)
    text = ''.join(root.itertext())
    assert 'QQ群630368941' not in text
    assert '24小時' not in text and '禁作商業用途' not in text
    assert all(t in text for t in ('漢化組：眾籌吃土教導院','譯者：烏衣巷','尾文','正文提到'))
    assert text.count(pitch) == 3
    once = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == once


def test_abridgement_notice_keeps_warning_but_removes_group_pitch():
    notice='因為10卷下內容較為特殊所以到時候網絡發布版均為刪減版。'
    root=etree.fromstring(('<html xmlns="http://www.w3.org/1999/xhtml"><body><p>漢化組：眾籌吃土教導院</p><p>QQ群630368941</p><p>'+notice+'完全版盡在群內有限放出請大家知曉謝謝</p></body></html>').encode())
    remove_known_source_ad_paragraphs(root)
    text=''.join(root.itertext())
    assert notice in text and '完全版盡在群內' not in text


def test_group_pitch_without_full_context_is_preserved():
    root = etree.fromstring('<html><body><p>QQ群630368941</p><p>本漢化為真愛眾籌翻譯。請大家珍惜。</p></body></html>')
    before = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == before
