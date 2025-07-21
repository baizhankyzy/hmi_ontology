from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
from typing import Dict, List, Set
import logging
from .duplicate_utils import load_ontology, find_duplicates, get_entity_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DuplicateAnalyzer:
    def __init__(self, input_file: str):
        """Initialize the analyzer with an ontology file."""
        self.input_file = input_file
        self.graph = load_ontology(input_file)
        self.duplicates = find_duplicates(self.graph)
    
    def analyze_all_duplicates(self) -> None:
        """Analyze and print information about all duplicates."""
        logger.info("=== Duplicate Analysis ===")
        
        if not self.duplicates:
            logger.info("No duplicates found in the ontology.")
            return
        
        for label, uris in self.duplicates.items():
            if len(uris) > 1:
                logger.info(f"\nDuplicate found: '{label}'")
                self._analyze_duplicate_set(label, uris)
    
    def _analyze_duplicate_set(self, label: str, uris: List[URIRef]) -> None:
        """Analyze a specific set of duplicates."""
        for uri in uris:
            logger.info(f"\nURI: {uri}")
            info = get_entity_info(self.graph, uri)
            
            # Print types
            if info['types']:
                logger.info("Types:")
                for _, type_uri in info['types']:
                    logger.info(f"  - {type_uri}")
            
            # Print properties
            if info['properties']:
                logger.info("Properties:")
                for prop, value in info['properties']:
                    logger.info(f"  {prop} -> {value}")
            
            # Print references
            if info['references']:
                logger.info("Referenced by:")
                for subj, prop in info['references']:
                    logger.info(f"  {subj} -{prop}-> this")
    
    def get_duplicate_stats(self) -> Dict[str, int]:
        """Get statistics about duplicates."""
        stats = {
            'total_duplicates': 0,
            'duplicate_labels': 0,
            'max_duplicates': 0
        }
        
        for label, uris in self.duplicates.items():
            if len(uris) > 1:
                stats['duplicate_labels'] += 1
                stats['total_duplicates'] += len(uris) - 1
                stats['max_duplicates'] = max(stats['max_duplicates'], len(uris))
        
        return stats
    
    def find_conflicting_properties(self) -> Dict[str, List[str]]:
        """Find properties that might conflict when merging duplicates."""
        conflicts = {}
        
        for label, uris in self.duplicates.items():
            if len(uris) > 1:
                property_sets = []
                for uri in uris:
                    properties = set()
                    for _, p, _ in self.graph.triples((uri, None, None)):
                        if p != RDF.type and p != RDFS.label:
                            properties.add(str(p))
                    property_sets.append(properties)
                
                # Find properties that differ between duplicates
                all_properties = set.union(*property_sets)
                common_properties = set.intersection(*property_sets)
                conflicting = all_properties - common_properties
                
                if conflicting:
                    conflicts[label] = list(conflicting)
        
        return conflicts

def main():
    """Main function for running the analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze duplicates in an ontology')
    parser.add_argument('input_file', help='Input ontology file (TTL format)')
    args = parser.parse_args()
    
    analyzer = DuplicateAnalyzer(args.input_file)
    analyzer.analyze_all_duplicates()
    
    stats = analyzer.get_duplicate_stats()
    logger.info("\n=== Duplicate Statistics ===")
    logger.info(f"Total duplicate entities: {stats['total_duplicates']}")
    logger.info(f"Labels with duplicates: {stats['duplicate_labels']}")
    logger.info(f"Maximum duplicates for a label: {stats['max_duplicates']}")
    
    conflicts = analyzer.find_conflicting_properties()
    if conflicts:
        logger.info("\n=== Conflicting Properties ===")
        for label, props in conflicts.items():
            logger.info(f"\n{label}:")
            for prop in props:
                logger.info(f"  - {prop}")

if __name__ == '__main__':
    main() 