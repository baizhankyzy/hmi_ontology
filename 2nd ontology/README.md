# Driver Monitoring System Ontology Project

This project contains tools and scripts for processing and analyzing a Driver Monitoring System ontology using competency questions and SPARQL queries.

## Project Structure

```
.
├── src/                    # Main source code
│   └── query_app.py       # Main query application
├── tests/                  # Test files
│   ├── test_query.py      # Test queries
│   └── test_ontology.py   # Ontology tests
├── scripts/               # Utility scripts
│   ├── process_competency_questions.py
│   ├── examine_ontology.py
│   ├── claude_ontology_generator.py
│   └── new_ontology_pipeline.py
├── data/                  # Data files
│   └── competency_questions.csv
├── output/               # Generated ontology files
├── templates/            # Template files for queries
├── patterns/            # Ontology design patterns
├── logs/                # Log files
└── requirements.txt     # Project dependencies
```

## Components

- **src/**: Contains the main application code
  - `query_app.py`: Web application for querying the ontology

- **tests/**: Contains test files
  - `test_query.py`: Tests for SPARQL queries
  - `test_ontology.py`: Tests for ontology validation

- **scripts/**: Utility scripts for various tasks
  - `process_competency_questions.py`: Processes competency questions
  - `examine_ontology.py`: Tools for ontology examination
  - `claude_ontology_generator.py`: Ontology generation script
  - `new_ontology_pipeline.py`: Pipeline for ontology processing

- **data/**: Contains input data files
- **output/**: Contains generated ontology files
- **templates/**: Contains query templates
- **patterns/**: Contains ontology design patterns
- **logs/**: Contains execution logs

## Requirements

The project has multiple requirement files for different components:
- `requirements.txt`: Main project dependencies
- `requirements_query_app.txt`: Dependencies for the query application
- `requirements_claude.txt`: Dependencies for the Claude-based generator
- `requirements_new.txt`: Additional dependencies 