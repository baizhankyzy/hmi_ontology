from rdflib import Graph, Namespace
from pathlib import Path

# Initialize graph and namespaces
g = Graph()
DMS = Namespace("http://www.example.org/test#")
g.bind("dms", DMS)

# Load the enriched ontology
project_root = Path(__file__).parent.parent
ontology_path = project_root / "output/test_100rows_ontology.ttl"
g.parse(ontology_path, format="turtle")

def run_query(query, description):
    """Run a SPARQL query and print results with description."""
    print(f"\n{'-'*80}")
    print(f"Query: {description}")
    print(f"{'-'*80}")
    
    results = g.query(query)
    for row in results:
        print(row)
    print(f"Total results: {len(list(results))}")

# Query 1: Get all voice assistant capabilities
voice_assistant_query = """
PREFIX dms: <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?assistant ?capability
WHERE {
    ?assistant a ?type .
    ?assistant ?relation ?capability .
    FILTER(REGEX(STR(?type), "VoiceAssistant$"))
}
"""
run_query(voice_assistant_query, "Voice Assistant Capabilities")

# Query 2: Get all emotion regulation techniques and their effects
emotion_regulation_query = """
PREFIX dms: <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?technique ?effect
WHERE {
    ?technique a ?type .
    ?technique ?relation ?effect .
    FILTER(REGEX(STR(?type), "EmotionRegulation(Technique)?$") || 
           REGEX(STR(?type), "EmotionalRegulation(Technique)?$"))
}
"""
run_query(emotion_regulation_query, "Emotion Regulation Techniques and Effects")

# Query 3: Get all feedback types and their characteristics
feedback_query = """
PREFIX dms: <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?feedbackType ?characteristic
WHERE {
    ?feedbackType a ?type .
    ?feedbackType ?relation ?characteristic .
    FILTER(REGEX(STR(?type), "Feedback(Type)?$"))
}
"""
run_query(feedback_query, "Feedback Types and Characteristics")

# Query 4: Get navigation system features and their impacts
navigation_query = """
PREFIX dms: <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?feature ?impact
WHERE {
    ?feature a ?type .
    ?feature ?relation ?impact .
    FILTER(REGEX(STR(?type), "Navigation(System)?$") || 
           REGEX(STR(?type), "Route$"))
}
"""
run_query(navigation_query, "Navigation System Features and Impacts")

# Query 5: Get emotional states and their influences
emotional_states_query = """
PREFIX dms: <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?emotionalState ?influence
WHERE {
    ?emotionalState a ?type .
    ?emotionalState ?relation ?influence .
    FILTER(REGEX(STR(?type), "EmotionalState$") || 
           REGEX(STR(?type), "Emotion$"))
}
"""
run_query(emotional_states_query, "Emotional States and Their Influences")

# Query 6: Get all HMI elements and their properties
hmi_query = """
PREFIX dms: <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?hmiElement ?property
WHERE {
    ?hmiElement a ?type .
    ?hmiElement ?relation ?property .
    FILTER(REGEX(STR(?type), "HMI.*$") || 
           REGEX(STR(?type), "Interface$"))
}
"""
run_query(hmi_query, "HMI Elements and Properties")

# Query 7: Get relationships between emotions and driving performance
emotion_performance_query = """
PREFIX dms: <http://www.example.org/test#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?emotion ?relation ?performance
WHERE {
    ?emotion a ?emotionType .
    ?emotion ?relation ?performance .
    ?performance a ?perfType .
    FILTER(REGEX(STR(?emotionType), "Emotion(alState)?$"))
    FILTER(REGEX(STR(?perfType), "DrivingPerformance$"))
}
"""
run_query(emotion_performance_query, "Emotion-Performance Relationships")

print("\nAll queries completed successfully!") 