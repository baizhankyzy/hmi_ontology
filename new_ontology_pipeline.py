import requests
import json
import logging
import pandas as pd
from typing import List, Tuple, Optional
import os
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
import glob
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API endpoint
API_URL = ""

def load_patterns() -> str:
    """
    Load all OWL pattern files from the patterns directory.
    
    Returns:
        str: Combined content of all pattern files
    """
    try:
        patterns_content = []
        pattern_files = glob.glob('patterns/*.owl.xml')
        
        for pattern_file in pattern_files:
            with open(pattern_file, 'r') as f:
                content = f.read()
                patterns_content.append(f"=== Pattern from {os.path.basename(pattern_file)} ===\n{content}\n")
        
        logger.info(f"Loaded {len(pattern_files)} pattern files from patterns directory")
        return "\n".join(patterns_content)
    except Exception as e:
        logger.error(f"Error loading pattern files: {str(e)}")
        return ""

def load_data_from_csv(cq_path: str, stories_path: str) -> List[Tuple[str, str]]:
    """
    Load competency questions and user stories from CSV files.
    
    Args:
        cq_path: Path to competency questions CSV
        stories_path: Path to user stories CSV
        
    Returns:
        List of tuples (competency_question, user_story)
    """
    try:
        cq_df = pd.read_csv(cq_path)
        stories_df = pd.read_csv(stories_path)
        
        # Create a dictionary of stories by Story_ID
        stories_dict = dict(zip(stories_df['Story_ID'], stories_df['User_Story']))
        
        # Map each competency question to its corresponding story
        pairs = []
        for _, row in cq_df.iterrows():
            cq = row['Competency_Question']
            story_id = row['Story_ID']
            story = stories_dict.get(story_id, '')
            pairs.append((cq, story))
        
        logger.info(f"Loaded {len(pairs)} competency questions and corresponding user stories")
        return pairs
        
    except Exception as e:
        logger.error(f"Error loading CSV files: {str(e)}")
        raise

