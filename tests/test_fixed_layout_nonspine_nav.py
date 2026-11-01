from lxml import etree
from epub3itizer.conversion import add_fixed_layout_viewports


def test_nonspine_navigation_does_not_remove_fixed_layout(tmp_path):
    (tmp_path/'content.opf').write_text('''<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
    <metadata><meta property="rendition:layout">pre-paginated</meta></metadata>
    <manifest><item id="p" href="page.xhtml" media-type="application/xhtml+xml"/>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>
    <spine><itemref idref="p"/></spine></package>''',encoding='utf-8')
    (tmp_path/'page.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>頁面</title><meta name="viewport" content="width=800,height=1200"/></head><body><p>固定版面內容</p></body></html>',encoding='utf-8')
    nav='<html xmlns="http://www.w3.org/1999/xhtml"><head><title>目錄</title></head><body><nav><a href="page.xhtml">第一頁</a></nav></body></html>'
    (tmp_path/'nav.xhtml').write_text(nav,encoding='utf-8')
    add_fixed_layout_viewports(tmp_path,'content.opf')
    assert etree.parse(str(tmp_path/'content.opf')).xpath('//*[local-name()="meta" and @property="rendition:layout"]/text()')==['pre-paginated']
    assert (tmp_path/'nav.xhtml').read_text(encoding='utf-8')==nav
