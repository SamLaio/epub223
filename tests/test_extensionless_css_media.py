import pytest
from lxml import etree as E
from epub3itizer.conversion import manifest_media_type_for_path, cleanup_opf_manifest, OPF_NS


@pytest.mark.parametrize('content', [b'@charset "UTF-8";body{margin:0.2}', b'\xef\xbb\xbf@charset "utf-8";p{color:blue}'])
def test_extensionless_explicit_css_corrects_manifest_preserving_bytes(tmp_path, content):
    path=tmp_path/'style_inside';path.write_bytes(content)
    assert manifest_media_type_for_path(path,'style_inside')=='text/css'
    opf=tmp_path/'content.opf';opf.write_text(f'<package xmlns="{OPF_NS}" version="3.0"><metadata/><manifest><item id="css" href="style_inside" media-type="application/octet-stream"/></manifest><spine/></package>',encoding='utf-8')
    cleanup_opf_manifest(tmp_path,'content.opf')
    assert E.parse(str(opf)).find('.//{*}item').get('media-type')=='text/css'
    assert path.read_bytes()==content


@pytest.mark.parametrize('content', [b'body{color:red}', b'@charset "UTF-8";plain text', b'@charset "UTF-8";body{color:red}\0', b'\xff\x00@charset "UTF-8";body{}'])
def test_unknown_extensionless_data_is_not_guessed_as_css(tmp_path, content):
    path=tmp_path/'unknown';path.write_bytes(content)
    assert manifest_media_type_for_path(path,'unknown')=='application/octet-stream'
