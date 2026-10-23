from lxml import etree
from epub3itizer.conversion import normalize_epubcheck_xhtml, collect_doc_features, XHTML_NS


def test_empty_malformed_ad_marker_preserves_text_tail_and_unsafe_variants():
    for prefix in ('', '<span>前文</span>'):
        for fragment in ('<divclass __contentadv_=""/>', '<divclass __contentadv_="">正文</divclass>',
                         '<divclass __contentadv_=""><span>正文</span></divclass>',
                         '<divclass __contentadv_="" id="anchor"/>', '<divclass __contentadv_="unknown"/>',
                         '<divclass xmlns="urn:other" __contentadv_=""/>'):
            root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body><p>{prefix}{fragment}後文</p></body></html>')
            prior = ''.join(root.itertext())
            normalize_epubcheck_xhtml(root)
            assert ''.join(root.itertext()) == prior
            nodes = root.xpath('//*[local-name()="divclass"]')
            assert len(nodes) == (0 if fragment == '<divclass __contentadv_=""/>' else 1)
            serialized = etree.tostring(root)
            normalize_epubcheck_xhtml(root)
            assert etree.tostring(root) == serialized


def test_normal_format_pipeline_removes_marker_before_private_attribute_cleanup():
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><head><title>正文</title></head><body><p>前文<divclass __contentadv_=""/>後文</p></body></html>')
    output = collect_doc_features(root, 'chapter.xhtml')[0]
    assert '<divclass' not in output and '__contentadv_' not in output
    assert ''.join(etree.fromstring(output.encode()).find(f'{{{XHTML_NS}}}body').itertext()) == '前文後文'
