"""
Improved script to fix and clean up generated Turtle (.ttl) files.
"""
import os
import re
import sys
import logging
from rdflib import Graph
from config import ONTOLOGY_PREFIX

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_turtle_from_file(file_path):
    """
    Extract Turtle content from a file with problematic formatting.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Extracted Turtle content or None if extraction fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Handle binary string artifacts (strip b'')
        content = re.sub(r"b['\"](.*?)['\"]", r"\1", content)
        content = re.sub(r"b['\"]{2}(.*?)['\"]", r"\1", content)
        
        # Handle escaped sequences
        content = content.replace("\\n", "\n").replace("\\t", "\t").replace("\\'", "'").replace('\\"', '"')
        
        # Extract Turtle from markdown code blocks
        markdown_pattern = r"```(?:turtle|ttl)\s*([\s\S]*?)```"
        markdown_matches = re.findall(markdown_pattern, content)
        if markdown_matches:
            content = markdown_matches[0]
        
        # Look for @prefix declarations to identify the start of Turtle content
        prefix_pattern = r"@prefix\s+(?:\w+|:)\s*:"
        prefix_matches = re.findall(prefix_pattern, content)
        
        if prefix_matches:
            # Find the first prefix declaration
            first_prefix_pos = content.find(prefix_matches[0])
            if first_prefix_pos > 0:
                content = content[first_prefix_pos:]
        
        # If no prefixes found, look for explanation text and extract content after it
        if not prefix_matches:
            explanation_markers = [
                "Here is the ontology module in Turtle syntax",
                "Here's the ontology module",
                "Here is the complete ontology",
                "I've designed an ontology module"
            ]
            
            for marker in explanation_markers:
                if marker in content:
                    # Look for ontology declaration after the explanation
                    marker_pos = content.find(marker) + len(marker)
                    
                    # Look for ontology content indicators
                    turtle_indicators = ["@prefix", "<http", ":Ontology", "a owl:"]
                    for indicator in turtle_indicators:
                        indicator_pos = content.find(indicator, marker_pos)
                        if indicator_pos >= 0:
                            content = content[indicator_pos:]
                            break
        
        # Create a sample Turtle file with standard prefixes and check if we can extract anything useful
        if not content.strip().startswith("@prefix") and not content.strip().startswith("<http"):
            # Apply standard prefixes
            content = ONTOLOGY_PREFIX + "\n" + content
        
        # Clean up remaining issues
        content = clean_turtle_content(content)
        
        return content
    
    except Exception as e:
        logger.error(f"Error extracting Turtle from {file_path}: {str(e)}")
        return None

def clean_turtle_content(content):
    """
    Clean up Turtle content to fix common issues.
    
    Args:
        content: The Turtle content to clean
        
    Returns:
        Cleaned Turtle content
    """
    if not content:
        return None
    
    # Remove any non-TTL artifacts at the beginning and end
    lines = content.split("\n")
    clean_lines = []
    in_turtle = False
    
    for line in lines:
        # Skip until we find a line that looks like Turtle
        stripped = line.strip()
        if not in_turtle:
            if (stripped.startswith("@prefix") or 
                stripped.startswith("<http") or 
                stripped.startswith(":") or 
                "a owl:" in stripped):
                in_turtle = True
                clean_lines.append(line)
        else:
            # Once we're in Turtle content, include all lines except obvious non-Turtle
            if stripped.startswith("```") or stripped == "":
                continue
            clean_lines.append(line)
    
    content = "\n".join(clean_lines)
    
    # Fix common Turtle syntax issues
    
    # Ensure statements end with a period
    content = re.sub(r"(\S+\s+\S+\s+\S+)\s*\n(?![\s\}])", r"\1 .\n", content)
    
    # Fix unquoted string literals (common in rdfs:comment)
    def fix_quotes(match):
        prop = match.group(1)
        value = match.group(2)
        if '"' in value or value.startswith("http"):
            return prop
        return f'{prop} "{value}"'
    
    content = re.sub(r'(rdfs:comment|rdfs:label)\s+([^"][^;.]*?)(?=[;.])', fix_quotes, content)
    
    # Add missing semicolons in property lists
    content = re.sub(r"(\S+\s+\S+)\s*\n\s+", r"\1 ;\n    ", content)
    
    # Fix missing periods at the end of blocks
    content = re.sub(r"((?:\n\s+\S+\s+\S+)+)\s*\n(?=\S)", r"\1 .\n\n", content)
    
    # Fix incomplete triples at end of file
    if not content.strip().endswith('.'):
        content += ' .'
    
    return content

def create_basic_ontology():
    """
    Create a basic valid ontology for files that can't be fixed.
    
    Returns:
        A valid basic ontology in Turtle format
    """
    return """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ahmi: <http://example.org/adaptive-hmi#> .

