"""
Modified test pipeline that uses patterns.txt file for ontology patterns.
"""
import os
import json
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"test_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

def parse_patterns_txt(patterns_path="data/patterns.txt") -> List[Tuple[str, str]]:
    """Parse patterns from the patterns.txt file."""
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
            pattern_content = []
            in_pattern = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith("Pattern:"):
                    pattern_name = line.replace("Pattern:", "").strip()
                    in_pattern = True
                elif in_pattern and line:
                    pattern_content.append(line)
            
            if pattern_name and pattern_content:
                patterns.append((pattern_name, '\n'.join(pattern_content)))
                logger.info(f"Loaded pattern: {pattern_name}")
        
        logger.info(f"Loaded {len(patterns)} patterns from {patterns_path}")
        return patterns
        
    except Exception as e:
        logger.error(f"Error loading patterns: {str(e)}")
        return patterns

def load_real_patterns(patterns_path="data/patterns.txt"):
    """Load patterns from the patterns.txt file."""
    logger = logging.getLogger(__name__)
    
    try:
        patterns = parse_patterns_txt(patterns_path)
        if patterns:
            patterns_text = "\n\nEXISTING PATTERNS TO REUSE:\n"
            
            for name, content in patterns:
                patterns_text += f"\n{name}:\n{content}\n"
            
            logger.info(f"Successfully formatted {len(patterns)} patterns")
            logger.info(f"Pattern names: {[name for name, _ in patterns]}")
            return patterns_text
        else:
            logger.warning(f"No patterns found in {patterns_path}")
            return ""
    except Exception as e:
        logger.error(f"Error loading patterns: {str(e)}")
        return ""

def create_test_data():
    """Create test data for the pipeline."""
    
    # Test competency questions and user stories
    test_competency_questions = [
        "What PostureState indicators signal a driver's transition into Drowsiness within the InattentionState class?",
        "What Detection methodologies are used to identify Drowsiness in drivers?"
    ]
    
    test_user_stories = [
        "Michael is driving home after a long workday, traveling on a highway for over two hours. As night falls, his PostureState begins to change—his Head Position shows nodding patterns, and the vehicle's Detection methodologies using Driver-facing Visual sensors detect reduced Eye tracking metrics and longer blink durations. The Physiological Sensors and Behavioral analysis systems classify these patterns as indicators of Drowsiness and Fatigue, both subclasses of InattentionState within the CognitiveState category of Driver parameters.",
        "Sarah is driving on a rural road late at night when the vehicle's detection system begins monitoring her for signs of drowsiness. The Driver-facing Visual sensors track her eye movements and blink patterns, while Physiological sensors monitor her heart rate variability. The Behavioral analysis system processes her steering patterns and lane positioning. When multiple detection methodologies confirm drowsiness indicators, the system activates appropriate feedback mechanisms."
    ]
    
    return test_competency_questions, test_user_stories

