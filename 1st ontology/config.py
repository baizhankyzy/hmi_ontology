"""
Configuration settings for the Adaptive HMI Ontology generation.
"""

# API Configuration
API_URL = "https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/"

# Ontology Configuration
ONTOLOGY_PREFIX = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ahmi: <http://example.org/adaptive-hmi#> .

<http://example.org/adaptive-hmi> a owl:Ontology ;
    rdfs:label "Adaptive Human-Machine Interface Ontology"@en ;
    rdfs:comment "An ontology for describing adaptive human-machine interfaces with a focus on driver state detection and multimodal feedback"@en .
"""

# File paths
PATTERNS_PATH = "data/patterns.csv"
COMPETENCY_QUESTIONS_PATH = "data/competency_questions.csv"
USER_STORIES_PATH = "data/user_stories.csv"
OUTPUT_DIR = "data/output/"

# Ontogenia prompting configuration
ONTOLOGY_ELEMENTS = """
Classes, Object Properties, Datatype Properties. Object properties need to have domain and range. 
All of them need to have an explanation in the rdfs:label. You also need to add restrictions, 
and subclasses for both classes and object properties when applicable.
"""

# Metacognitive Prompting Procedure for Ontology Design
METACOGNITIVE_PROCEDURE = """
As an ontology engineer, follow these steps to design an ontology module:

1. ANALYZE THE COMPETENCY QUESTION:
   - Understand the competency question (CQ) thoroughly
   - Identify the key components that need to be modeled
   - Consider the user story to establish context and extract domain terminology
   - Determine if the question is about events themselves or different views (situations) of those events

2. IDENTIFY THE CONTEXT:
   - Define the scope and domain of the ontology
   - Consider the boundaries of what should be included
   - Identify the key actors, actions, and relationships in the user story
   - Distinguish between the descriptions (conceptualizations) and the situations they define

3. DECOMPOSE THE COMPETENCY QUESTION:
   - Break down the CQ into subject, predicate, object, and predicate nominative
   - Map these elements to ontological constructs:
     * Subjects and objects → Classes
     * Predicates → Object Properties
     * Descriptive attributes → Datatype Properties
   - Pay special attention to driver states, vehicle systems, feedback modalities, and environmental factors
   - Consider whether to model aspects as events (with their identity) or as situations (views on events)

4. DETERMINE SUBCLASS RELATIONSHIPS:
   - Establish "is-a" relationships using rdfs:subClassOf
   - Create a hierarchical structure where appropriate
   - Organize driver states, detection methods, feedback types, and adaptation strategies into coherent taxonomies
   - Classify events as processes when they are considered in their evolution

5. EXTEND THE ONTOLOGY WITH RESTRICTIONS:
   - Apply restrictions like owl:allValuesFrom, owl:hasValue, and owl:someValuesFrom
   - Define cardinality with owl:minCardinality, owl:maxCardinality, or owl:cardinality
   - Use owl:Restriction to define anonymous classes
   - Create appropriate restrictions for relationships between drivers, vehicles, and contexts
   - Define how situations observe or interpret events

6. DEFINE EQUIVALENT AND DISJOINT CLASSES:
   - Use owl:equivalentClass for classes with the same instances
   - Use owl:disjointWith for mutually exclusive classes
   - Identify states or conditions that cannot co-exist
   - Define disjoint relationships between events and objects

7. INTEGRATE AND REFINE:
   - Review all interrelationships for logical consistency
   - Ensure completeness in addressing the competency question
   - Make sure the ontology captures the key aspects of the user story
   - Check that different views of events are properly modeled as situations

8. VALIDATE AND EXPLAIN:
   - Confirm the ontology answers all CQs
   - Explain the reasoning behind each ontological element
   - Verify that the ontology can represent the scenarios described in the user story
   - Ensure that the ontology allows for multiple interpretations of the same events

9. EVALUATE CONFIDENCE AND TEST:
   - Test the ontology with instances
   - Assess confidence based on how well the ontology performs
   - Consider how well the ontology captures the adaptive aspects described in the user story
   - Verify that the ontology can distinguish between events themselves and different ways of viewing them
"""