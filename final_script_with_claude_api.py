#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Contextual Topic Identification for Urban Planning Presentation
This script identifies both specific and broader topics from presentation slides,
taking into account the context of surrounding slides for knowledge graph creation.
"""

import os
import json
import requests
import re
import pandas as pd
from typing import List, Dict, Any
from collections import defaultdict

# Create a directory for output files
os.makedirs("output", exist_ok=True)

def load_slides_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load slides from a text file and extract their content.
    
    Args:
        file_path: Path to the text file containing slides
        
    Returns:
        List of dictionaries with slide number and content
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content by slide marker
        slides_raw = content.split('--- Slide')
        
        # Remove empty first element if it exists
        if slides_raw[0].strip() == '':
            slides_raw = slides_raw[1:]
        
        # Process each slide to clean up and structure
        processed_slides = []
        for i, slide in enumerate(slides_raw, 1):
            # Clean up slide content
            slide_content = slide.strip()
            
            # Extract slide number if present
            if '---' in slide_content:
                parts = slide_content.split('---', 1)
                slide_number_str = parts[0].strip()
                slide_content = parts[1].strip() if len(parts) > 1 else ""
                try:
                    slide_number = int(slide_number_str)
                except ValueError:
                    slide_number = i
            else:
                slide_number = i
                
            processed_slides.append({
                'slide_number': slide_number,
                'content': slide_content
            })
        
        print(f"Successfully loaded {len(processed_slides)} slides from {file_path}")
        return processed_slides
    except Exception as e:
        print(f"Error loading slides from {file_path}: {str(e)}")
        return []

def should_skip_slide(slide_content: str) -> bool:
    """
    Determine if a slide should be skipped (e.g., table of contents, section headers).
    
    Args:
        slide_content: The content of the slide
        
    Returns:
        True if the slide should be skipped, False otherwise
    """
    # Common keywords that indicate organizational slides
    organizational_keywords = [
        "Table of Contents", 
        "Agenda", 
        "Overview",
        "Part [A-Z]",
        "Section [0-9]",
        "Introduction",
        "Conclusion",
        "Summary",
        "Thank you"
    ]
    
    # Check if the slide contains these keywords or is very short
    if len(slide_content.split()) < 10:  # Very short slides are likely headers
        return True
        
    for keyword in organizational_keywords:
        if re.search(keyword, slide_content, re.IGNORECASE):
            # If keyword is found but slide has substantial content, keep it
            if len(slide_content.split()) > 50:
                return False
            return True
    
    return False

def query_claude(prompt: str) -> str:
    """
    Send a prompt to Claude via the Lambda function URL.
    
    Args:
        prompt: The prompt to send to Claude
        
    Returns:
        Claude's response as a string
    """
    # Lambda function URL for Claude API
    CLAUDE_LAMBDA_URL = "https://6poq7jfwb5xl3xujin32htosoq0mqlxz.lambda-url.eu-central-1.on.aws/"
    
    # Prepare the request payload
    payload = {
        "prompt": prompt
    }
    
    # Send the request
    try:
        response = requests.post(
            CLAUDE_LAMBDA_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            try:
                response_data = response.json()
                return response_data.get('data', {}).get('answer', '')
            except json.JSONDecodeError:
                print(f"Error decoding JSON response: {response.text}")
                return ""
        else:
            print(f"Error calling Claude: {response.status_code}, {response.text}")
            return ""
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return ""

def create_slide_chunks(slides: List[Dict[str, Any]], chunk_size: int = 3) -> List[Dict[str, Any]]:
    """
    Create chunks of slides to provide context for topic identification.
    
    Args:
        slides: List of slide dictionaries
        chunk_size: Number of slides in each chunk (odd number recommended)
        
    Returns:
        List of chunk dictionaries with target slide and context
    """
    chunks = []
    
    for i, slide in enumerate(slides):
        # Calculate the start and end indices for the chunk
        half_size = chunk_size // 2
        start_idx = max(0, i - half_size)
        end_idx = min(len(slides), i + half_size + 1)
        
        # Get the context slides
        context_slides = slides[start_idx:end_idx]
        
        # Create the chunk dictionary
        chunk = {
            'target_slide': slide,
            'context_slides': context_slides,
            'target_index': i - start_idx  # Index of target slide within context
        }
        
        chunks.append(chunk)
    
    return chunks

def identify_section_boundaries(slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identify section boundaries in the presentation.
    
    Args:
        slides: List of slide dictionaries
        
    Returns:
        List of section dictionaries with title, start index, end index, and slides
    """
    sections = []
    current_section = {"title": "Introduction", "start": 0, "slides": []}
    
    section_indicators = [
        "part",
        "section",
        "introduction",
        "conclusion",
        "summary",
        "planning",
        "technologies",
        "methodology",
        "results"
    ]
    
    for i, slide in enumerate(slides):
        content = slide['content'].lower()
        
        # Check if this slide seems to be a section header
        is_section_header = False
        
        # Very short slides with certain keywords might be headers
        if len(content.split()) < 15:
            for indicator in section_indicators:
                if indicator in content:
                    is_section_header = True
                    break
        
        # Also check for numbered sections (e.g., "Part A", "Section 1")
        if re.search(r"part\s+[a-z]|section\s+\d", content, re.IGNORECASE):
            is_section_header = True
        
        if is_section_header:
            # Complete the previous section if it exists
            if current_section["slides"]:
                current_section["end"] = i - 1
                sections.append(current_section)
            
            # Start a new section
            # Extract a title (use the first line or the whole content if it's short)
            title = content.split('\n')[0] if '\n' in content else content
            current_section = {"title": title, "start": i, "slides": []}
        
        current_section["slides"].append(slide)
    
    # Add the last section
    if current_section["slides"]:
        current_section["end"] = len(slides) - 1
        sections.append(current_section)
    
    return sections

