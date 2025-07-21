from rdflib import Graph
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_ontology():
    # Load the ontology
    g = Graph()
    g.parse("output/merged_ontology_final.ttl", format="turtle")
    
    # Get all classes
    class_query = """
    SELECT DISTINCT ?class ?label
    WHERE {
        ?class a owl:Class .
        OPTIONAL { ?class rdfs:label ?label }
    }
    """
    
    print("\n=== Classes in the Ontology ===")
    for row in g.query(class_query):
        print(f"Class: {row['class']}, Label: {row['label'] if row['label'] else 'No label'}")
    
    # Get all object properties
    prop_query = """
    SELECT DISTINCT ?prop ?label ?domain ?range
    WHERE {
        ?prop a owl:ObjectProperty .
        OPTIONAL { ?prop rdfs:label ?label }
        OPTIONAL { ?prop rdfs:domain ?domain }
        OPTIONAL { ?prop rdfs:range ?range }
    }
    """
    
    print("\n=== Object Properties in the Ontology ===")
    for row in g.query(prop_query):
        print(f"Property: {row['prop']}")
        if row['label']:
            print(f"  Label: {row['label']}")
        if row['domain']:
            print(f"  Domain: {row['domain']}")
        if row['range']:
            print(f"  Range: {row['range']}")
    
    # Test a simple query to get all triples
    print("\n=== Sample of Triples in the Ontology ===")
    for s, p, o in list(g)[:10]:  # Show first 10 triples
        print(f"Subject: {s}")
        print(f"Predicate: {p}")
        print(f"Object: {o}")
        print("---")
    
    # Count total triples
    print(f"\nTotal number of triples in the ontology: {len(g)}")

if __name__ == "__main__":
    analyze_ontology() 