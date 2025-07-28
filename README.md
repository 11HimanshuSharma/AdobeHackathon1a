# PDF Outline Extractor - Adobe India Hackathon 2025 Challenge 1a

## Overview

This solution automatically extracts structured outlines from PDF documents and outputs them as JSON files. It uses advanced text analysis techniques to identify document hierarchies, headings, and structure without relying on embedded PDF bookmarks.

## Approach

### Core Strategy
1. **Text Fragment Analysis**: Extract all text fragments with formatting information (font size, position, bold status)
2. **Fragment Combination**: Intelligently combine fragmented text pieces into complete headings
3. **Hierarchy Detection**: Analyze font sizes, positioning, and formatting to determine heading levels
4. **Structure Classification**: Map detected headings to hierarchical levels (H1, H2, H3, etc.)
5. **JSON Generation**: Output structured data conforming to the required schema

### Key Features
- **Smart Fragment Combining**: Handles PDFs where headings are split across multiple text fragments
- **Form Detection**: Automatically identifies form documents and returns empty outlines appropriately
- **Multi-column Support**: Processes complex layouts including multi-column documents
- **Robust Error Handling**: Provides fallback outputs for problematic documents
- **Performance Optimized**: Processes documents efficiently within time constraints

## Models and Libraries Used

### Primary Dependencies
- **PyMuPDF (v1.23.0+)**: 
  - Core PDF processing library
  - Text extraction with formatting information
  - Lightweight (~50MB), well under the 200MB model size limit
  - No GPU dependencies, runs efficiently on CPU

### Built-in Python Libraries
- **pathlib**: File path handling
- **json**: JSON serialization
- **logging**: Process monitoring and debugging
- **re**: Regular expression processing for text analysis
- **statistics**: Statistical analysis of font sizes and positioning
- **collections**: Data structure utilities (Counter, defaultdict)
- **dataclasses**: Structured data representation

### Algorithm Components
1. **TextFragment Class**: Represents individual text pieces with metadata
2. **FragmentCombiner**: Intelligently merges fragmented text
3. **ImprovedPDFExtractor**: Main extraction engine with hierarchy detection
4. **Heading Classification**: Multi-level analysis for document structure

## Technical Implementation

### Text Fragment Processing
- Extracts text with bounding boxes, font information, and positioning
- Combines fragments based on proximity, font consistency, and logical flow
- Handles special cases like split words and multi-line headings

### Hierarchy Detection Algorithm
- Analyzes font size distributions to identify heading candidates
- Uses statistical methods to determine relative importance levels
- Considers positioning, formatting, and content patterns
- Maps to standard heading levels (H1, H2, H3, etc.)

### Performance Optimizations
- Efficient memory usage for large documents
- Streamlined processing pipeline
- Minimal external dependencies
- CPU-optimized operations

## Docker Configuration

### Container Specifications
- **Base Image**: python:3.10-slim (AMD64 compatible)
- **Platform**: linux/amd64
- **Dependencies**: Installed via requirements.txt
- **Working Directory**: /app
- **Input/Output**: Mounted volumes for file processing

### Directory Structure
```
/app/
├── input/          # Mounted read-only input directory
├── output/         # Mounted output directory
├── process_pdfs.py # Main processing script
└── improved_extractor.py # Core extraction engine
```

## Build and Run Instructions

### Expected Execution (Official)
As per hackathon requirements:

**Build Command:**
```bash
docker build --platform linux/amd64 -t <reponame.someidentifier> .
```

**Run Command:**
```bash
docker run --rm -v $(pwd)/input:/app/input:ro -v $(pwd)/output:/app/output --network none <reponame.someidentifier>
```

### Local Development Testing

**Build Image:**
```bash
docker build --platform linux/amd64 -t pdf-processor .
```

**Test with Sample Data:**
```bash
docker run --rm -v $(pwd)/sample_dataset/pdfs:/app/input:ro -v $(pwd)/sample_dataset/outputs:/app/output --network none pdf-processor
```

**Custom Input/Output:**
```bash
# Create your input/output directories
mkdir input output

# Copy PDFs to input directory
cp your_pdfs/*.pdf input/

# Run processing
docker run --rm -v $(pwd)/input:/app/input:ro -v $(pwd)/output:/app/output --network none pdf-processor

# Check results in output directory
ls output/
```

## Project Structure

```
challenge_1a/
├── Dockerfile              # Container configuration
├── requirements.txt        # Python dependencies
├── process_pdfs.py         # Main processing script
├── improved_extractor.py   # Advanced PDF extraction engine
├── README.md              # This documentation
├── .dockerignore          # Docker build optimization
├── .gitignore             # Git ignore rules
└── sample_dataset/        # Test data
    ├── pdfs/              # Sample input PDFs
    ├── outputs/           # Expected outputs
    └── schema/            # JSON schema definition
```

## Output Format

Each processed PDF generates a corresponding JSON file with the following structure:

```json
{
  "title": "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Main Heading",
      "page": 1
    },
    {
      "level": "H2", 
      "text": "Sub Heading",
      "page": 2
    }
  ]
}
```

### Schema Compliance
- Conforms to `sample_dataset/schema/output_schema.json`
- UTF-8 encoding for international character support
- Consistent formatting with proper indentation

## Performance Characteristics

### Resource Usage
- **Memory**: Efficient processing, stays well under 16GB limit
- **CPU**: Optimized for multi-core usage (8 CPU environment)
- **Storage**: Minimal footprint, PyMuPDF ~50MB
- **Network**: Completely offline operation

### Processing Speed
- **Target**: <10 seconds for 50-page documents
- **Actual**: Sub-second processing for most documents
- **Scalability**: Handles multiple PDFs in batch processing

## Error Handling

### Robust Processing
- Graceful handling of corrupted or problematic PDFs
- Fallback JSON generation for failed extractions
- Comprehensive logging for debugging
- Continued processing despite individual file failures

### Edge Cases
- Form documents (returns empty outline)
- Scanned PDFs (basic text extraction)
- Complex layouts (multi-column, tables)
- Non-standard fonts and formatting

## Development and Testing

### Local Testing
The solution has been tested with the provided sample dataset and produces accurate results matching the expected outputs.

### Validation Checklist
- ✅ All PDFs in input directory processed
- ✅ JSON output files generated for each PDF
- ✅ Output format matches required schema
- ✅ Processing completes within time limits
- ✅ Works without internet access
- ✅ Memory usage within constraints
- ✅ AMD64 architecture compatibility

## Contributing

This solution is designed for the Adobe India Hackathon 2025 Challenge 1a. The implementation focuses on reliability, performance, and accuracy while meeting all specified constraints.

---

**Challenge Requirements Compliance**: This solution meets all official requirements including Docker containerization, offline operation, performance constraints, and output format specifications. 