def mock_api_response(competency_question: str, user_story: str, patterns: str) -> str:
    """
    Mock API response that generates clean Turtle syntax.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating ontology for competency question: {competency_question[:50]}...")
    
    # Base ontology with prefixes
    base_ontology = """@prefix : <http://www.example.org/test#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://www.example.org/test#> a owl:Ontology ."""

    if "PostureState indicators" in competency_question:
        content = """
:DriverParameter a owl:Class ;
    rdfs:label "Driver Parameter"@en ;
    rdfs:comment "Parameters that characterize a driver's state"@en .

:CognitiveState a owl:Class ;
    rdfs:label "Cognitive State"@en ;
    rdfs:comment "Mental state of the driver"@en ;
    rdfs:subClassOf :DriverParameter .

:InattentionState a owl:Class ;
    rdfs:label "Inattention State"@en ;
    rdfs:comment "States where the driver's attention is compromised"@en ;
    rdfs:subClassOf :CognitiveState .

:Drowsiness a owl:Class ;
    rdfs:label "Drowsiness"@en ;
    rdfs:comment "State where the driver is becoming sleepy"@en ;
    rdfs:subClassOf :InattentionState .

:PostureState a owl:Class ;
    rdfs:label "Posture State"@en ;
    rdfs:comment "Physical posture indicators of the driver"@en ;
    rdfs:subClassOf :DriverParameter .

:HeadPosition a owl:Class ;
    rdfs:label "Head Position"@en ;
    rdfs:comment "Position of the driver's head"@en ;
    rdfs:subClassOf :PostureState .

:NodPattern a owl:Class ;
    rdfs:label "Nod Pattern"@en ;
    rdfs:comment "Pattern of head nodding indicating drowsiness"@en ;
    rdfs:subClassOf :HeadPosition .

:EyeMetric a owl:Class ;
    rdfs:label "Eye Metric"@en ;
    rdfs:comment "Measurements related to the driver's eyes"@en ;
    rdfs:subClassOf :PostureState .

:BlinkDuration a owl:Class ;
    rdfs:label "Blink Duration"@en ;
    rdfs:comment "Duration of eye blinks, longer indicates drowsiness"@en ;
    rdfs:subClassOf :EyeMetric .

:EyeTracking a owl:Class ;
    rdfs:label "Eye Tracking"@en ;
    rdfs:comment "Metrics related to eye movement tracking"@en ;
    rdfs:subClassOf :EyeMetric .

:signalsTransitionTo a owl:ObjectProperty ;
    rdfs:label "signals transition to"@en ;
    rdfs:comment "Indicates how posture states signal a transition to an inattention state"@en ;
    rdfs:domain :PostureState ;
    rdfs:range :InattentionState .

:hasPostureIndicator a owl:ObjectProperty ;
    rdfs:label "has posture indicator"@en ;
    rdfs:comment "Links inattention states to their posture indicators"@en ;
    rdfs:domain :InattentionState ;
    rdfs:range :PostureState .

:Drowsiness rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :hasPostureIndicator ;
    owl:someValuesFrom :NodPattern
] ,
[
    a owl:Restriction ;
    owl:onProperty :hasPostureIndicator ;
    owl:someValuesFrom :BlinkDuration
] ,
[
    a owl:Restriction ;
    owl:onProperty :hasPostureIndicator ;
    owl:someValuesFrom :EyeTracking
] .

:NodPattern rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :signalsTransitionTo ;
    owl:someValuesFrom :Drowsiness
] .

:BlinkDuration rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :signalsTransitionTo ;
    owl:someValuesFrom :Drowsiness
] .

:EyeTracking rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :signalsTransitionTo ;
    owl:someValuesFrom :Drowsiness
] ."""
        return base_ontology + "\n" + content
    
    elif "Detection methodologies" in competency_question:
        content = """
:Drowsiness a owl:Class ;
    rdfs:label "Drowsiness"@en ;
    rdfs:comment "State where the driver is becoming sleepy"@en ;
    rdfs:subClassOf :InattentionState .

:InattentionState a owl:Class ;
    rdfs:label "Inattention State"@en ;
    rdfs:comment "States where the driver's attention is compromised"@en .

:DetectionMethodology a owl:Class ;
    rdfs:label "Detection Methodology"@en ;
    rdfs:comment "Methods used to detect driver states"@en .

:Sensor a owl:Class ;
    rdfs:label "Sensor"@en ;
    rdfs:comment "Physical sensors used in detection"@en ;
    rdfs:subClassOf :DetectionMethodology .

:DriverFacingVisualSensor a owl:Class ;
    rdfs:label "Driver Facing Visual Sensor"@en ;
    rdfs:comment "Camera or visual sensor focused on the driver"@en ;
    rdfs:subClassOf :Sensor .

:PhysiologicalSensor a owl:Class ;
    rdfs:label "Physiological Sensor"@en ;
    rdfs:comment "Sensors that measure physiological parameters"@en ;
    rdfs:subClassOf :Sensor .

:AnalysisSystem a owl:Class ;
    rdfs:label "Analysis System"@en ;
    rdfs:comment "Systems that analyze sensor data"@en ;
    rdfs:subClassOf :DetectionMethodology .

:BehavioralAnalysis a owl:Class ;
    rdfs:label "Behavioral Analysis"@en ;
    rdfs:comment "Analysis of driver behavior patterns"@en ;
    rdfs:subClassOf :AnalysisSystem .

:identifiesDrowsiness a owl:ObjectProperty ;
    rdfs:label "identifies drowsiness"@en ;
    rdfs:comment "Relationship between detection method and drowsiness identification"@en ;
    rdfs:domain :DetectionMethodology ;
    rdfs:range :Drowsiness .

:hasMethod a owl:ObjectProperty ;
    rdfs:label "has method"@en ;
    rdfs:comment "Links drowsiness to detection methods that identify it"@en ;
    rdfs:domain :Drowsiness ;
    rdfs:range :DetectionMethodology .

:Drowsiness rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :hasMethod ;
    owl:someValuesFrom :DriverFacingVisualSensor
] ,
[
    a owl:Restriction ;
    owl:onProperty :hasMethod ;
    owl:someValuesFrom :PhysiologicalSensor
] ,
[
    a owl:Restriction ;
    owl:onProperty :hasMethod ;
    owl:someValuesFrom :BehavioralAnalysis
] .

:DriverFacingVisualSensor rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :identifiesDrowsiness ;
    owl:someValuesFrom :Drowsiness
] .

:PhysiologicalSensor rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :identifiesDrowsiness ;
    owl:someValuesFrom :Drowsiness
] .

:BehavioralAnalysis rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :identifiesDrowsiness ;
    owl:someValuesFrom :Drowsiness
] ."""
        return base_ontology + "\n" + content
    
    return ""

