import json
import os
import csv
from pathlib import Path
from typing import Dict, List, Optional
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, DC, DCTERMS, XSD
import pandas as pd
from dotenv import load_dotenv
import requests
import hashlib
from datetime import datetime
from schema import CLAUDE_RESPONSE_SCHEMA

# Load environment variables
load_dotenv()

# Define namespaces
DMS = Namespace("http://www.example.org/test#")
PROV = Namespace("http://www.w3.org/ns/prov#")

def generate_unique_uri(base_uri: str, value: str) -> str:
    """Generate a unique URI for a new individual."""
    # Create a hash of the value to ensure uniqueness
    hash_value = hashlib.md5(value.encode()).hexdigest()[:8]
    # Clean the value to create a valid URI
    clean_value = "".join(c for c in value if c.isalnum())[:30]
    return f"{base_uri}{clean_value}_{hash_value}"

def create_claude_prompt(row: Dict) -> str:
    """Create a prompt for the Claude API based on a CSV row."""
    return f"""As an expert in knowledge extraction and ontology engineering, analyze the following knowledge statement and extract structured knowledge as triples:

Knowledge Statement: {row['Knowledge Statement']}
Topic: {row['Topic']}
Section: {row['Section Title']}
Source: {row['Source']}

Extract subject-predicate-object triples that capture the key knowledge, ensuring:
1. Each subject and object maps to an appropriate ontology class
2. Each predicate uses existing ontology properties
3. The knowledge is represented as concrete instances/individuals

Format your response as a JSON object following this schema:
{json.dumps(CLAUDE_RESPONSE_SCHEMA, indent=2)}

Focus on extracting precise, well-defined triples that can be directly implemented in the ontology."""

def query_claude_api(prompt: str) -> Dict:
    """Send a request to Claude API through Lambda endpoint and get structured response."""
    endpoint = "https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        endpoint,
        headers=headers,
        json={"prompt": prompt}
    )
    
    response.raise_for_status()
    return response.json()["response"]  # Assuming the Lambda function returns the response in a "response" field