def find_slide_section(slide_number: int, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Find which section a slide belongs to.
    
    Args:
        slide_number: The slide number to find
        sections: List of section dictionaries
        
    Returns:
        The section dictionary containing the slide
    """
    for section in sections:
        for slide in section["slides"]:
            if slide["slide_number"] == slide_number:
                return section
    
    # Default to the first section if not found
    return sections[0] if sections else {"title": "Unknown", "slides": []}

def get_topic_keywords(slides: List[Dict[str, Any]], num_keywords: int = 20) -> Dict[str, int]:
    """
    Extract key topic words from all slides to understand the presentation.
    
    Args:
        slides: List of slide dictionaries
        num_keywords: Number of top keywords to extract
        
    Returns:
        Dictionary of keywords and their frequency
    """
    # Combine all slide content
    all_text = " ".join([slide["content"] for slide in slides])
    
    # Simple keyword extraction based on word frequency
    # Remove common stop words
    stop_words = {"the", "and", "a", "to", "of", "in", "is", "that", "it", "with", "as", "for", "on", "was", "by", "are", "this", "an", "be"}
    
    # Split text into words and count frequency
    words = re.findall(r'\b\w+\b', all_text.lower())
    word_counts = defaultdict(int)
    
    for word in words:
        if len(word) > 3 and word not in stop_words:  # Only count words longer than 3 chars and not in stop words
            word_counts[word] += 1
    
    # Get top keywords
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    top_keywords = dict(sorted_words[:num_keywords])
    
    return top_keywords

def find_related_slides(target_slide: Dict[str, Any], slides: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Find slides related to the target slide based on content similarity.
    This is a simplified version without using embeddings.
    
    Args:
        target_slide: The target slide dictionary
        slides: List of all slide dictionaries
        top_n: Number of related slides to find
        
    Returns:
        List of related slide dictionaries
    """
    target_content = target_slide["content"].lower()
    
    # Extract important words from the target slide
    target_words = set(re.findall(r'\b\w+\b', target_content))
    
    # Calculate similarity scores for all slides
    similarities = []
    for slide in slides:
        if slide["slide_number"] == target_slide["slide_number"]:
            continue  # Skip the target slide itself
            
        slide_content = slide["content"].lower()
        slide_words = set(re.findall(r'\b\w+\b', slide_content))
        
        # Use Jaccard similarity (intersection over union of words)
        if not target_words or not slide_words:
            similarity = 0
        else:
            similarity = len(target_words.intersection(slide_words)) / len(target_words.union(slide_words))
        
        similarities.append((slide, similarity))
    
    # Sort by similarity and get top N
    similarities.sort(key=lambda x: x[1], reverse=True)
    return [slide for slide, _ in similarities[:top_n]]

def create_comprehensive_context(target_slide: Dict[str, Any], 
                                slides: List[Dict[str, Any]], 
                                sections: List[Dict[str, Any]],
                                global_keywords: Dict[str, int]) -> str:
    """
    Create a comprehensive context for a slide including section, neighbors, and related slides.
    
    Args:
        target_slide: The target slide dictionary
        slides: List of all slide dictionaries
        sections: List of section dictionaries
        global_keywords: Dictionary of important keywords from the presentation
        
    Returns:
        Context string for the slide
    """
    try:
        # Find the section this slide belongs to
        section = find_slide_section(target_slide["slide_number"], sections)
        
        # Get immediate neighbors (3 before and 3 after if available)
        slide_indices = [i for i, s in enumerate(slides) if s["slide_number"] == target_slide["slide_number"]]
        if not slide_indices:
            print(f"Warning: Slide {target_slide['slide_number']} not found in slides list.")
            slide_index = 0
        else:
            slide_index = slide_indices[0]
        
        start_idx = max(0, slide_index - 3)
        end_idx = min(len(slides), slide_index + 4)  # +4 because the end is exclusive
        neighbors = slides[start_idx:end_idx]
        
        # Find related slides from throughout the presentation
        related_slides = find_related_slides(target_slide, slides)
        
        # Prepare global context
        global_context = "PRESENTATION OVERVIEW:\n"
        global_context += f"- Total slides: {len(slides)}\n"
        global_context += f"- Key topics: {', '.join(list(global_keywords.keys())[:10])}\n"
        global_context += f"- Sections: {', '.join([s.get('title', 'Unknown') for s in sections])}\n\n"
        
        # Prepare section context
        section_context = f"SECTION CONTEXT:\n"
        section_context += f"- Current section: {section.get('title', 'Unknown')}\n"
        section_context += f"- Slides in section: {[s.get('slide_number', 0) for s in section.get('slides', [])]}\n\n"
        
        # Prepare neighboring slides context
        neighbor_context = "NEIGHBORING SLIDES:\n"
        for slide in neighbors:
            slide_marker = "TARGET SLIDE" if slide["slide_number"] == target_slide["slide_number"] else "SLIDE"
            content_preview = slide['content'][:200] + "..." if len(slide['content']) > 200 else slide['content']
            neighbor_context += f"\n{slide_marker} (Slide {slide['slide_number']}):\n{content_preview}"
        
        # Prepare related slides context
        related_context = "\n\nTOPICALLY RELATED SLIDES:\n"
        for slide in related_slides:
            content_preview = slide['content'][:200] + "..." if len(slide['content']) > 200 else slide['content']
            related_context += f"\nRELATED SLIDE (Slide {slide['slide_number']}):\n{content_preview}"
        
        # Combine all contexts
        full_context = global_context + section_context + neighbor_context + related_context
        
        return full_context
    except Exception as e:
        print(f"Error creating context: {str(e)}")
        return f"Error creating context: {str(e)}"

def identify_topics_with_context(chunk: Dict[str, Any], 
                             slides: List[Dict[str, Any]], 
                             sections: List[Dict[str, Any]],
                             global_keywords: Dict[str, int],
                             file_path: str) -> Dict[str, str]:
    """
    Identify both specific and broader topics for a slide using comprehensive context.
    
    Args:
        chunk: Dictionary with target slide and context slides
        slides: List of all slide dictionaries
        sections: List of section dictionaries
        global_keywords: Dictionary of global presentation keywords
        file_path: Path to the source file
        
    Returns:
        Dictionary with specific topic and broader category
    """
    try:
        target_slide = chunk['target_slide']
        
        # Create comprehensive context
        context_str = create_comprehensive_context(target_slide, slides, sections, global_keywords)
        
        # Create prompt with comprehensive context
        prompt = f"""
        You are an expert in analyzing presentation slides about urban planning and sustainability for knowledge graph creation.

        I will provide you with a target slide along with comprehensive context from a presentation. Your tasks are:

        1. Identify the SPECIFIC topic of the target slide (e.g., "Green Infrastructure", "Water Management Systems")

        2. Identify the BROADER CATEGORY this topic belongs to. This category will be used as the basis for creating a JSON SCHEMA to extract all properties and classes from related slides.

        The broader categories should be conceptual domains like:
        - "Urban Planning"
        - "Green Infrastructure"
        - "Transportation Systems" 
        - "Building Design"
        - "Community Engagement"
        - "Policy Frameworks"

        I am creating a knowledge graph from these presentation slides that will be queried in the future, so both specific topics and broader categories must be clearly defined and consistent.

        Context information for the slide:
        {context_str}

        The TARGET SLIDE content is:
        {target_slide['content']}

        Remember: The broader category will be used to create a JSON schema for extracting properties and classes.

        Source file: {os.path.basename(file_path) if file_path else "unknown"}

        Please respond in this exact JSON format with nothing else:
        {{"specific_topic": "The specific topic of the target slide", "broader_category": "The broader category for schema creation"}}
        """
        
        # Send request to Claude
        response = query_claude(prompt)
        
        # Parse the JSON response
        try:
            topics = json.loads(response)
            return topics
        except json.JSONDecodeError:
            print(f"Warning: Could not parse JSON response: {response}")
            # If parsing fails, try to extract the information using regex
            specific_match = re.search(r'"specific_topic"\s*:\s*"([^"]+)"', response)
            broader_match = re.search(r'"broader_category"\s*:\s*"([^"]+)"', response)
            
            specific_topic = specific_match.group(1) if specific_match else "Unknown"
            broader_category = broader_match.group(1) if broader_match else "Other"
            
            return {
                "specific_topic": specific_topic,
                "broader_category": broader_category
            }
    except Exception as e:
        print(f"Error in identify_topics_with_context: {str(e)}")
        return {
            "specific_topic": f"Error: {str(e)}",
            "broader_category": "Error"
        }

def analyze_slides_with_context(file_path: str, sample_size: int = None, chunk_size: int = 3) -> pd.DataFrame:
    """
    Analyze slides with comprehensive context to identify topics and broader categories.
    
    Args:
        file_path: Path to the text file containing slides
        sample_size: Optional limit on number of slides to process
        chunk_size: Number of slides in each context chunk
        
    Returns:
        DataFrame with slide numbers, specific topics, and broader categories
    """
    try:
        # Load slides
        all_slides = load_slides_from_file(file_path)
        if not all_slides:
            print("Error: No slides loaded from file.")
            return pd.DataFrame()
        
        # Filter out slides that should be skipped
        substantive_slides = [slide for slide in all_slides if not should_skip_slide(slide['content'])]
        print(f"Found {len(substantive_slides)} substantive slides after filtering.")
        
        # Limit to sample size if specified
        if sample_size is not None:
            substantive_slides = substantive_slides[:sample_size]
            print(f"Using sample of {len(substantive_slides)} slides.")
        
        print("Preparing comprehensive context...")
        
        # Identify sections in the presentation
        sections = identify_section_boundaries(substantive_slides)
        print(f"Identified {len(sections)} sections in the presentation")
        
        # Extract global keywords from all slides
        global_keywords = get_topic_keywords(substantive_slides)
        top_keywords = list(global_keywords.keys())[:5]
        print(f"Extracted key topics: {', '.join(top_keywords)}...")
        
        # Create context chunks
        chunks = create_slide_chunks(substantive_slides, chunk_size)
        
        # Analyze each chunk
        results = []
        print("\nAnalyzing slides with comprehensive context...")
        for i, chunk in enumerate(chunks):
            target_slide = chunk['target_slide']
            slide_number = target_slide['slide_number']
            
            # Show progress
            print(f"Processing slide {slide_number} ({i+1}/{len(chunks)})...")
            
            # Identify topics with comprehensive context
            topics = identify_topics_with_context(chunk, substantive_slides, sections, global_keywords, file_path)
            
            # Add to results
            results.append({
                'slide_number': slide_number,
                'specific_topic': topics['specific_topic'],
                'broader_category': topics['broader_category']
            })
            
            # Print result for this slide
            print(f"Slide {slide_number}: {topics['specific_topic']} (Category: {topics['broader_category']})")
        
        # Convert to DataFrame
        if not results:
            print("Warning: No results generated.")
            return pd.DataFrame()
            
        return pd.DataFrame(results)
    except Exception as e:
        print(f"Error in analyze_slides_with_context: {str(e)}")
        return pd.DataFrame()

def summarize_by_category(df: pd.DataFrame):
    """
    Summarize the identified topics by broader category.
    
    Args:
        df: DataFrame with slide numbers, specific topics, and broader categories
    """
    # Group by broader category
    categories = df['broader_category'].unique()
    
    # Print summary
    print("\nHierarchical Topic Summary:")
    print("---------------------------")
    for category in sorted(categories):
        category_slides = df[df['broader_category'] == category]
        print(f"\n{category} ({len(category_slides)} slides):")
        
        # Group by specific topic within category
        topic_groups = category_slides.groupby('specific_topic')['slide_number'].apply(list)
        
        for topic, slides in topic_groups.items():
            print(f"  - {topic}: Slides {slides}")
            
    # Return dictionary of categories and their slides
    category_dict = {}
    for category in categories:
        category_slides = df[df['broader_category'] == category]
        category_dict[category] = list(category_slides['slide_number'])
    
    return category_dict

def main():
    """Main function to run the script"""
    # File path to the slides
    file_path = "data/test-urban-planning.txt"
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found. Please check the path.")
        return
    
    print(f"Starting analysis with file: {file_path}")
    
    # Ask user for analysis mode
    analysis_mode = input("Choose analysis mode (1: Sample only, 2: All slides): ").strip()
    
    if analysis_mode == "1":
        # Run on a small sample (3 slides)
        print("Testing with a small sample of slides...")
        sample_df = analyze_slides_with_context(file_path, sample_size=3)
        
        if not sample_df.empty:
            # Display sample results
            print("\nSample Results:")
            print("---------------")
            for _, row in sample_df.iterrows():
                print(f"Slide {row['slide_number']}: {row['specific_topic']} (Category: {row['broader_category']})")
            
            # Save sample results
            sample_df.to_csv('output/sample_topic_analysis.csv', index=False)
            print("Sample results saved to 'output/sample_topic_analysis.csv'")
    else:
        # Analyze all slides
        print("\nAnalyzing all slides...")
        df_results = analyze_slides_with_context(file_path)
        
        if not df_results.empty:
            # Save all results to CSV
            df_results.to_csv('output/hierarchical_topic_analysis.csv', index=False)
            print(f"\nResults saved to 'output/hierarchical_topic_analysis.csv'")
            
            # Summarize by category
            category_dict = summarize_by_category(df_results)
            
            # Calculate category statistics
            category_counts = df_results['broader_category'].value_counts()
            category_percentages = df_results['broader_category'].value_counts(normalize=True) * 100
            
            # Display category statistics
            print("\nCategory Distribution:")
            print("---------------------")
            for category, count in category_counts.items():
                percentage = category_percentages[category]
                print(f"{category}: {count} slides ({percentage:.1f}%)")

if __name__ == "__main__":
    main()
