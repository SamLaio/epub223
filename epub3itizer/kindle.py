"""Opt-in horizontal, reflowable copies of EPUB3 text books."""
from pathlib import Path
from urllib.parse import unquote

from lxml import etree
import tinycss2

from . import conversion as conv
from .compat import EpubBookAdapter, XML_PARSER
from .repair import repair_epub_contents

NS = {"o": conv.OPF_NS, "h": conv.XHTML_NS, "dc": conv.DC_NS}
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
SVG = "http://www.w3.org/2000/svg"


def horizontal_css(css: str, inline: bool = False) -> str:
    nodes = (tinycss2.parse_declaration_list(css) if inline
             else tinycss2.parse_stylesheet(css))
    for node in nodes:
        if node.type == "error":
            raise ValueError("CSS 無法解析，停止製作 Kindle 副本")
        if node.type == "declaration":
            name = node.lower_name
            if name.endswith("writing-mode"):
                node.value = tinycss2.parse_component_value_list("horizontal-tb")
            elif "text-combine" in name or name.endswith("text-orientation"):
                node.value = tinycss2.parse_component_value_list(
                    "none" if "text-combine" in name else "mixed")
            elif name == "position" and tinycss2.serialize(node.value).strip() in {"absolute", "fixed"}:
                raise ValueError("包含絕對定位，不能安全自動轉成流式排版")
        elif node.type == "qualified-rule":
            node.content = tinycss2.parse_component_value_list(
                horizontal_css(tinycss2.serialize(node.content), inline=True))
        elif node.type == "at-rule" and node.content is not None:
            declarations = node.lower_at_keyword in {"font-face", "page"}
            node.content = tinycss2.parse_component_value_list(
                horizontal_css(tinycss2.serialize(node.content), inline=declarations))
    return tinycss2.serialize(nodes)


def _unwrap_image(svg):
    images = svg.findall(f"{{{SVG}}}image")
    if len(images) != 1 or any(
        child.tag not in {f"{{{SVG}}}image", f"{{{SVG}}}title"} for child in svg
    ):
        raise ValueError("SVG 不是單張圖片包裝，保留原書並停止轉換")
    image = images[0]
    if any(k not in {"height", "width", "href", f"{{{conv.XLINK_NS}}}href", "x", "y"} for k in image.attrib):
        raise ValueError("SVG 圖片含額外效果，不能安全攤平成插圖")
    if any(k not in {"height", "width", "version", "viewBox", "preserveAspectRatio", "id", "class"} for k in svg.attrib):
        raise ValueError("SVG 容器含額外效果，不能安全攤平成插圖")
    box = [float(v) for v in svg.get("viewBox", "").replace(",", " ").split()]
    if (len(box) != 4 or box[:2] != [0, 0]
            or float(image.get("x", "0")) != 0 or float(image.get("y", "0")) != 0
            or [float(image.get("width", "0")), float(image.get("height", "0"))] != box[2:]
            or svg.get("preserveAspectRatio", "xMidYMid meet") != "xMidYMid meet"):
        raise ValueError("SVG 存在裁切或位移，不能安全轉換")
    href = image.get(f"{{{conv.XLINK_NS}}}href") or image.get("href")
    if not href:
        raise ValueError("SVG 圖片缺少來源")
    wrapper = etree.Element(f"{{{conv.XHTML_NS}}}div")
    for key in ("id", "class"):
        if svg.get(key):
            wrapper.set(key, svg.get(key))
    alt = "".join(svg.xpath("./*[local-name()='title']/text()"))
    etree.SubElement(wrapper, f"{{{conv.XHTML_NS}}}img", src=href, alt=alt,
                     style="max-width:100%; height:auto;")
    wrapper.tail = svg.tail
    svg.getparent().replace(svg, wrapper)


