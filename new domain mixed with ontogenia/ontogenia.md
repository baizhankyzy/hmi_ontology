
## Ontogenia
### Description

Ontogenia is a technique for ontology generation using metacognitive prompting in Large Language Models (LLMs). First introduced by Lippolis, A. S., Ceriani, M., Zuppiroli, S., & Nuzzolese, A. G., this method is explained in their poster "Ontogenia: Ontology Generation with Metacognitive Prompting in Large Language Models." This technique refines the metacognitive prompting process to guide an LLM in the role of an ontology engineer, providing it with guidelines for effective ontology formalization.

The inputs for the prompting process include:
- A user story, a new addition not included in previous work.
- One or more Competency Questions (CQs) to model.
- A Metacognitive Prompting Procedure.
- Guidelines for ontology formalization.

Ontogenia is designed to handle one CQ at a time, generating and merging the resulting ontology at each step. The procedure merges five steps from Wang et al.'s metacognitive prompting method with the eXtreme Design methodology, emphasizing collaboration between ontology designers and domain experts, and iterative assessment to ensure the ontology meets initial requirements.

### How It Works with Prompts

#### Single CQ Ontology Design

1. **Procedure Definition:**
   The procedure is defined in a separated file.

2. **Ontology Elements:**
    ```python
    ontology_elements = "Classes, Object Properties, Datatype Properties. Object properties need to have domain and range. All of them need to have an explanation in the rdfs:label. You also need to add restrictions, and subclasses for both classes and object properties when applicable."
    ```

3. **Load Patterns:**
    ```python
    data = pd.read_csv('data/patterns.csv')  # Update the path to your CSV file
    patterns_json = json.dumps({row['Name']: row['Pattern_owl'] for _, row in data.iterrows()})
    ```

4. **Design Ontology Function:**
    ```python
    def design_ontology(patterns_json, CQ, scenario, procedure, ontology_elements):
        prompt = (
            f"Read the following instructions: '{procedure}'. Based on the scenario: '{scenario}', design an ontology module that comprehensively answers the following competency question: '{CQ}'. You can use the following ontology design patterns in OWL format: {patterns_json}. Remember what are the ontology elements: {ontology_elements}. When you're done send me only the whole ontology you've designed in Turtle (.ttl) format, do not comment."
        )
    ```

#### Grouped CQs Ontology Design

1. **Procedure Definition:**
    The procedure is defined in a separated file.

2. **Ontology Elements:**
    ```python
    ontology_elements = "Classes, Object Properties, Datatype Properties. Object properties need to have domain and range. All of them need to have an explanation in the rdfs:label. You also need to add restrictions, and subclasses for both classes and object properties when applicable."
    ```

3. **Load Patterns:**
    ```python
    data = pd.read_csv('data/patterns.csv')  # Update the path to your CSV file
    patterns_json = json.dumps({row['Name']: row['Pattern_owl'] for _, row in data.iterrows()})
    ```

4. **Design Ontology Function with Previous Output:**
    ```python
    def design_ontology(patterns_json, CQ, scenario, procedure, ontology_elements, previous_output=""):
        prompt = (
            f"Following the previous output: '{previous_output}' Read the following instructions: '{procedure}'. Based on the scenario: '{scenario}', design an ontology module that comprehensively answers the following competency question: '{CQ}'. You can use the following ontology design patterns in OWL format: {patterns_json}. Remember what are the ontology elements: {ontology_elements}. When you're done send me only the whole ontology you've designed in Turtle (.ttl) format, do not comment."
        )
    ```

### Detailed Procedure for Ontology Design

1. **Analyze the Competency Question:**
    - Understand the CQ to identify key components.

2. **Identify the Context:**
    - Define the scope and domain of the ontology.

3. **Decompose the Competency Question:**
    - Break down the CQ into subject, predicate, object, and predicate nominative.
    - Map these elements to ontological constructs.

4. **Determine Subclass Relationships:**
    - Establish subclass relationships using rdfs:subClassOf.

5. **Extend the Ontology with Restrictions:**
    - Apply restrictions like owl:allValuesFrom, owl:hasValue, and owl:someValuesFrom.
    - Define cardinality with owl:minCardinality.

6. **Define Equivalent and Disjoint Classes:**
    - Use owl:equivalentClass and owl:disjointWith for class relationships.

7. **Integrate and Refine:**
    - Review interrelationships for logical consistency and completeness.

8. **Validate and Explain:**
    - Confirm the ontology answers all CQs and explain the reasoning behind each element.

9. **Evaluate Confidence and Test:**
    - Test the ontology with instances and assess confidence based on performance.
