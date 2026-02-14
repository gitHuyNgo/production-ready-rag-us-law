from pathlib import Path
from docling.document_converter import DocumentConverter
from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import MarkdownNodeParser


class LegalChunker:
    def __init__(self):
        self.converter = DocumentConverter()
        self.parser = MarkdownNodeParser()

    def load_and_chunk(self, file_path: Path):
        print(f"--- Converting: {file_path.name} ---")
        result = self.converter.convert(file_path)
        markdown_text = result.document.export_to_markdown()

        nodes = self.parser.get_nodes_from_documents(
            [LlamaDocument(text=markdown_text, metadata={"source": file_path.name})]
        )
        
        return nodes