def add_knowledge_to_ontology(g: Graph, claude_response: Dict) -> None:
    """Add extracted knowledge to the ontology graph."""
    # Create an individual for the knowledge statement itself
    knowledge_uri = generate_unique_uri(str(DMS), claude_response["knowledge_id"])
    knowledge_node = URIRef(knowledge_uri)
    
    # Add metadata about the knowledge statement
    g.add((knowledge_node, RDF.type, DMS.KnowledgeStatement))
    g.add((knowledge_node, DCTERMS.source, Literal(claude_response["source"])))
    g.add((knowledge_node, DMS.sectionTitle, Literal(claude_response["section_title"])))
    g.add((knowledge_node, DMS.topic, Literal(claude_response["topic"])))
    g.add((knowledge_node, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
    
    # Add metadata if present
    if "metadata" in claude_response:
        if "extraction_timestamp" in claude_response["metadata"]:
            g.add((knowledge_node, DMS.extractionTimestamp, 
                   Literal(claude_response["metadata"]["extraction_timestamp"], datatype=XSD.dateTime)))
        if "confidence_score" in claude_response["metadata"]:
            g.add((knowledge_node, DMS.confidenceScore, 
                   Literal(claude_response["metadata"]["confidence_score"], datatype=XSD.decimal)))
    
    # Process each extracted triple
    for triple in claude_response["extracted_knowledge"]:
        # Create or get subject node
        subject_uri = generate_unique_uri(str(DMS), triple["subject"]["value"])
        subject_node = URIRef(subject_uri)
        g.add((subject_node, RDF.type, DMS[triple["subject"]["ontology_class"]]))
        
        # Create or get object node
        if triple["object"].get("ontology_class"):
            object_uri = generate_unique_uri(str(DMS), triple["object"]["value"])
            object_node = URIRef(object_uri)
            g.add((object_node, RDF.type, DMS[triple["object"]["ontology_class"]]))
        else:
            datatype = None
            if triple["object"].get("datatype"):
                datatype = getattr(XSD, triple["object"]["datatype"])
            object_node = Literal(triple["object"]["value"], datatype=datatype)
        
        # Add the main triple
        predicate = DMS[triple["predicate"]["ontology_property"]]
        g.add((subject_node, predicate, object_node))
        
        # Add confidence score if present
        if "confidence" in triple:
            triple_node = BNode()
            g.add((knowledge_node, DMS.hasTriple, triple_node))
            g.add((triple_node, RDF.type, DMS.Triple))
            g.add((triple_node, DMS.hasSubject, subject_node))
            g.add((triple_node, DMS.hasPredicate, predicate))
            g.add((triple_node, DMS.hasObject, object_node))
            g.add((triple_node, DMS.confidence, Literal(triple["confidence"], datatype=XSD.decimal)))
        else:
            g.add((knowledge_node, DMS.hasTriple, BNode([
                (RDF.type, DMS.Triple),
                (DMS.hasSubject, subject_node),
                (DMS.hasPredicate, predicate),
                (DMS.hasObject, object_node)
            ])))

def process_csv_file(input_csv: str, output_ttl: str):
    """Process the CSV file and enrich the ontology."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Load existing ontology
    g = Graph()
    g.parse(project_root / "output" / "merged_ontology_final.ttl", format="turtle")
    
    # Add our namespaces
    g.bind("dms", DMS)
    g.bind("prov", PROV)
    g.bind("dcterms", DCTERMS)
    g.bind("xsd", XSD)
    
    # Read CSV file with error handling
    try:
        df = pd.read_csv(
            project_root / input_csv,
            quoting=csv.QUOTE_ALL,  # Handle all fields as quoted
            escapechar='\\',        # Handle escaped characters
            encoding='utf-8',       # Specify encoding
            on_bad_lines='warn'     # Warn about problematic lines instead of failing
        )
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        print("Attempting to read with different options...")
        try:
            # Try alternative reading method
            df = pd.read_csv(
                project_root / input_csv,
                quoting=csv.QUOTE_MINIMAL,
                encoding='utf-8',
                on_bad_lines='skip'  # Skip problematic lines
            )
        except Exception as e:
            print(f"Failed to read CSV file: {e}")
            return
    
    print(f"Successfully loaded {len(df)} rows from CSV")
    
    # Process each row
    for index, row in df.iterrows():
        try:
            print(f"\nProcessing row {index + 1}/{len(df)}")
            # Create prompt and query Claude
            prompt = create_claude_prompt(row.to_dict())
            claude_response = query_claude_api(prompt)
            
            # Add extracted knowledge to ontology
            add_knowledge_to_ontology(g, claude_response)
            print(f"Successfully processed row {index + 1}")
            
        except Exception as e:
            print(f"Error processing row {index + 1}: {e}")
            continue
    
    # Save enriched ontology
    output_path = project_root / output_ttl
    output_path.parent.mkdir(exist_ok=True)
    g.serialize(output_path, format="turtle")
    print(f"\nEnriched ontology saved to {output_path}")

def example_queries():
    """Return example SPARQL queries for the enriched ontology."""
    return {
        "get_all_knowledge_statements": """
        PREFIX dms: <http://www.example.org/test#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        
        SELECT ?statement ?source ?topic ?confidence
        WHERE {
            ?statement a dms:KnowledgeStatement ;
                      dcterms:source ?source ;
                      dms:topic ?topic .
            OPTIONAL { ?statement dms:confidenceScore ?confidence }
        }
        """,
        
        "get_triples_by_topic": """
        PREFIX dms: <http://www.example.org/test#>
        
        SELECT ?subject ?predicate ?object ?confidence
        WHERE {
            ?statement dms:topic "driver_monitoring" ;
                      dms:hasTriple ?triple .
            ?triple dms:hasSubject ?subject ;
                    dms:hasPredicate ?predicate ;
                    dms:hasObject ?object .
            OPTIONAL { ?triple dms:confidence ?confidence }
        }
        """,
        
        "get_high_confidence_knowledge": """
        PREFIX dms: <http://www.example.org/test#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT ?statement ?triple ?confidence
        WHERE {
            ?statement dms:hasTriple ?triple .
            ?triple dms:confidence ?confidence .
            FILTER(?confidence >= "0.8"^^xsd:decimal)
        }
        """
    }

if __name__ == "__main__":
    # Process the CSV file with test data first
    print("Starting with test file...")
    process_csv_file("data/fixed_nudges.csv", "output/test_enriched_ontology.ttl")
    
    # If successful, ask to continue with full file
    response = input("\nTest completed. Process full file? (y/n): ")
    if response.lower() == 'y':
        process_csv_file("data/nudges_paper_cleaned.csv", "output/enriched_ontology.ttl")
    
    # Print example queries
    print("\nExample SPARQL Queries:")
    for name, query in example_queries().items():
        print(f"\n{name}:")
        print(query) 