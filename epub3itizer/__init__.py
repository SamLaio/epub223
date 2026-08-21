__version__ = "1.0"

from .conversion import convert_epub2_to_epub3
from .repair import repair_epub
from .chinese import convert_chinese_document, to_traditional

__all__ = ["__version__", "convert_epub2_to_epub3", "repair_epub", "convert_chinese_document", "to_traditional"]
