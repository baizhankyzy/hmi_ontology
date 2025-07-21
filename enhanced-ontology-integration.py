#!/usr/bin/env python3
"""
Enhanced script to integrate knowledge statements into existing ontology file
Works with adaptive_hmi_merged_deduped.ttl
Uses Lambda endpoint for Claude API
"""

import csv
import json
import requests
from typing import List, Dict, Tuple, Set
import re
from datetime import datetime
import os
import sys
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD, DC

# Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

# Try to import config
try:
    from config import BASE_ONTOLOGY_PATH, CSV_FILE_PATH, OUTPUT_FILE_PATH
except ImportError:
    BASE_ONTOLOGY_PATH = None
    CSV_FILE_PATH = None
    OUTPUT_FILE_PATH = None

class EnhancedOntologyIntegrator:
    def __init__(self, base_ontology_file: str = "adaptive_hmi_merged_deduped.ttl"):
        """
        Initialize the integrator with base ontology file
        No API key needed - using Lambda endpoint directly
        """
        # Use the Lambda URL endpoint
        self.api_url = ""
        self.base_ontology_file = base_ontology_file
        
        # Define namespaces
        self.NS1 = Namespace("http://ontologydesignpatterns.org/ont/dul/DUL.owl#")
        self.NS2 = Namespace("http://example.org/ahmi#")
        self.PROV = Namespace("http://www.w3.org/ns/prov#")
        
        # Initialize RDF graph
        self.graph = Graph()
        self.graph.bind("ns1", self.NS1)
        self.graph.bind("ns2", self.NS2)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
        self.graph.bind("dc", DC)
        self.graph.bind("prov", self.PROV)
        
        # Track existing classes and properties
        self.existing_classes = set()
        self.existing_properties = set()
        self.new_classes = set()
        self.new_properties = set()
        self.knowledge_statements_added = 0

    def load_existing_ontology(self):
        """Load the existing ontology and extract classes and properties"""
        print(f"Loading existing ontology from {self.base_ontology_file}...")
        
        try:
            # Parse the existing ontology
            self.graph.parse(self.base_ontology_file, format="turtle")
            
            # Extract existing classes
            for s, p, o in self.graph.triples((None, RDF.type, OWL.Class)):
                if isinstance(s, URIRef):
                    class_name = str(s).split('#')[-1]
                    self.existing_classes.add(class_name)
            
            # Extract existing properties
            for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
                for s, p, o in self.graph.triples((None, RDF.type, prop_type)):
                    if isinstance(s, URIRef):
                        prop_name = str(s).split('#')[-1]
                        self.existing_properties.add(prop_name)
            
            print(f"  Found {len(self.existing_classes)} existing classes")
            print(f"  Found {len(self.existing_properties)} existing properties")
            
            # Add metadata properties if they don't exist
            self._add_metadata_properties()
            
        except Exception as e:
            print(f"Error loading ontology: {e}")
            print("Starting with empty graph...")
            self._initialize_base_ontology()

    def _initialize_base_ontology(self):
        """Initialize with basic ontology structure if file doesn't exist"""
        ontology_uri = URIRef("http://example.org/adaptive-hmi")
        self.graph.add((ontology_uri, RDF.type, OWL.Ontology))
        self.graph.add((ontology_uri, RDFS.label, 
                       Literal("Adaptive HMI Ontology - Enhanced", lang="en")))
        self._add_metadata_properties()

    def _add_metadata_properties(self):
        """Add properties for knowledge statement metadata"""
        # Check if metadata properties exist
        if "extractedFromSection" not in self.existing_properties:
            prop = self.NS2.extractedFromSection
            self.graph.add((prop, RDF.type, OWL.DatatypeProperty))
            self.graph.add((prop, RDFS.label, Literal("extracted from section", lang="en")))
            self.graph.add((prop, RDFS.range, XSD.string))
            self.existing_properties.add("extractedFromSection")
        
        if "hasTopic" not in self.existing_properties:
            prop = self.NS2.hasTopic
            self.graph.add((prop, RDF.type, OWL.DatatypeProperty))
            self.graph.add((prop, RDFS.label, Literal("has topic", lang="en")))
            self.graph.add((prop, RDFS.range, XSD.string))
            self.existing_properties.add("hasTopic")
        
        if "knowledgeSource" not in self.existing_properties:
            prop = self.NS2.knowledgeSource
            self.graph.add((prop, RDF.type, OWL.DatatypeProperty))
            self.graph.add((prop, RDFS.label, Literal("knowledge source", lang="en")))
            self.graph.add((prop, RDFS.range, XSD.string))
            self.existing_properties.add("knowledgeSource")

    def read_csv(self, filename: str) -> List[Dict[str, str]]:
        """Read CSV file and extract knowledge statements with metadata"""
        statements = []
        
        with open(filename, 'r', encoding='utf-8') as file:
            # Skip the first line which contains the title
            next(file)
            
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                if row.get('Knowledge Statement') and row['Knowledge Statement'].strip():
                    statements.append({
                        'statement': row['Knowledge Statement'].strip(),
                        'source': row.get('Source', '').strip(),
                        'section': row.get('Section Title', '').strip(),
                        'topic': row.get('Topic', '').strip()
                    })
        
        return statements

    def call_claude_api(self, prompt: str) -> str:
        """Call Claude API via Lambda endpoint - no API key needed"""
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [{
                "role": "user",
                "content": prompt
            }]
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                # Handle different response formats
                if 'content' in response_data:
                    if isinstance(response_data['content'], list):
                        return response_data['content'][0]['text']
                    else:
                        return response_data['content']
                elif 'completion' in response_data:
                    return response_data['completion']
                else:
                    return json.dumps(response_data)
            else:
                raise Exception(f"API call failed: {response.status_code} - {response.text}")
        except requests.exceptions.Timeout:
            raise Exception("API request timed out")
        except Exception as e:
            raise Exception(f"API call error: {str(e)}")

    def extract_spo_triple(self, statement: str) -> Dict[str, any]:
        """Extract subject-predicate-object triple using Claude API"""
        
        # List existing classes for context
        existing_classes_list = list(self.existing_classes)[:20]  # Limit for prompt
        
        prompt = f"""Given a knowledge statement about adaptive HMI and driving, extract the subject-predicate-object (SPO) triple.

Knowledge statement: "{statement}"

Existing ontology classes (use these when applicable):
{', '.join(existing_classes_list)}
(Key classes: HMI, EmotionalState, CognitiveState, Driver, AdaptiveHMI, Context, EnvironmentFactor)

Return ONLY a JSON object with this exact structure:
{{
    "subject": "the main entity/concept",
    "predicate": "the relationship",
    "object": "what the subject relates to",
    "subject_type": "class",
    "object_type": "class",
    "predicate_type": "objectProperty"
}}

Rules:
1. Use existing class names when possible (HMI, Driver, Context, etc.)
2. For predicates, use clear action words (adaptsTo, monitors, influences, etc.)
3. Keep concept names concise and meaningful
4. Use camelCase for multi-word concepts

Examples:
Statement: "An HMI should have the ability to adapt to different context"
Response:
{{
    "subject": "HMI",
    "predicate": "shouldAdaptTo",
    "object": "Context",
    "subject_type": "class",
    "object_type": "class",
    "predicate_type": "objectProperty"
}}

Statement: "The system monitors driver emotional state"
Response:
{{
    "subject": "System",
    "predicate": "monitors",
    "object": "EmotionalState",
    "subject_type": "class",
    "object_type": "class",
    "predicate_type": "objectProperty"
}}"""

        try:
            response = self.call_claude_api(prompt)
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Try to parse the entire response as JSON
                return json.loads(response)
        except Exception as e:
            print(f"    Error extracting SPO: {e}")
            # Improved fallback extraction
            return self._improved_fallback_extraction(statement)

    def _improved_fallback_extraction(self, statement: str) -> Dict[str, any]:
        """Improved fallback extraction when API fails"""
        statement_lower = statement.lower()
        
        # Define extraction patterns
        patterns = {
            # HMI patterns
            r"hmi.*(should|must|can|will).*adapt": {
                "subject": "HMI", "predicate": "shouldAdaptTo", "object": "Context"
            },
            r"hmi.*(monitor|detect|sense)": {
                "subject": "HMI", "predicate": "monitors", "object": "DriverState"
            },
            r"system.*(monitor|detect|track).*emotion": {
                "subject": "System", "predicate": "monitors", "object": "EmotionalState"
            },
            r"driver.*(emotion|stress|frustration)": {
                "subject": "Driver", "predicate": "experiences", "object": "EmotionalState"
            },
            r"emotion.*influence.*reaction": {
                "subject": "EmotionalState", "predicate": "influences", "object": "ReactionTime"
            },
            r"nudge.*help.*decision": {
                "subject": "Nudge", "predicate": "facilitates", "object": "DecisionMaking"
            },
            r"heuristic.*used.*shortcut": {
                "subject": "Heuristic", "predicate": "isUsedAs", "object": "DecisionShortcut"
            },
        }
        
        # Try to match patterns
        for pattern, spo in patterns.items():
            if re.search(pattern, statement_lower):
                return {
                    "subject": spo["subject"],
                    "predicate": spo["predicate"],
                    "object": spo["object"],
                    "subject_type": "class",
                    "object_type": "class",
                    "predicate_type": "objectProperty"
                }
        
        # Generic fallback based on keywords
        if "hmi" in statement_lower:
            subject = "HMI"
        elif "driver" in statement_lower:
            subject = "Driver"
        elif "system" in statement_lower:
            subject = "System"
        else:
            subject = "Component"
        
        if "adapt" in statement_lower:
            predicate = "adaptsTo"
            obj = "Context"
        elif "monitor" in statement_lower or "detect" in statement_lower:
            predicate = "monitors"
            obj = "State"
        elif "emotion" in statement_lower:
            predicate = "relatesTo"
            obj = "EmotionalState"
        else:
            predicate = "relatesTo"
            obj = "Concept"
        
        return {
            "subject": subject,
            "predicate": predicate,
            "object": obj,
            "subject_type": "class",
            "object_type": "class",
            "predicate_type": "objectProperty"
        }

    def add_spo_to_graph(self, spo: Dict, metadata: Dict):
        """Add SPO triple to RDF graph with individuals and full provenance"""
        
        subject = spo['subject']
        predicate = spo['predicate']
        obj = spo['object']
        
        # Create URIs
        subject_uri = self.NS2[subject]
        predicate_uri = self.NS2[predicate]
        object_uri = self.NS2[obj] if spo['object_type'] == 'class' else Literal(obj)
        
        # Create unique ID for this knowledge statement
        stmt_id = f"stmt_{abs(hash(metadata['statement'])) % 1000000}"
        stmt_uri = self.NS2[stmt_id]
        
        # Create a KnowledgeStatement class if it doesn't exist
        ks_class = self.NS2.KnowledgeStatement
        if "KnowledgeStatement" not in self.existing_classes:
            self.graph.add((ks_class, RDF.type, OWL.Class))
            self.graph.add((ks_class, RDFS.label, Literal("Knowledge Statement", lang="en")))
            self.graph.add((ks_class, RDFS.comment, 
                           Literal("A statement extracted from source documents", lang="en")))
            self.existing_classes.add("KnowledgeStatement")
        
        # Create individual for this knowledge statement
        self.graph.add((stmt_uri, RDF.type, ks_class))
        self.graph.add((stmt_uri, RDF.type, self.PROV.Entity))
        self.graph.add((stmt_uri, RDFS.label, 
                       Literal(f"Statement: {metadata['statement'][:50]}...", lang="en")))
        
        # Add provenance information
        self.graph.add((stmt_uri, DC.source, Literal(metadata['source'])))
        self.graph.add((stmt_uri, DC.description, Literal(metadata['statement'])))
        self.graph.add((stmt_uri, self.NS2.extractedFromSection, Literal(metadata['section'])))
        self.graph.add((stmt_uri, self.NS2.hasTopic, Literal(metadata['topic'])))
        self.graph.add((stmt_uri, self.PROV.generatedAtTime, 
                       Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
        
        # Add SPO structure to the statement individual
        self.graph.add((stmt_uri, self.NS2.hasSubject, subject_uri))
        self.graph.add((stmt_uri, self.NS2.hasPredicate, predicate_uri))
        self.graph.add((stmt_uri, self.NS2.hasObject, object_uri))
        
        # Create properties for linking if they don't exist
        if "hasSubject" not in self.existing_properties:
            hs_uri = self.NS2.hasSubject
            self.graph.add((hs_uri, RDF.type, OWL.ObjectProperty))
            self.graph.add((hs_uri, RDFS.label, Literal("has subject", lang="en")))
            self.existing_properties.add("hasSubject")
        
        if "hasPredicate" not in self.existing_properties:
            hp_uri = self.NS2.hasPredicate
            self.graph.add((hp_uri, RDF.type, OWL.ObjectProperty))
            self.graph.add((hp_uri, RDFS.label, Literal("has predicate", lang="en")))
            self.existing_properties.add("hasPredicate")
        
        if "hasObject" not in self.existing_properties:
            ho_uri = self.NS2.hasObject
            self.graph.add((ho_uri, RDF.type, OWL.ObjectProperty))
            self.graph.add((ho_uri, RDFS.label, Literal("has object", lang="en")))
            self.existing_properties.add("hasObject")
        
        # Add reification for the triple
        self.graph.add((stmt_uri, RDF.subject, subject_uri))
        self.graph.add((stmt_uri, RDF.predicate, predicate_uri))
        self.graph.add((stmt_uri, RDF.object, object_uri))
        
        # Add classes if new
        if spo['subject_type'] == 'class' and subject not in self.existing_classes:
            self.graph.add((subject_uri, RDF.type, OWL.Class))
            self.graph.add((subject_uri, RDFS.label, Literal(self.to_label(subject), lang="en")))
            self.graph.add((subject_uri, RDFS.comment, 
                           Literal(f"Extracted from: {metadata['statement']}", lang="en")))
            self.graph.add((subject_uri, self.NS2.knowledgeSource, Literal(metadata['source'])))
            
            # Add appropriate subclass relationships
            if subject.lower() == "hmi":
                self.graph.add((subject_uri, RDFS.subClassOf, self.NS2.HMISystem))
            elif 'emotion' in subject.lower() or subject in ['Stress', 'Frustration', 'Anger']:
                self.graph.add((subject_uri, RDFS.subClassOf, self.NS2.EmotionalState))
            elif 'cognitive' in subject.lower():
                self.graph.add((subject_uri, RDFS.subClassOf, self.NS2.CognitiveState))
            elif subject.lower() in ['nudge', 'nudging']:
                self.graph.add((subject_uri, RDFS.subClassOf, self.NS2.InterventionStrategy))
            
            self.new_classes.add(subject)
        
        if spo['object_type'] == 'class' and obj not in self.existing_classes:
            self.graph.add((object_uri, RDF.type, OWL.Class))
            self.graph.add((object_uri, RDFS.label, Literal(self.to_label(obj), lang="en")))
            self.graph.add((object_uri, RDFS.comment, 
                           Literal(f"Extracted from: {metadata['statement']}", lang="en")))
            self.graph.add((object_uri, self.NS2.knowledgeSource, Literal(metadata['source'])))
            self.new_classes.add(obj)
        
        # Add property if new
        if predicate not in self.existing_properties:
            if spo['predicate_type'] == 'objectProperty':
                self.graph.add((predicate_uri, RDF.type, OWL.ObjectProperty))
                self.graph.add((predicate_uri, RDFS.domain, subject_uri))
                self.graph.add((predicate_uri, RDFS.range, object_uri))
            else:
                self.graph.add((predicate_uri, RDF.type, OWL.DatatypeProperty))
                self.graph.add((predicate_uri, RDFS.domain, subject_uri))
                self.graph.add((predicate_uri, RDFS.range, XSD.string))
            
            self.graph.add((predicate_uri, RDFS.label, Literal(self.to_label(predicate), lang="en")))
            self.graph.add((predicate_uri, RDFS.comment, 
                           Literal(f"Extracted from: {metadata['statement']}", lang="en")))
            self.graph.add((predicate_uri, self.NS2.knowledgeSource, Literal(metadata['source'])))
            self.new_properties.add(predicate)
        
        # Add the actual triple (creates the relationship)
        if spo['predicate_type'] == 'objectProperty':
            self.graph.add((subject_uri, predicate_uri, object_uri))
        
        # Create an individual example for this relationship
        example_id = f"example_{stmt_id}"
        example_uri = self.NS2[example_id]
        self.graph.add((example_uri, RDF.type, subject_uri))
        self.graph.add((example_uri, RDFS.label, 
                       Literal(f"{subject} instance from statement {stmt_id}", lang="en")))
        self.graph.add((example_uri, self.NS2.derivedFromStatement, stmt_uri))
        
        self.knowledge_statements_added += 1

    def to_label(self, camel_case: str) -> str:
        """Convert camelCase to human-readable label"""
        label = re.sub(r'([a-z])([A-Z])', r'\1 \2', camel_case)
        return label[0].upper() + label[1:] if label else ""

    def integrate_knowledge_statements(self, csv_file: str, output_file: str):
        """Main integration process"""
        # Load existing ontology
        self.load_existing_ontology()
        
        # Read CSV
        print(f"\nReading CSV file: {csv_file}")
        statements = self.read_csv(csv_file)
        print(f"Found {len(statements)} knowledge statements")
        
        # Process each statement
        for i, stmt_data in enumerate(statements):
            print(f"\nProcessing {i+1}/{len(statements)}: {stmt_data['statement'][:60]}...")
            
            try:
                # Extract SPO triple
                spo = self.extract_spo_triple(stmt_data['statement'])
                print(f"  → {spo['subject']} - {spo['predicate']} - {spo['object']}")
                
                # Add to graph
                self.add_spo_to_graph(spo, stmt_data)
                
            except Exception as e:
                print(f"  → Error: {e}")
                continue
        
        # Save enhanced ontology
        print(f"\nSaving enhanced ontology to {output_file}")
        self.graph.serialize(destination=output_file, format='turtle')
        
        # Summary
        print(f"\n✓ Integration complete!")
        print(f"✓ Added {self.knowledge_statements_added} knowledge statements")
        print(f"✓ Added {len(self.new_classes)} new classes")
        print(f"✓ Added {len(self.new_properties)} new properties")
        print(f"✓ Total classes: {len(self.existing_classes) + len(self.new_classes)}")
        print(f"✓ Total properties: {len(self.existing_properties) + len(self.new_properties)}")

def main():
    # Configuration - NO API KEY NEEDED!
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Go up one level from src/
    
    # Set file paths based on actual directory structure
    BASE_ONTOLOGY = os.path.join(project_root, 'data', 'output', 'adaptive_hmi_merged_deduped.ttl')
    CSV_FILE = os.path.join(project_root, 'data', 'nudges_paper_emotions_only.csv')
    OUTPUT_FILE = os.path.join(project_root, 'data', 'output', 'adaptive_hmi_enriched.ttl')
    
    # Check if files exist
    if not os.path.exists(BASE_ONTOLOGY):
        print(f"Warning: Base ontology not found at {BASE_ONTOLOGY}")
        print("Will create a new ontology")
    
    if not os.path.exists(CSV_FILE):
        # Try alternate locations
        alt_csv_paths = [
            os.path.join(project_root, 'data', 'nudges_paper_emotions_only.csv'),
            os.path.join(script_dir, 'nudges_paper_emotions_only.csv'),
            'nudges_paper_emotions_only.csv'
        ]
        
        for alt_path in alt_csv_paths:
            if os.path.exists(alt_path):
                CSV_FILE = alt_path
                print(f"Found CSV at: {CSV_FILE}")
                break
        else:
            print(f"Error: CSV file not found. Tried:")
            print(f"  - {CSV_FILE}")
            for path in alt_csv_paths:
                print(f"  - {path}")
            return
    print(f"Using files:")
    print(f"  Base ontology: {BASE_ONTOLOGY}")
    print(f"  CSV file: {CSV_FILE}")
    print(f"  Output file: {OUTPUT_FILE}")
    print(f"  Lambda endpoint: https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/")
    print()
    
    # Create integrator and run - no API key needed!
    integrator = EnhancedOntologyIntegrator(BASE_ONTOLOGY)
    integrator.integrate_knowledge_statements(CSV_FILE, OUTPUT_FILE)
    
    print("\nExample SPARQL queries to explore the enriched ontology:")
    print("-" * 60)
    print("""
# 1. Get all knowledge statements with their SPO structure:
PREFIX ns2: <http://example.org/ahmi#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT ?statement ?source ?subject ?predicate ?object
WHERE {
    ?stmt a ns2:KnowledgeStatement ;
          dc:description ?statement ;
          dc:source ?source ;
          ns2:hasSubject ?subject ;
          ns2:hasPredicate ?predicate ;
          ns2:hasObject ?object .
}
LIMIT 10

# 2. Find all statements about HMI adaptation:
PREFIX ns2: <http://example.org/ahmi#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT ?statement ?predicate ?object
WHERE {
    ?stmt a ns2:KnowledgeStatement ;
          dc:description ?statement ;
          ns2:hasSubject ns2:HMI ;
          ns2:hasPredicate ?predicate ;
          ns2:hasObject ?object .
    FILTER(CONTAINS(STR(?predicate), "adapt"))
}

# 3. Get all relationships extracted from a specific source:
PREFIX ns2: <http://example.org/ahmi#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?subject ?predicate ?object ?statement
WHERE {
    ?stmt a ns2:KnowledgeStatement ;
          dc:source "Nudges-Based Design Method for Adaptive HMI to Improve Driving Safety.pdf" ;
          dc:description ?statement ;
          ns2:hasSubject ?subject ;
          ns2:hasPredicate ?predicate ;
          ns2:hasObject ?object .
}
""")

if __name__ == "__main__":
    main()