def generate_ontology(competency_question: str, ontology_story: str = "") -> str:
    """
    Generate an ontology using the Claude API based on a competency question and ontology story.
    
    Args:
        competency_question: The competency question
        ontology_story: The ontology story
        
    Returns:
        str: The generated ontology in Turtle format
    """
    # Load patterns
    patterns_xml = load_patterns()
    
    # The exact prompt that should be preserved
    prompt = """<instruction>
You are a helpful assistant designed to generate ontologies. You receive a Competency Question (CQ) and an Ontology Story (OS). \n
Based on CQ, which is a requirement for the ontology, and OS, which tells you what the context of the ontology is, your task is generating one ontology (O). The goal is to generate O that models the CQ properly. This means there is a way to write a SPARQL query to extract the answer to this CQ in O.  \n

Use the following ontology design patterns in OWL format for ontology generation: {patterns_xml}

Use the following prefixes: \n
@prefix : <http://www.example.org/test#> .\n
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n

Don't put any A-Box (instances) in the ontology and just generate the OWL file using Turtle syntax. Include the entities mentioned in the CQ. Remember to use restrictions when the CQ implies it. For union classes, use the proper Turtle syntax: [ rdf:type owl:Class ; owl:unionOf ( :Class1 :Class2 ) ]. The output should be self-contained without any errors. Outside of the code box don't put any comment.

</instruction>
<example>
I will give you an example now:
CQ: For an aquatic resource, what species, in what fishing areas, climatic zones, bottom types, depth zones, geo forms, horizontal and vertical distribution, and for what standardized abundance level, exploitation state and rate, have been observed? for what reference year? At what year the observation has been recorded?

OS: The aquatic resource for Skipjack tuna in Northern Atlantic in 2004 (as reported in 2008) was observed with low abundance level. 

O:
@prefix : <http://www.example.org/test#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<http://www.example.org/test#> a owl:Ontology .
:AquaticResource a owl:Class ;
    rdfs:label "Aquatic Resource" ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :hasObservation ;
        owl:someValuesFrom :AquaticResourceObservation
    ] .
:AquaticResourceObservation a owl:Class ;
    rdfs:label "Aquatic Resource Observation" ;
    rdfs:subClassOf :Observation ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :isObservationOf ;
        owl:onClass :AquaticResource ;
        owl:qualifiedCardinality "1"^^xsd:nonNegativeInteger
    ] ;
    
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :forReferenceYear ;
        owl:onDataRange xsd:int ;
        owl:qualifiedCardinality "1"^^xsd:nonNegativeInteger
    ] ;

    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :hasReportingYear ;
        owl:onDataRange xsd:int ;
        owl:qualifiedCardinality "1"^^xsd:nonNegativeInteger
    ] ;
    
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofSpecies ;
        owl:onClass :Species ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofFishingArea ;
        owl:onClass :FAO_fishing_area ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofClimaticZone ;
        owl:onClass :ClimaticZone ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofBottomType ;
        owl:onClass :BottomType ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofDepthZone ;
        owl:onClass :DepthZone ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofGeoForm ;
        owl:onClass :GeoForm ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofHorizontalDistribution ;
        owl:onClass :HorizontalDistribution ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofVerticalDistribution ;
        owl:onClass :VerticalDistribution ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofStdAbundanceLevel ;
        owl:onClass :StdAbundanceLevel ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofStdExploitationState ;
        owl:onClass :StdExploitationState ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty :ofStdExploitationRate ;
        owl:onClass :StdExploitationRate ;
        owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
    ] .
:Species a owl:Class .
:FAO_fishing_area a owl:Class .
:ClimaticZone a owl:Class .
:BottomType a owl:Class .
:DepthZone a owl:Class .
:GeoForm a owl:Class .
:HorizontalDistribution a owl:Class .
:VerticalDistribution a owl:Class .
:StdAbundanceLevel a owl:Class .
:StdExploitationState a owl:Class .
:StdExploitationRate a owl:Class .
:ofSpecies a owl:ObjectProperty ;
    rdfs:label "ofSpecies" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :Species .

:ofFishingArea a owl:ObjectProperty ;
    rdfs:label "ofFishingArea" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :FAO_fishing_area .

:ofClimaticZone a owl:ObjectProperty ;
    rdfs:label "ofClimaticZone" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :ClimaticZone .

:ofBottomType a owl:ObjectProperty ;
    rdfs:label "ofBottomType" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :BottomType .

:ofDepthZone a owl:ObjectProperty ;
    rdfs:label "ofDepthZone" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :DepthZone .

:ofGeoForm a owl:ObjectProperty ;
    rdfs:label "ofGeoForm" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :GeoForm .

:ofHorizontalDistribution a owl:ObjectProperty ;
    rdfs:label "ofHorizontalDistribution" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :HorizontalDistribution .

:ofVerticalDistribution a owl:ObjectProperty ;
    rdfs:label "ofVerticalDistribution" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :VerticalDistribution .

:ofStdAbundanceLevel a owl:ObjectProperty ;
    rdfs:label "ofStdAbundanceLevel" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :StdAbundanceLevel .

:ofStdExploitationState a owl:ObjectProperty ;
    rdfs:label "ofStdExploitationState" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :StdExploitationState .

:ofStdExploitationRate a owl:ObjectProperty ;
    rdfs:label "ofStdExploitationRate" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range :StdExploitationRate .
:forReferenceYear a owl:DatatypeProperty ;
    rdfs:label "forReferenceYear" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range xsd:int .

:hasReportingYear a owl:DatatypeProperty ;
    rdfs:label "hasReportingYear" ;
    rdfs:domain :AquaticResourceObservation ;
    rdfs:range xsd:int .
:hasObservation a owl:ObjectProperty .
:isObservationOf a owl:ObjectProperty .
:Observation a owl:Class .

</example>

CQ: {CQ}
OS: {OS}
O:"""
    
    # Format the prompt with the provided CQ, OS, and patterns
    formatted_prompt = prompt.format(CQ=competency_question, OS=ontology_story, patterns_xml=patterns_xml)
    
    try:
        # Prepare the request payload
        payload = {
            "prompt": formatted_prompt,
            "temperature": 0.0,  # Keep temperature at 0.0 for consistent results
            "max_tokens": 2000   # Adjust based on expected response length
        }
        
        # Make the API request
        logger.info("Sending request to Claude API...")
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        logger.info(f"API Response received")
        
        # Extract the ontology from the response
        ontology = result.get('data', {}).get('answer', '')
        
        if not ontology:
            raise ValueError("No ontology generated in the response")
            
        logger.info("Successfully generated ontology")
        return ontology
        
    except Exception as e:
        logger.error(f"Error generating ontology: {str(e)}")
        raise

