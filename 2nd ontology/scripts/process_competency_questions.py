import csv
from rdflib import Graph
import requests
import json
from pathlib import Path

# Claude API endpoint
CLAUDE_ENDPOINT = "https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/"

# Load the ontology
g = Graph()
g.parse("output/merged_ontology_final.ttl", format="turtle")

def get_competency_questions():
    """Get competency questions from the CSV file."""
    questions = []
    with open('data/competency_questions.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append((row['CQ_ID'], row['Competency_Question']))
    return questions

def extract_ontology_structure():
    """Extract classes, properties, and their relationships from the ontology."""
    structure = {"classes": [], "object_properties": []}
    
    # Query for all classes
    class_query = """
    SELECT DISTINCT ?class ?label ?superclass
    WHERE {
        ?class a owl:Class .
        OPTIONAL { ?class rdfs:label ?label }
        OPTIONAL { ?class rdfs:subClassOf ?superclass }
    }
    """
    
    # Query for object properties
    property_query = """
    SELECT DISTINCT ?prop ?label ?domain ?range
    WHERE {
        ?prop a owl:ObjectProperty .
        OPTIONAL { ?prop rdfs:label ?label }
        OPTIONAL { ?prop rdfs:domain ?domain }
        OPTIONAL { ?prop rdfs:range ?range }
    }
    """
    
    # Execute queries and store results
    for row in g.query(class_query):
        class_info = {
            "uri": str(row["class"]),
            "label": str(row["label"]) if row["label"] else str(row["class"]).split("#")[-1],
            "superclass": str(row["superclass"]) if row["superclass"] else None
        }
        structure["classes"].append(class_info)
    
    for row in g.query(property_query):
        prop_info = {
            "uri": str(row["prop"]),
            "label": str(row["label"]) if row["label"] else str(row["prop"]).split("#")[-1],
            "domain": str(row["domain"]) if row["domain"] else None,
            "range": str(row["range"]) if row["range"] else None
        }
        structure["object_properties"].append(prop_info)
    
    return structure

def natural_language_to_sparql(query, ontology_structure):
    """Convert natural language query to SPARQL using Claude."""
    # Create class and property lists for the prompt
    class_list = "\n".join([f"- {c['label']} ({c['uri']})" for c in ontology_structure['classes']])
    prop_list = "\n".join([f"- {p['label']} ({p['uri']}) [Domain: {p['domain']}, Range: {p['range']}]" 
                          for p in ontology_structure['object_properties']])
    
    prompt = f"""You are a SPARQL query generator for a Driver Monitoring System Ontology. 
    Convert the given natural language question to a SPARQL query.
    
    IMPORTANT: Return ONLY the SPARQL query without any explanation or additional text.
    When using multiple UNION clauses, they must be inside the WHERE clause.
    
    Guidelines:
    1. Use PREFIX : <http://www.example.org/test#> for the base ontology
    2. Always include standard prefixes (rdf, rdfs, owl)
    3. Use OPTIONAL for properties that might not exist
    4. Consider indirect relationships through property chains
    5. Use UNION when multiple property paths might be relevant
    6. Include labels in results when available
    7. Filter out blank nodes and system URIs
    8. Use rdfs:subClassOf* to include subclasses
    9. Consider both direct properties and property chains
    10. Use DISTINCT to avoid duplicates
    11. When using multiple UNION clauses, they must be inside the WHERE clause
    
    The ontology has these components:
    
    Classes:
    {class_list}
    
    Object Properties:
    {prop_list}
    
    Key ontology patterns:
    - Driver study capabilities include various analysis tools
    - Observations have results through hasResult property
    - Vehicle systems adapt to emotional and cognitive states
    - Visual elements include alerts and display components
    - Personality traits are organized under PersonalityDimension
    - Measurements and analyses are linked to specific capabilities
    
    Example SPARQL patterns:
    1. Finding study capabilities and their measurements:
       SELECT DISTINCT ?capability ?measurement WHERE {{
         ?capability rdfs:subClassOf :DriverStudyCapability .
         OPTIONAL {{ ?capability :performs ?measurement }}
       }}
    
    2. Finding system adaptations with multiple paths:
       SELECT DISTINCT ?system ?state WHERE {{
         ?system rdfs:subClassOf* :VehicleSystem .
         {{
           ?system :adaptsToEmotionalState ?state
         }} UNION {{
           ?system :adaptsToDetected ?state
         }} UNION {{
           ?system :adaptsTo ?state
         }}
       }}
    
    3. Finding observations and results:
       SELECT DISTINCT ?observation ?result WHERE {{
         ?observation rdfs:subClassOf* :Observation .
         ?observation :hasResult ?result .
       }}
    
    Convert this question to SPARQL (return ONLY the query, no explanations):
    {query}"""

    try:
        response = requests.post(CLAUDE_ENDPOINT, json={"prompt": prompt})
        response.raise_for_status()
        sparql_query = response.json()["data"]["answer"].strip()
        
        # Clean up the response to ensure we only get the SPARQL query
        if "PREFIX" not in sparql_query.split("\n")[0]:
            lines = sparql_query.split("\n")
            for i, line in enumerate(lines):
                if "PREFIX" in line:
                    sparql_query = "\n".join(lines[i:])
                    break
        
        return sparql_query
    except Exception as e:
        return f"Error generating SPARQL: {str(e)}"

def execute_sparql(query):
    """Execute SPARQL query and return results."""
    try:
        # Add default prefixes if not present
        default_prefixes = """
        PREFIX : <http://www.example.org/test#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        """
        
        if not any(prefix in query.lower() for prefix in ['prefix :', 'prefix rdf:', 'prefix rdfs:', 'prefix owl:']):
            query = default_prefixes + query
        
        # Clean up any explanatory text before the query
        query_lines = query.split('\n')
        start_idx = 0
        for i, line in enumerate(query_lines):
            if 'PREFIX' in line:
                start_idx = i
                break
        query = '\n'.join(query_lines[start_idx:])
            
        results = g.query(query)
        
        # Format results
        formatted_results = []
        for row in results:
            if len(row) == 1:
                val = str(row[0])
                if val.startswith('http://www.example.org/test#'):
                    val = val.split('#')[-1]
                formatted_results.append(val)
            else:
                result_parts = []
                for val in row:
                    if val is None:
                        continue
                    val_str = str(val)
                    # Clean up URIs
                    if val_str.startswith('http://www.example.org/test#'):
                        val_str = val_str.split('#')[-1]
                    elif val_str.startswith('http://www.w3.org/'):
                        val_str = val_str.split('/')[-1]
                    # Clean up literal values
                    elif val_str.startswith('"') and val_str.endswith('"'):
                        val_str = val_str[1:-1]
                    # Skip blank nodes
                    elif val_str.startswith('N'):
                        continue
                    result_parts.append(val_str)
                if result_parts:  # Only add if we have non-blank-node results
                    formatted_results.append(" | ".join(result_parts))
        
        # Remove duplicates and sort
        formatted_results = sorted(list(set(formatted_results)))
        
        return formatted_results if formatted_results else ["No results found"]
    except Exception as e:
        return [f"Error executing query: {str(e)}"]

def main():
    # Extract ontology structure
    ontology_structure = extract_ontology_structure()
    
    # Get competency questions from CSV
    competency_questions = get_competency_questions()
    
    # Prepare CSV output
    output_file = "competency_questions_results.csv"
    fieldnames = ['CQ_ID', 'Competency Question', 'SPARQL Query', 'Results']
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Process each competency question
        for cq_id, question in competency_questions:
            print(f"\nProcessing {cq_id}: {question}")
            
            # Generate SPARQL query
            sparql_query = natural_language_to_sparql(question, ontology_structure)
            print("\nGenerated SPARQL query:")
            print(sparql_query)
            
            # Execute query
            results = execute_sparql(sparql_query)
            print("\nResults:")
            print("\n".join(results))
            
            # Write to CSV
            writer.writerow({
                'CQ_ID': cq_id,
                'Competency Question': question,
                'SPARQL Query': sparql_query,
                'Results': json.dumps(results)  # Store results as JSON string
            })
    
    print(f"\nResults have been saved to {output_file}")

if __name__ == "__main__":
    main() 