"""
Module for analyzing and preserving hierarchical relationships from user stories and competency questions.
"""
import re
import logging
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS, OWL

logger = logging.getLogger(__name__)

@dataclass
class DomainConcept:
    """Represents a concept from the domain with its hierarchical relationships."""
    name: str
    parent: Optional[str] = None
    children: Set[str] = None
    properties: Set[str] = None
    related_concepts: Set[str] = None
    pattern_mappings: Dict[str, str] = None
    source: str = None  # 'cq' or 'story'
    
    def __post_init__(self):
        self.children = self.children or set()
        self.properties = self.properties or set()
        self.related_concepts = self.related_concepts or set()
        self.pattern_mappings = self.pattern_mappings or {}

class HierarchyAnalyzer:
    """Analyzes and preserves hierarchical relationships in domain concepts."""
    
    def __init__(self):
        self.concepts: Dict[str, DomainConcept] = {}
        self.hierarchical_indicators = [
            (r'has|contains|includes|consists of', 'parent-child'),
            (r'is a|type of|kind of|subclass of', 'is-a'),
            (r'part of|belongs to|component of', 'part-of'),
            (r'related to|connected with|associated with', 'related'),
        ]
        
    def analyze_text(self, text: str, source: str) -> List[DomainConcept]:
        """
        Analyze text to extract domain concepts and their relationships.
        
        Args:
            text: The text to analyze (competency question or user story)
            source: Source of the text ('cq' or 'story')
            
        Returns:
            List of identified domain concepts with their relationships
        """
        # Extract noun phrases as potential concepts
        concepts = self._extract_noun_phrases(text)
        
        # Analyze relationships between concepts
        for i, concept1 in enumerate(concepts):
            for pattern, rel_type in self.hierarchical_indicators:
                for concept2 in concepts[i+1:]:
                    if re.search(pattern, text, re.IGNORECASE):
                        self._add_relationship(concept1, concept2, rel_type, source)
        
        return list(self.concepts.values())
    
    def _extract_noun_phrases(self, text: str) -> List[str]:
        """Extract potential noun phrases from text using simple heuristics."""
        # Split into sentences
        sentences = text.split('.')
        noun_phrases = []
        
        for sentence in sentences:
            # Look for capitalized words followed by other words
            matches = re.finditer(r'([A-Z][a-z]+(?:\s+[a-z]+)*)', sentence)
            for match in matches:
                noun_phrases.append(match.group(1))
            
            # Look for words before/after relationship indicators
            for pattern, _ in self.hierarchical_indicators:
                parts = re.split(pattern, sentence, flags=re.IGNORECASE)
                for part in parts:
                    words = part.strip().split()
                    if len(words) > 0:
                        noun_phrases.append(words[-1])  # Take the last word before the pattern
                        
        return list(set(noun_phrases))
    
    def _add_relationship(self, concept1: str, concept2: str, rel_type: str, source: str):
        """Add a relationship between two concepts."""
        if concept1 not in self.concepts:
            self.concepts[concept1] = DomainConcept(name=concept1, source=source)
        if concept2 not in self.concepts:
            self.concepts[concept2] = DomainConcept(name=concept2, source=source)
            
        if rel_type == 'parent-child':
            self.concepts[concept1].children.add(concept2)
            self.concepts[concept2].parent = concept1
        elif rel_type == 'is-a':
            self.concepts[concept2].parent = concept1
        elif rel_type == 'part-of':
            self.concepts[concept1].parent = concept2
        else:  # related
            self.concepts[concept1].related_concepts.add(concept2)
            self.concepts[concept2].related_concepts.add(concept1)
            
    def map_to_pattern(self, concept: DomainConcept, pattern_name: str, 
                      pattern_concept: str) -> None:
        """
        Map a domain concept to a pattern concept.
        
        Args:
            concept: The domain concept to map
            pattern_name: Name of the ontology pattern
            pattern_concept: Name of the concept in the pattern
        """
        concept.pattern_mappings[pattern_name] = pattern_concept
        
    def validate_pattern_mapping(self, concept: DomainConcept, 
                               pattern_graph: Graph) -> bool:
        """
        Validate that a pattern mapping preserves the concept's hierarchical relationships.
        
        Args:
            concept: The domain concept to validate
            pattern_graph: The ontology pattern graph
            
        Returns:
            True if the mapping preserves relationships, False otherwise
        """
        if not concept.pattern_mappings:
            return True
            
        for pattern_name, pattern_concept in concept.pattern_mappings.items():
            pattern_uri = URIRef(pattern_concept)
            
            # Check if parent relationship is preserved
            if concept.parent and concept.parent in self.concepts:
                parent_concept = self.concepts[concept.parent]
                if parent_concept.pattern_mappings.get(pattern_name):
                    parent_uri = URIRef(parent_concept.pattern_mappings[pattern_name])
                    if not any(pattern_graph.triples((pattern_uri, RDFS.subClassOf, parent_uri))):
                        logger.warning(f"Pattern mapping breaks parent relationship for {concept.name}")
                        return False
                        
            # Check if child relationships are preserved
            for child in concept.children:
                if child in self.concepts:
                    child_concept = self.concepts[child]
                    if child_concept.pattern_mappings.get(pattern_name):
                        child_uri = URIRef(child_concept.pattern_mappings[pattern_name])
                        if not any(pattern_graph.triples((child_uri, RDFS.subClassOf, pattern_uri))):
                            logger.warning(f"Pattern mapping breaks child relationship for {concept.name}")
                            return False
                            
        return True
    
    def generate_annotations(self, concept: DomainConcept) -> List[Tuple[URIRef, URIRef, Literal]]:
        """
        Generate RDF annotations to document concept origins and pattern usage.
        
        Args:
            concept: The domain concept to annotate
            
        Returns:
            List of RDF triples for annotations
        """
        annotations = []
        
        # Add source annotation
        annotations.append((
            URIRef(f"#{concept.name}"),
            URIRef("http://purl.org/dc/terms/source"),
            Literal("Competency Question" if concept.source == 'cq' else "User Story")
        ))
        
        # Add pattern mapping annotations
        for pattern, mapping in concept.pattern_mappings.items():
            annotations.append((
                URIRef(f"#{concept.name}"),
                URIRef("http://purl.org/dc/terms/relation"),
                Literal(f"Maps to {mapping} in {pattern} pattern")
            ))
            
        return annotations 