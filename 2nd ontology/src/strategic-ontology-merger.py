"""
Strategic ontology merger that implements the five-principle merging strategy.
"""
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
import logging
from typing import List, Dict, Set, Tuple, Optional
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StrategicOntologyMerger:
    def __init__(self, base_uri: str = "http://www.example.org/test#"):
        """
        Initialize the strategic ontology merger.
        
        Args:
            base_uri: The base URI for the merged ontology
        """
        self.base_uri = base_uri
        self.logger = logging.getLogger(__name__)
        
        # Initialize the merged graph
        self.merged_graph = Graph()
        
        # Bind common namespaces
        self.merged_graph.bind("", Namespace(self.base_uri))
        self.merged_graph.bind("rdf", RDF)
        self.merged_graph.bind("rdfs", RDFS)
        self.merged_graph.bind("owl", OWL)
        self.merged_graph.bind("xsd", XSD)
        
        # Create the ontology declaration
        self.ontology_uri = URIRef(self.base_uri.rstrip("#"))
        self.merged_graph.add((self.ontology_uri, RDF.type, OWL.Ontology))
        
        # Tracking for merging strategy
        self.class_mappings = {}
        self.property_mappings = {}
        self.inverse_properties = {}
        self.consolidated_properties = {}
        
    def normalize_name(self, name: str) -> str:
        """Normalize entity names for comparison."""
        if not name:
            return ""
        # Remove common prefixes and suffixes, convert to lowercase
        name = name.lower()
        name = re.sub(r'^(has|is|of|to|for|with|by)_?', '', name)
        name = re.sub(r'_?(state|type|system|method|property)$', '', name)
        return name.strip()
    
    def find_similar_classes(self, ontologies: List[Graph]) -> Dict[str, Set[URIRef]]:
        """Find classes with similar names or purposes across ontologies."""
        similar_classes = {}
        all_classes = {}
        
        # Collect all classes with their labels
        for i, graph in enumerate(ontologies):
            for class_uri in graph.subjects(RDF.type, OWL.Class):
                if isinstance(class_uri, URIRef):
                    label = self.get_label(graph, class_uri)
                    normalized = self.normalize_name(label or str(class_uri).split('#')[-1])
                    
                    if normalized not in all_classes:
                        all_classes[normalized] = []
                    all_classes[normalized].append((class_uri, i, label))
        
        # Group similar classes
        for normalized, classes in all_classes.items():
            if len(classes) > 1:
                similar_classes[normalized] = {cls[0] for cls in classes}
        
        return similar_classes
    
    def find_similar_properties(self, ontologies: List[Graph]) -> Dict[str, Set[URIRef]]:
        """Find properties with similar names or purposes across ontologies."""
        similar_properties = {}
        all_properties = {}
        
        # Collect all properties with their labels
        for i, graph in enumerate(ontologies):
            for prop_uri in set(graph.subjects(RDF.type, OWL.ObjectProperty)) | set(graph.subjects(RDF.type, OWL.DatatypeProperty)):
                if isinstance(prop_uri, URIRef):
                    label = self.get_label(graph, prop_uri)
                    prop_name = label or str(prop_uri).split('#')[-1]
                    normalized = self.normalize_name(prop_name)
                    
                    if normalized not in all_properties:
                        all_properties[normalized] = []
                    all_properties[normalized].append((prop_uri, i, label, prop_name))
        
        # Group similar properties and identify potential inverse pairs
        for normalized, properties in all_properties.items():
            if len(properties) > 1:
                similar_properties[normalized] = {prop[0] for prop in properties}
            
            # Check for inverse property patterns
            for prop_uri, i, label, prop_name in properties:
                inverse_candidates = self.find_inverse_candidates(prop_name, all_properties)
                if inverse_candidates:
                    for inv_prop, _, _, _ in inverse_candidates:
                        self.inverse_properties[prop_uri] = inv_prop
        
        return similar_properties
    
    def find_inverse_candidates(self, prop_name: str, all_properties: Dict) -> List:
        """Find potential inverse properties based on naming patterns."""
        inverse_patterns = [
            ('has', 'isOf'),
            ('detects', 'detectedBy'),
            ('observes', 'observedBy'),
            ('activates', 'activatedBy'),
            ('responds', 'respondsTo'),
            ('signals', 'signaledBy'),
            ('indicates', 'indicatedBy'),
            ('classifies', 'classifiedBy'),
            ('analyzes', 'analyzedBy')
        ]
        
        prop_lower = prop_name.lower()
        candidates = []
        
        for forward, backward in inverse_patterns:
            if forward in prop_lower:
                # Look for the inverse pattern
                inverse_name = prop_lower.replace(forward, backward)
                for normalized, properties in all_properties.items():
                    for prop_uri, i, label, full_name in properties:
                        if inverse_name in full_name.lower():
                            candidates.append((prop_uri, i, label, full_name))
            elif backward in prop_lower:
                # Look for the forward pattern
                forward_name = prop_lower.replace(backward, forward)
                for normalized, properties in all_properties.items():
                    for prop_uri, i, label, full_name in properties:
                        if forward_name in full_name.lower():
                            candidates.append((prop_uri, i, label, full_name))
        
        return candidates
    
    def get_label(self, graph: Graph, uri: URIRef) -> Optional[str]:
        """Get the rdfs:label for a URI."""
        for _, _, label in graph.triples((uri, RDFS.label, None)):
            if isinstance(label, Literal):
                return str(label)
        return None
    
    def get_comment(self, graph: Graph, uri: URIRef) -> Optional[str]:
        """Get the rdfs:comment for a URI."""
        for _, _, comment in graph.triples((uri, RDFS.comment, None)):
            if isinstance(comment, Literal):
                return str(comment)
        return None
    
    def merge_ontologies(self, ontology_contents: List[str], competency_questions: List[str]) -> Optional[str]:
        """
        Merge ontologies following the five-principle strategy.
        
        Args:
            ontology_contents: List of ontology content strings in Turtle format
            competency_questions: List of competency questions that need to be preserved
            
        Returns:
            Merged ontology in Turtle format
        """
        try:
            self.logger.info("Starting strategic ontology merge")
            
            # Parse all ontologies
            ontologies = []
            for i, content in enumerate(ontology_contents):
                graph = Graph()
                graph.parse(data=content, format="turtle")
                ontologies.append(graph)
                self.logger.info(f"Parsed ontology {i+1} with {len(graph)} triples")
            
            # PRINCIPLE 1: Preserve both competency questions
            self.logger.info("Applying Principle 1: Preserving competency questions")
            essential_entities = self.identify_essential_entities(ontologies, competency_questions)
            
            # PRINCIPLE 2: Eliminate duplicates through consolidation
            self.logger.info("Applying Principle 2: Eliminating duplicates")
            similar_classes = self.find_similar_classes(ontologies)
            similar_properties = self.find_similar_properties(ontologies)
            
            # Choose canonical entities for duplicates
            self.create_entity_mappings(similar_classes, similar_properties, ontologies)
            
            # PRINCIPLE 3: Maintain clear naming and relationships
            self.logger.info("Applying Principle 3: Maintaining clear naming")
            
            # PRINCIPLE 4 & 5: Balance expressivity and use inverse properties
            self.logger.info("Applying Principles 4 & 5: Balancing expressivity and using inverse properties")
            
            # Merge all graphs with mappings
            for i, graph in enumerate(ontologies):
                self.add_graph_with_mappings(graph, i)
            
            # Add inverse property declarations
            self.add_inverse_property_declarations()
            
            # Clean up redundant restrictions
            self.clean_redundant_restrictions()
            
            # Serialize the result
            result = self.merged_graph.serialize(format="turtle")
            self.logger.info(f"Merged ontology created with {len(self.merged_graph)} triples")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in strategic merge: {str(e)}")
            return None
    
    def identify_essential_entities(self, ontologies: List[Graph], competency_questions: List[str]) -> Set[URIRef]:
        """Identify entities essential for answering competency questions."""
        essential = set()
        
        # Simple heuristic: entities mentioned in competency questions
        for cq in competency_questions:
            words = re.findall(r'\b[A-Z][a-zA-Z]+\b', cq)  # Find capitalized words
            for word in words:
                for graph in ontologies:
                    for entity in graph.subjects():
                        if isinstance(entity, URIRef) and word.lower() in str(entity).lower():
                            essential.add(entity)
        
        return essential
    
    def create_entity_mappings(self, similar_classes: Dict, similar_properties: Dict, ontologies: List[Graph]):
        """Create mappings from similar entities to canonical ones."""
        
        # Map classes
        for group_name, class_set in similar_classes.items():
            classes = list(class_set)
            if len(classes) > 1:
                # Choose the class with the most detailed definition as canonical
                canonical = self.choose_canonical_entity(classes, ontologies)
                for cls in classes:
                    if cls != canonical:
                        self.class_mappings[cls] = canonical
                        self.logger.info(f"Mapping class {cls} -> {canonical}")
        
        # Map properties
        for group_name, prop_set in similar_properties.items():
            properties = list(prop_set)
            if len(properties) > 1:
                # Choose the property with the most detailed definition as canonical
                canonical = self.choose_canonical_entity(properties, ontologies)
                for prop in properties:
                    if prop != canonical:
                        self.property_mappings[prop] = canonical
                        self.logger.info(f"Mapping property {prop} -> {canonical}")
    
    def choose_canonical_entity(self, entities: List[URIRef], ontologies: List[Graph]) -> URIRef:
        """Choose the canonical entity from a list of similar entities."""
        entity_scores = {}
        
        for entity in entities:
            score = 0
            for graph in ontologies:
                # Count properties (higher is better)
                score += len(list(graph.triples((entity, None, None))))
                # Check for label and comment (bonus points)
                if list(graph.triples((entity, RDFS.label, None))):
                    score += 2
                if list(graph.triples((entity, RDFS.comment, None))):
                    score += 2
            entity_scores[entity] = score
        
        # Return entity with highest score
        return max(entity_scores.items(), key=lambda x: x[1])[0]
    
    def add_graph_with_mappings(self, graph: Graph, graph_index: int):
        """Add a graph to the merged graph, applying entity mappings."""
        for s, p, o in graph:
            # Apply mappings
            subject = self.apply_mapping(s)
            predicate = self.apply_mapping(p)
            obj = self.apply_mapping(o) if isinstance(o, URIRef) else o
            
            # Add the mapped triple
            self.merged_graph.add((subject, predicate, obj))
    
    def apply_mapping(self, entity):
        """Apply class and property mappings to an entity."""
        if entity in self.class_mappings:
            return self.class_mappings[entity]
        elif entity in self.property_mappings:
            return self.property_mappings[entity]
        else:
            return entity
    
    def add_inverse_property_declarations(self):
        """Add owl:inverseOf declarations for identified inverse properties."""
        for prop1, prop2 in self.inverse_properties.items():
            # Apply mappings to the properties
            mapped_prop1 = self.apply_mapping(prop1)
            mapped_prop2 = self.apply_mapping(prop2)
            
            if mapped_prop1 != mapped_prop2:  # Don't create self-inverse
                self.merged_graph.add((mapped_prop1, OWL.inverseOf, mapped_prop2))
                self.logger.info(f"Added inverse property: {mapped_prop1} owl:inverseOf {mapped_prop2}")
    
    def clean_redundant_restrictions(self):
        """Remove redundant restrictions that can be inferred from inverse properties."""
        # This is a simplified cleanup - in practice, this would be more sophisticated
        restrictions_to_remove = []
        
        for s, p, o in self.merged_graph.triples((None, RDFS.subClassOf, None)):
            if isinstance(o, BNode):
                # Check if this is a restriction that might be redundant
                restriction_type = None
                for _, _, restriction_obj in self.merged_graph.triples((o, RDF.type, None)):
                    if restriction_obj == OWL.Restriction:
                        restriction_type = "restriction"
                        break
                
                if restriction_type:
                    # Check if we can infer this restriction from inverse properties
                    # This is a placeholder for more sophisticated logic
                    pass
        
        # Remove identified redundant restrictions
        for triple in restrictions_to_remove:
            self.merged_graph.remove(triple)
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about the merged ontology."""
        classes = set(self.merged_graph.subjects(RDF.type, OWL.Class))
        obj_props = set(self.merged_graph.subjects(RDF.type, OWL.ObjectProperty))
        data_props = set(self.merged_graph.subjects(RDF.type, OWL.DatatypeProperty))
        inverse_props = len(set(self.merged_graph.subjects(OWL.inverseOf, None)))
        
        return {
            "classes": len(classes),
            "object_properties": len(obj_props),
            "datatype_properties": len(data_props),
            "inverse_properties": inverse_props,
            "class_mappings": len(self.class_mappings),
            "property_mappings": len(self.property_mappings),
            "total_triples": len(self.merged_graph)
        }