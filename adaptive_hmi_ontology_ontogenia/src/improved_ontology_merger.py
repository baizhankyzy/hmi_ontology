"""
Improved utility for merging multiple ontologies with duplicate detection and resolution.
"""
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
import logging
from typing import List, Dict, Set, Tuple, Optional
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImprovedOntologyMerger:
    def __init__(self, base_uri: str = "http://example.org/adaptive-hmi#"):
        """
        Initialize the ontology merger.
        
        Args:
            base_uri: The base URI for the merged ontology
        """
        self.base_uri = base_uri
        self.logger = logging.getLogger(__name__)
        
        # Initialize the merged graph
        self.merged_graph = Graph()
        
        # Bind common namespaces
        self.merged_graph.bind("rdf", RDF)
        self.merged_graph.bind("rdfs", RDFS)
        self.merged_graph.bind("owl", OWL)
        self.merged_graph.bind("xsd", XSD)
        self.merged_graph.bind("ahmi", Namespace(self.base_uri))
        
        # Create the ontology declaration
        self.ontology_uri = URIRef(self.base_uri.rstrip("#"))
        self.merged_graph.add((self.ontology_uri, RDF.type, OWL.Ontology))
        self.merged_graph.add((self.ontology_uri, RDFS.label, Literal("Adaptive Human-Machine Interface Ontology", lang="en")))
        self.merged_graph.add((self.ontology_uri, RDFS.comment, Literal("An ontology for describing adaptive human-machine interfaces with a focus on driver state detection and multimodal feedback", lang="en")))
        
        # Dictionary to track entity mappings for duplicate detection
        self.entity_mappings = {}
        
        # Track entities by their label/comment for potential merging
        self.label_to_entity = {}
        self.similar_entities = {}
    
    def normalize_text(self, text):
        """Normalize text for comparison by lowercasing and removing punctuation."""
        if not text:
            return ""
        # Convert to lowercase
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def find_similar_entity(self, entity, label, comment):
        """Find an existing entity with similar label or comment."""
        if not label:
            return None
        
        normalized_label = self.normalize_text(label)
        normalized_comment = self.normalize_text(comment) if comment else ""
        
        # Check for exact label match
        if normalized_label in self.label_to_entity:
            return self.label_to_entity[normalized_label]
        
        # Check for similar labels (e.g., "Drowsiness Event" vs "Drowsiness Driving Event")
        for existing_label, existing_entity in self.label_to_entity.items():
            # Skip if the entity types don't match (class with class, property with property)
            entity_type = None
            existing_type = None
            
            for _, p, o in self.merged_graph.triples((existing_entity, RDF.type, None)):
                existing_type = o
                break
                
            for g in self.temp_graphs:
                for _, p, o in g.triples((entity, RDF.type, None)):
                    entity_type = o
                    break
                if entity_type:
                    break
            
            if entity_type and existing_type and entity_type != existing_type:
                continue
            
            # Check if one label contains the other
            if (normalized_label in existing_label or existing_label in normalized_label) and len(normalized_label) > 5:
                return existing_entity
            
            # Check if comments are similar
            if normalized_comment and len(normalized_comment) > 10:
                existing_comment = ""
                for _, _, o in self.merged_graph.triples((existing_entity, RDFS.comment, None)):
                    if isinstance(o, Literal):
                        existing_comment = self.normalize_text(str(o))
                        break
                
                if existing_comment and (normalized_comment in existing_comment or existing_comment in normalized_comment):
                    return existing_entity
        
        return None
    
    def get_entity_label_comment(self, graph, entity):
        """Get label and comment for an entity."""
        label = None
        comment = None
        
        for _, _, o in graph.triples((entity, RDFS.label, None)):
            if isinstance(o, Literal):
                label = str(o)
                break
        
        for _, _, o in graph.triples((entity, RDFS.comment, None)):
            if isinstance(o, Literal):
                comment = str(o)
                break
                
        return label, comment
    
    def add_ontology(self, turtle_content: str) -> bool:
        """
        Add an ontology to the merged graph with duplicate detection.
        
        Args:
            turtle_content: The ontology content in Turtle format
            
        Returns:
            True if the ontology was successfully added, False otherwise
        """
        try:
            # Parse the ontology
            g = Graph()
            g.parse(data=turtle_content, format="turtle")
            
            # Store in temporary graphs list for reference during merging
            if not hasattr(self, 'temp_graphs'):
                self.temp_graphs = []
            self.temp_graphs.append(g)
            
            # Collect statistics before merging
            classes_before = set(self.merged_graph.subjects(RDF.type, OWL.Class))
            props_before = set(self.merged_graph.subjects(RDF.type, OWL.ObjectProperty)) | set(self.merged_graph.subjects(RDF.type, OWL.DatatypeProperty))
            
            # First pass: collect all entity labels for duplicate detection
            for s, p, o in g.triples((None, RDF.type, None)):
                if isinstance(s, URIRef) and (o == OWL.Class or o == OWL.ObjectProperty or o == OWL.DatatypeProperty):
                    label, comment = self.get_entity_label_comment(g, s)
                    if label:
                        normalized_label = self.normalize_text(label)
                        if s not in self.entity_mappings:
                            similar_entity = self.find_similar_entity(s, label, comment)
                            if similar_entity:
                                self.entity_mappings[s] = similar_entity
                                self.logger.info(f"Found duplicate: {label} -> {similar_entity}")
                            else:
                                if normalized_label in self.label_to_entity:
                                    # If we have multiple entities with the same normalized label,
                                    # we'll need to determine which to keep later
                                    if normalized_label not in self.similar_entities:
                                        self.similar_entities[normalized_label] = [self.label_to_entity[normalized_label]]
                                    self.similar_entities[normalized_label].append(s)
                                else:
                                    self.label_to_entity[normalized_label] = s
            
            # Second pass: add triples with entity mapping
            for s, p, o in g:
                # Map subject if it's a duplicate
                subject = self.entity_mappings.get(s, s)
                
                # Map object if it's a duplicate and a URI (not a literal)
                obj = o
                if isinstance(o, URIRef) and o in self.entity_mappings:
                    obj = self.entity_mappings[o]
                
                # Add the triple with potentially mapped entities
                self.merged_graph.add((subject, p, obj))
            
            # Collect statistics after merging
            classes_after = set(self.merged_graph.subjects(RDF.type, OWL.Class))
            props_after = set(self.merged_graph.subjects(RDF.type, OWL.ObjectProperty)) | set(self.merged_graph.subjects(RDF.type, OWL.DatatypeProperty))
            
            new_classes = len(classes_after - classes_before)
            new_props = len(props_after - props_before)
            
            self.logger.info(f"Added ontology with {new_classes} new classes and {new_props} new properties")
            self.logger.info(f"Detected {len(self.entity_mappings)} duplicates")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding ontology: {str(e)}")
            return False
    
    def merge_ontologies(self, ontologies: Dict[str, str]) -> Optional[str]:
        """
        Merge multiple ontologies with duplicate detection.
        
        Args:
            ontologies: Dictionary mapping ontology IDs to their content
            
        Returns:
            The merged ontology in Turtle format, or None if merging failed
        """
        try:
            # Reset the merged graph
            self.merged_graph = Graph()
            
            # Reset tracking dictionaries
            self.entity_mappings = {}
            self.label_to_entity = {}
            self.similar_entities = {}
            self.temp_graphs = []
            
            # Bind common namespaces again
            self.merged_graph.bind("rdf", RDF)
            self.merged_graph.bind("rdfs", RDFS)
            self.merged_graph.bind("owl", OWL)
            self.merged_graph.bind("xsd", XSD)
            self.merged_graph.bind("ahmi", Namespace(self.base_uri))
            
            # Create the ontology declaration again
            self.ontology_uri = URIRef(self.base_uri.rstrip("#"))
            self.merged_graph.add((self.ontology_uri, RDF.type, OWL.Ontology))
            self.merged_graph.add((self.ontology_uri, RDFS.label, Literal("Adaptive Human-Machine Interface Ontology", lang="en")))
            self.merged_graph.add((self.ontology_uri, RDFS.comment, Literal("An ontology for describing adaptive human-machine interfaces with a focus on driver state detection and multimodal feedback", lang="en")))
            
            # Add all ontologies
            for ontology_id, content in ontologies.items():
                self.logger.info(f"Merging ontology {ontology_id}")
                success = self.add_ontology(content)
                if not success:
                    self.logger.warning(f"Failed to merge ontology {ontology_id}")
            
            # Consolidate comments for merged entities
            self.consolidate_entity_descriptions()
            
            # Merge entities with same normalized label if needed
            self.merge_similar_entities()
            
            # Serialize the merged graph to Turtle
            return self.merged_graph.serialize(format="turtle")
            
        except Exception as e:
            self.logger.error(f"Error merging ontologies: {str(e)}")
            return None
    
    def consolidate_entity_descriptions(self):
        """Consolidate labels and comments for entities that were mapped together."""
        # Look through all entity mappings
        for source, target in self.entity_mappings.items():
            # Collect all comments from the source entity in the original graphs
            source_comments = []
            source_labels = []
            
            for g in self.temp_graphs:
                for _, _, comment in g.triples((source, RDFS.comment, None)):
                    if isinstance(comment, Literal) and str(comment) not in source_comments:
                        source_comments.append(str(comment))
                
                for _, _, label in g.triples((source, RDFS.label, None)):
                    if isinstance(label, Literal) and str(label) not in source_labels:
                        source_labels.append(str(label))
            
            # Add any unique comments to the target entity
            target_comments = []
            for _, _, comment in self.merged_graph.triples((target, RDFS.comment, None)):
                if isinstance(comment, Literal):
                    target_comments.append(str(comment))
            
            for comment in source_comments:
                if comment not in target_comments:
                    self.merged_graph.add((target, RDFS.comment, Literal(comment, lang="en")))
    
    def merge_similar_entities(self):
        """Merge entities that have the same normalized label."""
        for label, entities in self.similar_entities.items():
            if len(entities) <= 1:
                continue
                
            # Choose the entity to keep (the one with the most connections)
            entity_connections = {}
            for entity in entities:
                count = 0
                for g in [self.merged_graph] + self.temp_graphs:
                    count += len(list(g.triples((entity, None, None))))
                    count += len(list(g.triples((None, None, entity))))
                entity_connections[entity] = count
            
            # Keep the entity with the most connections
            entities_sorted = sorted(entities, key=lambda e: entity_connections.get(e, 0), reverse=True)
            keep_entity = entities_sorted[0]
            
            # Map other entities to the one we're keeping
            for entity in entities[1:]:
                if entity != keep_entity:
                    self.entity_mappings[entity] = keep_entity
                    
                    # Transfer all properties from entity to keep_entity
                    for s, p, o in list(self.merged_graph.triples((entity, None, None))):
                        self.merged_graph.remove((s, p, o))
                        self.merged_graph.add((keep_entity, p, o))
                    
                    # Update all references to this entity
                    for s, p, o in list(self.merged_graph.triples((None, None, entity))):
                        self.merged_graph.remove((s, p, o))
                        self.merged_graph.add((s, p, keep_entity))
    
    def save_merged_ontology(self, file_path: str) -> bool:
        """
        Save the merged ontology to a file.
        
        Args:
            file_path: Path to save the merged ontology
            
        Returns:
            True if the ontology was successfully saved, False otherwise
        """
        try:
            self.merged_graph.serialize(destination=file_path, format="turtle")
            self.logger.info(f"Saved merged ontology to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving merged ontology: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about the merged ontology.
        
        Returns:
            Dictionary with statistics
        """
        classes = set(self.merged_graph.subjects(RDF.type, OWL.Class))
        obj_props = set(self.merged_graph.subjects(RDF.type, OWL.ObjectProperty))
        data_props = set(self.merged_graph.subjects(RDF.type, OWL.DatatypeProperty))
        individuals = set(self.merged_graph.subjects(RDF.type, OWL.NamedIndividual))
        
        # Try to get counts of situation and event classes if they exist
        situation_uri = URIRef(self.base_uri + "Situation")
        event_uri = URIRef(self.base_uri + "Event")
        
        situations = set(s for s, p, o in self.merged_graph.triples((None, RDFS.subClassOf, None)) 
                         if o == situation_uri)
        events = set(s for s, p, o in self.merged_graph.triples((None, RDFS.subClassOf, None)) 
                     if o == event_uri)
        
        return {
            "classes": len(classes),
            "object_properties": len(obj_props),
            "datatype_properties": len(data_props),
            "individuals": len(individuals),
            "situation_classes": len(situations),
            "event_classes": len(events),
            "duplicates_detected": len(self.entity_mappings),
            "total_triples": len(self.merged_graph)
        }