from html import escape
import pytest
from lxml import etree
from epub3itizer.conversion import remove_known_source_ad_paragraphs, XHTML_NS

PITCH = '爱下电子书Txt版阅读,下载和分享更多电子书请访问，简体:https://ixdzs8.com,繁体:https://ixdzs8.tw,E-mail:support@ixdzs.com'

@pytest.mark.parametrize('text', [PITCH, '愛下電子書Txt版閱讀,下載和分享更多電子書請訪問，簡體:https://ixdzs8.com,繁體:https://ixdzs8.tw,E-mail:support@ixdzs.com', '<divclass="contentadv">'])
def test_exact_export_markers_preserve_neighbouring_text_and_are_idempotent(text):
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>前文</p><p class="content">{escape(text)}</p>尾文<p>後文</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert ''.join(root.itertext()) == '前文尾文後文'
    before = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == before

def test_only_known_pitch_can_remove_its_exact_export_separator():
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>{PITCH}</p>------章节内容开始-------<p>正文</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    assert ''.join(root.itertext()) == '正文'

@pytest.mark.parametrize('text', ['欢迎关注公众号“丹青拾字”', '歡迎關注公眾號「丹青拾字」'])
def test_exact_account_pitch_keeps_credits_mentions_and_other_accounts(text):
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>作者：甲</p><p>排版：丹青</p><p>{text}</p><p>「{text}」</p><p>{text.replace("丹青拾字", "其他帳號")}</p></body></html>')
    remove_known_source_ad_paragraphs(root)
    visible = ''.join(root.itertext())
    assert '作者：甲' in visible and '排版：丹青' in visible and visible.count(text) == 1 and '其他帳號' in visible

@pytest.mark.parametrize('fragment', [
    f'<p id="anchor">{PITCH}</p>', f'<p>「{PITCH}」</p>',
    f'<p>{PITCH}正文仍在這裡。</p>', f'<p>{PITCH.replace("ixdzs8.com", "example.com")}</p>',
    '<pre><p>&lt;divclass="contentadv"&gt;</p></pre>',
    '<p>&lt;divclass="contentadv"&gt;正文</p>',
    '<p><span>&lt;divclass="contentadv"&gt;</span></p>',
    f'<blockquote><p>{PITCH}</p></blockquote>',
])
def test_anchors_quotes_story_code_and_unknown_variants_are_preserved(fragment):
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body>{fragment}</body></html>')
    before = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == before
