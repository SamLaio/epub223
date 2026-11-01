import sys
from pathlib import Path

import pytest
from lxml import etree

from epub3itizer.repair import repair_media_overlays

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from opf_converter import Opf_Converter

OPF = '''<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0" unique-identifier="uid"><metadata><dc:title>Audio</dc:title><dc:identifier id="uid">urn:uuid:audio</dc:identifier><dc:language>en</dc:language>{meta}</metadata><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml" media-overlay="overlay"/><item id="overlay" href="song.smil" media-type="application/octet-stream"/></manifest><spine><itemref idref="chapter"/></spine></package>'''


def fixture(tmp_path, end='00:03.500', meta=''):
    (tmp_path / 'content.opf').write_text(OPF.format(meta=meta), encoding='utf-8')
    smil = f'<smil xmlns="http://www.w3.org/ns/SMIL" version="3.0"><body><seq><par><text src="chapter.xhtml#word"/><audio src="song.mp3" clipBegin="1s" clipEnd="{end}"/></par></seq></body></smil>'.encode()
    (tmp_path / 'song.smil').write_bytes(smil)
    return smil


def test_converter_preserves_media_metadata_text_and_refinement():
    meta = '<meta property="media:duration" refines="#overlay">3.5s</meta><meta property="media:active-class">speaking</meta><meta property="media:narrator">Voice</meta>'
    result = etree.fromstring(Opf_Converter(OPF.format(meta=meta), {}, {}, {}, ['chapter', 'overlay']).get_opf3().encode())
    assert result.xpath('//*[local-name()="meta" and starts-with(@property,"media:")]/text()') == ['3.5s', 'speaking', 'Voice']
    assert result.xpath('//*[local-name()="meta" and @property="media:duration"]/@refines') == ['#overlay']


@pytest.mark.parametrize('end', ['00:03.500', '3.5s', '3500ms', '0.0009722222222222222222222222222h'])
def test_overlay_mime_and_missing_durations_preserve_smil(tmp_path, end):
    smil = fixture(tmp_path, end)
    repair_media_overlays(tmp_path, 'content.opf')
    result = etree.parse(str(tmp_path / 'content.opf'))
    assert result.xpath('//*[local-name()="item" and @id="overlay"]/@media-type') == ['application/smil+xml']
    assert all(abs(float(t[:-1]) - 2.5) < 1e-12 for t in result.xpath('//*[local-name()="meta" and @property="media:duration"]/text()'))
    assert (tmp_path / 'song.smil').read_bytes() == smil
    saved = (tmp_path / 'content.opf').read_bytes()
    repair_media_overlays(tmp_path, 'content.opf')
    assert (tmp_path / 'content.opf').read_bytes() == saved


def test_existing_duration_is_preserved_and_total_added(tmp_path):
    fixture(tmp_path, meta='<meta property="media:duration" refines="#overlay">0:01:02.5</meta>')
    repair_media_overlays(tmp_path, 'content.opf')
    result = etree.parse(str(tmp_path / 'content.opf'))
    assert result.xpath('//*[local-name()="meta" and @refines="#overlay"]/text()') == ['0:01:02.5']
    assert result.xpath('//*[local-name()="meta" and not(@refines)]/text()') == ['62.5s']


def test_cleanup_preserves_manifest_duration_refinement(tmp_path):
    from epub3itizer.conversion import cleanup_opf_manifest
    fixture(tmp_path, meta='<meta property="media:duration" refines="#overlay">62.5s</meta>')
    (tmp_path / 'chapter.xhtml').write_text('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Song</title></head><body><p id="word">Song</p></body></html>')
    cleanup_opf_manifest(tmp_path, 'content.opf')
    result = etree.parse(str(tmp_path / 'content.opf'))
    assert result.xpath('//*[local-name()="meta" and @refines="#overlay"]/text()') == ['62.5s']


def test_global_duration_matches_sum_after_missing_item_duration_repair(tmp_path):
    fixture(tmp_path, meta='<meta property="media:duration">1s</meta>')
    repair_media_overlays(tmp_path, 'content.opf')
    result = etree.parse(str(tmp_path / 'content.opf'))
    assert result.xpath('//*[local-name()="meta" and @property="media:duration"]/text()') == ['2.500s', '2.500s']


@pytest.mark.parametrize('end', ['bad', '00:00.5', ''])
def test_unsafe_timing_does_not_write_opf(tmp_path, end):
    fixture(tmp_path, end)
    saved = (tmp_path / 'content.opf').read_bytes()
    with pytest.raises(ValueError):
        repair_media_overlays(tmp_path, 'content.opf')
    assert (tmp_path / 'content.opf').read_bytes() == saved


def test_missing_clip_end_requires_manual_duration(tmp_path):
    fixture(tmp_path)
    p = tmp_path / 'song.smil'
    p.write_bytes(p.read_bytes().replace(b' clipEnd="00:03.500"', b''))
    with pytest.raises(ValueError, match='clipEnd'):
        repair_media_overlays(tmp_path, 'content.opf')


def test_external_overlay_is_rejected(tmp_path):
    fixture(tmp_path)
    p = tmp_path / 'content.opf'
    p.write_bytes(p.read_bytes().replace(b'href="song.smil"', b'href="https://example.com/song.smil"'))
    with pytest.raises(ValueError, match='包內'):
        repair_media_overlays(tmp_path, 'content.opf')
