from lxml import etree

from epub3itizer.conversion import cleanup_opf_manifest


def test_metadata_scheme_survives_repair_and_illegal_attributes_do_not(tmp_path):
    page = '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Book</title></head><body><p>Keep text</p></body></html>'
    (tmp_path / 'chapter.xhtml').write_text(page)
    opf = tmp_path / 'content.opf'
    opf.write_text('''<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0" unique-identifier="uid"><metadata><dc:title>Book</dc:title><dc:language>en</dc:language><dc:identifier id="uid">urn:uuid:keep</dc:identifier><dc:creator id="author">Author</dc:creator><meta refines="#author" property="role" scheme="marc:relators" invalid="remove">aut</meta></metadata><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="chapter"/></spine></package>''')
    cleanup_opf_manifest(tmp_path, 'content.opf')
    result = etree.parse(str(opf))
    role = result.find('.//{http://www.idpf.org/2007/opf}meta[@property="role"]')
    assert role.attrib == {'refines': '#author', 'property': 'role', 'scheme': 'marc:relators'}
    assert role.text == 'aut'
    assert (tmp_path / 'chapter.xhtml').read_text() == page
    saved = opf.read_bytes()
    cleanup_opf_manifest(tmp_path, 'content.opf')
    assert opf.read_bytes() == saved
