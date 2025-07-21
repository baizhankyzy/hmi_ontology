import csv
from collections import defaultdict

def clean_nudges_csv(input_file: str, output_file: str):
    """
    Clean the nudges paper CSV by removing unwanted sections.
    """
    # Sections to exclude
    exclude_sections = {
        "Discussion and Conclusions",
        "Introduction and Background",
        "Case Study",
        "Case Study -",
        "Case Study - First Phase",
        "Case Study - Participants",
        "Case Study - Second Phase",
        "Case Study - Study Design",
        "Case Study - Subjective Measures"
    }
    
    # Keep track of sections and their counts
    section_counts = defaultdict(int)
    cleaned_rows = []
    total_rows = 0
    
    print(f"Reading {input_file}...")
    
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        headers = reader.fieldnames
        
        # Process each row
        for row in reader:
            total_rows += 1
            section = row.get('Section Title', '')
            
            # Skip excluded sections
            if section in exclude_sections:
                continue
                
            cleaned_rows.append(row)
            section_counts[section] += 1
    
    print(f"Original rows: {total_rows}")
    print(f"Rows after cleaning: {len(cleaned_rows)}")
    
    # Write the cleaned data
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(cleaned_rows)
    
    print(f"Cleaned data saved to {output_file}")
    
    # Print unique remaining sections
    print("\nRemaining sections:")
    for section in sorted(section_counts.keys()):
        print(f"- {section}: {section_counts[section]} rows")

if __name__ == "__main__":
    clean_nudges_csv(
        "data/nudges_paper.csv",
        "data/nudges_paper_cleaned.csv"
    ) 