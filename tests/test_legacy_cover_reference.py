from lxml import etree
from epub3itizer.conversion import repair_legacy_cover_references


def test_filename_resolves_to_existing_manifest_image():
    root = etree.XML('<package><metadata><meta name="cover" content="cover.jpg"/></metadata>'
                      '<manifest><item id="image" href="Images/cover.jpg" media-type="image/jpeg" '
                      'properties="cover-image"/></manifest></package>')
    assert repair_legacy_cover_references(root, lambda _: False) == 0
    assert repair_legacy_cover_references(root, lambda _: True) == 1
    assert root.find("metadata/meta").get("content") == "image"
    assert repair_legacy_cover_references(root, lambda _: True) == 0
