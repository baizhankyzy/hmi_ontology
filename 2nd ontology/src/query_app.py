from flask import Flask, render_template, request, jsonify
from rdflib import Graph, Namespace
from pathlib import Path
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Enable CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Claude API endpoint
CLAUDE_ENDPOINT = "https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/"

# Load the ontology
g = Graph()
g.parse("output/merged_ontology_final.ttl", format="turtle")

# Extract ontology structure
def extract_ontology_structure():
    """Extract classes, properties, and their relationships from the ontology."""
    structure = {"classes": [], "object_properties": [], "data_properties": []}
    
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

# Get ontology structure once at startup
ONTOLOGY_STRUCTURE = extract_ontology_structure()

def natural_language_to_sparql(query):
    """Convert natural language query to SPARQL using Claude."""
    # Create class and property lists for the prompt
    class_list = "\n".join([f"- {c['label']} ({c['uri']})" for c in ONTOLOGY_STRUCTURE['classes'][:20]])
    prop_list = "\n".join([f"- {p['label']} (Domain: {p['domain']}, Range: {p['range']})" 
                          for p in ONTOLOGY_STRUCTURE['object_properties'][:10]])
    
    # Create the prompt with examples and semantic guidance
    prompt = f"""You are a SPARQL query generator for a Driver Monitoring System Ontology. Your task is to convert natural language questions into SPARQL queries.

Important guidelines:
1. Consider semantic variations (e.g., "inattention" could match "InattentionState")
2. Look for related concepts (e.g., a question about detection might involve classes with "Detector", "Monitor", or properties like "detects", "monitors")
3. Use OPTIONAL for labels to ensure results even if labels are missing
4. Consider both direct and indirect relationships (using path expressions where appropriate)
5. When looking for systems or components, consider all subclasses of relevant system types
6. Always include complete prefix declarations in your queries

The ontology has these main components:

Classes:
{class_list}
... and {len(ONTOLOGY_STRUCTURE['classes']) - 20} more classes

Object Properties:
{prop_list}
... and {len(ONTOLOGY_STRUCTURE['object_properties']) - 10} more properties

Base URI: http://www.example.org/test#

Here are some example conversions:

Question: "What cognitive states can vehicle systems detect or analyze?"
SPARQL:
PREFIX : <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?cognitiveState ?label
WHERE {{
    ?cognitiveState rdfs:subClassOf* :CognitiveState .
    OPTIONAL {{ ?cognitiveState rdfs:label ?label }}
    {{
        ?vehicleSystem rdfs:subClassOf* :VehicleSystem .
        ?vehicleSystem ?detectsProp ?cognitiveState .
        FILTER(CONTAINS(str(?detectsProp), "detects"))
    }} UNION {{
        ?vehicleSystem rdfs:subClassOf* :VehicleSystem .
        ?vehicleSystem ?analyzesProp ?cognitiveState .
        FILTER(CONTAINS(str(?analyzesProp), "analyzes"))
    }}
}}

Question: "What properties are related to cognitive state?"
SPARQL:
PREFIX : <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?prop ?label
WHERE {{
    ?prop a owl:ObjectProperty .
    OPTIONAL {{ ?prop rdfs:label ?label }}
    {{
        ?prop rdfs:domain :CognitiveState
    }} UNION {{
        ?prop rdfs:range :CognitiveState
    }}
}}

Convert this question to SPARQL (return only the SPARQL query):
{query}"""

    # Make request to Claude endpoint
    try:
        response = requests.post(CLAUDE_ENDPOINT, json={"prompt": prompt})
        response.raise_for_status()
        return response.json()["data"]["answer"].strip()
    except Exception as e:
        raise Exception(f"Error calling Claude API: {str(e)}")

def execute_sparql(query):
    """Execute SPARQL query and return results."""
    try:
        # Standard prefixes for the ontology
        standard_prefixes = """
        PREFIX : <http://www.example.org/test#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        """
        
        # Check if query has prefixes
        has_prefixes = any(prefix in query.lower() for prefix in ['prefix :', 'prefix rdf:', 'prefix rdfs:', 'prefix owl:'])
        
        # If query doesn't have complete prefixes, add them
        if not has_prefixes:
            query = standard_prefixes + query
        else:
            # Replace any empty prefix declarations with proper ones
            query = query.replace('PREFIX : ', 'PREFIX : <http://www.example.org/test#>')
            query = query.replace('PREFIX rdf: ', 'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>')
            query = query.replace('PREFIX rdfs: ', 'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>')
            query = query.replace('PREFIX owl: ', 'PREFIX owl: <http://www.w3.org/2002/07/owl#>')
            
        # Execute query
        results = g.query(query)
        
        # Convert results to a more readable format
        formatted_results = []
        for row in results:
            if len(row) == 1:
                formatted_results.append(str(row[0]))
            else:
                # Format multi-column results
                result_parts = []
                for val in row:
                    # Clean up URIs in the output
                    val_str = str(val)
                    if val_str.startswith('http://www.example.org/test#'):
                        val_str = val_str.replace('http://www.example.org/test#', ':')
                    elif val_str.startswith('http://www.w3.org/'):
                        val_str = val_str.split('/')[-1]
                    result_parts.append(val_str)
                formatted_results.append(" | ".join(result_parts))
        
        return formatted_results if formatted_results else ["No results found"]
    except Exception as e:
        return [f"Error executing query: {str(e)}"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    natural_query = request.json.get('query', '')
    
    try:
        # Convert natural language to SPARQL
        sparql_query = natural_language_to_sparql(natural_query)
        
        # Execute the SPARQL query
        results = execute_sparql(sparql_query)
        
        return jsonify({
            'sparql': sparql_query,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    Path("templates").mkdir(exist_ok=True)
    # Run the app on all interfaces (0.0.0.0) and port 8080
    app.run(host='0.0.0.0', port=8080, debug=True) 