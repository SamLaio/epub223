from lxml import etree

from epub3itizer.conversion import normalize_epubcheck_xhtml, sanitize_all_css_files, sanitize_css


CSS = '''@font-face {
  font-family: "Body Book";
  src: url("../fonts/body.otf") format("opentype");
  font-weight: 300;
  font-style: normal;
}
@font-face {font-family: "Heading"; src: url(../fonts/heading.ttf);}
body {font-family: "Body Book";}
h1 {font-family: "Heading";}
'''


def test_embedded_font_links_survive_css_sanitizing(tmp_path):
    output = sanitize_css(CSS)
    assert output == CSS
    assert sanitize_css(output) == output
    file = tmp_path / 'style.css'
    file.write_text(CSS, encoding='utf8')
    sanitize_all_css_files(tmp_path)
    assert file.read_text(encoding='utf8') == CSS


def test_embedded_fonts_survive_inline_style_and_external_face_cleanup():
    external = '@font-face {font-family: "Device"; src: url(file:///mnt/font.ttf);}'
    root = etree.fromstring(f'<html xmlns="http://www.w3.org/1999/xhtml"><head><style>{CSS}{external}</style></head><body><h1>章標</h1><p>正文</p></body></html>')
    normalize_epubcheck_xhtml(root)
    output = root.find('.//{*}style').text
    assert 'Device' not in output and 'file:' not in output
    assert output.count('@font-face') == 2
    for fragment in ('../fonts/body.otf', '../fonts/heading.ttf', 'font-family: "Body Book"', 'font-family: "Heading"'):
        assert fragment in output
    assert ''.join(root.find('{*}body').itertext()) == '章標正文'
