from lxml import etree
from epub3itizer.conversion import remove_known_source_ad_paragraphs, XHTML_NS


def test_exact_shoe_ad_preserves_story_quotes_credits_and_tail():
    root = etree.fromstring(f'''<html xmlns="{XHTML_NS}"><body>
<p>名牌球鞋NIKE,ADIDAS       通通1200 (臺幣)</p>保留尾文
<p>LV,GUCCI,Chanel,NIKE,ADIDAS,Timberland,ROLEX,OMEGA,Cartier,Armani,AF,APE ..</p>
<p id="story">她穿著NIKE球鞋，售價1200。</p>
<p>「名牌球鞋NIKE,ADIDAS通通1200(臺幣)」</p>
<p>錄入：風動</p></body></html>''')
    remove_known_source_ad_paragraphs(root)
    text = ''.join(root.itertext())
    assert 'LV,GUCCI' not in text
    assert text.count('名牌球鞋') == 1
    assert '保留尾文' in text and '她穿著NIKE球鞋，售價1200。' in text
    assert '錄入：風動' in text and root.xpath('//*[@id="story"]')
    prior = etree.tostring(root)
    remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root) == prior


def test_exact_fmx_navigation_preserves_quotes_and_credits():
    root = etree.fromstring(f'''<html xmlns="{XHTML_NS}"><body>
<p>黑潔明小說作品集|饕餮戀(上)|鳳鳴軒言情小說書庫</p>尾文
<p>位置： 首頁 作家列表 黑潔明 饕餮戀(上) 字體大小 默認字型 9pt 10pt 11pt 12pt 13pt 14pt 15pt 16pt 17pt 18pt 20pt 25pt 30pt 35pt 40pt 45pt 50pt 背景顏色 牋 牋 牋 牋</p>
<p>＊＊＊牋鳳鳴軒獨家制作牋＊＊＊牋bbs.fmx.cn牋＊＊＊</p>
<p id="keep">她說：「鳳鳴軒是小說網站。」</p>
<p>「黑潔明小說作品集|饕餮戀(上)|鳳鳴軒言情小說書庫」</p>
<p>製作網站：鳳鳴軒 掃描人員：coco 校對人員：絳月</p>
<p>位置：首頁作家列表黑潔明字體大小默認字型9pt背景顏色牋</p>
<p id="source-anchor">黑潔明小說作品集|饕餮戀(上)|鳳鳴軒言情小說書庫</p>
</body></html>''')
    remove_known_source_ad_paragraphs(root)
    text=''.join(root.itertext())
    assert 'bbs.fmx.cn' not in text and '尾文' in text
    assert '校對人員：絳月' in text and root.xpath('//*[@id="keep"]')
    assert text.count('黑潔明小說作品集')==2 and root.xpath('//*[@id="source-anchor"]')
    assert '9pt背景顏色牋' in text
    prior=etree.tostring(root);remove_known_source_ad_paragraphs(root)
    assert etree.tostring(root)==prior
