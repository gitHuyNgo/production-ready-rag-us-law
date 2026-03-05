import os
import csv
import logging
import glob
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from lxml import etree
from tqdm import tqdm

# Configure structured logging
logger = logging.getLogger(__name__)

class USCodeXMLProcessor:
    """
    Processor to parse US Code XML files (USLM schema) into structured 
    Nodes and Edges for GraphRAG ingestion.
    """
    
    # USLM Namespace mapping
    NAMESPACES = {'uslm': 'http://xml.house.gov/schemas/uslm/1.0'}
    
    def __init__(self, input_dir: str, output_node_path: str, output_edge_path: str):
        self.input_dir = Path(input_dir)
        self.output_node_path = Path(output_node_path)
        self.output_edge_path = Path(output_edge_path)
        self.edge_registry: Set[Tuple[str, str]] = set() # For in-memory deduplication

    def _clean_text(self, text: Optional[str]) -> str:
        """Standardizes text by removing extra whitespaces and fixing quotes."""
        if not text:
            return ""
        # Remove newlines, tabs and normalize multiple spaces to one
        cleaned = " ".join(text.replace('"', "'").split())
        return cleaned.strip()

    def _get_title_num(self, identifier: str) -> str:
        """Extracts the Title number from a USLM identifier string."""
        parts = identifier.split('/')
        return parts[3] if len(parts) > 3 else "unknown"

    def _parse_file(self, file_path: Path, node_writer, edge_writer) -> Tuple[int, int]:
        """Parses a single XML file and streams data to CSV writers."""
        nodes_count = 0
        edges_count = 0
        
        try:
            parser = etree.XMLParser(recover=True, remove_blank_text=True)
            tree = etree.parse(str(file_path), parser=parser)
            
            sections = tree.xpath('//uslm:section', namespaces=self.NAMESPACES)
            
            for section in sections:
                section_id = section.get('identifier')
                if not section_id:
                    continue

                heading = section.findtext('uslm:heading', namespaces=self.NAMESPACES) or ""
                raw_content = "".join(section.xpath('.//text()'))
                
                node_writer.writerow({
                    "id": section_id,
                    "title": self._clean_text(heading),
                    "content": self._clean_text(raw_content),
                    "title_num": self._get_title_num(section_id)
                })
                nodes_count += 1

                for ref in section.xpath('.//uslm:ref', namespaces=self.NAMESPACES):
                    target_href = ref.get('href')
                    if target_href and target_href.startswith('/us/usc/'):
                        edge_pair = (section_id, target_href)
                        
                        if edge_pair not in self.edge_registry:
                            edge_writer.writerow({
                                "source": section_id,
                                "target": target_href
                            })
                            self.edge_registry.add(edge_pair)
                            edges_count += 1
                            
        except etree.XMLSyntaxError as e:
            logger.error(f"XML Syntax Error in {file_path.name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path.name}: {e}")
            
        return nodes_count, edges_count

    def run(self):
        """Orchestrates the batch processing of all XML files in the input directory."""
        xml_files = list(self.input_dir.glob("*.xml"))
        if not xml_files:
            logger.warning(f"No XML files found in {self.input_dir}")
            return

        logger.info(f"Starting batch process for {len(xml_files)} files...")

        self.output_node_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_node_path, 'w', encoding='utf-8', newline='') as f_node, \
             open(self.output_edge_path, 'w', encoding='utf-8', newline='') as f_edge:
            
            node_writer = csv.DictWriter(f_node, fieldnames=["id", "title", "content", "title_num"])
            edge_writer = csv.DictWriter(f_edge, fieldnames=["source", "target"])
            
            node_writer.writeheader()
            edge_writer.writeheader()

            total_nodes = 0
            total_edges = 0

            for file_path in tqdm(xml_files, desc="Parsing USLM XMLs"):
                n_count, e_count = self._parse_file(file_path, node_writer, edge_writer)
                total_nodes += n_count
                total_edges += e_count

        logger.info(f"Process complete. Extracted {total_nodes} nodes and {total_edges} unique edges.")

if __name__ == "__main__":
    processor = USCodeXMLProcessor(
        input_dir="app/ingestion-worker/data", 
        output_node_path="app/ingestion-worker/src/vector_store/data/all_nodes.csv", 
        output_edge_path="app/ingestion-worker/src/vector_store/data/all_edges.csv"
    )
    processor.run()