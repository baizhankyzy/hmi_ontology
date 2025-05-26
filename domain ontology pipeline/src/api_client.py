"""
Client for interacting with the Claude API via AWS Lambda.
"""
import json
import requests
import time
from typing import Dict, Any, Optional, List, Tuple
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ClaudeAPIClient:
    def __init__(self, api_url: str):
        """
        Initialize the Claude API client.
        
        Args:
            api_url: The URL for the Claude API Lambda endpoint
        """
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug(f"Initialized API client with URL: {api_url}")
    
    def query(self, prompt: str) -> Optional[str]:
        """
        Send a query to the Claude API.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            The API response text or None if the request fails
        """
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            data = {
                'prompt': prompt
            }
            
            self.logger.info("Sending request to API")
            response = requests.post(self.api_url, headers=headers, json=data)
            
            if response.status_code == 200:
                self.logger.debug(f"Response status: {response.status_code}")
                self.logger.debug(f"Response headers: {response.headers}")
                
                try:
                    response_data = response.json()
                    if 'data' in response_data and 'answer' in response_data['data']:
                        return response_data['data']['answer']
                    else:
                        self.logger.error("Unexpected response format")
                        return None
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse JSON response")
                    return None
            else:
                self.logger.error(f"Request failed with status code: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error making API request: {str(e)}")
            return None
    
    def generate_ontology(self, prompt: str) -> Optional[str]:
        """
        Generate an ontology using the Claude API via Lambda.
        
        Args:
            prompt: The ontology generation prompt containing CQ and OS
            
        Returns:
            Generated ontology in Turtle format or None if generation fails
        """
        try:
            response = self.query(prompt)
            
            if not response:
                self.logger.error("No response received from API")
                return None
                
            # Log the full response for debugging
            self.logger.debug(f"Raw API response: {response}")
            
            # First try to find a code block with turtle syntax
            turtle_blocks = re.findall(r"```turtle\n(.*?)```", response, re.DOTALL)
            
            if turtle_blocks:
                # Use the first turtle block found
                ontology = turtle_blocks[0].strip()
                self.logger.info("Found Turtle syntax in code block")
            else:
                # If no code blocks found, try to extract based on common markers
                if "@prefix" in response:
                    # Find the start of the ontology content
                    start_idx = response.find("@prefix")
                    ontology = response[start_idx:].strip()
                    self.logger.info("Extracted Turtle syntax based on prefix markers")
                else:
                    self.logger.error("Could not find valid ontology content in response")
                    return None
            
            # Clean up the ontology text
            cleaned_lines = []
            current_subject = None
            in_restriction = False
            restriction_depth = 0
            
            # Remove any control characters
            ontology = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', ontology)
            
            for line in ontology.split('\n'):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                    
                # Handle prefixes and base
                if line.startswith('@prefix') or line.startswith('@base'):
                    cleaned_lines.append(line)
                    continue
                    
                # New subject
                if not line.startswith(' ') and ':' in line:
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        current_subject = parts[0]
                        predicates = parts[1].strip()
                        if predicates:
                            cleaned_lines.append(f"{current_subject} {predicates}")
                        else:
                            cleaned_lines.append(f"{current_subject} a owl:Class ;")
                    else:
                        current_subject = line
                        cleaned_lines.append(f"{current_subject} a owl:Class ;")
                    continue
                    
                # Handle restrictions
                if '[' in line:
                    in_restriction = True
                    restriction_depth += line.count('[')
                    cleaned_lines.append('    ' + line)
                    continue
                    
                if in_restriction:
                    if ']' in line:
                        restriction_depth -= line.count(']')
                        if restriction_depth == 0:
                            in_restriction = False
                            if not line.strip().endswith(';'):
                                line = line.rstrip('.') + ' ;'
                            cleaned_lines.append('    ' + line)
                        else:
                            cleaned_lines.append('        ' + line)
                    else:
                        cleaned_lines.append('        ' + line)
                    continue
                    
                # Regular property
                if ':' in line:
                    # Ensure property lines end with semicolon
                    if not line.strip().endswith(';') and not line.strip().endswith('.'):
                        line = line + ' ;'
                    cleaned_lines.append('    ' + line)
                    continue
                    
                # Other lines
                cleaned_lines.append('    ' + line)
            
            # Close the last subject
            if cleaned_lines:
                cleaned_lines[-1] = cleaned_lines[-1].rstrip(' ;') + ' .'
            
            ontology = '\n'.join(cleaned_lines)
            self.logger.info("Successfully cleaned ontology text")
            return ontology
            
        except Exception as e:
            self.logger.error(f"Error generating ontology: {str(e)}")
            return None

    def analyze_patterns(self, 
                        competency_question: str, 
                        user_story: str, 
                        pattern_examples: str) -> List[Tuple[str, str]]:
        """
        Analyze how patterns can be used for modeling based on examples.
        
        Args:
            competency_question: The competency question to analyze
            user_story: The user story providing context
            pattern_examples: Examples of pattern usage
            
        Returns:
            List of tuples containing (pattern_name, usage_explanation)
        """
        prompt = f"""
Given the following competency question and user story, analyze how ontology design patterns can be applied based on the provided examples.

Competency Question:
{competency_question}

User Story:
{user_story}

Pattern Usage Examples:
{pattern_examples}

Task:
1. Identify which patterns from the examples are relevant for modeling this competency question and user story
2. For each relevant pattern, explain:
   - Why it's applicable
   - How it should be used in this specific case
   - What elements from the CQ/story map to pattern components
   - Any adaptations needed

Format your response as a list of pattern applications, each containing:
- Pattern name
- Justification
- Specific mapping details
- Implementation guidance

Focus on practical, concrete pattern applications rather than theoretical possibilities.
"""
        response = self.query(prompt)
        if not response:
            return []
            
        # Parse the response to extract pattern recommendations
        pattern_recommendations = []
        current_pattern = None
        current_explanation = []
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Look for pattern headers (usually in format "Pattern: Name" or "1. Pattern Name:")
            if re.match(r'^(?:\d+\.)?\s*(?:Pattern:)?\s*([A-Za-z-]+)\s*(?:Pattern)?:?$', line):
                # Save previous pattern if exists
                if current_pattern and current_explanation:
                    pattern_recommendations.append(
                        (current_pattern, '\n'.join(current_explanation))
                    )
                # Start new pattern
                current_pattern = re.match(r'^(?:\d+\.)?\s*(?:Pattern:)?\s*([A-Za-z-]+)\s*(?:Pattern)?:?$', line).group(1)
                current_explanation = []
            elif current_pattern:
                current_explanation.append(line)
        
        # Add last pattern
        if current_pattern and current_explanation:
            pattern_recommendations.append(
                (current_pattern, '\n'.join(current_explanation))
            )
            
        return pattern_recommendations