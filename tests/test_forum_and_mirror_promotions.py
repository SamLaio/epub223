import hashlib
from lxml import etree as E
import pytest
from epub3itizer import conversion as c

CREDIT='製作人員臺版轉自天使動漫論壇輕書架×天使動漫錄入組圖源：Miku雪蘭錄入：十六夜小夜最後更新：2026-10-17'

def test_nonpromotional_document_preserves_body_comment(tmp_path):
 path=tmp_path/'chapter.xhtml';path.write_text(f'<html xmlns="{c.XHTML_NS}"><body><!-- 排版註解 --><p>正常正文。</p></body></html>',encoding='utf-8')
 manifest=E.fromstring(f'<manifest xmlns="{c.OPF_NS}"><item href="chapter.xhtml"/></manifest>')
 before=path.read_bytes();assert c.remove_known_image_only_promotions(tmp_path,'',manifest,set()) is False
 assert path.read_bytes()==before

@pytest.mark.parametrize('credit', [CREDIT, '製作人員我準備把同事埋在公司後面，有什麼想問的嗎？臺版轉自天使動漫論壇輕書架×天使動漫錄入組圖源：Miku雪蘭錄入：十六夜小夜最後更新：2026-10-29'] + [f'製作人員臺版轉自深夜讀書會發佈：深夜讀書會論壇：ritdon.com最後更新：{date}' for date in ('2026-07-24', '2026-08-24', '2026-08-20')])
@pytest.mark.parametrize('extra', ['', '<p>作者後記，這是正文。</p>', '<img src="unknown.jpg"/>', '<p id="note"/>'])
def test_credit_requires_entire_safe_document(tmp_path, extra, credit):
 path=tmp_path/'credits.xhtml';path.write_text(f'<html xmlns="{c.XHTML_NS}"><body><div><h1><b>{credit}</b></h1>{extra}</div></body></html>',encoding='utf-8')
 manifest=E.fromstring(f'<manifest xmlns="{c.OPF_NS}"><item id="credits" href="credits.xhtml"/></manifest>')
 c.remove_known_image_only_promotions(tmp_path,'',manifest,set())
 assert path.exists()==bool(extra)
 assert len(manifest)==int(bool(extra))

@pytest.mark.parametrize('unsafe', [False, True])
@pytest.mark.parametrize('wrapper', ['a href="https://mirrorfiction.com/zh-Hant/book/27037"', 'span'])
def test_mirror_block_keeps_excerpt_and_unknown_images(tmp_path, monkeypatch, unsafe, wrapper):
 image=tmp_path/'qr.jpg';image.write_bytes(b'approved QR fixture')
 monkeypatch.setattr(c,'KNOWN_PROMOTIONAL_IMAGE_SHA256',set() if unsafe else {hashlib.sha256(image.read_bytes()).hexdigest()})
 path=tmp_path/'chapter.xhtml';path.write_text(f'<html xmlns="{c.XHTML_NS}"><body><p>番外原文完整保留。</p><p>更多精彩內容，歡迎上鏡文學官網繼續閱讀。<{wrapper}><img src="qr.jpg"/></{wrapper.split()[0]}></p></body></html>',encoding='utf-8')
 manifest=E.fromstring(f'<manifest xmlns="{c.OPF_NS}"><item href="chapter.xhtml"/><item href="qr.jpg"/></manifest>')
 c.remove_known_image_only_promotions(tmp_path,'',manifest,set())
 text=path.read_text(encoding='utf-8');assert '番外原文完整保留。' in text
 assert ('更多精彩' in text)==unsafe and image.exists()==unsafe
 before=path.read_bytes();c.remove_known_image_only_promotions(tmp_path,'',manifest,set());assert path.read_bytes()==before