def kindle_reflowable(input_path: Path, output_path: Path, language: str | None = None) -> Path:
    input_path, output_path = Path(input_path).resolve(), Path(output_path).resolve()
    if input_path == output_path or (output_path.exists() and input_path.samefile(output_path)):
        raise ValueError("Kindle 副本不可覆寫輸入檔")
    with EpubBookAdapter.open(input_path) as book:
        opf_href = book.get_opfbookpath()
        opf_path = book.root_dir / opf_href
        tree = etree.parse(str(opf_path), XML_PARSER)
        package = tree.getroot()
        if not package.get("version", "").startswith("3"):
            raise ValueError("請先以 epub223 將 EPUB2 轉為 EPUB3")
        layouts = tree.xpath("//o:meta[@property='rendition:layout']", namespaces=NS)
        if any(node.text == "pre-paginated" for node in layouts):
            raise ValueError("全書固定版面不適用文字書的 Kindle 流式副本功能")
        metadata = package.find("o:metadata", NS)
        if not layouts:
            layouts = [etree.SubElement(metadata, f"{{{conv.OPF_NS}}}meta", property="rendition:layout")]
        for node in layouts:
            node.text = "reflowable"
        package.find("o:spine", NS).set("page-progression-direction", "ltr")
        if language:
            package.set(XML_LANG, language)
            for node in metadata.findall("dc:language", NS):
                node.text = language
        for ref in tree.xpath("//o:itemref[@properties]", namespaces=NS):
            tokens = [p for p in ref.get("properties").split()
                      if not p.startswith(("rendition:layout-", "rendition:spread-", "rendition:page-spread-", "page-spread-", "rendition:orientation-"))]
            if tokens:
                ref.set("properties", " ".join(tokens))
            else:
                ref.attrib.pop("properties")
        tree.write(str(opf_path), encoding="utf-8", xml_declaration=True)
        for item in tree.xpath("//o:manifest/o:item", namespaces=NS):
            path = (opf_path.parent / unquote(item.get("href"))).resolve()
            path.relative_to(book.root_dir.resolve())
            if item.get("media-type") == "text/css":
                conv.write_text_file(path, horizontal_css(conv.read_text_file(path)))
            elif item.get("media-type") == "application/xhtml+xml":
                doc = etree.parse(str(path), XML_PARSER)
                if language:
                    doc.getroot().set("lang", language)
                    doc.getroot().set(XML_LANG, language)
                for meta in doc.xpath("//h:meta[@name='viewport']", namespaces=NS):
                    meta.getparent().remove(meta)
                for svg in doc.xpath("//*[local-name()='svg' and namespace-uri()=$ns]", ns=SVG):
                    _unwrap_image(svg)
                for node in doc.xpath("//*[@style]"):
                    node.set("style", horizontal_css(node.get("style"), inline=True))
                for node in doc.xpath("//h:style", namespaces=NS):
                    node.text = horizontal_css(node.text or "")
                # Fixed image-page styles often set body font-size to zero.
                head = doc.find("h:head", NS)
                style = head.find("h:style[@id='kindle-reflowable-profile']", NS)
                if style is None:
                    style = etree.SubElement(head, f"{{{conv.XHTML_NS}}}style", id="kindle-reflowable-profile")
                style.text = "html,body{font-size:1em;} img{max-width:100%;height:auto;}"
                doc.write(str(path), encoding="utf-8", xml_declaration=True)
        repair_epub_contents(book.root_dir, opf_href)
        conv.zip_epub(book.root_dir, output_path)
    return output_path


def kindle_vertical_compatible(input_path: Path, output_path: Path, language: str | None = None) -> Path:
    """Make a Kindle test copy by removing only the EPUB spine RTL declaration."""
    input_path, output_path = Path(input_path).resolve(), Path(output_path).resolve()
    if input_path == output_path or (output_path.exists() and input_path.samefile(output_path)):
        raise ValueError("Kindle 副本不可覆寫輸入檔")
    with EpubBookAdapter.open(input_path) as book:
        opf_href = book.get_opfbookpath()
        opf_path = book.root_dir / opf_href
        tree = etree.parse(str(opf_path), XML_PARSER)
        package = tree.getroot()
        if not package.get("version", "").startswith("3"):
            raise ValueError("請先以 epub223 將 EPUB2 轉為 EPUB3")
        spine = package.find("o:spine", NS)
        if spine is None:
            raise ValueError("OPF 缺少 spine，不能製作 Kindle 副本")
        spine.attrib.pop("page-progression-direction", None)
        if language:
            package.set(XML_LANG, language)
            metadata = package.find("o:metadata", NS)
            for node in metadata.findall("dc:language", NS):
                node.text = language
            for item in tree.xpath("//o:manifest/o:item[@media-type='application/xhtml+xml']", namespaces=NS):
                path = (opf_path.parent / unquote(item.get("href"))).resolve()
                path.relative_to(book.root_dir.resolve())
                doc = etree.parse(str(path), XML_PARSER)
                doc.getroot().set("lang", language)
                doc.getroot().set(XML_LANG, language)
                doc.write(str(path), encoding="utf-8", xml_declaration=True)
        tree.write(str(opf_path), encoding="utf-8", xml_declaration=True)
        conv.zip_epub(book.root_dir, output_path)
    return output_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="製作 Kindle 副本，不改原書")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--language", help="已確認的內容語言，例如 zh-Hant")
    parser.add_argument("--keep-vertical", action="store_true",
                        help="保留直排與固定版面，只移除 spine 的 RTL 宣告")
    args = parser.parse_args()
    converter = kindle_vertical_compatible if args.keep_vertical else kindle_reflowable
    print(converter(args.input, args.output, args.language))
