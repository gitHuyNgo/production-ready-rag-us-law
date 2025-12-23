from docling.document_converter import DocumentConverter
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core import Document


def process_legal_pdf(pdf_path):
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    markdown_text = result.document.export_to_markdown()

    parser = MarkdownNodeParser()
    nodes = parser.get_nodes_from_document([Document(text=markdown_text)])

    for node in nodes:
        header_path = node.metadata.get("header_path", "")
        node.metadata["citation_context"] = header_path

    return nodes