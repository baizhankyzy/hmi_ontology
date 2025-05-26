"""
Module for generating ontologies using the Claude API and integrating ontology design patterns.
"""
import logging
from typing import Optional
from rdflib import Graph

from .api_client import ClaudeAPIClient
from .pattern_integrator import PatternIntegrator
import config

logger = logging.getLogger(__name__)

class OntologyGenerator:
    """
    Generates ontologies from competency questions and ontology stories using the provided prompt
    and integrates appropriate ontology design patterns.
    """
    
    def __init__(self, api_client: ClaudeAPIClient):
        """
        Initialize the ontology generator.
        
        Args:
            api_client: The Claude API client for ontology generation
        """
        self.api_client = api_client
        self.pattern_integrator = PatternIntegrator(config.PATTERNS_DIR)
        self.prompt_template = config.ONTOLOGY_GENERATION_PROMPT
        
    def generate_ontology(self, competency_question: str, ontology_story: str) -> Optional[str]:
        """
        Generate an ontology for a given competency question and story.
        
        Args:
            competency_question: The competency question
            ontology_story: The ontology story providing context
            
        Returns:
            Generated ontology in Turtle format
        """
        try:
            # Analyze both competency question and story for relevant patterns
            relevant_patterns = self.pattern_integrator.analyze_competency_question_and_story(
                competency_question=competency_question,
                user_story=ontology_story
            )
            
            # Get pattern guidance with examples for the prompt
            pattern_guidance = self.pattern_integrator.get_pattern_prompt(
                patterns=relevant_patterns,
                include_examples=True
            )
            
            # Create the prompt by replacing placeholders
            prompt = self.prompt_template.format(
                CQ=competency_question,
                OS=ontology_story,
                pattern_guidance=pattern_guidance
            )
            
            # Get the initial ontology from the API
            initial_ontology = self.api_client.generate_ontology(prompt)
            if not initial_ontology:
                return None

            # Parse the generated ontology
            g = Graph()
            g.parse(data=initial_ontology, format="turtle")
            
            # Integrate relevant patterns
            for pattern in relevant_patterns:
                logger.info(f"Integrating pattern: {pattern}")
                g = self.pattern_integrator.integrate_pattern(g, pattern, config.BASE_URI)
                if g is None:
                    logger.error(f"Failed to integrate pattern: {pattern}")
                    continue
                    
            # Serialize the final ontology
            final_ontology = g.serialize(format="turtle")
            
            return final_ontology
            
        except Exception as e:
            logger.error(f"Error generating ontology: {str(e)}")
            return None
    
    def _ensure_prefixes(self, ontology: str) -> str:
        """Ensure all necessary prefixes are present in the ontology."""
        if not ontology:
            return ontology
            
        # Check if the ontology already has prefix declarations
        has_prefixes = any(line.strip().startswith("@prefix") for line in ontology.split("\n"))
        
        if not has_prefixes:
            # Add standard prefixes
            ontology = config.ONTOLOGY_PREFIX + "\n" + ontology
            
        return ontology 