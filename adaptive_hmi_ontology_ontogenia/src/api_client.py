"""
Client for interacting with the Claude API.
"""
import json
import requests
import time
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ClaudeAPIClient:
    def __init__(self, api_url: str):
        """
        Initialize the Claude API client.
        
        Args:
            api_url: The URL for the Claude API endpoint
        """
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
    
    def query(self, prompt: str, max_retries: int = 3, retry_delay: int = 2) -> Optional[str]:
        """
        Send a prompt to the Claude API and get the response.
        
        Args:
            prompt: The prompt to send to the API
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            The response from the API or None if all retries fail
        """
        payload = {
            "prompt": prompt
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Sending request to API (attempt {attempt+1}/{max_retries})")
                response = requests.post(self.api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("data", {}).get("answer")
                    
                    if answer:
                        # Log the first 100 characters of the response for debugging
                        self.logger.debug(f"Response (first 100 chars): {answer[:100]}...")
                        
                        # Clean up any potential binary string artifacts
                        if answer.startswith("b'") and answer.endswith("'"):
                            answer = answer[2:-1]
                            answer = answer.replace("\\n", "\n").replace("\\t", "\t").replace("\\'", "'")
                        
                        return answer
                    else:
                        self.logger.warning("API response doesn't contain an answer")
                else:
                    self.logger.warning(f"API request failed with status code {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.logger.error(f"Error during API request: {str(e)}")
            
            if attempt < max_retries - 1:
                self.logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Exponential backoff
                retry_delay *= 2
        
        self.logger.error("All API request attempts failed")
        return None