<http://example.org/adaptive-hmi> a owl:Ontology ;
    rdfs:label "Adaptive Human-Machine Interface Ontology"@en ;
    rdfs:comment "An ontology for describing adaptive human-machine interfaces"@en .

ahmi:DriverState a owl:Class ;
    rdfs:label "Driver State"@en ;
    rdfs:comment "A state or condition of the driver"@en .

ahmi:DetectionMethod a owl:Class ;
    rdfs:label "Detection Method"@en ;
    rdfs:comment "A method or technique for detecting driver state"@en .

ahmi:detectedBy a owl:ObjectProperty ;
    rdfs:label "detected by"@en ;
    rdfs:comment "Relates a driver state to a detection method used to identify it"@en ;
    rdfs:domain ahmi:DriverState ;
    rdfs:range ahmi:DetectionMethod .
"""

def validate_turtle(content):
    """
    Validate if the content is valid Turtle.
    
    Args:
        content: Turtle content to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not content:
        return False
    
    try:
        g = Graph()
        g.parse(data=content, format="turtle")
        return True
    except Exception as e:
        logger.debug(f"Validation error: {str(e)}")
        return False

def fix_file(file_path, force_basic=False):
    """
    Fix a Turtle file.
    
    Args:
        file_path: Path to the file to fix
        force_basic: If True, replace with a basic valid ontology if fixing fails
        
    Returns:
        True if fixed successfully, False otherwise
    """
    try:
        # Check if the file is already valid
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        if validate_turtle(original_content):
            logger.info(f"File {file_path} is already valid Turtle")
            return True
        
        # Extract Turtle content
        turtle_content = extract_turtle_from_file(file_path)
        
        # If extraction failed or resulting content is not valid, try more aggressive cleaning
        if not turtle_content or not validate_turtle(turtle_content):
            logger.warning(f"Initial extraction failed for {file_path}, trying more aggressive extraction")
            
            # Try to manually extract prefixes and content
            prefixes = ""
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract prefixes
                prefix_patterns = re.findall(r"@prefix[^.]*\.", content)
                if prefix_patterns:
                    prefixes = "\n".join(prefix_patterns) + "\n\n"
                
                # Extract triples
                triple_pattern = re.compile(r"[:\w]+\s+[:\w]+\s+[:\w\"]+\s*[;.]")
                triples = triple_pattern.findall(content)
                
                if triples:
                    # Combine with prefixes and make a new attempt
                    turtle_content = prefixes + "\n".join(triples)
        
        # If still not valid and force_basic is enabled, use a basic ontology
        if (not turtle_content or not validate_turtle(turtle_content)) and force_basic:
            logger.warning(f"Could not extract valid Turtle from {file_path}, using basic ontology")
            turtle_content = create_basic_ontology()
        
        # If we have valid content, save it
        if turtle_content and validate_turtle(turtle_content):
            # Create backup of original file
            backup_path = file_path + '.bak'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Write the fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(turtle_content)
            
            logger.info(f"Successfully fixed {file_path} (original backed up to {backup_path})")
            return True
        else:
            logger.error(f"Failed to fix {file_path}: could not produce valid Turtle")
            return False
    
    except Exception as e:
        logger.error(f"Error fixing {file_path}: {str(e)}")
        return False

def main():
    # Check if a directory is provided
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = 'data/output'
    
    # Check if force basic option is enabled
    force_basic = '--force-basic' in sys.argv
    
    logger.info(f"Looking for .ttl files in {directory}")
    
    # Get all .ttl files
    ttl_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.ttl') and not file.endswith('.bak.ttl'):
                ttl_files.append(os.path.join(root, file))
    
    logger.info(f"Found {len(ttl_files)} .ttl files")
    
    # Fix each file
    fixed_count = 0
    for file_path in ttl_files:
        if fix_file(file_path, force_basic):
            fixed_count += 1
    
    logger.info(f"Fixed {fixed_count} out of {len(ttl_files)} files")
    
    if fixed_count < len(ttl_files) and not force_basic:
        logger.info("Some files could not be fixed. Try again with '--force-basic' to replace problematic files with basic valid ontologies.")

if __name__ == "__main__":
    main()