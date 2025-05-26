"""
Configuration settings for the Adaptive HMI Ontology generation.
"""

import os

# API Configuration
API_URL = os.getenv('CLAUDE_API_URL', 'https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/')

# Ontology Configuration
ONTOLOGY_PREFIX = """
@prefix : <http://example.org/ontology#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix ssn: <http://www.w3.org/ns/ssn/> .
@prefix schema: <http://schema.org/> .
@prefix prov: <http://www.w3.org/ns/prov#> .

<http://www.example.org/test#> a owl:Ontology .
"""

# File paths
PATTERNS_PATH = "data/patterns.csv"
COMPETENCY_QUESTIONS_PATH = "data/competency_questions.csv"
USER_STORIES_PATH = "data/user_stories.csv"
OUTPUT_DIR = "data/output/"

# Pattern Configuration
PATTERNS_DIR = "data/patterns"
BASE_URI = "http://example.org/adaptive-hmi#"

# Update the ontology generation prompt to include pattern guidance
ONTOLOGY_GENERATION_PROMPT = """
Given the following competency question and user story, generate an ontology in Turtle format that:
1. Preserves the hierarchical relationships and domain structure from the input
2. Integrates appropriate ontology design patterns while maintaining the original hierarchy
3. Uses clear and consistent naming conventions
4. Includes comprehensive annotations documenting concept origins and pattern usage

Competency Question:
{CQ}

User Story:
{OS}

Pattern Integration Guidelines:
{pattern_guidance}

Additional Requirements:
1. Maintain the hierarchical relationships between concepts as they appear in the competency question and user story
2. Use rdfs:subClassOf to represent hierarchical relationships
3. Document any adaptations made to patterns to preserve domain structure
4. Add dct:source annotations to indicate concept origins
5. Add dct:relation annotations to document pattern usage
6. Use ssn:observes for sensor observations
7. Use prov:wasGeneratedBy for derived information
8. Include rdfs:label and rdfs:comment for documentation

Please generate the ontology in Turtle format, ensuring all relationships from the input are preserved.
"""

# Pattern Analysis Prompt
PATTERN_ANALYSIS_PROMPT = """
Analyze how the following ontology design patterns can be applied while preserving the domain hierarchy:

Competency Question:
{CQ}

User Story:
{OS}

Available Patterns:
{patterns}

For each relevant pattern:
1. Identify which domain concepts map to pattern elements
2. Explain how the pattern's structure aligns with or differs from the domain hierarchy
3. Describe any adaptations needed to preserve domain relationships
4. Provide specific examples of how the pattern should be applied

Focus on maintaining the original semantic structure while leveraging pattern benefits.
"""

# Ontology Elements Requirements
ONTOLOGY_ELEMENTS = """
1. Use only T-Box (no instances)
2. Include all entities from CQ
3. Use restrictions where implied by CQ
4. Ensure self-contained output
5. Follow Turtle syntax
6. Include proper domain and range for properties
7. Use rdfs:label for readability
8. Include appropriate cardinality restrictions
"""

# Metacognitive Prompting Procedure for Ontology Design
METACOGNITIVE_PROCEDURE = """
1. ANALYZE INPUT:
   - Parse the Competency Question (CQ) carefully
   - Understand the Ontology Story (OS) context
   - Identify key concepts and relationships

2. IDENTIFY COMPONENTS:
   - Extract classes from nouns
   - Identify object properties from verbs and relationships
   - Determine datatype properties for attributes
   - Note implied restrictions and cardinalities

3. STRUCTURE DESIGN:
   - Define class hierarchy
   - Establish property domains and ranges
   - Add appropriate restrictions
   - Ensure all CQ elements are covered

4. VALIDATE OUTPUT:
   - Verify Turtle syntax correctness
   - Check for complete coverage of CQ
   - Ensure no A-Box (instances) included
   - Confirm self-contained nature

5. OPTIMIZE:
   - Remove redundant elements
   - Standardize naming conventions
   - Add clear labels
   - Verify restriction logic
"""

# Logging Configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'DEBUG'