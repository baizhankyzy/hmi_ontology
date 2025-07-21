import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API endpoint from the config
API_URL = "https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/"

def generate_ontology(competency_question: str, ontology_story: str = "") -> str:
    """
    Generate an ontology using the Claude API based on a competency question and ontology story.
    
    Args:
        competency_question (str): The competency question
        ontology_story (str): The ontology story (optional)
        
    Returns:
        str: The generated ontology in Turtle format
    """
    # Construct the prompt
    prompt = """
<instruction>
You are a helpful assistant designed to generate ontologies. You receive a Competency Question (CQ) and an Ontology Story (OS). \n
Based on CQ, which is a requirement for the ontology, and OS, which tells you what the context of the ontology is, your task is generating one ontology (O). The goal is to generate O that models the CQ properly. This means there is a way to write a SPARQL query to extract the answer to this CQ in O.  \n
Use the following prefixes: \n
@prefix : <http://www.example.org/test#> .\n
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n

Don't put any A-Box (instances) in the ontology and just generate the OWL file using Turtle syntax. Include the entities mentioned in the CQ. Remember to use restrictions when the CQ implies it. The output should be self-contained without any errors. Outside of the code box don't put any comment.
</instruction>
<example>
I will give you an example now:
CQ: For an aquatic resource, what species, in what fishing areas, climatic zones, bottom types, depth zones, geo forms, horizontal and vertical distribution, and for what standardized abundance level, exploitation state and rate, have been observed? for what reference year? At what year the observation has been recorded?

OS: The aquatic resource for Skipjack tuna in Northern Atlantic in 2004 (as reported in 2008) was observed with low abundance level. 

O:
@prefix : <http://www.example.org/test#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<http://www.example.org/test#> a owl:Ontology .
:AquaticResource a owl:Class ;
	rdfs:label "Aquatic Resource" ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :hasObservation ;
    	owl:someValuesFrom :AquaticResourceObservation
	] .
:AquaticResourceObservation a owl:Class ;
	rdfs:label "Aquatic Resource Observation" ;
	rdfs:subClassOf :Observation ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :isObservationOf ;
    	owl:onClass :AquaticResource ;
    	owl:qualifiedCardinality "1"^^xsd:nonNegativeInteger
	] ;
    
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :forReferenceYear ;
    	owl:onDataRange xsd:int ;
    	owl:qualifiedCardinality "1"^^xsd:nonNegativeInteger
	] ;

	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :hasReportingYear ;
    	owl:onDataRange xsd:int ;
    	owl:qualifiedCardinality "1"^^xsd:nonNegativeInteger
	] ;
    
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofSpecies ;
    	owl:onClass :Species ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofFishingArea ;
    	owl:onClass :FAO_fishing_area ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofClimaticZone ;
    	owl:onClass :ClimaticZone ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofBottomType ;
    	owl:onClass :BottomType ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofDepthZone ;
    	owl:onClass :DepthZone ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofGeoForm ;
    	owl:onClass :GeoForm ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofHorizontalDistribution ;
    	owl:onClass :HorizontalDistribution ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofVerticalDistribution ;
    	owl:onClass :VerticalDistribution ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofStdAbundanceLevel ;
    	owl:onClass :StdAbundanceLevel ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofStdExploitationState ;
    	owl:onClass :StdExploitationState ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] ;
	rdfs:subClassOf [
    	a owl:Restriction ;
    	owl:onProperty :ofStdExploitationRate ;
    	owl:onClass :StdExploitationRate ;
    	owl:minQualifiedCardinality "0"^^xsd:nonNegativeInteger
	] .
:Species a owl:Class .
:FAO_fishing_area a owl:Class .
:ClimaticZone a owl:Class .
:BottomType a owl:Class .
:DepthZone a owl:Class .
:GeoForm a owl:Class .
:HorizontalDistribution a owl:Class .
:VerticalDistribution a owl:Class .
:StdAbundanceLevel a owl:Class .
:StdExploitationState a owl:Class .
:StdExploitationRate a owl:Class .
:ofSpecies a owl:ObjectProperty ;
	rdfs:label "ofSpecies" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :Species .

:ofFishingArea a owl:ObjectProperty ;
	rdfs:label "ofFishingArea" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :FAO_fishing_area .

:ofClimaticZone a owl:ObjectProperty ;
	rdfs:label "ofClimaticZone" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :ClimaticZone .

:ofBottomType a owl:ObjectProperty ;
	rdfs:label "ofBottomType" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :BottomType .

:ofDepthZone a owl:ObjectProperty ;
	rdfs:label "ofDepthZone" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :DepthZone .

:ofGeoForm a owl:ObjectProperty ;
	rdfs:label "ofGeoForm" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :GeoForm .

:ofHorizontalDistribution a owl:ObjectProperty ;
	rdfs:label "ofHorizontalDistribution" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :HorizontalDistribution .

:ofVerticalDistribution a owl:ObjectProperty ;
	rdfs:label "ofVerticalDistribution" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :VerticalDistribution .

:ofStdAbundanceLevel a owl:ObjectProperty ;
	rdfs:label "ofStdAbundanceLevel" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :StdAbundanceLevel .

:ofStdExploitationState a owl:ObjectProperty ;
	rdfs:label "ofStdExploitationState" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :StdExploitationState .

:ofStdExploitationRate a owl:ObjectProperty ;
	rdfs:label "ofStdExploitationRate" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range :StdExploitationRate .
:forReferenceYear a owl:DatatypeProperty ;
	rdfs:label "forReferenceYear" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range xsd:int .

:hasReportingYear a owl:DatatypeProperty ;
	rdfs:label "hasReportingYear" ;
	rdfs:domain :AquaticResourceObservation ;
	rdfs:range xsd:int .
:hasObservation a owl:ObjectProperty .
:isObservationOf a owl:ObjectProperty .
:Observation a owl:Class .



</example>

CQ: {CQ}
OS: {OS}
O: 
"""
    
    # Format the prompt with the provided CQ and OS
    formatted_prompt = prompt.format(CQ=competency_question, OS=ontology_story)
    
    try:
        # Prepare the request payload
        payload = {
            "prompt": formatted_prompt,
            "temperature": 0.0,  # Keep temperature at 0.0 for consistent results
            "max_tokens": 2000   # Adjust based on expected response length
        }
        
        # Make the API request
        logger.info("Sending request to Claude API...")
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        logger.info(f"API Response: {json.dumps(result, indent=2)}")
        
        # Extract the ontology from the response
        ontology = result.get('data', {}).get('answer', '')  # Get the answer from data
        
        if not ontology:
            logger.error(f"Unexpected API response format: {result}")
            raise ValueError("No ontology generated in the response")
            
        logger.info("Successfully generated ontology")
        return ontology
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making API request: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing API response: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

def main():
    # Example usage with a specific competency question and ontology story
    competency_question = """What PostureState types show that driver's Cognitive state is Drowsiness which is an individual of InattentionState class(which is a subclass of Cognitive State class)?"""
    
    ontology_story = """Michael is driving home after a long workday, traveling on a highway for over two hours. As night falls, his PostureState begins to change—his Head Position shows nodding patterns, and the vehicle's Detection methodologies using Driver-facing Visual sensors detect reduced Eye tracking metrics and longer blink durations. The Physiological Sensors and Behavioral analysis systems classify these patterns as indicators of Drowsiness and Fatigue, both subclasses of InattentionState within the CognitiveState category of Driver parameters."""
    
    try:
        ontology = generate_ontology(competency_question, ontology_story)
        print("\nGenerated Ontology:")
        print(ontology)
        
        # Save to file
        with open("generated_ontology.ttl", "w") as f:
            f.write(ontology)
            logger.info("Saved ontology to generated_ontology.ttl")
            
    except Exception as e:
        logger.error(f"Failed to generate ontology: {str(e)}")

if __name__ == "__main__":
    main() 