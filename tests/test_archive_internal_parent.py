import zipfile
import pytest
from epub3itizer.compat import _extract_epub_archive


def test_internal_parent_segment_preserves_cover_and_reference(tmp_path):
    archive = tmp_path / 'input.epub';root = tmp_path / 'out';root.mkdir()
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('OEBPS/../cover.jpg', b'original image')
        z.writestr('OEBPS/chapter.xhtml', '<html><body><img src="../cover.jpg"/>正文</body></html>')
    with zipfile.ZipFile(archive) as z:_extract_epub_archive(z, root)
    assert (root/'cover.jpg').read_bytes() == b'original image'
    assert '../cover.jpg' in (root/'OEBPS/chapter.xhtml').read_text(encoding='utf-8')
    assert '正文' in (root/'OEBPS/chapter.xhtml').read_text(encoding='utf-8')


@pytest.mark.parametrize('names', [
    ['../escape.txt'], ['OEBPS/../../escape.txt'],
    ['OEBPS/../cover.jpg', 'cover.jpg'],
    ['OEBPS/../cover.jpg', 'COVER.JPG'],
])
def test_escape_and_canonical_collision_fail_before_any_write(tmp_path, names):
    archive = tmp_path / 'input.epub';root = tmp_path / 'out';root.mkdir()
    with zipfile.ZipFile(archive, 'w') as z:
        for index,name in enumerate(names):z.writestr(name, f'conflicting content {index}'.encode())
    with zipfile.ZipFile(archive) as z:
        with pytest.raises(ValueError):_extract_epub_archive(z, root)
    assert not list(root.iterdir())
    assert not (tmp_path/'escape.txt').exists()


def test_identical_raster_aliases_are_kept_without_overwriting(tmp_path):
    archive = tmp_path/'input.epub';root=tmp_path/'out';root.mkdir()
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('cover.jpg',b'original image')
        z.writestr('OEBPS/../cover.jpg',b'original image')
        z.writestr('OEBPS/chapter.xhtml','<html><body><img src="../cover.jpg"/>正文</body></html>')
    with zipfile.ZipFile(archive) as z:_extract_epub_archive(z,root)
    images=list(root.rglob('*.jpg'))
    assert len(images)==2 and all(p.read_bytes()==b'original image' for p in images)
    assert (root/'cover.jpg').read_bytes()==b'original image'
    assert 'epub3itizer_resource_' in (root/'OEBPS/chapter.xhtml').read_text(encoding='utf-8')
