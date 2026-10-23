import pytest
from lxml import etree
from epub3itizer.conversion import remove_known_source_ad_paragraphs


@pytest.mark.parametrize('text',[
    '附：【本作品來自網際網路及出版圖書,本人不做任何負責】內容版權歸作者所有',
    '附：【本作品来自网络及出版图书,本人不做任何负责】内容版权归作者所有',
])
def test_exact_disclaimer_keeps_body_quotes_credits_anchors_and_tail(text):
    root=etree.fromstring(f'''<html xmlns="http://www.w3.org/1999/xhtml"><body>
<p>作者：眼鏡腿兒</p><p>{text}</p><p>「{text}」</p>
<p id="keep">{text}</p><p><a href="#keep">{text}</a></p>
<p>{text}</p>相鄰尾文<p>正文結尾與後記保留。</p></body></html>'''.encode())
    remove_known_source_ad_paragraphs(root)
    paragraphs=root.xpath('//*[local-name()="p"]')
    assert sum(''.join(p.itertext())==text for p in paragraphs)==3
    assert '作者：眼鏡腿兒' in ''.join(root.itertext()) and '正文結尾與後記保留' in ''.join(root.itertext())
    assert root.xpath('//*[@id="keep"]') and root.xpath('//*[@href="#keep"]')
    assert '相鄰尾文' in ''.join(root.itertext()) and f'「{text}」' in ''.join(root.itertext())
    once=etree.tostring(root);remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root)==once
