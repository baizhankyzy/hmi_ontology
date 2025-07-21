"""
Implementation of the Ontogenia prompting technique for ontology generation.
"""
import json
import os
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

from src.api_client import ClaudeAPIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OntogeniaPrompting:
    def __init__(
        self, 
        api_client: ClaudeAPIClient,
        patterns_path: str,
        ontology_elements: str,
        metacognitive_procedure: str,
        output_dir: str
    ):
        """
        Initialize the Ontogenia prompting system.
        
        Args:
            api_client: Client for the LLM API
            patterns_path: Path to the CSV file containing ontology design patterns
            ontology_elements: Description of ontology elements to include
            metacognitive_procedure: The metacognitive procedure for ontology design
            output_dir: Directory to save generated ontologies
        """
        self.api_client = api_client
        self.patterns_path = patterns_path
        self.ontology_elements = ontology_elements
        self.metacognitive_procedure = metacognitive_procedure
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load ontology design patterns
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, str]:
        """
        Load ontology design patterns from CSV file.
        
        Returns:
            Dictionary mapping pattern names to their OWL representations
        """
        try:
            data = pd.read_csv(self.patterns_path)
            patterns = {row['Name']: row['Pattern_owl'] for _, row in data.iterrows()}
            self.logger.info(f"Loaded {len(patterns)} ontology design patterns")
            return patterns
        except Exception as e:
            self.logger.error(f"Error loading patterns: {str(e)}")
            self.logger.warning("Using sample patterns instead")
            # Load sample patterns from config if CSV loading fails
            from config import SAMPLE_PATTERNS
            return SAMPLE_PATTERNS
    
    def design_ontology_for_cq(
        self, 
        competency_question: str, 
        user_story: str, 
        previous_output: str = ""
    ) -> Optional[str]:
        """
        Design an ontology module for a single competency question.
        
        Args:
            competency_question: The competency question to model
            user_story: The user story providing context
            previous_output: Previous ontology output (if any)
            
        Returns:
            Generated ontology in Turtle format, or None if generation failed
        """
        patterns_json = json.dumps(self.patterns)
        
        # Construct the prompt
        context = f"previous output: '{previous_output}'" if previous_output else ""
        
        prompt = f"""
You are an expert ontology engineer specializing in creating OWL ontologies using the Turtle syntax.

{context}

Follow these instructions for designing an ontology module: 

{self.metacognitive_procedure}

Based on the user story:
"{user_story}"

Design an ontology module that comprehensively answers the following competency question:
"{competency_question}"

You can use the following ontology design patterns:
{patterns_json}

Remember to include these ontology elements:
{self.ontology_elements}

IMPORTANT INSTRUCTIONS:
1. Provide your answer in valid Turtle (.ttl) syntax
2. Include proper prefix declarations at the beginning
3. Use a custom namespace prefix for the domain concepts (e.g., :HMI or :ahmi)
4. Make sure all classes and properties have rdfs:label annotations in English
5. Include appropriate domain and range for all properties
6. Create proper class hierarchies and restrictions
7. Focus specifically on modeling the adaptive aspects of HMIs
8. Pay attention to distinguishing between:
   - Events (physical, social, or mental processes)
   - Situations (views or interpretations of events)
   - Descriptions (conceptualizations that provide context for situations)
9. Consider if alternative aspectual views should be modeled as different situations referring to the same event

Return ONLY the complete ontology in Turtle (.ttl) syntax without any additional explanations, markdown formatting, or code blocks. Start directly with the @prefix declarations.
"""
        
        self.logger.info(f"Generating ontology for competency question: {competency_question}")
        result = self.api_client.query(prompt)
        
        if result:
            # Extract the turtle content from the response
            turtle_content = self._extract_turtle(result)
            
            # Validate that we have a proper Turtle file
            if not turtle_content.strip().startswith("@prefix") and not turtle_content.strip().startswith("<http"):
                self.logger.warning(f"Extracted content does not appear to be valid Turtle: {turtle_content[:100]}...")
                
                # Try a second attempt with a more direct prompt
                second_prompt = f"""
You previously generated a Turtle ontology for the competency question:
"{competency_question}"

But the output wasn't in the correct format. Please provide ONLY the Turtle (.ttl) syntax with no explanations, markdown, or code blocks.

Start directly with the @prefix declarations. For example:

@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ahmi: <http://example.org/adaptive-hmi#> .

<http://example.org/adaptive-hmi> a owl:Ontology ;
    rdfs:label "Adaptive Human-Machine Interface Ontology"@en ;
    rdfs:comment "An ontology for describing adaptive human-machine interfaces"@en .

# Rest of your ontology...
"""
                self.logger.info("Attempting second query with more direct prompt")
                result2 = self.api_client.query(second_prompt)
                if result2:
                    turtle_content = self._extract_turtle(result2)
            
            # Add standard prefixes if they're missing
            if not turtle_content.strip().startswith("@prefix"):
                self.logger.warning("Adding standard prefixes to the ontology")
                from config import ONTOLOGY_PREFIX
                turtle_content = ONTOLOGY_PREFIX + "\n" + turtle_content
            
            return turtle_content
        
        return None
    
    def _extract_turtle(self, text: str) -> str:
        """
        Extract the Turtle syntax from the response.
        
        Args:
            text: The full text response from the API
            
        Returns:
            The extracted Turtle content
        """
        # Log the raw response for debugging
        self.logger.debug(f"Raw response: {repr(text[:100])}...")
        
        # Remove any binary prefixes that might be present
        if isinstance(text, str) and text.startswith("b'"):
            text = text.replace("b'", "", 1)
            if text.endswith("'"):
                text = text[:-1]
        
        # Unescape escaped characters
        text = text.replace("\\n", "\n").replace("\\t", "\t").replace("\\'", "'").replace('\\"', '"')
        
        # If the response is already pure Turtle, return it as is
        if text.strip().startswith("@prefix") or text.strip().startswith("<http"):
            return text.strip()
        
        # Handle case where Turtle might be embedded in markdown code blocks
        if "```turtle" in text or "```ttl" in text:
            # Find the start of the turtle block
            start_markers = ["```turtle", "```ttl"]
            end_marker = "```"
            
            start_idx = -1
            for marker in start_markers:
                if marker in text:
                    start_idx = text.find(marker) + len(marker)
                    break
            
            if start_idx >= 0:
                end_idx = text.find(end_marker, start_idx)
                if end_idx >= 0:
                    turtle_content = text[start_idx:end_idx].strip()
                    self.logger.debug(f"Extracted turtle content from code block: {turtle_content[:100]}...")
                    return turtle_content
        
        # Look for prefix declarations without code blocks
        prefix_pattern = "@prefix"
        if prefix_pattern in text:
            start_idx = text.find(prefix_pattern)
            # Try to find the end of the turtle content (look for markdown or plain text indicators)
            end_markers = ["\n\n", "\n## ", "\n# "]
            end_idx = len(text)
            
            for marker in end_markers:
                marker_idx = text.rfind(marker, start_idx)
                if marker_idx != -1:
                    end_idx = min(end_idx, marker_idx)
            
            turtle_content = text[start_idx:end_idx].strip()
            self.logger.debug(f"Extracted turtle content using prefix pattern: {turtle_content[:100]}...")
            return turtle_content
        
        # If Claude prefaced the response with explanatory text, try to find the start of the turtle content
        explanation_markers = [
            "Here is the ontology module in Turtle syntax",
            "Here's the ontology module",
            "Here is the complete ontology",
            "I've designed an ontology module"
        ]
        
        for marker in explanation_markers:
            if marker in text:
                marker_pos = text.find(marker)
                # Look for the first occurrence of '@prefix' after the marker
                prefix_pos = text.find("@prefix", marker_pos)
                if prefix_pos != -1:
                    # Find the end of the turtle content
                    turtle_content = text[prefix_pos:].strip()
                    self.logger.debug(f"Extracted turtle content after explanation: {turtle_content[:100]}...")
                    return turtle_content
        
        # Fallback: assume the whole response is intended to be Turtle
        self.logger.warning("Could not extract turtle content using standard methods, using fallback")
        return text
    
    def save_ontology(self, ontology: str, file_name: str) -> str:
        """
        Save the generated ontology to a file.
        
        Args:
            ontology: The ontology content in Turtle format
            file_name: Base name for the file (without extension)
            
        Returns:
            Path to the saved file
        """
        file_path = os.path.join(self.output_dir, f"{file_name}.ttl")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(ontology)
        
        self.logger.info(f"Saved ontology to {file_path}")
        return file_path
    
    def process_competency_questions(
        self, 
        competency_questions: List[Tuple[str, str]]
    ) -> Dict[str, str]:
        """
        Process multiple competency questions independently.
        
        Args:
            competency_questions: List of (question, story) tuples
            
        Returns:
            Dictionary mapping question IDs to generated ontologies
        """
        results = {}
        
        for i, (question, story) in enumerate(competency_questions):
            question_id = f"CQ{i+1}"
            self.logger.info(f"Processing {question_id}: {question}")
            
            ontology = self.design_ontology_for_cq(question, story)
            if ontology:
                self.save_ontology(ontology, question_id)
                results[question_id] = ontology
            
        return results