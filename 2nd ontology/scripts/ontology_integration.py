import json
import csv
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, BNode, RDF, RDFS, OWL
from rdflib.namespace import XSD, DCTERMS
import requests
import re
from datetime import datetime
from schema import CLAUDE_RESPONSE_SCHEMA

# Define namespaces
DMS = Namespace("http://www.example.org/test#")

def clean_uri_value(value: str) -> str:
    """Clean a string to be used in a URI."""
    value = re.sub(r'[^a-zA-Z0-9\s]', '', value)
    words = value.split()
    if not words:
        return "unknown"
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

def generate_uri(base_uri: str, value: str, class_name: str) -> str:
    """Generate a unique and meaningful URI for an entity."""
    # For certain classes, just use the class name directly
    reuse_classes = {
        'EmotionalState', 'CognitiveState', 'DriverState', 'DrivingPerformance',
        'ReactionTime', 'RiskPerception', 'Distraction', 'RiskyDriving',
        'Decision', 'Intention', 'Action', 'KnowledgeBase', 'InterventionStrategy'
    }
    
    if class_name in reuse_classes:
        return f"{base_uri}{class_name}"
    
    # For other cases, clean and use the value
    clean_value = clean_uri_value(value)
    if class_name:
        return f"{base_uri}{class_name}_{clean_value}"
    return f"{base_uri}{clean_value}"

def map_to_existing_class(class_name: str) -> str:
    """Map extracted classes to existing ontology classes."""
    class_mappings = {
        'EmotionalState': 'EmotionalState',
        'Emotion': 'EmotionalState',
        'CognitiveProcess': 'CognitiveState',
        'DrivingBehavior': 'DriverState',
        'Theory': 'KnowledgeBase',
        'InterventionTechnique': 'InterventionStrategy',
        'AffectiveHeuristic': 'CognitiveState',
        'CognitiveShortcut': 'CognitiveState',
        'Error': 'RiskFactor',
        'RiskTakingBehavior': 'RiskTaking',
        'DrivingPerformance': 'DrivingPerformance',
        'ReactionTime': 'ReactionTime',
        'PerceivedRisk': 'RiskPerception',
        'PerceivedDistraction': 'Distraction',
        'UnsafeDrivingBehavior': 'RiskyDriving',
        'Decision': 'Decision',
        'Intention': 'Intention',
        'Action': 'Action'
    }
    return class_mappings.get(class_name, class_name)

def map_to_existing_property(property_name: str) -> str:
    """Map extracted properties to existing ontology properties."""
    property_mappings = {
        'influences': 'influences',
        'affects': 'influences',
        'impacts': 'influences',
        'reliesOn': 'dependsOn',
        'hasEffect': 'affects',
        'causes': 'leads_to',
        'increases': 'increases',
        'decreases': 'decreases',
        'adaptsTo': 'adaptsToEmotionalState'
    }
    return property_mappings.get(property_name, property_name)

def ensure_class_exists(g: Graph, class_name: str):
    """Ensure a class exists in the ontology, map to existing classes where possible."""
    mapped_class = map_to_existing_class(class_name)
    class_uri = DMS[mapped_class]
    
    # Only create if it doesn't exist and isn't mapped to an existing class
    if (class_uri, RDF.type, OWL.Class) not in g and mapped_class == class_name:
        g.add((class_uri, RDF.type, OWL.Class))
        g.add((class_uri, RDFS.label, Literal(class_name)))
        
        # Add appropriate subclass relationships
        if class_name in ['EmotionalState', 'CognitiveState', 'DriverState']:
            g.add((class_uri, RDFS.subClassOf, DMS.DriverState))
        elif class_name in ['Theory', 'KnowledgeBase']:
            g.add((class_uri, RDFS.subClassOf, DMS.Knowledge))
        elif class_name in ['InterventionTechnique', 'InterventionStrategy']:
            g.add((class_uri, RDFS.subClassOf, DMS.Intervention))

def ensure_property_exists(g: Graph, property_name: str):
    """Ensure a property exists in the ontology, map to existing properties where possible."""
    mapped_property = map_to_existing_property(property_name)
    prop_uri = DMS[mapped_property]
    
    # Only create if it doesn't exist and isn't mapped to an existing property
    if (prop_uri, RDF.type, OWL.ObjectProperty) not in g and \
       (prop_uri, RDF.type, OWL.DatatypeProperty) not in g and \
       mapped_property == property_name:
        
        if property_name in ['hasConfidence', 'hasSource', 'influences', 'reliesOn', 'adaptsTo']:
            g.add((prop_uri, RDF.type, OWL.ObjectProperty))
            
            # Add domain and range
            if property_name == 'influences':
                g.add((prop_uri, RDFS.domain, DMS.EmotionalState))
                g.add((prop_uri, RDFS.range, DMS.DriverState))
            elif property_name == 'adaptsTo':
                g.add((prop_uri, RDFS.domain, DMS.InterventionStrategy))
                g.add((prop_uri, RDFS.range, DMS.EmotionalState))
        else:
            g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        
        g.add((prop_uri, RDFS.label, Literal(mapped_property)))

