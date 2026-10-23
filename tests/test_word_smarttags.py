from lxml import etree
from epub3itizer.conversion import collect_doc_features, XHTML_NS


def test_word_date_and_metric_wrappers_keep_text_ids_links_and_foreign_elements():
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}" xmlns:w="urn:schemas-microsoft-com:office:word"><head><title>正文</title></head><body><p>前<chsdate year="2008" month="8" w:st="on" id="date" class="date">八月十三日</chsdate>中<chmetcnv unitname="公分" sourcevalue="10" w:st="on"><a href="#date">十公分</a></chmetcnv>後</p><chsdate xmlns="urn:other" year="2008">外部元素</chsdate></body></html>')
    before = ''.join(root.find(f'{{{XHTML_NS}}}body').itertext())
    output = collect_doc_features(root, 'chapter.xhtml')[0]
    doc = etree.fromstring(output.encode())
    assert ''.join(doc.find(f'{{{XHTML_NS}}}body').itertext()) == before
    assert not doc.findall(f'.//{{{XHTML_NS}}}chsdate') and not doc.findall(f'.//{{{XHTML_NS}}}chmetcnv')
    date = doc.find(f'.//{{{XHTML_NS}}}span[@id="date"]')
    assert date.text == '八月十三日' and date.get('class') == 'date'
    assert doc.find(f'.//{{{XHTML_NS}}}a').get('href') == '#date'
    assert not any(attr.startswith('{urn:schemas-microsoft-com:office:word}') for node in doc.iter() for attr in node.attrib)
    assert doc.find('.//{urn:other}chsdate').get('year') == '2008'
    again = etree.fromstring(collect_doc_features(doc, 'chapter.xhtml')[0].encode())
    assert etree.tostring(again, method='c14n') == etree.tostring(etree.fromstring(output.encode()), method='c14n')
