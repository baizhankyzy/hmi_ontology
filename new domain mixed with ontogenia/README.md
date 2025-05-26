# Ontology Generator

This Python script automates the generation of ontologies from domain input files using the Ontogenia methodology and Claude API via a Lambda endpoint.

## Prerequisites

- Python 3.8+
- Required Python packages (install using `pip install -r requirements.txt`)

## File Structure

The script expects the following file structure:

```
.
├── data/
│   ├── competency_questions.csv
│   ├── user_stories.csv
│   ├── patterns/
│   │   └── *.txt (ontology design pattern files)
│   └── output/
│       └── (generated ontologies will be stored here)
├── lambda code.txt
├── ontogenia.md
├── domain_prompt.txt
├── generate_ontology.py
└── requirements.txt
```

### Input Files

1. `competency_questions.csv`: List of competency questions (one per row)
2. `user_stories.csv`: List of user stories with descriptions
3. `patterns/*.txt`: Ontology design pattern templates
4. `ontogenia.md`: Describes the Ontogenia methodology
5. `domain_prompt.txt`: Domain-specific ontology modeling methodology
6. `lambda code.txt`: Contains the Lambda endpoint URL for Claude API

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure all input files are in place with the correct structure.

3. Run the script:
   ```bash
   python generate_ontology.py
   ```

## Output

The script will generate:
1. Individual ontology files for each competency question in `data/output/ontology_*.ttl`
2. A merged ontology file `data/output/all_ontologies.ttl`

## Process

1. For each competency question:
   - Identifies related user stories
   - Combines Ontogenia and domain-specific methodologies
   - Constructs a prompt using both approaches
   - Sends the prompt to Claude API via Lambda
   - Saves the generated ontology

2. After processing all questions:
   - Merges individual ontologies into a final file
   - Maintains concept hierarchy
   - Avoids redundancy

## Error Handling

- The script handles missing files gracefully
- Failed API calls are logged but don't stop the process
- Ontology merging preserves all unique elements 