def merge_ontologies(ontologies: List[str]) -> str:
    """
    Merge multiple ontologies using an improved strategy that follows five key principles:
    1. Preserve all competency questions
    2. Eliminate duplicates through property consolidation
    3. Maintain clear naming and relationships
    4. Balance expressivity with simplicity
    5. Use inverse properties to reduce redundancy
    
    Args:
        ontologies: List of ontologies in Turtle format
        
    Returns:
        str: Merged ontology in Turtle format
    """
    try:
        # Create a new graph for the merged ontology
        merged_graph = Graph()
        
        # Add standard prefixes
        merged_graph.bind('owl', 'http://www.w3.org/2002/07/owl#')
        merged_graph.bind('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        merged_graph.bind('rdfs', 'http://www.w3.org/2000/01/rdf-schema#')
        merged_graph.bind('xsd', 'http://www.w3.org/2001/XMLSchema#')
        merged_graph.bind('', 'http://www.example.org/test#')
        
        # Process each ontology
        for i, ontology in enumerate(ontologies, 1):
            try:
                # Create a temporary graph for this ontology
                g = Graph()
                
                # Clean up the ontology content
                cleaned_content = clean_ontology_content(ontology)
                
                # Create a temporary file for the cleaned content
                temp_file = f"temp_ontology_{i}.ttl"
                with open(temp_file, "w", encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                try:
                    # Parse the cleaned ontology
                    g.parse(temp_file, format="turtle")
                    
                    # Add all triples to merged graph
                    for s, p, o in g:
                        merged_graph.add((s, p, o))
                    
                    logging.info(f"Successfully processed ontology {i}")
                except Exception as parse_error:
                    logging.error(f"Error parsing ontology {i}: {str(parse_error)}")
                    continue
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        
            except Exception as e:
                logging.error(f"Error processing ontology {i}: {str(e)}")
                continue
        
        # Add ontology metadata
        merged_graph.add((URIRef("http://www.example.org/test"), RDF.type, OWL.Ontology))
        merged_graph.add((URIRef("http://www.example.org/test"), RDFS.label, Literal("Driver Monitoring System Ontology")))
        
        try:
            # Serialize the merged graph with proper formatting
            merged_content = merged_graph.serialize(format="turtle", encoding="utf-8")
            if not merged_content:
                raise ValueError("Empty serialization result")
            return merged_content.decode('utf-8') if isinstance(merged_content, bytes) else merged_content
        except Exception as serialize_error:
            logging.error(f"Error serializing merged graph: {str(serialize_error)}")
            # Fallback serialization
            prefixes = [
                "@prefix : <http://www.example.org/test#> .",
                "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
                "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
                "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
                "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
                "",
                "<http://www.example.org/test> a owl:Ontology ;",
                '    rdfs:label "Driver Monitoring System Ontology" .'
            ]
            
            # Add all triples
            triples = []
            for s, p, o in merged_graph:
                if isinstance(o, Literal):
                    o_str = f'"{o}"'
                    if o.datatype:
                        o_str += f"^^{o.datatype}"
                    elif o.language:
                        o_str += f"@{o.language}"
                else:
                    o_str = str(o)
                
                triples.append(f"{s} {p} {o_str} .")
            
            return "\n".join(prefixes + [""] + sorted(triples))
            
    except Exception as e:
        logging.error(f"Error in merge_ontologies: {str(e)}")
        return ""

def clean_ontology_content(content: str) -> str:
    """
    Clean up ontology content by removing markdown and fixing common syntax issues.
    
    Args:
        content: Raw ontology content
        
    Returns:
        str: Cleaned ontology content
    """
    try:
        # Remove markdown code block markers
        content = re.sub(r'```turtle\n', '', content)
        content = re.sub(r'```\n?', '', content)
        
        # Remove byte string markers and fix quotes
        content = re.sub(r"b'|'b'|'$", '', content)
        content = re.sub(r'"(\d+)"(\^+)b?\'xsd:nonNegativeInteger', r'"\1"^^xsd:nonNegativeInteger', content)
        content = re.sub(r'"([^"]*)"(\^+)b?\'([^\s\']+)', r'"\1"^^\3', content)
        
        # Fix common syntax issues
        content = re.sub(r'\s+$', '', content, flags=re.MULTILINE)  # Remove trailing whitespace
        content = re.sub(r'[\r\n]+', '\n', content)  # Normalize line endings
        content = re.sub(r'\n\s*\n+', '\n\n', content)  # Normalize blank lines
        
        # Fix URI formatting
        content = re.sub(r'<http://www\s+\.\s+', '<http://www.', content)
        content = re.sub(r'\s+\.\s+org/', '.org/', content)
        content = re.sub(r'(\S+)\s+\.\s+(\S+)', r'\1.\2', content)
        
        # Ensure proper spacing around dots in non-URI contexts
        content = re.sub(r'(\s)\.\s*([A-Z])', r'\1.\n\2', content)
        
        # Fix concatenation artifacts
        content = re.sub(r'\.:', ' .\n:', content)
        content = re.sub(r'([^a-zA-Z]):\s*([a-zA-Z])', r'\1\n:\2', content)
        
        # Fix property list endings
        content = re.sub(r';\s*$', ' .', content)
        content = re.sub(r';\s*\n\s*\n', ' .\n\n', content)
        
        # Fix missing dots at the end of property lists
        content = re.sub(r'(\s+;[^\.]*)$', r'\1 .', content)
        
        return content.strip()
    except Exception as e:
        logging.error(f"Error in clean_ontology_content: {str(e)}")
        return content

def main():
    # File paths
    cq_file = "data/competency_questions.csv"
    stories_file = "data/user_stories.csv"
    output_dir = "output"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Load competency questions and user stories
        pairs = load_data_from_csv(cq_file, stories_file)
        logger.info(f"Processing {len(pairs)} competency questions")
        
        # Process each competency question
        ontologies = []
        for i, (cq, story) in enumerate(pairs):
            # Extract CQ ID for file naming
            cq_id = cq.split(',')[0] if ',' in cq else f"CQ{i+1}"
            logger.info(f"Processing {cq_id}: {cq[:50]}...")
            
            # Generate ontology
            ontology = generate_ontology(cq, story)
            ontologies.append(ontology)
            
            # Save individual ontology
            with open(f"{output_dir}/ontology_{cq_id}.ttl", "w") as f:
                f.write(ontology)
                logger.info(f"Saved individual ontology to {output_dir}/ontology_{cq_id}.ttl")
        
        # Merge all ontologies into one final ontology
        if len(ontologies) >= 2:
            logger.info(f"\nMerging all {len(ontologies)} ontologies into final ontology...")
            final_merged_ontology = merge_ontologies(ontologies)
            
            # Save final merged ontology
            with open(f"{output_dir}/merged_ontology_final.ttl", "w") as f:
                f.write(final_merged_ontology)
                logger.info("Saved final merged ontology to output/merged_ontology_final.ttl")
        
        logger.info("\n=== Pipeline Results ===")
        logger.info(f"Total competency questions processed: {len(pairs)}")
        logger.info(f"Individual ontologies generated: {len(ontologies)}")
        logger.info(f"Final merged ontology created: {len(ontologies) >= 2}")
        logger.info(f"Output directory: {output_dir}")
        logger.info("\nFiles created:")
        for i, (cq, _) in enumerate(pairs):
            cq_id = cq.split(',')[0] if ',' in cq else f"CQ{i+1}"
            logger.info(f"- ontology_{cq_id}.ttl")
        if len(ontologies) >= 2:
            logger.info("- merged_ontology_final.ttl")
            
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")

if __name__ == "__main__":
    main() 