def add_knowledge_to_ontology(g: Graph, claude_response: dict, row: dict):
    """Add extracted knowledge to the ontology while maintaining proper structure."""
    # Process each triple
    for triple in claude_response["extracted_knowledge"]:
        # Map classes and ensure they exist
        subject_class = map_to_existing_class(triple['subject']['ontology_class'])
        ensure_class_exists(g, subject_class)
        
        if triple['object'].get('ontology_class'):
            object_class = map_to_existing_class(triple['object']['ontology_class'])
            ensure_class_exists(g, object_class)
        
        # Map and ensure property exists
        property_name = map_to_existing_property(triple['predicate']['ontology_property'])
        ensure_property_exists(g, property_name)
        
        # Create subject node
        subject_uri = generate_uri(
            str(DMS),
            triple['subject']['value'],
            subject_class
        )
        subject_node = URIRef(subject_uri)
        
        # Only add type if it's not already in the ontology
        if (subject_node, RDF.type, DMS[subject_class]) not in g:
            g.add((subject_node, RDF.type, DMS[subject_class]))
        
        # Create object node
        if triple['object'].get('ontology_class'):
            object_uri = generate_uri(
                str(DMS),
                triple['object']['value'],
                object_class
            )
            object_node = URIRef(object_uri)
            if (object_node, RDF.type, DMS[object_class]) not in g:
                g.add((object_node, RDF.type, DMS[object_class]))
        else:
            object_node = Literal(triple['object']['value'])
        
        # Add the triple
        predicate = DMS[property_name]
        g.add((subject_node, predicate, object_node))
        
        # Add source
        g.add((subject_node, DCTERMS.source, Literal(row['Source'])))

def integrate_knowledge(input_csv: str, base_ontology: str, output_ttl: str, num_rows: int = None):
    """Integrate extracted knowledge into the existing ontology."""
    project_root = Path(__file__).parent.parent
    
    # Load existing ontology
    g = Graph()
    g.parse(project_root / base_ontology, format="turtle")
    print(f"\nLoaded base ontology with {len(g)} triples")
    
    processed_rows = 0
    successful_rows = 0
    
    with open(project_root / input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader, 1):
            if num_rows and i > num_rows:
                break
                
            print(f"\n{'='*80}")
            print(f"Processing row {i}")
            print(f"Section: {row['Section Title']}")
            print(f"Topic: {row['Topic']}")
            print(f"Knowledge Statement: {row['Knowledge Statement'][:100]}...")
            
            try:
                # Create prompt for Claude
                prompt = f"""As an expert in knowledge extraction and ontology engineering, analyze the following knowledge statement and extract structured knowledge as triples:

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

                # Query Claude API
                print("\nSending prompt to Claude API...")
                response = requests.post(
                    "https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/",
                    headers={"Content-Type": "application/json"},
                    json={"prompt": prompt},
                    timeout=30
                )
                response.raise_for_status()
                
                # Parse response
                claude_response = json.loads(response.json()["data"]["answer"])
                
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
                add_knowledge_to_ontology(g, claude_response, row)
                successful_rows += 1
                print("\nSuccessfully added to ontology")
                
            except Exception as e:
                print(f"\nError processing row {i}: {str(e)}")
                continue
            
            processed_rows += 1
    
    # Save enriched ontology
    output_path = project_root / output_ttl
    output_path.parent.mkdir(exist_ok=True)
    g.serialize(output_path, format="turtle")
    
    print(f"\n{'='*80}")
    print(f"Integration complete:")
    print(f"- Original triples: {len(g)}")
    print(f"- Rows processed: {processed_rows}")
    print(f"- Successful rows: {successful_rows}")
    print(f"- Failed rows: {processed_rows - successful_rows}")
    print(f"\nEnriched ontology saved to {output_path}")

if __name__ == "__main__":
    # Process rows 21-100
    print("Processing rows 21-100...")
    integrate_knowledge(
        "data/nudges_paper_cleaned.csv",
        "output/test_20rows_ontology.ttl",  # Use the previous output as base
        "output/test_100rows_ontology.ttl",
        num_rows=100
    ) 