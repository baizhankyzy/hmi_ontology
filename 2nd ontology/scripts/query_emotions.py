from rdflib import Graph, Namespace
from pathlib import Path

# Initialize graph and load ontology
g = Graph()
g.parse("output/test_20rows_ontology.ttl", format="turtle")

# Define namespaces
DMS = Namespace("http://www.example.org/test#")
DCTERMS = Namespace("http://purl.org/dc/terms/")

# SPARQL query to get emotion-related information
query = """
PREFIX dms: <http://www.example.org/test#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?emotion ?predicate ?object
WHERE {
    {
        # Get emotions and their properties
        ?emotion rdf:type dms:EmotionalState ;
                dcterms:source "Nudges-Based Design Method for Adaptive HMI to Improve Driving Safety.pdf" ;
                ?predicate ?object .
    }
    UNION
    {
        # Get instances that are affected by or related to emotions
        ?emotion rdf:type dms:EmotionalState .
        ?subject ?predicate ?emotion .
        ?subject dcterms:source "Nudges-Based Design Method for Adaptive HMI to Improve Driving Safety.pdf" .
        BIND(?subject as ?object)
    }
}
ORDER BY ?emotion ?predicate
"""

# Execute query and print results
print("Emotion-related information from Nudges paper:")
print("=" * 80)
for row in g.query(query):
    emotion = str(row.emotion).replace(str(DMS), "dms:")
    predicate = str(row.predicate).replace(str(DMS), "dms:")
    object_val = str(row.object).replace(str(DMS), "dms:")
    
    print(f"\nEmotion: {emotion}")
    print(f"Predicate: {predicate}")
    print(f"Object: {object_val}")
    print("-" * 40) 