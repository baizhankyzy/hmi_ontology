"""
Main script for generating the Adaptive HMI ontology using Ontogenia prompting.
"""
import os
import json
import pandas as pd
import logging
from typing import List, Tuple, Dict
import argparse
from datetime import datetime

# Import from our modules
from src.api_client import ClaudeAPIClient
from src.ontogenia import OntogeniaPrompting
from src.improved_ontology_merger import ImprovedOntologyMerger
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"ontology_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
                    # Use a placeholder story
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
         "Sample user story about a driver experiencing drowsiness..."),
        ("What Physiological Sensors are used to detect elevated cognitive load in drivers?", 
         "Sample user story about a driver experiencing cognitive load..."),
        ("What Display Types are most appropriate for elderly drivers?",
         "Sample user story about an elderly driver...")
    ]

def main():
    parser = argparse.ArgumentParser(description="Generate Adaptive HMI Ontology")
    parser.add_argument('--cq-file', type=str, help='Path to competency questions CSV file')
    parser.add_argument('--user-stories-file', type=str, help='Path to user stories CSV file')
    parser.add_argument('--patterns-file', type=str, help='Path to patterns CSV file')
    parser.add_argument('--output-dir', type=str, help='Output directory')
    parser.add_argument('--num-questions', type=int, default=None, help='Number of questions to process (default: all)')
    parser.add_argument('--use-situation-event', action='store_true', help='Emphasize situation-event modeling')
    args = parser.parse_args()
    
    # Override config with command line arguments if provided
    cq_file_path = args.cq_file or config.COMPETENCY_QUESTIONS_PATH
    user_stories_file_path = args.user_stories_file or config.USER_STORIES_PATH
    patterns_file_path = args.patterns_file or config.PATTERNS_PATH
    output_dir = args.output_dir or config.OUTPUT_DIR
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("Starting Adaptive HMI Ontology generation")
    
    # If specified, modify the metacognitive procedure to emphasize situation-event modeling
    if args.use_situation_event:
        logger.info("Emphasizing situation-event modeling in the metacognitive procedure")
        config.METACOGNITIVE_PROCEDURE = config.METACOGNITIVE_PROCEDURE.replace(
            "Pay special attention to driver states, vehicle systems, feedback modalities, and environmental factors",
            "Pay special attention to driver states, vehicle systems, feedback modalities, environmental factors, and the distinction between events and situations"
        )
    
    # Initialize the API client
    api_client = ClaudeAPIClient(config.API_URL)
    
    # Initialize the Ontogenia prompting system
    ontogenia = OntogeniaPrompting(
        api_client=api_client,
        patterns_path=patterns_file_path,
        ontology_elements=config.ONTOLOGY_ELEMENTS,
        metacognitive_procedure=config.METACOGNITIVE_PROCEDURE,
        output_dir=output_dir
    )
    
    # Load user stories
    stories = load_user_stories(user_stories_file_path)
    
    # Load competency questions
    competency_questions = load_competency_questions(cq_file_path, stories)
    
    # Limit the number of questions if specified
    if args.num_questions is not None and args.num_questions > 0:
        competency_questions = competency_questions[:args.num_questions]
        logger.info(f"Processing {args.num_questions} competency questions")
    else:
        logger.info(f"Processing all {len(competency_questions)} competency questions")
    
    # Process each competency question independently
    ontologies = ontogenia.process_competency_questions(competency_questions)
    
    if ontologies:
        # Initialize the ontology merger
        merger = ImprovedOntologyMerger()
        
        # Merge the ontologies
        merged_ontology = merger.merge_ontologies(ontologies)
        
        if merged_ontology:
            # Save the merged ontology
            merged_path = os.path.join(output_dir, "adaptive_hmi_merged.ttl")
            with open(merged_path, "w", encoding="utf-8") as f:
                f.write(merged_ontology)
            
            logger.info(f"Saved merged ontology to {merged_path}")
            
            # Get and log statistics
            stats = merger.get_statistics()
            logger.info(f"Ontology statistics: {stats}")
            
            # Save statistics to JSON
            stats_path = os.path.join(output_dir, "statistics.json")
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
            
            logger.info(f"Saved statistics to {stats_path}")
        else:
            logger.error("Failed to merge ontologies")
    else:
        logger.error("No ontologies were generated")
    
    logger.info("Adaptive HMI Ontology generation completed")

if __name__ == "__main__":
    main()