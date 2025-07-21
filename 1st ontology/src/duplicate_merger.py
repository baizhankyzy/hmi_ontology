from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
from typing import Dict, List, Optional
import logging
from .duplicate_utils import (
    load_ontology, 
    save_ontology, 
    find_duplicates, 
    transfer_relationships
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DuplicateMerger:
    def __init__(self, input_file: str):
        """Initialize the merger with an ontology file."""
        self.input_file = input_file
        self.graph = load_ontology(input_file)
        self.duplicates = find_duplicates(self.graph)
    
    def merge_all_duplicates(self, output_file: str, preferences: Optional[Dict[str, str]] = None) -> None:
        """Merge all duplicates, optionally using preferences for which URI to keep."""
        if not self.duplicates:
            logger.info("No duplicates found in the ontology.")
            return
        
        for label, uris in self.duplicates.items():
            if len(uris) > 1:
                logger.info(f"Merging duplicates for '{label}'")
                self._merge_duplicate_set(label, uris, preferences)
        
        save_ontology(self.graph, output_file)
        logger.info(f"Merged ontology saved to {output_file}")
    
    def _merge_duplicate_set(self, label: str, uris: List[URIRef], 
                           preferences: Optional[Dict[str, str]] = None) -> None:
        """Merge a specific set of duplicates."""
        # Determine primary URI
        primary_uri = self._select_primary_uri(label, uris, preferences)
        
        # Merge all other URIs into the primary
        for uri in uris:
            if uri != primary_uri:
                self._merge_entities(primary_uri, uri)
                logger.info(f"Merged {uri} into {primary_uri}")
    
    def _select_primary_uri(self, label: str, uris: List[URIRef], 
                          preferences: Optional[Dict[str, str]] = None) -> URIRef:
        """Select which URI to keep as primary."""
        if preferences and label in preferences:
            preferred = URIRef(preferences[label])
            if preferred in uris:
                return preferred
            else:
                logger.warning(f"Preferred URI {preferred} for label '{label}' not found in duplicates")
        
        # Default to the first URI if no preference or preference not found
        return uris[0]
    
    def _merge_entities(self, primary_uri: URIRef, duplicate_uri: URIRef) -> None:
        """Merge one entity into another."""
        # Transfer all relationships
        transfer_relationships(self.graph, duplicate_uri, primary_uri)
        
        # Remove the duplicate
        self.graph.remove((duplicate_uri, None, None))
        self.graph.remove((None, None, duplicate_uri))
    
    def merge_with_strategy(self, output_file: str, strategy: str = 'first') -> None:
        """Merge duplicates using a specific strategy."""
        if strategy not in ['first', 'most_connected', 'most_properties']:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        for label, uris in self.duplicates.items():
            if len(uris) > 1:
                if strategy == 'most_connected':
                    primary_uri = self._get_most_connected_uri(uris)
                elif strategy == 'most_properties':
                    primary_uri = self._get_uri_with_most_properties(uris)
                else:  # 'first'
                    primary_uri = uris[0]
                
                for uri in uris:
                    if uri != primary_uri:
                        self._merge_entities(primary_uri, uri)
        
        save_ontology(self.graph, output_file)
    
    def _get_most_connected_uri(self, uris: List[URIRef]) -> URIRef:
        """Find the URI with the most connections."""
        connection_counts = {}
        for uri in uris:
            count = 0
            # Count incoming connections
            count += len(list(self.graph.triples((None, None, uri))))
            # Count outgoing connections
            count += len(list(self.graph.triples((uri, None, None))))
            connection_counts[uri] = count
        
        return max(connection_counts.items(), key=lambda x: x[1])[0]
    
    def _get_uri_with_most_properties(self, uris: List[URIRef]) -> URIRef:
        """Find the URI with the most properties."""
        property_counts = {}
        for uri in uris:
            count = len(list(self.graph.triples((uri, None, None))))
            property_counts[uri] = count
        
        return max(property_counts.items(), key=lambda x: x[1])[0]

def main():
    """Main function for running the merger."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Merge duplicates in an ontology')
    parser.add_argument('input_file', help='Input ontology file (TTL format)')
    parser.add_argument('output_file', help='Output ontology file (TTL format)')
    parser.add_argument('--preferences', help='JSON file with URI preferences')
    parser.add_argument('--strategy', choices=['first', 'most_connected', 'most_properties'],
                      default='first', help='Strategy for selecting primary URI')
    args = parser.parse_args()
    
    merger = DuplicateMerger(args.input_file)
    
    if args.preferences:
        with open(args.preferences) as f:
            preferences = json.load(f)
        merger.merge_all_duplicates(args.output_file, preferences)
    else:
        merger.merge_with_strategy(args.output_file, args.strategy)

if __name__ == '__main__':
    main() 