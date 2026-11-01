from lxml import etree
import pytest
from epub3itizer.conversion import remove_known_source_ad_paragraphs


def document(header='台版 轉自 輕之國度', extra=''):
    return etree.fromstring(f'''<html xmlns="http://www.w3.org/1999/xhtml"><body><h2>後記</h2>
<p>────────────</p><p>{header}</p><p>作者：空埜一樹</p><p>插畫：ぽんじりつ</p><p>譯者：馮鈺婷</p>
<p>圖源：氮氣</p><p>錄入：zbszsr</p><p>修圖：ember1010</p><p>輕之國度：www.lightnovel.cn</p>
<p>僅供個人學習交流使用，禁作商業用途</p><p>下載後請在24小時內刪除，輕之國度不負擔任何責任</p>
<p>請尊重翻譯、掃圖、錄入、校對的辛勤勞動，轉載請保留信息</p>{extra}<p>────────────</p>
<p>作者後記：謝謝讀者與插畫老師。</p></body></html>'''.encode())


@pytest.mark.parametrize('header', ['台版 轉自 輕之國度', '輕之國度錄入組錄入', '輕之國度×天使動漫錄入組'])
def test_framed_credits_keep_official_credits_and_afterword(header):
    root = document(header)
    remove_known_source_ad_paragraphs(root)
    text = ''.join(root.itertext())
    assert all(value in text for value in ('作者：空埜一樹', '插畫：ぽんじりつ', '譯者：馮鈺婷', '作者後記：謝謝讀者與插畫老師。'))
    assert '輕之國度' not in text and '圖源' not in text and '────────' not in text
    once = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == once


@pytest.mark.parametrize('extra', ['<p>這是正文，不可刪除。</p>', '<p id="keep">圖源：其他人</p>'])
def test_unsafe_block_is_not_removed(extra):
    root = document(extra=extra)
    remove_known_source_ad_paragraphs(root)
    assert '台版 轉自 輕之國度' in ''.join(root.itertext())
    assert '圖源：氮氣' in ''.join(root.itertext())
    if 'id=' in extra:
        assert root.xpath('//*[@id="keep"]')
