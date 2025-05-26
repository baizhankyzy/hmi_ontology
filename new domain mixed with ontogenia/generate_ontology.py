import os
import csv
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

class OntologyGenerator:
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data"
        self.patterns_dir = self.data_dir / "patterns"
        self.output_dir = self.data_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load Lambda endpoint
        with open(self.base_dir / "lambda code.txt", "r") as f:
            first_line = f.readline().strip()
            self.lambda_url = first_line.split("Link-")[-1] if "Link-" in first_line else first_line
        
        # Load Ontogenia methodology
        with open(self.base_dir / "ontogenia.md", "r") as f:
            self.ontogenia_method = f.read()
        
        # Try to load domain prompt if it exists
        try:
            with open(self.base_dir / "domain_prompt.txt", "r") as f:
                self.domain_prompt = f.read()
        except FileNotFoundError:
            self.domain_prompt = ""

    def load_competency_questions(self) -> List[Dict[str, str]]:
        """Load competency questions from CSV file."""
        questions = []
        with open(self.data_dir / "competency_questions.csv", "r") as f:
            reader = csv.DictReader(f)
            questions = list(reader)
        return questions

    def load_user_stories(self) -> List[Dict[str, str]]:
        """Load user stories from CSV file."""
        stories = []
        with open(self.data_dir / "user_stories.csv", "r") as f:
            reader = csv.DictReader(f)
            stories = list(reader)
        return stories

    def load_patterns(self) -> Dict[str, str]:
        """Load ontology design patterns from the patterns directory."""
        patterns = {}
        for pattern_file in self.patterns_dir.glob("*.txt"):
            with open(pattern_file, "r") as f:
                patterns[pattern_file.stem] = f.read()
        
        # Also load XML patterns
        for pattern_file in self.patterns_dir.glob("*.xml"):
            with open(pattern_file, "r") as f:
                patterns[pattern_file.stem] = f.read()
        return patterns

    def find_related_stories(self, competency_question: Dict[str, str], user_stories: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Find user stories related to a competency question using story ID matching."""
        story_id = competency_question.get('StoryID')
        if not story_id:
            return []
        
        return [story for story in user_stories if story.get('StoryID') == story_id]

    def construct_prompt(self, competency_question: Dict[str, str], related_stories: List[Dict[str, str]], patterns: Dict[str, str]) -> str:
        """Construct a prompt combining Ontogenia methodology and domain-specific approach."""
        cq_text = competency_question.get('CompetencyQuestion', '')
        stories_text = "\n".join(f"- {story.get('UserStory', '')}" for story in related_stories)
        
        prompt = f"""Following the Ontogenia methodology:

1. Competency Question to model: {cq_text}

2. Related User Stories:
{stories_text}

3. Available Ontology Design Patterns:
{chr(10).join(f'- {name}' for name in patterns.keys())}

4. Methodology Guidelines:
{self.ontogenia_method}

{self.domain_prompt if self.domain_prompt else ""}

Please generate an ontology module in Turtle (.ttl) format that answers the competency question while:
1. Following the Ontogenia step-by-step approach
2. Incorporating relevant design patterns
3. Maintaining alignment with user stories
4. Including proper labels, comments, and documentation

Return ONLY the Turtle syntax without any additional explanation."""

        return prompt

    def call_claude_api(self, prompt: str) -> str:
        """Send prompt to Claude API via Lambda endpoint."""
        try:
            print(f"Sending request to Lambda endpoint: {self.lambda_url}")
            response = requests.post(
                self.lambda_url,
                json={"prompt": prompt},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()["data"]["answer"]
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            return ""

    def merge_ontologies(self, ontology_files: List[Path]) -> Graph:
        """Merge multiple ontology files into a single graph."""
        merged_graph = Graph()
        
        for ontology_file in ontology_files:
            try:
                g = Graph()
                g.parse(ontology_file, format="turtle")
                merged_graph += g
                print(f"Successfully merged {ontology_file}")
            except Exception as e:
                print(f"Error merging {ontology_file}: {e}")
            
        return merged_graph

    def generate_ontologies(self):
        """Main method to generate ontologies for all competency questions."""
        competency_questions = self.load_competency_questions()
        user_stories = self.load_user_stories()
        patterns = self.load_patterns()
        
        print(f"Loaded {len(competency_questions)} competency questions")
        print(f"Loaded {len(user_stories)} user stories")
        print(f"Loaded {len(patterns)} patterns")
        
        ontology_files = []
        
        for i, cq in enumerate(competency_questions):
            print(f"\nProcessing competency question {i+1}: {cq.get('CompetencyQuestion', '')}")
            
            # Find related stories
            related_stories = self.find_related_stories(cq, user_stories)
            print(f"Found {len(related_stories)} related stories")
            
            # Construct prompt
            prompt = self.construct_prompt(cq, related_stories, patterns)
            
            # Get ontology from Claude
            print("Sending prompt to Claude API...")
            ontology_ttl = self.call_claude_api(prompt)
            
            if ontology_ttl:
                # Save individual ontology
                output_file = self.output_dir / f"ontology_{i+1}.ttl"
                with open(output_file, "w") as f:
                    f.write(ontology_ttl)
                ontology_files.append(output_file)
                print(f"Generated ontology saved to {output_file}")
            else:
                print(f"Failed to generate ontology for CQ {i+1}")
        
        # Merge all ontologies
        if ontology_files:
            print("\nMerging ontologies...")
            merged_graph = self.merge_ontologies(ontology_files)
            merged_file = self.output_dir / "all_ontologies.ttl"
            merged_graph.serialize(destination=str(merged_file), format="turtle")
            print(f"Successfully merged all ontologies into {merged_file}")
        else:
            print("No ontologies were generated to merge.")

if __name__ == "__main__":
    generator = OntologyGenerator()
    generator.generate_ontologies() 