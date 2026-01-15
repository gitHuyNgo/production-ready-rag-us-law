from pathlib import Path
from docling.document_converter import DocumentConverter
from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser


def load_and_chunk(data_path: Path):
    converter = DocumentConverter()
    parser = MarkdownNodeParser()

    for file in data_path.glob("*.pdf"):
        markdown = converter.convert(file).document.export_to_markdown()
        nodes = parser.get_nodes_from_documents(
            [Document(text=markdown)]
        )
        yield file.name, nodes