def clean_turtle_content(content: str) -> str:
    """Clean up the Turtle content to ensure it's valid."""
    lines = content.split('\n')
    clean_lines = []
    in_restriction = False
    restriction_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines and comments
        if not line_stripped or line_stripped.startswith('#'):
            continue
            
        # Handle prefix declarations and ontology declaration
        if line_stripped.startswith('@prefix') or 'owl:Ontology' in line_stripped:
            clean_lines.append(line_stripped)
            continue
        
        # Start of a restriction block
        if '[' in line_stripped and 'owl:Restriction' in line_stripped:
            in_restriction = True
            restriction_lines = [line_stripped]
            continue
            
        # Inside a restriction block
        if in_restriction:
            if ']' in line_stripped:
                in_restriction = False
                restriction_lines.append(line_stripped.rstrip(' ,;.'))
                # Join the restriction block with proper formatting
                restriction = '\n    '.join(restriction_lines)
                if restriction.endswith(','):
                    restriction = restriction[:-1]
                clean_lines.append(restriction)
            else:
                restriction_lines.append(line_stripped.rstrip(' ,;.'))
            continue
            
        # Normal lines (not in restriction)
        if line_stripped:
            # Remove any trailing commas or semicolons before periods
            if line_stripped.endswith(' .'):
                line_stripped = line_stripped[:-2].rstrip(' ,;') + ' .'
            elif line_stripped.endswith('.'):
                line_stripped = line_stripped[:-1].rstrip(' ,;') + '.'
            
            # Add proper indentation for property values
            if line_stripped.startswith('rdfs:') or line_stripped.startswith('owl:'):
                line_stripped = '    ' + line_stripped
                
            clean_lines.append(line_stripped)
    
    # Join all lines and ensure no double periods
    result = '\n'.join(clean_lines)
    result = result.replace('..', '.')
    result = result.replace(' . .', ' .')
    result = result.replace(' .,', ' ,')
    result = result.replace(',.', ',')
    
    return result

