from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
from typing import Dict, List, Tuple, Set
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_ontology(input_file: str) -> Graph:
    """Load an ontology from a file."""
    try:
        g = Graph()
        g.parse(input_file, format="turtle")
        return g
    except Exception as e:
        logger.error(f"Error loading ontology from {input_file}: {e}")
        raise

def save_ontology(g: Graph, output_file: str) -> None:
    """Save an ontology to a file."""
    try:
        g.serialize(destination=output_file, format="turtle")
        logger.info(f"Ontology saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving ontology to {output_file}: {e}")
        raise

def find_duplicates(g: Graph) -> Dict[str, List[URIRef]]:
    """Find duplicate entities based on labels."""
    label_dict: Dict[str, URIRef] = {}
    duplicates: Dict[str, List[URIRef]] = {}
    
    for s, p, o in g.triples((None, RDFS.label, None)):
        if isinstance(o, Literal):
            label = str(o)
            if label in label_dict:
                if label not in duplicates:
                    duplicates[label] = [label_dict[label]]
                duplicates[label].append(s)
            else:
                label_dict[label] = s
    
    return duplicates

def get_entity_info(g: Graph, uri: URIRef) -> Dict[str, List[Tuple]]:
    """Get detailed information about an entity."""
    info = {
        'types': [],
        'properties': [],
        'references': []
    }
    
    # Get types
    for _, _, type_uri in g.triples((uri, RDF.type, None)):
        info['types'].append(('type', type_uri))
    
    # Get properties
    for _, prop, value in g.triples((uri, None, None)):
        if prop != RDF.type and prop != RDFS.label:
            info['properties'].append((prop, value))
    
    # Get references
    for subj, prop, _ in g.triples((None, None, uri)):
        if prop != RDF.type:
            info['references'].append((subj, prop))
    
    return info

def transfer_relationships(g: Graph, source_uri: URIRef, target_uri: URIRef) -> None:
    """Transfer all relationships from source URI to target URI."""
    # Transfer incoming relationships
    for s, p, _ in g.triples((None, None, source_uri)):
        g.add((s, p, target_uri))
    
    # Transfer outgoing relationships
    for _, p, o in g.triples((source_uri, None, None)):
        if p != RDF.type and p != RDFS.label:
            g.add((target_uri, p, o)) 