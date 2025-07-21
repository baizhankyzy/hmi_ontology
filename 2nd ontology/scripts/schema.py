"""JSON Schema definitions for the ontology enrichment pipeline."""

CLAUDE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "knowledge_id": {
            "type": "string",
            "description": "Unique identifier for the knowledge statement"
        },
        "original_statement": {
            "type": "string",
            "description": "The original knowledge statement from the CSV"
        },
        "topic": {
            "type": "string",
            "description": "High-level topic of the statement"
        },
        "section_title": {
            "type": "string",
            "description": "Section title from the source paper"
        },
        "source": {
            "type": "string",
            "description": "Source paper reference"
        },
        "extracted_knowledge": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "string",
                                "description": "The actual subject value"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["individual", "class"],
                                "description": "Whether this is an individual or class reference"
                            },
                            "ontology_class": {
                                "type": "string",
                                "description": "The ontology class this subject belongs to"
                            }
                        },
                        "required": ["value", "type", "ontology_class"]
                    },
                    "predicate": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "string",
                                "description": "The relationship described in natural language"
                            },
                            "ontology_property": {
                                "type": "string",
                                "description": "The corresponding ontology property"
                            }
                        },
                        "required": ["value", "ontology_property"]
                    },
                    "object": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "string",
                                "description": "The actual object value"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["individual", "class", "literal"],
                                "description": "Whether this is an individual, class, or literal value"
                            },
                            "ontology_class": {
                                "type": "string",
                                "description": "The ontology class this object belongs to (if applicable)"
                            },
                            "datatype": {
                                "type": "string",
                                "description": "XSD datatype for literal values"
                            }
                        },
                        "required": ["value", "type"]
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score for this triple extraction"
                    }
                },
                "required": ["subject", "predicate", "object"]
            }
        },
        "metadata": {
            "type": "object",
            "properties": {
                "extraction_timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "When this knowledge was extracted"
                },
                "confidence_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Overall confidence in the extraction"
                }
            }
        }
    },
    "required": ["knowledge_id", "original_statement", "topic", "section_title", "source", "extracted_knowledge"]
} 