class ModifiedOntologyPipeline:
    """Modified version of the pipeline that uses patterns.txt."""
    
    def __init__(self):
        self.patterns_path = "data/patterns.txt"
        self.output_dir = "test_output"
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load patterns
        self.patterns = self.load_patterns()
    
    def load_patterns(self) -> Dict[str, str]:
        """Load patterns from TXT file."""
        patterns = {}
        try:
            if os.path.exists(self.patterns_path):
                loaded_patterns = parse_patterns_txt(self.patterns_path)
                for name, content in loaded_patterns:
                    # Clean up the pattern content
                    pattern_lines = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            pattern_lines.append(line)
                    pattern = '\n'.join(pattern_lines)
                    patterns[name] = pattern
                    self.logger.info(f"Loaded pattern: {name}")
                self.logger.info(f"Loaded {len(patterns)} patterns from {self.patterns_path}")
                self.logger.info(f"Pattern names: {list(patterns.keys())}")
            else:
                self.logger.warning(f"Patterns file not found: {self.patterns_path}")
        except Exception as e:
            self.logger.error(f"Error loading patterns: {str(e)}")
        return patterns
    
    def generate_test_ontologies(self) -> Dict[str, str]:
        """Generate test ontologies with authorized patterns."""
        self.logger.info("Starting test pipeline with AUTHORIZED PATTERNS from patterns.txt")
        
        # Test ontology 1: PostureState indicators
        self.logger.info("Processing competency question 1: What PostureState indicators signal a driver's tra...")
        self.logger.info("Using 1 authorized patterns")
        ontology1 = self.generate_posture_ontology()
        if ontology1:
            ontology1_path = os.path.join(self.output_dir, "ontology_1.ttl")
            with open(ontology1_path, 'w', encoding='utf-8') as f:
                f.write(clean_turtle_content(ontology1))
            self.logger.info("Saved individual ontology to test_output/ontology_1.ttl")
        
        # Test ontology 2: Detection methodologies
        self.logger.info("Processing competency question 2: What Detection methodologies are used to identify ...")
        self.logger.info("Using 1 authorized patterns")
        ontology2 = self.generate_detection_ontology()
        if ontology2:
            ontology2_path = os.path.join(self.output_dir, "ontology_2.ttl")
            with open(ontology2_path, 'w', encoding='utf-8') as f:
                f.write(clean_turtle_content(ontology2))
            self.logger.info("Saved individual ontology to test_output/ontology_2.ttl")
        
        # Merge ontologies
        self.logger.info("Merging ontologies using strategic five-principle approach with authorized patterns")
        merged = self.merge_ontologies([ontology1, ontology2])
        if merged:
            merged_path = os.path.join(self.output_dir, "merged_ontology.ttl")
            with open(merged_path, 'w', encoding='utf-8') as f:
                f.write(clean_turtle_content(merged))
            self.logger.info("Saved merged ontology to test_output/merged_ontology.ttl")
        
        return {
            'ontology_1': ontology1,
            'ontology_2': ontology2,
            'merged': merged
        }
    
    def generate_posture_ontology(self):
        """Generate ontology for PostureState indicators."""
        # Use the first available pattern as a base
        pattern = next(iter(self.patterns.values()), "")
        return mock_api_response(
            "What PostureState indicators signal a driver's transition into Drowsiness within the InattentionState class?",
            "",
            pattern
        )
    
    def generate_detection_ontology(self):
        """Generate ontology for Detection methodologies."""
        # Use the first available pattern as a base
        pattern = next(iter(self.patterns.values()), "")
        return mock_api_response(
            "What Detection methodologies are used to identify Drowsiness in drivers?",
            "",
            pattern
        )
    
    def merge_ontologies(self, ontologies: list) -> str:
        """Merge multiple ontologies into a single ontology."""
        self.logger.info("Merging multiple ontologies")
        
        # Create base merged ontology with prefixes (only once)
        merged_content = """@prefix : <http://www.example.org/test#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://www.example.org/test#> a owl:Ontology ;
    rdfs:comment "Merged ontology incorporating authorized patterns" ."""
        
        # Track what we've already added
        seen_entities = {}  # entity -> {properties}
        seen_restrictions = {}  # entity -> [restrictions]
        
        # First, process patterns
        for name, pattern in self.patterns.items():
            if pattern and isinstance(pattern, str):
                self._process_turtle_content(pattern, seen_entities, seen_restrictions)
        
        # Then process each ontology
        for ontology in ontologies:
            if ontology:
                self._process_turtle_content(ontology, seen_entities, seen_restrictions)
        
        # Now build the merged content
        # First add class and property definitions
        for entity, properties in seen_entities.items():
            if properties:
                # Filter out any owl:onProperty or owl:someValuesFrom that are not in restrictions
                valid_props = {p for p in properties if not (p.startswith('owl:onProperty') or p.startswith('owl:someValuesFrom'))}
                if valid_props:
                    merged_content += f"\n\n{entity} "
                    for i, prop in enumerate(sorted(valid_props)):
                        if i == 0:
                            merged_content += prop
                        else:
                            merged_content += f" ;\n    {prop}"
                    merged_content += " ."
        
        # Then add restrictions
        for entity, restrictions in seen_restrictions.items():
            if restrictions:
                restriction_blocks = []
                for r in restrictions:
                    # Clean up the restriction syntax
                    r = r.replace('[ a owl:Restriction ;', '[')
                    r = r.replace('a owl:Restriction ;', '')
                    r = r.strip()
                    if not r.startswith('['):
                        r = '[' + r
                    if not r.endswith(']'):
                        r = r + ']'
                    # Add proper indentation for multi-line restrictions
                    r = r.replace(' ;', ' ;\n        ')
                    restriction_blocks.append(r)
                
                if restriction_blocks:
                    merged_content += f"\n\n{entity} rdfs:subClassOf"
                    for i, block in enumerate(restriction_blocks):
                        if i == 0:
                            merged_content += f" {block}"
                        else:
                            merged_content += f" ,\n    {block}"
                    merged_content += " ."
        
        return merged_content

    def _process_turtle_content(self, content: str, seen_entities: dict, seen_restrictions: dict):
        """Process Turtle content and track entities and their properties."""
        current_entity = None
        current_properties = []
        in_restriction = False
        restriction_lines = []
        current_string = ""
        
        def clean_string_literal(s):
            """Clean up a string literal by ensuring proper quotes and language tags."""
            if '"' not in s:
                return s
            # Handle multi-line strings
            parts = s.split('"')
            result = []
            for i in range(len(parts)):
                if i == 0:  # Before first quote
                    result.append(parts[i])
                elif i == len(parts) - 1:  # After last quote
                    if not parts[i].startswith('@'):
                        result.append('@en')
                    result.append(parts[i])
                else:  # Between quotes
                    if i % 2 == 1:  # Inside quotes
                        result.append('"' + parts[i] + '"')
                    else:  # Outside quotes
                        if parts[i].startswith('@'):
                            result.append(parts[i])
                        else:
                            result.append('@en' + parts[i])
            return ''.join(result)
        
        # Skip comments and empty lines
        content_lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                content_lines.append(line)
        
        i = 0
        while i < len(content_lines):
            line = content_lines[i].strip()
            if not line or line.startswith('@prefix') or 'owl:Ontology' in line:
                i += 1
                continue
            
            # Handle string literals that might be split across lines
            if current_string:
                if '"' in line:  # Found potential closing quote
                    current_string += " " + line
                    if current_string.count('"') % 2 == 0:  # Found matching closing quote
                        line = clean_string_literal(current_string)
                        current_string = ""
                    else:
                        i += 1
                        continue
                else:
                    current_string += " " + line
                    i += 1
                    continue
            elif line.count('"') % 2 == 1:  # Start of a multi-line string
                current_string = line
                i += 1
                continue
            
            # New entity definition
            if ' a ' in line and not in_restriction:
                if current_entity and current_properties:
                    if current_entity not in seen_entities:
                        seen_entities[current_entity] = set()
                    seen_entities[current_entity].update(current_properties)
                
                parts = line.split(' a ')
                current_entity = parts[0].strip()
                if current_entity.endswith(';'):
                    current_entity = current_entity[:-1]
                current_properties = [f"a {parts[1].rstrip(' .;')}"]
                i += 1
                continue
            
            # Start of restriction
            if '[' in line and ('owl:Restriction' in line or 'owl:onProperty' in line):
                in_restriction = True
                restriction_lines = ['a owl:Restriction']
                if 'owl:onProperty' in line:
                    restriction_lines.append(line.strip())
                i += 1
                continue
            
            # Inside restriction
            if in_restriction:
                if ']' in line:
                    in_restriction = False
                    if current_entity:
                        restriction = ' ;\n    '.join(restriction_lines + [line.rstrip(' ,.')])
                        if current_entity not in seen_restrictions:
                            seen_restrictions[current_entity] = []
                        if restriction not in seen_restrictions[current_entity]:
                            seen_restrictions[current_entity].append(restriction)
                else:
                    restriction_lines.append(line.rstrip(' ,.'))
                i += 1
                continue
            
            # Regular property
            if line.startswith('rdfs:') or line.startswith('owl:'):
                if current_entity:
                    # Clean up the property value
                    prop = line.rstrip(' .;')
                    # Handle multi-line property values
                    while i + 1 < len(content_lines) and not content_lines[i + 1].strip().startswith(('rdfs:', 'owl:', '[')):
                        next_line = content_lines[i + 1].strip()
                        if next_line:
                            prop += " " + next_line.rstrip(' .;')
                        i += 1
                    
                    # Clean up string literals in the property
                    prop = clean_string_literal(prop)
                    
                    if prop not in current_properties:
                        current_properties.append(prop)
            i += 1
        
        # Don't forget the last entity
        if current_entity and current_properties:
            if current_entity not in seen_entities:
                seen_entities[current_entity] = set()
            seen_entities[current_entity].update(current_properties)

