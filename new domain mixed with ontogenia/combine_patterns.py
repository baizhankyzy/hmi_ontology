from pathlib import Path
import os

def combine_patterns():
    patterns_dir = Path("data/patterns")
    output_file = Path("data/all_patterns.txt")
    
    # Create a list to store pattern contents
    all_patterns = []
    
    # Process all .txt and .xml files
    for pattern_file in sorted(patterns_dir.glob("*.[tx][xm][tl]")):
        if pattern_file.name == ".DS_Store":
            continue
            
        all_patterns.append(f"\n{'='*80}\n")
        all_patterns.append(f"Pattern: {pattern_file.name}\n")
        all_patterns.append(f"{'='*80}\n")
        
        try:
            with open(pattern_file, "r", encoding="utf-8") as f:
                content = f.read()
                all_patterns.append(content)
        except Exception as e:
            print(f"Error reading {pattern_file}: {e}")
    
    # Write combined patterns to output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(all_patterns))
    
    print(f"Combined patterns saved to {output_file}")

if __name__ == "__main__":
    combine_patterns() 