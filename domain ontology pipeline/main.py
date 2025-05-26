"""
Main script for generating ontologies from competency questions and ontology stories.
"""
import os
import json
import pandas as pd
import logging
from typing import List, Tuple, Dict
import argparse
from datetime import datetime
from rdflib import Graph

# Import from our modules
from src.api_client import ClaudeAPIClient
from src.pattern_integrator import PatternIntegrator
import config

# Set up logging
log_file = f"ontology_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.debug("Logging initialized")  # Test log message

def load_user_stories(file_path: str) -> Dict[str, str]:
    """
    Load user stories from a CSV file.
    
    Args:
        file_path: Path to the user stories CSV file
        
    Returns:
        Dictionary mapping story IDs to story texts
    """
    try:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            
            # Ensure the required columns exist
            required_cols = ['StoryID', 'UserStory']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"User stories CSV file missing required columns: {required_cols}")
                return {}
            
            # Create a dictionary mapping story IDs to story texts
            stories = {}
            for _, row in df.iterrows():
                stories[row['StoryID']] = row['UserStory']
            
            logger.info(f"Loaded {len(stories)} user stories from {file_path}")
            return stories
        else:
            logger.error(f"User stories file not found: {file_path}")
            return {}
    except Exception as e:
        logger.error(f"Error loading user stories: {str(e)}")
        return {}

def load_competency_questions(cq_file_path: str, stories: Dict[str, str]) -> List[Tuple[str, str]]:
    """
    Load competency questions and their user stories from CSV files.
    
    Args:
        cq_file_path: Path to the competency questions CSV file
        stories: Dictionary mapping story IDs to story texts
        
    Returns:
        List of (question, story) tuples
    """
    try:
        if os.path.exists(cq_file_path):
            df = pd.read_csv(cq_file_path)
            
            # Ensure the required columns exist
            required_cols = ['CQID', 'CompetencyQuestion', 'StoryID']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Competency questions CSV file missing required columns: {required_cols}")
                return _get_sample_questions()
            
            # Create the list of (question, story) tuples
            result = []
            for _, row in df.iterrows():
                question = row['CompetencyQuestion']
                story_id = row['StoryID']
                
                # Get the story text for this story ID
                story = stories.get(story_id)
                if story is None:
                    logger.warning(f"Story ID {story_id} not found for question {row['CQID']}")
                    story = f"No story found for ID: {story_id}"
                
                result.append((question, story))
            
            logger.info(f"Loaded {len(result)} competency questions from {cq_file_path}")
            return result
        else:
            logger.error(f"Competency questions file not found: {cq_file_path}")
            return _get_sample_questions()
    except Exception as e:
        logger.error(f"Error loading competency questions: {str(e)}")
        return _get_sample_questions()

def _get_sample_questions():
    """Return sample questions if loading from files fails."""
    return [
        ("What PostureState indicators signal a driver's transition into Drowsiness within the InattentionState class?", 
         "A driver named John was showing signs of drowsiness while driving. His head was nodding, and his eyes were closing frequently."),
        ("What Physiological Sensors are used to detect elevated cognitive load in drivers?", 
         "During a complex driving scenario, Sarah's cognitive load was monitored using various physiological sensors.")
    ]

class OntologyGenerator:
    """
    Generates ontologies from competency questions and ontology stories using the provided prompt
    and integrates appropriate ontology design patterns while preserving domain hierarchies.
    """
    
    def __init__(self, api_client: ClaudeAPIClient, pattern_integrator: PatternIntegrator):
        """
        Initialize the ontology generator.
        
        Args:
            api_client: The Claude API client for ontology generation
            pattern_integrator: The pattern integrator instance
        """
        self.api_client = api_client
        self.pattern_integrator = pattern_integrator
        self.prompt_template = config.ONTOLOGY_GENERATION_PROMPT
    
    def generate_ontology(self, competency_question: str, ontology_story: str) -> str:
        """
        Generate an ontology for a given competency question and story.
        
        Args:
            competency_question: The competency question
            ontology_story: The ontology story providing context
            
        Returns:
            Generated ontology in Turtle format
        """
        try:
            # Create the prompt by replacing placeholders
            prompt = self.prompt_template.format(
                CQ=competency_question,
                OS=ontology_story,
                pattern_guidance=config.ONTOLOGY_ELEMENTS
            )
            
            # Get the initial ontology from the API
            initial_ontology = self.api_client.generate_ontology(prompt)
            if not initial_ontology:
                logger.error("Failed to generate initial ontology")
                return None

            # Add standard prefixes if not present
            if not any(line.strip().startswith("@prefix") for line in initial_ontology.split("\n")):
                initial_ontology = config.ONTOLOGY_PREFIX + "\n" + initial_ontology

            try:
                # Parse the generated ontology
                g = Graph()
                g.parse(data=initial_ontology, format="turtle")
                logger.info("Successfully parsed ontology")
                return initial_ontology
            except Exception as e:
                logger.error(f"Error parsing ontology: {str(e)}")
                # Try to clean up the ontology text
                cleaned_ontology = self._clean_ontology_text(initial_ontology)
                try:
                    g = Graph()
                    g.parse(data=cleaned_ontology, format="turtle")
                    logger.info("Successfully parsed cleaned ontology")
                    return cleaned_ontology
                except Exception as e2:
                    logger.error(f"Error parsing cleaned ontology: {str(e2)}")
                    return None

        except Exception as e:
            logger.error(f"Error generating ontology: {str(e)}")
            return None
            
    def _clean_ontology_text(self, ontology: str) -> str:
        """Clean up ontology text to fix common formatting issues."""
        lines = []
        for line in ontology.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Fix common formatting issues
            if line.endswith(' ;'):
                lines.append(line)
            elif line.endswith(';'):
                lines.append(line + ' ')
            elif line.endswith(' .'):
                lines.append(line)
            elif line.endswith('.'):
                lines.append(line + ' ')
            else:
                lines.append(line + ' .')
                
        return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description="Generate ontologies from competency questions")
    parser.add_argument('--cq-file', type=str, help='Path to competency questions CSV file')
    parser.add_argument('--user-stories-file', type=str, help='Path to user stories CSV file')
    parser.add_argument('--output-dir', type=str, help='Output directory')
    args = parser.parse_args()
    
    # Override config with command line arguments if provided
    cq_file_path = args.cq_file or config.COMPETENCY_QUESTIONS_PATH
    user_stories_file_path = args.user_stories_file or config.USER_STORIES_PATH
    output_dir = args.output_dir or config.OUTPUT_DIR
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("Starting ontology generation from competency questions")
    
    # Initialize the API client
    api_client = ClaudeAPIClient(config.API_URL)
    
    # Initialize the pattern integrator with API client
    pattern_integrator = PatternIntegrator(config.PATTERNS_DIR, api_client=api_client)
    
    # Initialize the ontology generator
    generator = OntologyGenerator(api_client, pattern_integrator)
    
    # Load user stories
    stories = load_user_stories(user_stories_file_path)
    
    # Load competency questions
    competency_questions = load_competency_questions(cq_file_path, stories)
    
    # Process each competency question
    for i, (question, story) in enumerate(competency_questions):
        logger.info(f"Processing competency question {i+1}")
        
        # Generate ontology
        ontology = generator.generate_ontology(question, story)
        
        if ontology:
            # Save the ontology
            output_path = os.path.join(output_dir, f"ontology_cq{i+1}.ttl")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(ontology)
            logger.info(f"Saved ontology to {output_path}")
        else:
            logger.error(f"Failed to generate ontology for question {i+1}")
    
    logger.info("Ontology generation completed")

if __name__ == "__main__":
    main()