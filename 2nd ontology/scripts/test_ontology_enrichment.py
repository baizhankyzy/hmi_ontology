import json
import csv
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, DC, DCTERMS, XSD
import requests
from datetime import datetime
import re
from schema import CLAUDE_RESPONSE_SCHEMA

# Define namespaces
DMS = Namespace("http://www.example.org/test#")
PROV = Namespace("http://www.w3.org/ns/prov#")

def clean_uri_value(value: str) -> str:
    """Clean a string to be used in a URI."""
    # Remove special characters and spaces, convert to camelCase
    value = re.sub(r'[^a-zA-Z0-9\s]', '', value)
    words = value.split()
    if not words:
        return "unknown"
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

def generate_uri(base_uri: str, value: str, class_name: str) -> str:
    """Generate a unique and meaningful URI for an entity."""
    clean_value = clean_uri_value(value)
    if class_name:
        return f"{base_uri}{class_name}_{clean_value}"
    return f"{base_uri}{clean_value}"

def create_claude_prompt(row: dict) -> str:
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

def query_claude_api(prompt: str) -> dict:
    """Send a request to Claude API through Lambda endpoint and get structured response."""
    endpoint = "https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/"
    
    try:
        response = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            json={"prompt": prompt},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        # Print the raw response for debugging
        print("\nRaw API Response:")
        print(json.dumps(result, indent=2))
        
        # Parse the nested JSON string in data.answer
        answer_json = json.loads(result["data"]["answer"])
        return answer_json
        
    except Exception as e:
        print(f"API Error: {str(e)}")
        if hasattr(response, 'text'):
            print(f"Response text: {response.text}")
        raise

def process_test_rows(input_csv: str, output_ttl: str, num_rows: int = 10):
    """Process first N rows of the CSV file and enrich the ontology with detailed logging."""
    project_root = Path(__file__).parent.parent
    
    # Initialize the graph
    g = Graph()
    g.bind("dms", DMS)
    g.bind("prov", PROV)
    g.bind("dcterms", DCTERMS)
    g.bind("xsd", XSD)
    
    print(f"\nReading first {num_rows} rows from {input_csv}...")
    
    processed_rows = 0
    successful_rows = 0
    
    with open(project_root / input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader, 1):
            if i > num_rows:
                break
                
            print(f"\n{'='*80}")
            print(f"Processing row {i}/{num_rows}")
            print(f"Section: {row['Section Title']}")
            print(f"Topic: {row['Topic']}")
            print(f"Knowledge Statement: {row['Knowledge Statement'][:100]}...")
            
            try:
                # Create and send prompt
                prompt = create_claude_prompt(row)
                print("\nSending prompt to Claude API...")
                claude_response = query_claude_api(prompt)
                
                # Print extracted knowledge
                print("\nExtracted Knowledge:")
                for triple in claude_response["extracted_knowledge"]:
                    print(f"Subject: {triple['subject']['value']} ({triple['subject']['ontology_class']})")
                    print(f"Predicate: {triple['predicate']['ontology_property']}")
                    print(f"Object: {triple['object']['value']}")
                    if 'confidence' in triple:
                        print(f"Confidence: {triple['confidence']}")
                    print("---")
                
                # Add to ontology
                statement_uri = generate_uri(str(DMS), claude_response["knowledge_id"], "Statement")
                statement_node = URIRef(statement_uri)
                
                # Add basic metadata
                g.add((statement_node, RDF.type, DMS.KnowledgeStatement))
                g.add((statement_node, DCTERMS.source, Literal(row['Source'])))
                g.add((statement_node, DMS.sectionTitle, Literal(row['Section Title'])))
                g.add((statement_node, DMS.topic, Literal(row['Topic'])))
                
                # Add triples
                for triple in claude_response["extracted_knowledge"]:
                    # Create subject node
                    subject_uri = generate_uri(
                        str(DMS),
                        triple['subject']['value'],
                        triple['subject']['ontology_class']
                    )
                    subject_node = URIRef(subject_uri)
                    g.add((subject_node, RDF.type, DMS[triple['subject']['ontology_class']]))
                    
                    # Create object node
                    if triple['object'].get('ontology_class'):
                        object_uri = generate_uri(
                            str(DMS),
                            triple['object']['value'],
                            triple['object']['ontology_class']
                        )
                        object_node = URIRef(object_uri)
                        g.add((object_node, RDF.type, DMS[triple['object']['ontology_class']]))
                    else:
                        object_node = Literal(triple['object']['value'])
                    
                    # Add the triple
                    predicate = DMS[triple['predicate']['ontology_property']]
                    g.add((subject_node, predicate, object_node))
                    
                    # Add confidence score if present
                    if 'confidence' in triple:
                        confidence_node = BNode()
                        g.add((statement_node, DMS.hasConfidence, confidence_node))
                        g.add((confidence_node, DMS.confidenceValue, Literal(triple['confidence'], datatype=XSD.decimal)))
                        g.add((confidence_node, DMS.confidenceFor, subject_node))
                
                successful_rows += 1
                print("\nSuccessfully added to ontology")
                
            except Exception as e:
                print(f"\nError processing row {i}: {str(e)}")
                continue
            
            processed_rows += 1
    
    # Save the ontology
    output_path = project_root / output_ttl
    output_path.parent.mkdir(exist_ok=True)
    g.serialize(output_path, format="turtle")
    
    print(f"\n{'='*80}")
    print(f"Processing complete:")
    print(f"- Rows processed: {processed_rows}")
    print(f"- Successful rows: {successful_rows}")
    print(f"- Failed rows: {processed_rows - successful_rows}")
    print(f"\nEnriched ontology saved to {output_path}")
    
    # Print some example triples
    print("\nSample of added triples:")
    for s, p, o in g[:10]:
        print(f"{s} {p} {o}")

if __name__ == "__main__":
    process_test_rows(
        "data/nudges_paper_cleaned.csv",
        "output/test_enriched_ontology.ttl"
    ) 