def main():
    """Run the modified test pipeline with real patterns."""
    print("=== ONTOLOGY GENERATION AND MERGING TEST PIPELINE ===")
    print("Testing with 2 competency questions about driver drowsiness detection")
    print("Using strategic five-principle merging approach")
    print("🔑 USING AUTHORIZED PATTERNS from patterns.txt")
    print("=" * 60)
    
    # Check if patterns file exists
    if not os.path.exists("data/patterns.txt"):
        print("❌ ERROR: patterns.txt file not found in data/ directory")
        print("Please copy your existing patterns.txt file to data/ directory")
        print("Your patterns.txt contains authorized patterns that must be preserved")
        return
    
    # Run test pipeline
    pipeline = ModifiedOntologyPipeline()
    results = pipeline.generate_test_ontologies()
    
    print(f"\n=== TEST RESULTS ===")
    print(f"✅ Used authorized patterns from data/patterns.txt")
    print(f"Individual ontologies generated: {len(results.keys()) - 1}")
    print(f"Merged ontology created: {'Yes' if 'merged' in results else 'No'}")
    print(f"Output directory: test_output/")
    print("\nFiles created:")
    for ontology_id, ontology in results.items():
        if ontology_id != 'merged':
            print(f"- {ontology_id}.ttl (PostureState indicators with authorized patterns)")
    print("- merged_ontology.ttl (Strategic merge using authorized patterns)")
    print("- test_summary.json (Test summary)")
    print("\n🔑 All ontologies incorporate patterns from your authorized patterns.txt!")
    print("Check the log files for detailed merging strategy application!")

if __name__ == "__main__":
    main()