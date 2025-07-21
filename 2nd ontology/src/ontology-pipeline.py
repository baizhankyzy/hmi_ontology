"""
Main pipeline for generating and merging ontologies with strategic approach.
"""
import os
import json
import pandas as pd
import logging
from typing import List, Tuple, Dict, Optional
import argparse
from datetime import datetime
import requests
import time
import importlib.util

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_patterns_txt(patterns_path: str) -> List[Tuple[str, str]]:
    """Parse patterns from the patterns.txt file and convert all to XML format."""
    logger = logging.getLogger(__name__)
    patterns = []
    
    try:
        if not os.path.exists(patterns_path):
            logger.warning(f"Patterns file not found: {patterns_path}")
            return patterns
            
        with open(patterns_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split by pattern delimiter
        pattern_sections = content.split("================================================================================")
        
        # Process each pattern section
        for section in pattern_sections:
            section = section.strip()
            if not section:
                continue
                
            # Extract pattern name and content
            lines = section.split('\n')
            pattern_name = None
            xml_content = []
            in_pattern = False
            in_xml = False
            in_turtle = False
            current_xml_block = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith("Pattern:"):
                    pattern_name = line.replace("Pattern:", "").strip()
                    # Remove file extension from pattern name
                    if pattern_name.endswith('.owl.xml'):
                        pattern_name = pattern_name[:-8]
                    elif pattern_name.endswith('.xml'):
                        pattern_name = pattern_name[:-4]
                    elif pattern_name.endswith('.txt'):
                        pattern_name = pattern_name[:-4]
                    in_pattern = True
                    continue
                
                if in_pattern:
                    # Handle XML content
                    if line.startswith('<?xml') or line.startswith('<!DOCTYPE'):
                        in_xml = True
                        current_xml_block = [line]
                        continue
                    
                    if in_xml:
                        current_xml_block.append(line)
                        if line.startswith('</rdf:RDF>'):
                            xml_content.extend(current_xml_block)
                            in_xml = False
                        continue
                    
                    # Handle Turtle content
                    if line.startswith('#') and ('Pattern Example' in line or 'Combined Pattern' in line):
                        in_turtle = True
                        # Start a new XML block for this pattern
                        current_xml_block = [
                            '<?xml version="1.0"?>',
                            '<rdf:RDF xmlns="http://www.example.org/test#"',
                            '     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"',
                            '     xmlns:owl="http://www.w3.org/2002/07/owl#"',
                            '     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"',
                            '     xmlns:xsd="http://www.w3.org/2001/XMLSchema#"',
                            '     xmlns:dct="http://purl.org/dc/terms/"',
                            '     xmlns:ssn="http://www.w3.org/ns/ssn/"',
                            '     xmlns:sosa="http://www.w3.org/ns/sosa/"',
                            '     xmlns:agentrole="http://www.ontologydesignpatterns.org/cp/owl/agentrole.owl#"',
                            '     xmlns:situation="http://www.ontologydesignpatterns.org/cp/owl/situation.owl#"',
                            '     xmlns:observation="http://www.ontologydesignpatterns.org/cp/owl/observation.owl#"',
                            '     xmlns:participation="http://www.ontologydesignpatterns.org/cp/owl/participation.owl#"',
                            '     xmlns:timeindexed="http://www.ontologydesignpatterns.org/cp/owl/timeindexed.owl#"',
                            '     xmlns:time="http://www.w3.org/2006/time#"',
                            '     xmlns:inforeal="http://www.ontologydesignpatterns.org/cp/owl/informationrealization.owl#">',
                            f'<owl:Ontology rdf:about="http://www.example.org/test#{pattern_name}"/>'
                        ]
                        continue
                    
                    if in_turtle:
                        # Skip comments
                        if not line.startswith('#'):
                            # Convert Turtle to XML
                            if line.startswith(':'):
                                # Extract subject, predicate, object
                                parts = line.split(' ', 2)
                                if len(parts) >= 3:
                                    subject = parts[0].replace(':', '')
                                    predicate = parts[1]
                                    obj = parts[2].rstrip(' .;')
                                    
                                    if predicate == 'a':
                                        # Class declaration
                                        current_xml_block.append(f'<owl:Class rdf:about="#{subject}"/>')
                                    else:
                                        # Property assertion
                                        current_xml_block.append(f'<owl:ObjectProperty rdf:about="#{predicate}">')
                                        current_xml_block.append(f'    <rdfs:domain rdf:resource="#{subject}"/>')
                                        current_xml_block.append(f'    <rdfs:range rdf:resource="#{obj}"/>')
                                        current_xml_block.append('</owl:ObjectProperty>')
                            elif line == '}' or line == '].':
                                # End of a block
                                current_xml_block.append('</owl:Restriction>')
                            elif line.startswith('['):
                                # Start of a restriction block
                                current_xml_block.append('<owl:Restriction>')
                            elif line.startswith('rdfs:') or line.startswith('owl:'):
                                # Handle RDFS/OWL properties
                                current_xml_block.append(f'<{line}/>')
                    else:
                        # Direct XML content
                        current_xml_block.append(line)
            
            if pattern_name:
                # If we have Turtle content, close the XML block
                if in_turtle:
                    current_xml_block.append('</rdf:RDF>')
                    xml_content.extend(current_xml_block)
                
                # Clean up XML content
                xml_str = '\n'.join(xml_content).strip()
                if xml_str:
                    patterns.append((pattern_name, xml_str))
                    logger.info(f"Loaded pattern: {pattern_name}")
        
        logger.info(f"Loaded {len(patterns)} patterns from {patterns_path}")
        return patterns
        
    except Exception as e:
        logger.error(f"Error loading patterns: {str(e)}")
        return patterns

class OntologyGenerationPipeline:
    def __init__(self, api_url: str, patterns_path: str, output_dir: str):
        """
        Initialize the ontology generation pipeline.
        
        Args:
            api_url: API endpoint for ontology generation
            patterns_path: Path to patterns.txt file
            output_dir: Directory for output files
        """
        self.api_url = api_url
        self.patterns_path = patterns_path
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        
        # Load patterns
        self.patterns = self.load_patterns()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def load_patterns(self) -> Dict[str, str]:
        """Load reusable patterns from TXT file."""
        patterns = {}
        try:
            if os.path.exists(self.patterns_path):
                loaded_patterns = parse_patterns_txt(self.patterns_path)
                for name, content in loaded_patterns:
                    # Store XML content directly
                    patterns[name] = content
                    self.logger.info(f"Loaded pattern: {name}")
                self.logger.info(f"Loaded {len(patterns)} patterns from {self.patterns_path}")
            else:
                self.logger.warning(f"Patterns file not found: {self.patterns_path}")
        except Exception as e:
            self.logger.error(f"Error loading patterns: {str(e)}")
        return patterns
    
    def generate_ontology(self, competency_question: str, user_story: str, max_retries: int = 3) -> Optional[str]:
        """
        Generate an ontology for a competency question and user story.
        
        Args:
            competency_question: The competency question to address
            user_story: The user story providing context
            max_retries: Maximum number of API retries
            
        Returns:
            Generated ontology in Turtle format, or None if generation failed
        """
        # Create base ontology with prefixes
        base_ontology = """@prefix : <http://www.example.org/test#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix ssn: <http://www.w3.org/ns/ssn/> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix agentrole: <http://www.ontologydesignpatterns.org/cp/owl/agentrole.owl#> .
@prefix situation: <http://www.ontologydesignpatterns.org/cp/owl/situation.owl#> .
@prefix observation: <http://www.ontologydesignpatterns.org/cp/owl/observation.owl#> .
@prefix participation: <http://www.ontologydesignpatterns.org/cp/owl/participation.owl#> .
@prefix timeindexed: <http://www.ontologydesignpatterns.org/cp/owl/timeindexed.owl#> .
@prefix time: <http://www.w3.org/2006/time#> .
@prefix inforeal: <http://www.ontologydesignpatterns.org/cp/owl/informationrealization.owl#> .

<http://www.example.org/test#> a owl:Ontology ."""

        # Add patterns directly as valid Turtle syntax
        pattern_turtle = "\n\n# Imported patterns\n"
        for name, pattern in self.patterns.items():
            if pattern and isinstance(pattern, str):
                # Clean up the pattern and ensure it's valid Turtle
                clean_pattern = pattern.strip()
                if clean_pattern:
                    pattern_turtle += f"\n# Pattern: {name}\n{clean_pattern}\n"

        prompt = """<instruction>
You are a helpful assistant designed to generate ontologies. You receive a Competency Question (CQ) and an Ontology Story (OS). \n
Based on CQ, which is a requirement for the ontology, and OS, which tells you what the context of the ontology is, your task is generating one ontology (O). The goal is to generate O that models the CQ properly. This means there is a way to write a SPARQL query to extract the answer to this CQ in O.  \n
Use the following prefixes: \n
@prefix : <http://www.example.org/test#> .\n
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n

Don't put any A-Box (instances) in the ontology and just generate the OWL file using Turtle syntax. Include the entities mentioned in the CQ. Remember to use restrictions when the CQ implies it. The output should be self-contained without any errors. Outside of the code box don't put any comment.
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


Available prefixes:
- dct: <http://purl.org/dc/terms/>
- ssn: <http://www.w3.org/ns/ssn/>
- sosa: <http://www.w3.org/ns/sosa/>
- agentrole: <http://www.ontologydesignpatterns.org/cp/owl/agentrole.owl#>
- situation: <http://www.ontologydesignpatterns.org/cp/owl/situation.owl#>
- observation: <http://www.ontologydesignpatterns.org/cp/owl/observation.owl#>
- participation: <http://www.ontologydesignpatterns.org/cp/owl/participation.owl#>
- timeindexed: <http://www.ontologydesignpatterns.org/cp/owl/timeindexed.owl#>
- time: <http://www.w3.org/2006/time#>
- inforeal: <http://www.ontologydesignpatterns.org/cp/owl/informationrealization.owl#>

CQ: {cq}
OS: {os}

Generate additional ontology elements in Turtle format:""".format(
            cq=competency_question,
            os=user_story
        )
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Generating ontology (attempt {attempt+1}/{max_retries})")
                
                payload = {"prompt": prompt}
                headers = {"Content-Type": "application/json"}
                
                response = requests.post(self.api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("data", {}).get("answer")
                    
                    if answer:
                        self.logger.info(f"API Response: {answer}")
                        # Clean up any potential binary string artifacts
                        if answer.startswith("b'") and answer.endswith("'"):
                            answer = answer[2:-1]
                            answer = answer.replace("\\n", "\n").replace("\\t", "\t").replace("\\'", "'")
                        
                        # Extract just the turtle content and combine with base ontology and patterns
                        additional_content = self.extract_turtle_content(answer)
                        complete_ontology = f"{base_ontology}\n{pattern_turtle}\n{additional_content}"
                        return complete_ontology
                    else:
                        self.logger.warning("API response doesn't contain an answer")
                else:
                    self.logger.warning(f"API request failed with status code {response.status_code}")
                    
            except Exception as e:
                self.logger.error(f"Error during ontology generation: {str(e)}")
            
            if attempt < max_retries - 1:
                self.logger.info("Retrying in 2 seconds...")
                time.sleep(2)
        
        self.logger.error("All ontology generation attempts failed")
        return None
    
    def extract_turtle_content(self, response: str) -> str:
        """Extract turtle content from API response."""
        lines = response.split('\n')
        turtle_lines = []
        current_subject = None
        property_list = []
        in_intersection = False
        intersection_items = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip prefix declarations and ontology declaration as they're in base_ontology
            if (line_stripped.startswith('@prefix') or 
                line_stripped.startswith('<http') or
                'owl:Ontology' in line_stripped):
                continue
            
            # Skip empty lines and comments
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Handle class definitions and property assertions
            if ('rdf:type' in line_stripped or ' a ' in line_stripped) and not line_stripped.startswith(' '):
                # If we have a previous subject with properties, add them
                if current_subject and property_list:
                    turtle_lines.extend(property_list)
                    if property_list:  # Check if we have properties
                        turtle_lines[-1] = turtle_lines[-1].replace(' ;', ' .').strip()
                    property_list = []
                
                # Handle both 'a' and 'rdf:type' syntax
                if ' a ' in line_stripped:
                    current_subject = line_stripped.split(' a ')[0].strip()
                    turtle_lines.append(f"{current_subject} a {line_stripped.split(' a ')[1].strip()} ;")
                else:
                    current_subject = line_stripped.split(' rdf:type ')[0].strip()
                    turtle_lines.append(f"{current_subject} rdf:type {line_stripped.split(' rdf:type ')[1].strip()} ;")
                
            elif line_stripped.startswith('rdfs:') or line_stripped.startswith('owl:') or line_stripped.startswith('dct:') or line_stripped.startswith('ssn:') or line_stripped.startswith('sosa:') or line_stripped.startswith(':'):
                if current_subject:
                    # Clean up the property assertion
                    prop = line_stripped.rstrip(' ;.')
                    if prop:
                        # Handle owl:intersectionOf lists
                        if 'owl:intersectionOf' in prop:
                            in_intersection = True
                            intersection_items = []
                            # Extract the first item if it's on the same line
                            if '(' in prop:
                                first_item = prop[prop.find('(')+1:].strip()
                                if first_item:
                                    intersection_items.append(first_item)
                            property_list.append(f"    {prop[:prop.find('(')+1]}")
                        elif in_intersection:
                            if ')' in prop:
                                in_intersection = False
                                item = prop[:prop.find(')')].strip()
                                if item:
                                    intersection_items.append(item)
                                # Join all items with spaces
                                property_list[-1] += f" {' '.join(intersection_items)} ) ] ;"
                            else:
                                intersection_items.append(prop)
                        # Handle property lists (comma-separated values)
                        elif ',' in prop:
                            # Split into predicate and objects
                            pred_obj = prop.split(' ', 1)
                            if len(pred_obj) == 2:
                                predicate = pred_obj[0]
                                objects = [obj.strip() for obj in pred_obj[1].split(',')]
                                # Remove empty objects and trailing commas
                                objects = [obj for obj in objects if obj and not obj.isspace()]
                                if objects:
                                    # Join objects with commas on the same line
                                    property_list.append(f"    {predicate} {objects[0]}")
                                    for obj in objects[1:]:
                                        property_list[-1] += f" ,{obj}"
                                    property_list[-1] += " ;"
                        else:
                            # Regular property assertion
                            property_list.append(f"    {prop} ;")
        
        # Add any remaining properties
        if current_subject and property_list:
            turtle_lines.extend(property_list)
            if property_list:  # Check if we have properties
                turtle_lines[-1] = turtle_lines[-1].replace(' ;', ' .').strip()
        
        # Clean up any double semicolons or periods
        result = []
        for line in turtle_lines:
            line = line.strip()
            if line:
                # Remove multiple semicolons
                while ' ; ;' in line:
                    line = line.replace(' ; ;', ' ;')
                # Remove multiple periods
                while ' . .' in line:
                    line = line.replace(' . .', '.')
                # Remove space before period
                line = line.replace(' .', '.')
                # Fix incorrect line endings
                if line.endswith('. ;'):
                    line = line[:-3] + '.'
                result.append(line)
        
        return '\n'.join(result)
    
    def merge_ontologies_strategically(self, ontology_contents: List[str], competency_questions: List[str]) -> Optional[str]:
        """
        Merge ontologies using the strategic five-principle approach.
        
        Args:
            ontology_contents: List of ontology content strings
            competency_questions: List of competency questions to preserve
            
        Returns:
            Merged ontology in Turtle format
        """
        # Import the strategic merger module dynamically
        spec = importlib.util.spec_from_file_location(
            "strategic_merger",
            os.path.join(os.path.dirname(__file__), "strategic-ontology-merger.py")
        )
        strategic_merger = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(strategic_merger)
        
        merger = strategic_merger.StrategicOntologyMerger()
        merged_ontology = merger.merge_ontologies(ontology_contents, competency_questions)
        
        # Log statistics
        if merged_ontology:
            stats = merger.get_statistics()
            self.logger.info(f"Merge statistics: {stats}")
        
        return merged_ontology
    
    def run_pipeline(self, competency_questions: List[str], user_stories: List[str], test_mode: bool = True) -> Dict[str, str]:
        """
        Run the complete ontology generation and merging pipeline.
        
        Args:
            competency_questions: List of competency questions
            user_stories: List of corresponding user stories
            test_mode: If True, process only first 2 questions for testing
            
        Returns:
            Dictionary containing generated and merged ontologies
        """
        self.logger.info("Starting ontology generation pipeline")
        
        # Limit to 2 questions for testing
        if test_mode:
            competency_questions = competency_questions[:2]
            user_stories = user_stories[:2]
            self.logger.info("Test mode: Processing first 2 competency questions")
        
        # Generate individual ontologies
        ontologies = {}
        ontology_contents = []
        
        for i, (cq, story) in enumerate(zip(competency_questions, user_stories)):
            self.logger.info(f"Processing competency question {i+1}: {cq[:100]}...")
            
            ontology = self.generate_ontology(cq, story)
            if ontology:
                ontology_id = f"ontology_{i+1}"
                ontologies[ontology_id] = ontology
                ontology_contents.append(ontology)
                
                # Save individual ontology
                individual_path = os.path.join(self.output_dir, f"{ontology_id}.ttl")
                with open(individual_path, 'w', encoding='utf-8') as f:
                    f.write(ontology)
                self.logger.info(f"Saved individual ontology to {individual_path}")
            else:
                self.logger.error(f"Failed to generate ontology for question {i+1}")
        
        # Merge ontologies if we have more than one
        if len(ontology_contents) > 1:
            self.logger.info("Merging ontologies using strategic approach")
            merged_ontology = self.merge_ontologies_strategically(ontology_contents, competency_questions)
            
            if merged_ontology:
                ontologies['merged'] = merged_ontology
                
                # Save merged ontology
                merged_path = os.path.join(self.output_dir, "merged_ontology.ttl")
                with open(merged_path, 'w', encoding='utf-8') as f:
                    f.write(merged_ontology)
                self.logger.info(f"Saved merged ontology to {merged_path}")
            else:
                self.logger.error("Failed to merge ontologies")
        
        return ontologies

def load_data_from_csv(cq_path: str, stories_path: str) -> Tuple[List[str], List[str]]:
    """Load competency questions and user stories from CSV files."""
    logger = logging.getLogger(__name__)
    
    try:
        # Load user stories
        stories_df = pd.read_csv(stories_path)
        stories_dict = dict(zip(stories_df['StoryID'], stories_df['UserStory']))
        
        # Load competency questions
        cq_df = pd.read_csv(cq_path)
        
        competency_questions = []
        user_stories = []
        
        for _, row in cq_df.iterrows():
            competency_questions.append(row['CompetencyQuestion'])
            story_id = row['StoryID']
            user_story = stories_dict.get(story_id, f"No story found for ID: {story_id}")
            user_stories.append(user_story)
        
        logger.info(f"Loaded {len(competency_questions)} competency questions and corresponding user stories")
        return competency_questions, user_stories
        
    except Exception as e:
        logger.error(f"Error loading data from CSV: {str(e)}")
        return [], []

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate and merge ontologies")
    parser.add_argument("--api-url", required=True, help="API endpoint for ontology generation")
    parser.add_argument("--patterns", default="data/patterns.txt", help="Path to patterns.txt file")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--cq-file", default="data/competency_questions.csv", help="Competency questions CSV file")
    parser.add_argument("--stories-file", default="data/user_stories.csv", help="User stories CSV file")
    parser.add_argument("--test", action="store_true", help="Run in test mode (process only first 2 questions)")
    
    args = parser.parse_args()
    
    # Check if patterns file exists
    if not os.path.exists(args.patterns):
        print(f"❌ ERROR: {args.patterns} file not found")
        print(f"Please ensure {args.patterns} exists in the specified location")
        return
    
    # Load data from CSV files
    competency_questions, user_stories = load_data_from_csv(args.cq_file, args.stories_file)
    
    # Initialize and run pipeline
    pipeline = OntologyGenerationPipeline(args.api_url, args.patterns, args.output_dir)
    results = pipeline.run_pipeline(competency_questions, user_stories, args.test)
    
    # Print summary
    print("\n=== Pipeline Results ===")
    print(f"✅ Used patterns from {args.patterns}")
    print(f"Individual ontologies generated: {len(results) - 1}")  # -1 for merged
    print(f"Merged ontology created: {'Yes' if 'merged' in results else 'No'}")
    print(f"Output directory: {args.output_dir}")
    print("\nFiles created:")
    for ontology_id, _ in results.items():
        if ontology_id != 'merged':
            print(f"- ontology_{ontology_id}.ttl")
    print("- merged_ontology.ttl")
    print("\n🔑 All ontologies incorporate patterns from your patterns.txt!")

if __name__ == "__main__":
    main()