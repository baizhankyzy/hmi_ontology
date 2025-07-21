from rdflib import Graph
import json

def examine_ontology():
    g = Graph()
    g.parse("output/merged_ontology_final.ttl", format="turtle")
    
    # Get all classes
    print("\n=== Classes ===")
    classes_query = """
    SELECT DISTINCT ?class ?label
    WHERE {
        ?class a owl:Class .
        OPTIONAL { ?class rdfs:label ?label }
    }
    ORDER BY ?class
    """
    
    print("\nClasses with labels:")
    for row in g.query(classes_query):
        class_uri = str(row['class'])
        if class_uri.startswith('http://www.example.org/test#'):
            class_name = class_uri.replace('http://www.example.org/test#', ':')
            label = str(row['label']) if row['label'] else 'No label'
            print(f"{class_name} - {label}")
    
    # Get all object properties
    print("\n=== Object Properties ===")
    props_query = """
    SELECT DISTINCT ?prop ?label ?domain ?range
    WHERE {
        ?prop a owl:ObjectProperty .
        OPTIONAL { ?prop rdfs:label ?label }
        OPTIONAL { ?prop rdfs:domain ?domain }
        OPTIONAL { ?prop rdfs:range ?range }
    }
    ORDER BY ?prop
    """
    
    print("\nProperties with domain and range:")
    for row in g.query(props_query):
        prop_uri = str(row['prop'])
        if prop_uri.startswith('http://www.example.org/test#'):
            prop_name = prop_uri.replace('http://www.example.org/test#', ':')
            label = str(row['label']) if row['label'] else 'No label'
            domain = str(row['domain']).replace('http://www.example.org/test#', ':') if row['domain'] else 'No domain'
            range_ = str(row['range']).replace('http://www.example.org/test#', ':') if row['range'] else 'No range'
            print(f"{prop_name}")
            print(f"  Label: {label}")
            print(f"  Domain: {domain}")
            print(f"  Range: {range_}")
            print()

    # Get some example triples
    print("\n=== Sample Triples ===")
    count = 0
    for s, p, o in g:
        if count < 10 and str(s).startswith('http://www.example.org/test#'):
            print(f"Subject: {str(s).replace('http://www.example.org/test#', ':')}")
            print(f"Predicate: {str(p).replace('http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'rdf:').replace('http://www.w3.org/2000/01/rdf-schema#', 'rdfs:')}")
            print(f"Object: {str(o).replace('http://www.example.org/test#', ':')}")
            print("---")
            count += 1

if __name__ == "__main__":
    examine_ontology() 