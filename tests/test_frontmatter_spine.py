from lxml import etree
import pytest
from epub3itizer.conversion import cleanup_opf_manifest


@pytest.mark.parametrize('complete', [True, False])
def test_frontmatter_spine_requires_complete_nav(tmp_path, complete):
    names = ['cover', 'copyright', 'story-2', 'story-10']
    for name in names:
        (tmp_path / f'{name}.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>正文</title></head><body><p>正文</p></body></html>', encoding='utf-8')
    order = ['cover', 'story-2', 'story-10', 'copyright'] if complete else ['cover', 'story-2', 'copyright']
    (tmp_path / 'nav.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>目錄</title></head><body><nav epub:type="toc"><ol>' + ''.join(f'<li><a href="{name}.xhtml">{name}</a></li>' for name in order) + '</ol></nav></body></html>', encoding='utf-8')
    (tmp_path / 'content.opf').write_text('<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata/><manifest>' + ''.join(f'<item id="{name}" href="{name}.xhtml" media-type="application/xhtml+xml"/>' for name in names) + '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="cover"/><itemref idref="copyright"/></spine></package>', encoding='utf-8')
    cleanup_opf_manifest(tmp_path, 'content.opf')
    once = (tmp_path / 'content.opf').read_bytes()
    root = etree.fromstring(once)
    assert root.xpath('//*[local-name()="spine"]/*/@idref') == (order if complete else ['cover', 'copyright'])
    cleanup_opf_manifest(tmp_path, 'content.opf')
    assert (tmp_path / 'content.opf').read_bytes() == once
