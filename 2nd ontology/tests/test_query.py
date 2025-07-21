from rdflib import Graph

# Load the ontology
g = Graph()
g.parse("output/merged_ontology_final.ttl", format="turtle")

# The SPARQL query
query = """
PREFIX : <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?indicator ?characteristic
WHERE {
  {
    :DrowsinessState rdfs:subClassOf ?restriction .
    ?restriction a owl:Restriction .
    ?restriction owl:onProperty ?property .
    ?restriction owl:someValuesFrom ?indicator .
  }
  UNION
  {
    :DrowsinessState rdfs:subClassOf ?restriction .
    ?restriction a owl:Restriction .
    ?restriction owl:onProperty ?property .
    ?restriction owl:someValuesFrom ?union .
    ?union owl:unionOf ?list .
    ?list rdf:rest*/rdf:first ?characteristic .
  }
}
"""

# Execute query
results = g.query(query)

print("\nCharacteristics indicating DrowsinessState:")
print("==========================================")
for row in results:
    indicator, characteristic = row
    if indicator:
        print(f"Direct Indicator: {str(indicator).split('#')[-1]}")
    if characteristic:
        print(f"Union Characteristic: {str(characteristic).split('#')[-1]}") 