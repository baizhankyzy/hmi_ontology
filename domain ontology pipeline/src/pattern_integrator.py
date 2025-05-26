"""
Module for integrating ontology design patterns into the ontology generation process.
"""
import os
import logging
from typing import Dict, Optional, List, Set, Tuple
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL, XSD
import xml.etree.ElementTree as ET
from .hierarchy_analyzer import HierarchyAnalyzer, DomainConcept

logger = logging.getLogger(__name__)

class PatternIntegrator:
    """Handles the integration of ontology design patterns into generated ontologies."""
    
    def __init__(self, patterns_dir: str, api_client=None):
        """
        Initialize the pattern integrator.
        
        Args:
            patterns_dir: Directory containing the ontology pattern files
            api_client: Optional Claude API client for pattern analysis
        """
        self.patterns_dir = patterns_dir
        self.api_client = api_client
        self.patterns: Dict[str, Graph] = {}
        self.pattern_examples = {}
        self.hierarchy_analyzer = HierarchyAnalyzer()
        self.pattern_keywords = {
            'event': ['event', 'occur', 'happen', 'when', 'during'],
            'observation': ['observe', 'detect', 'measure', 'monitor', 'sensor'],
            'situation': ['situation', 'context', 'condition', 'state'],
            'participation': ['participate', 'involve', 'role', 'actor'],
            'agentrole': ['agent', 'actor', 'role', 'perform'],
            'timeindexedpersonrole': ['time', 'duration', 'period', 'role'],
            'informationrealization': ['information', 'data', 'represent']
        }
        self.load_patterns()
        self.load_pattern_examples()
        
    def load_patterns(self):
        """Load all available ontology patterns from the patterns directory."""
        try:
            pattern_files = [f for f in os.listdir(self.patterns_dir) 
                           if f.endswith(('.owl', '.xml', '.ttl'))]
            
            for pattern_file in pattern_files:
                pattern_name = os.path.splitext(pattern_file)[0].replace('.owl', '')
                file_path = os.path.join(self.patterns_dir, pattern_file)
                
                try:
                    g = Graph()
                    
                    # For XML/OWL files, try to clean and parse them first
                    if pattern_file.endswith(('.xml', '.owl')):
                        try:
                            # Parse XML to clean it up
                            tree = ET.parse(file_path)
                            root = tree.getroot()
                            
                            # Extract the RDF/XML content
                            rdf_content = ""
                            for elem in root.iter():
                                if "RDF" in elem.tag:
                                    rdf_content = ET.tostring(elem, encoding='unicode')
                                    break
                            
                            if rdf_content:
                                # Parse the cleaned RDF/XML content
                                g.parse(data=rdf_content, format='xml')
                                self.patterns[pattern_name] = g
                                logger.info(f"Loaded pattern: {pattern_name}")
                                continue
                        except ET.ParseError:
                            pass
                    
                    # Try different formats if XML parsing failed
                    for fmt in ['xml', 'turtle', 'n3']:
                        try:
                            g.parse(file_path, format=fmt)
                            self.patterns[pattern_name] = g
                            logger.info(f"Loaded pattern: {pattern_name}")
                            break
                        except Exception as e:
                            logger.debug(f"Failed to parse {pattern_file} as {fmt}: {str(e)}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error loading pattern {pattern_file}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error accessing patterns directory: {str(e)}")
    
    def get_pattern_elements(self, pattern_name: str) -> Dict[str, List[URIRef]]:
        """
        Get the classes and properties defined in a pattern.
        
        Args:
            pattern_name: Name of the pattern to analyze
            
        Returns:
            Dictionary with classes and properties from the pattern
        """
        if pattern_name not in self.patterns:
            return {"classes": [], "object_properties": [], "data_properties": []}
            
        g = self.patterns[pattern_name]
        
        classes = list(g.subjects(RDF.type, OWL.Class))
        obj_props = list(g.subjects(RDF.type, OWL.ObjectProperty))
        data_props = list(g.subjects(RDF.type, OWL.DatatypeProperty))
        
        return {
            "classes": classes,
            "object_properties": obj_props,
            "data_properties": data_props
        }
    
    def integrate_pattern(self, target_graph: Graph, pattern_name: str, 
                         base_uri: str) -> Optional[Graph]:
        """
        Integrate a pattern into a target ontology.
        
        Args:
            target_graph: The ontology graph to integrate the pattern into
            pattern_name: Name of the pattern to integrate
            base_uri: Base URI for the target ontology
            
        Returns:
            Modified graph with pattern integrated, or None if pattern not found
        """
        if pattern_name not in self.patterns:
            logger.error(f"Pattern {pattern_name} not found")
            return None
            
        pattern_graph = self.patterns[pattern_name]
        base_ns = Namespace(base_uri)
        
        # First validate the target graph
        if not self._validate_graph(target_graph):
            logger.error("Target graph validation failed")
            return None
            
        # Copy pattern elements with new namespace
        for s, p, o in pattern_graph:
            # Skip annotation properties
            if (p == RDF.type and 
                o in [OWL.AnnotationProperty, OWL.Ontology]):
                continue
                
            # Modify URIs to use target namespace
            new_s = self._modify_uri(s, base_ns)
            new_p = self._modify_uri(p, base_ns)
            new_o = self._modify_uri(o, base_ns)
            
            # Add triple to target graph
            target_graph.add((new_s, new_p, new_o))
            
        # Validate the integrated graph
        if not self._validate_graph(target_graph):
            logger.error("Integrated graph validation failed")
            return None
            
        return target_graph
    
    def _modify_uri(self, node, base_ns):
        """Modify a URI to use the target namespace."""
        if isinstance(node, URIRef):
            # Keep standard vocabulary URIs unchanged
            if any(str(node).startswith(ns) for ns in 
                  ['http://www.w3.org/2002/07/owl',
                   'http://www.w3.org/2000/01/rdf-schema',
                   'http://www.w3.org/1999/02/22-rdf-syntax-ns']):
                return node
            
            # Extract local name and create new URI
            local_name = str(node).split('#')[-1]
            return base_ns[local_name]
        return node
    
    def analyze_text(self, text: str) -> List[str]:
        """
        Analyze any text to determine relevant patterns.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of pattern names that are relevant
        """
        relevant_patterns = []
        
        # Check for pattern keywords in the text
        text_lower = text.lower()
        for pattern, keywords in self.pattern_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                relevant_patterns.append(pattern)
                
        return relevant_patterns

    def load_pattern_examples(self):
        """Load pattern examples from the examples file."""
        try:
            example_file = os.path.join(self.patterns_dir, "hmi-ontology-patterns-examples.txt")
            if os.path.exists(example_file):
                with open(example_file, 'r') as f:
                    self.pattern_examples = f.read()
                logger.info("Loaded pattern examples file")
            else:
                logger.warning("Pattern examples file not found")
        except Exception as e:
            logger.error(f"Error loading pattern examples: {str(e)}")

    def analyze_competency_question_and_story(self, 
                                            competency_question: str, 
                                            user_story: str) -> List[str]:
        """
        Analyze both competency question and user story to determine relevant patterns
        while preserving hierarchical relationships.
        
        Args:
            competency_question: The competency question text
            user_story: The user story text
            
        Returns:
            List of unique pattern names that are relevant
        """
        # First analyze the hierarchical structure
        cq_concepts = self.hierarchy_analyzer.analyze_text(competency_question, 'cq')
        story_concepts = self.hierarchy_analyzer.analyze_text(user_story, 'story')
        
        # If API client is available, use it for example-based analysis
        if self.api_client and self.pattern_examples:
            try:
                pattern_recommendations = self.api_client.analyze_patterns(
                    competency_question=competency_question,
                    user_story=user_story,
                    pattern_examples=self.pattern_examples
                )
                
                # Extract pattern names and store explanations
                api_patterns = []
                self.pattern_explanations = {}
                
                for pattern_name, explanation in pattern_recommendations:
                    pattern_name = pattern_name.lower()
                    api_patterns.append(pattern_name)
                    self.pattern_explanations[pattern_name] = explanation
                    
                    # Map concepts to pattern elements
                    self._map_concepts_to_pattern(pattern_name, explanation, 
                                                cq_concepts + story_concepts)
                
                if api_patterns:
                    logger.info(f"Patterns identified by API: {api_patterns}")
                    return api_patterns
                    
            except Exception as e:
                logger.error(f"Error in API-based pattern analysis: {str(e)}")
                logger.info("Falling back to keyword-based analysis")
        
        # Fallback to keyword-based analysis
        cq_patterns = self.analyze_text(competency_question)
        story_patterns = self.analyze_text(user_story)
        
        # Combine and deduplicate patterns
        all_patterns = list(set(cq_patterns + story_patterns))
        
        # Map concepts to patterns using keyword analysis
        for pattern in all_patterns:
            self._map_concepts_to_pattern_keywords(pattern, cq_concepts + story_concepts)
        
        # Log found patterns
        if all_patterns:
            logger.info(f"Found patterns in CQ: {cq_patterns}")
            logger.info(f"Found patterns in story: {story_patterns}")
            logger.info(f"Combined unique patterns: {all_patterns}")
        
        return all_patterns

    def _map_concepts_to_pattern(self, pattern_name: str, explanation: str, 
                               concepts: List[DomainConcept]) -> None:
        """Map domain concepts to pattern elements based on pattern explanation."""
        # Extract pattern concept mentions from explanation
        pattern_concepts = re.findall(r'`([^`]+)`', explanation)
        
        for concept in concepts:
            for pattern_concept in pattern_concepts:
                # Check if concept name appears near pattern concept in explanation
                if concept.name.lower() in explanation.lower():
                    context = self._get_context(explanation, concept.name)
                    if pattern_concept in context:
                        self.hierarchy_analyzer.map_to_pattern(
                            concept, pattern_name, pattern_concept
                        )
                        # Validate the mapping preserves relationships
                        if not self.hierarchy_analyzer.validate_pattern_mapping(
                            concept, self.patterns[pattern_name]
                        ):
                            logger.warning(
                                f"Pattern mapping for {concept.name} breaks hierarchical relationships"
                            )

    def _map_concepts_to_pattern_keywords(self, pattern_name: str,
                                        concepts: List[DomainConcept]) -> None:
        """Map domain concepts to pattern elements based on keywords."""
        if pattern_name not in self.pattern_keywords:
            return
            
        keywords = self.pattern_keywords[pattern_name]
        pattern_graph = self.patterns.get(pattern_name)
        if not pattern_graph:
            return
            
        # Get pattern classes
        pattern_classes = list(pattern_graph.subjects(RDF.type, OWL.Class))
        
        for concept in concepts:
            # Find best matching pattern class based on keywords
            best_match = None
            max_score = 0
            
            for pattern_class in pattern_classes:
                class_name = str(pattern_class).split('#')[-1].lower()
                score = sum(1 for kw in keywords if kw in class_name)
                
                if score > max_score:
                    max_score = score
                    best_match = pattern_class
                    
            if best_match and max_score > 0:
                self.hierarchy_analyzer.map_to_pattern(
                    concept, pattern_name, str(best_match)
                )
                # Validate the mapping
                if not self.hierarchy_analyzer.validate_pattern_mapping(
                    concept, pattern_graph
                ):
                    logger.warning(
                        f"Pattern mapping for {concept.name} breaks hierarchical relationships"
                    )

    def _get_context(self, text: str, term: str, window: int = 50) -> str:
        """Get the context around a term in text."""
        idx = text.lower().find(term.lower())
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(term) + window)
        return text[start:end]

    def get_pattern_prompt(self, patterns: List[str], 
                         include_examples: bool = True) -> str:
        """
        Generate a prompt section for pattern usage that preserves hierarchical relationships.
        
        Args:
            patterns: List of pattern names to include
            include_examples: Whether to include example usages
            
        Returns:
            Prompt text describing pattern usage
        """
        if not patterns:
            return ""
            
        prompt = "\nConsider using the following ontology design patterns while preserving domain hierarchies:\n"
        
        for pattern in patterns:
            if pattern in self.patterns:
                elements = self.get_pattern_elements(pattern)
                prompt += f"\n{pattern.capitalize()} Pattern:\n"
                
                # Add classes with hierarchy information
                if elements["classes"]:
                    class_hierarchy = self._get_class_hierarchy(self.patterns[pattern])
                    prompt += "Class Hierarchy:\n"
                    for parent, children in class_hierarchy.items():
                        prompt += f"- {parent}\n"
                        for child in children:
                            prompt += f"  - {child}\n"
                    
                # Add properties
                if elements["object_properties"]:
                    prompt += "\nProperties: " + ", ".join(
                        [str(p).split('#')[-1] for p in elements["object_properties"][:3]]
                    ) + "\n"
                
                # Add API-based explanation if available
                if hasattr(self, 'pattern_explanations') and pattern in self.pattern_explanations:
                    prompt += f"\nRecommended Usage:\n{self.pattern_explanations[pattern]}\n"
                    prompt += "\nMapped Domain Concepts:\n"
                    for concept in self.hierarchy_analyzer.concepts.values():
                        if pattern in concept.pattern_mappings:
                            prompt += f"- {concept.name} -> {concept.pattern_mappings[pattern]}\n"
                
                # Add example from pattern examples if available
                elif include_examples and self.pattern_examples:
                    pattern_section = self._extract_pattern_section(pattern)
                    if pattern_section:
                        prompt += f"\nExample Usage:\n{pattern_section}\n"
                
        return prompt

    def _get_class_hierarchy(self, graph: Graph) -> Dict[str, List[str]]:
        """Extract class hierarchy from a pattern graph."""
        hierarchy = {}
        
        for s, p, o in graph.triples((None, RDFS.subClassOf, None)):
            if isinstance(o, URIRef):
                parent = str(o).split('#')[-1]
                child = str(s).split('#')[-1]
                
                if parent not in hierarchy:
                    hierarchy[parent] = []
                hierarchy[parent].append(child)
                
        return hierarchy

    def _extract_pattern_section(self, pattern_name: str) -> Optional[str]:
        """Extract the relevant section for a pattern from the examples file."""
        if not self.pattern_examples:
            return None
            
        lines = self.pattern_examples.split('\n')
        pattern_content = []
        in_pattern_section = False
        
        for line in lines:
            if f"# {len(pattern_content)+1}. " in line and pattern_name.lower() in line.lower():
                in_pattern_section = True
                continue
            elif in_pattern_section and line.strip().startswith("# "):
                break
            elif in_pattern_section and line.strip():
                pattern_content.append(line)
                
        return '\n'.join(pattern_content) if pattern_content else None

    def _validate_graph(self, graph: Graph) -> bool:
        """
        Validate an RDF graph.
        
        Args:
            graph: The graph to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check for any triples
            if len(graph) == 0:
                logger.error("Graph is empty")
                return False
                
            # Check for basic ontology structure
            has_classes = False
            has_properties = False
            
            for s, p, o in graph:
                # Check for class declarations
                if p == RDF.type and o == OWL.Class:
                    has_classes = True
                # Check for property declarations
                elif p == RDF.type and (o == OWL.ObjectProperty or o == OWL.DatatypeProperty):
                    has_properties = True
                    
                if has_classes and has_properties:
                    break
            
            if not has_classes:
                logger.warning("No explicit class declarations found, but continuing")
            if not has_properties:
                logger.warning("No explicit property declarations found, but continuing")
                
            return True
            
        except Exception as e:
            logger.error(f"Graph validation error: {str(e)}")
            return False

    def _extract_turtle(self, text: str) -> Optional[str]:
        """
        Extract Turtle syntax from text.
        
        Args:
            text: Text containing Turtle syntax
            
        Returns:
            Extracted Turtle syntax or None if not found
        """
        try:
            # First try to find code blocks
            import re
            turtle_blocks = re.findall(r"```turtle\n(.*?)```", text, re.DOTALL)
            
            if turtle_blocks:
                # Use the first turtle block found
                ontology = turtle_blocks[0].strip()
                
                # Basic validation
                required_elements = ["@prefix", "owl:Class", "rdf:type"]
                if not all(element in ontology for element in required_elements):
                    logger.error("Generated ontology doesn't meet basic requirements")
                    return None
                    
                return ontology
                
            # If no code blocks found, try to extract based on common markers
            if "@prefix" in text and "owl:Class" in text:
                # Remove any markdown code block markers
                ontology = re.sub(r"```.*?\n", "", text)
                ontology = re.sub(r"```\s*$", "", ontology)
                return ontology.strip()
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting Turtle syntax: {str(e)}")
            return None 