import os
import json
from pathlib import Path
from improved_extractor import ImprovedPDFExtractor

def process_pdfs():
    # Get input and output directories
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in input directory")
        return
    
    for pdf_file in pdf_files:
        try:
            print(f"Processing {pdf_file.name}...")
            
            # Initialize the PDF extractor for this specific file
            extractor = ImprovedPDFExtractor(str(pdf_file))
            
            # Extract outline from PDF
            result = extractor.extract_outline()
            
            # Create output JSON file
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully processed {pdf_file.name} -> {output_file.name}")
            
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {str(e)}")
            
            # Create a fallback JSON with basic structure
            fallback_data = {
                "title": f"Document: {pdf_file.stem}",
                "outline": [
                    {
                        "level": "H1",
                        "text": "Document Content",
                        "page": 1
                    }
                ]
            }
            
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(fallback_data, f, indent=2, ensure_ascii=False)
            
            print(f"Created fallback output for {pdf_file.name}")

if __name__ == "__main__":
    print("Starting PDF processing...")
    process_pdfs() 
    print("Completed PDF processing")