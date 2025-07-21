import csv
from rdflib import Graph
import pandas as pd
from pathlib import Path
import re

def extract_key_terms(question):
    """Extract key terms from the competency question."""
    # Common patterns in the questions
    class_pattern = r'([A-Z][a-zA-Z]+(?:State|Monitor|Camera|System|Position|Characteristics|Analysis))'
    property_pattern = r'(?:what|which)\s+([a-zA-Z]+)\s+(?:of|do|does)'
    
    # Find all matches
    classes = re.findall(class_pattern, question)
    properties = re.findall(property_pattern, question, re.IGNORECASE)
    
    return {
        'classes': list(set(classes)),
        'properties': list(set(properties))
    }

def create_sparql_query(question):
    """
    Create a SPARQL query based on the competency question.
    Analyzes the question structure to generate appropriate SPARQL patterns.
    """
    terms = extract_key_terms(question)
    classes = terms['classes']
    
    prefixes = """PREFIX : <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>"""
    
    # If question asks about characteristics or indicators
    if "characteristics" in question.lower() or "indicate" in question.lower():
        target_class = next((c for c in classes if "State" in c), None)
        if not target_class:
            return None
            
        query = f"""{prefixes}
SELECT DISTINCT ?indicator ?characteristic
WHERE {{
  {{
    :{target_class} rdfs:subClassOf ?restriction .
    ?restriction a owl:Restriction .
    ?restriction owl:onProperty ?property .
    ?restriction owl:someValuesFrom ?indicator .
    FILTER(CONTAINS(STR(?indicator), "Position") || CONTAINS(STR(?indicator), "Characteristics"))
  }}
  UNION
  {{
    :{target_class} rdfs:subClassOf ?restriction .
    ?restriction a owl:Restriction .
    ?restriction owl:onProperty ?property .
    ?restriction owl:someValuesFrom ?union .
    ?union owl:unionOf ?list .
    ?list rdf:rest*/rdf:first ?characteristic .
    FILTER(CONTAINS(STR(?characteristic), "Position") || CONTAINS(STR(?characteristic), "Characteristics"))
  }}
}}"""
    
    # If question asks about what something performs/detects
    elif any(word in question.lower() for word in ["perform", "detect", "analyze"]):
        subject_classes = [c for c in classes if any(term in c for term in ["Camera", "Monitor", "System"])]
        target_class = next((c for c in classes if "State" in c), None)
        
        if not subject_classes or not target_class:
            return None
            
        subject_filters = " || ".join(f"?subject = :{c}" for c in subject_classes)
        
        query = f"""{prefixes}
SELECT DISTINCT ?subject ?action ?object
WHERE {{
  ?subject rdfs:subClassOf ?restriction .
  ?restriction a owl:Restriction .
  ?restriction owl:onProperty ?action .
  ?restriction owl:someValuesFrom ?object .
  FILTER({subject_filters})
  FILTER(CONTAINS(STR(?object), "{target_class}"))
}}"""
    
    # If question asks about types
    elif "types" in question.lower():
        target_class = next((c for c in classes if "State" in c), None)
        if not target_class:
            return None
            
        query = f"""{prefixes}
SELECT DISTINCT ?type
WHERE {{
  {{
    ?type rdfs:subClassOf :{target_class} .
  }}
  UNION
  {{
    ?type owl:equivalentClass ?restriction .
    ?restriction owl:onProperty ?property .
    ?restriction owl:someValuesFrom :{target_class} .
  }}
}}"""
    
    # If question asks about components
    elif "components" in question.lower():
        system_class = next((c for c in classes if "System" in c), None)
        if not system_class:
            return None
            
        query = f"""{prefixes}
SELECT DISTINCT ?component ?property ?value
WHERE {{
  :{system_class} rdfs:subClassOf ?restriction .
  ?restriction a owl:Restriction .
  ?restriction owl:onProperty ?property .
  ?restriction owl:someValuesFrom ?component .
}}"""
    
    else:
        return None
    
    return query

def format_query_results(results):
    """Format query results into a readable string."""
    output = []
    for row in results:
        row_items = []
        for item in row:
            if item:  # Only process non-None values
                # Extract the last part after # from the URI
                value = str(item).split('#')[-1]
                row_items.append(value)
        if row_items:
            output.append(' -> '.join(row_items))
    return '\n'.join(output) if output else "No results found"

def process_competency_questions():
    # Create output directory if it doesn't exist
    Path('output').mkdir(exist_ok=True)
    
    # Load the ontology
    g = Graph()
    g.parse("output/merged_ontology_final.ttl", format="turtle")
    
    # Read competency questions
    questions_df = pd.read_csv("data/competency_questions.csv")
    
    # Prepare results list
    results = []
    
    # Process each question
    for index, row in questions_df.iterrows():
        cq_id = row['CQ_ID']
        question = row['Competency_Question']
        
        # Generate and execute query
        query = create_sparql_query(question)
        if query:
            try:
                query_results = g.query(query)
                output = format_query_results(query_results)
            except Exception as e:
                output = f"Error executing query: {str(e)}"
        else:
            output = "Could not generate appropriate query for this question"
        
        # Add to results list
        results.append({
            'CQID': cq_id,
            'Competency Question': question,
            'Query Used': query if query else "No query generated",
            'Output': output
        })
    
    # Convert to DataFrame and save
    results_df = pd.DataFrame(results)
    results_df.to_csv('output/query_results.csv', index=False, quoting=csv.QUOTE_ALL)
    print(f"Processed {len(results)} questions. Results saved to output/query_results.csv")

if __name__ == "__main__":
    process_competency_questions() 