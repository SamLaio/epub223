from lxml import etree
from epub3itizer.conversion import normalize_epubcheck_xhtml
from epub3itizer.repair import repair_obfuscated_font_media_types


def test_legacy_body_link_attributes_preserve_text_and_links():
    doc = etree.fromstring(b'<html xmlns="http://www.w3.org/1999/xhtml"><head/><body link="blue" vlink="purple" alink="red"><p>Keep <a href="chapter.xhtml">link</a></p></body></html>')
    normalize_epubcheck_xhtml(doc)
    body = doc.find('{http://www.w3.org/1999/xhtml}body')
    assert not {'link', 'vlink', 'alink'} & set(body.attrib)
    assert ''.join(body.itertext()) == 'Keep link'
    assert body.find('.//{http://www.w3.org/1999/xhtml}a').get('href') == 'chapter.xhtml'


def test_idpf_font_mime_preserves_obfuscated_bytes_and_other_resources(tmp_path):
    (tmp_path/'META-INF').mkdir()
    encryption = b'<encryption xmlns:enc="http://www.w3.org/2001/04/xmlenc#"><enc:EncryptedData><enc:EncryptionMethod Algorithm="http://www.idpf.org/2008/embedding"/><enc:CipherData><enc:CipherReference URI="font.dat"/></enc:CipherData></enc:EncryptedData></encryption>'
    (tmp_path/'META-INF/encryption.xml').write_bytes(encryption)
    (tmp_path/'font.dat').write_bytes(b'obfuscated-font')
    (tmp_path/'other.dat').write_bytes(b'other')
    opf = tmp_path/'content.opf'
    opf.write_text('<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="f" href="font.dat" media-type="application/octet-stream"/><item id="o" href="other.dat" media-type="application/octet-stream"/></manifest></package>')
    repair_obfuscated_font_media_types(tmp_path, 'content.opf')
    items = etree.fromstring(opf.read_bytes()).findall('.//{http://www.idpf.org/2007/opf}item')
    assert [x.get('media-type') for x in items] == ['application/vnd.ms-opentype', 'application/octet-stream']
    assert (tmp_path/'font.dat').read_bytes() == b'obfuscated-font'
    assert (tmp_path/'META-INF/encryption.xml').read_bytes() == encryption
    saved = opf.read_bytes()
    repair_obfuscated_font_media_types(tmp_path, 'content.opf')
    assert opf.read_bytes() == saved
    (tmp_path/'META-INF/encryption.xml').write_bytes(encryption.replace(b'http://www.idpf.org/2008/embedding', b'urn:unknown-encryption'))
    opf.write_bytes(saved.replace(b'application/vnd.ms-opentype', b'application/octet-stream'))
    untouched = opf.read_bytes()
    repair_obfuscated_font_media_types(tmp_path, 'content.opf')
    assert opf.read_bytes() == untouched
