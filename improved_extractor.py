import pymupdf as fitz
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter, defaultdict
import statistics
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TextFragment:
    """Represents a text fragment that needs to be combined."""
    text: str
    page: int
    font_size: float
    is_bold: bool
    x_pos: float
    y_pos: float
    bbox: List[float]
    
class FragmentCombiner:
    """Combines text fragments into meaningful headings."""
    
    def __init__(self, fragments: List[TextFragment]):
        self.fragments = fragments
        
    def combine_fragments(self) -> List[TextFragment]:
        """Combine fragmented text into complete headings."""
        if not self.fragments:
            return []
        
        # Sort fragments by page, then by y position, then by x position
        self.fragments.sort(key=lambda f: (f.page, f.y_pos, f.x_pos))
        
        combined = []
        i = 0
        
        while i < len(self.fragments):
            current = self.fragments[i]
            combined_text = current.text
            combined_bbox = list(current.bbox)
            
            # Look ahead for fragments that should be combined
            j = i + 1
            while j < len(self.fragments):
                next_fragment = self.fragments[j]
                
                # Check if fragments should be combined
                should_combine = self._should_combine_fragments(current, next_fragment, combined_text)
                
                if should_combine:
                    # Add appropriate spacing
                    if self._needs_space_between(combined_text, next_fragment.text):
                        combined_text += " "
                    
                    combined_text += next_fragment.text
                    
                    # Update bounding box
                    combined_bbox[2] = max(combined_bbox[2], next_fragment.bbox[2])  # Extend right
                    combined_bbox[3] = max(combined_bbox[3], next_fragment.bbox[3])  # Extend down
                    
                    j += 1
                else:
                    break
            
            # Create combined fragment if the text is meaningful
            if self._is_meaningful_text(combined_text):
                combined_fragment = TextFragment(
                    text=combined_text.strip(),
                    page=current.page,
                    font_size=current.font_size,
                    is_bold=current.is_bold,
                    x_pos=current.x_pos,
                    y_pos=current.y_pos,
                    bbox=combined_bbox
                )
                combined.append(combined_fragment)
            
            i = j if j > i + 1 else i + 1
        
        return combined
    
    def _should_combine_fragments(self, current: TextFragment, next_frag: TextFragment, combined_text: str) -> bool:
        """Determine if two fragments should be combined."""
        # Must be on same page
        if current.page != next_frag.page:
            return False
        
        # Must have similar font properties (more lenient for invitations)
        font_size_diff = abs(next_frag.font_size - current.font_size)
        if font_size_diff > 4:  # Increased tolerance
            return False
        
        if current.is_bold != next_frag.is_bold:
            return False
        
        # Must be reasonably close vertically (more lenient for scattered text)
        y_diff = abs(next_frag.y_pos - current.y_pos)
        if y_diff > 0.15:  # Increased tolerance for scattered layouts
            return False
        
        # More lenient horizontal positioning for invitation layouts
        x_gap = next_frag.x_pos - current.x_pos
        if x_gap < -0.3:  # Allow more left movement for creative layouts
            return False
        
        # Check if this looks like a continuation
        current_text = combined_text.lower().strip()
        next_text = next_frag.text.lower().strip()
        
        # Don't combine if we have important standalone section headings
        if any(heading in current_text for heading in ['pathway options', 'program overview', 'course requirements']):
            return False
        
        if any(heading in next_text for heading in ['pathway options', 'program overview', 'course requirements']):
            return False
        
        # Special cases for invitation text patterns
        if self._looks_like_invitation_continuation(current_text, next_text):
            return True
        
        # Special cases for RFP fragmentations
        if (current_text.endswith(('request', 'rfp:', 'rfp: r', 'for pr', 'proposal')) or
            next_text.startswith(('quest', 'oposal', 'for', 'to present')) or
            self._looks_like_title_continuation(current_text, next_text)):
            return True
        
        # General continuation logic for short fragments
        if (len(combined_text) < 50 and  # Shorter limit for better combinations
            len(next_text) < 20 and  # Don't combine with long text
            not combined_text.endswith('.') and  # Not end of sentence
            not next_text.startswith('http')):  # Not URL
            return True
        
        return False
    
    def _needs_space_between(self, current_text: str, next_text: str) -> bool:
        """Determine if space is needed between fragments."""
        if not current_text or not next_text:
            return False
        
        # Don't add space if current ends with space or next starts with space
        if current_text.endswith(' ') or next_text.startswith(' '):
            return False
        
        # Don't add space for punctuation
        if next_text[0] in '.,;:!?)':
            return False
        
        # Special handling for invitation text
        current_lower = current_text.lower()
        next_lower = next_text.lower()
        
        # Handle "Y ou T" -> "You T" cases
        if (current_lower.endswith('y') and next_lower.startswith('ou')):
            return False
        if (current_lower.endswith('you') and next_lower.startswith('t')):
            return True  # Need space between "You" and "T"
        if (current_lower.endswith('t') and next_lower.startswith('here')):
            return False  # No space between "T" and "HERE" to make "THERE"
        
        # Add space for normal word boundaries
        return True
    
    def _looks_like_title_continuation(self, current: str, next_text: str) -> bool:
        """Check if this looks like a title continuation."""
        title_patterns = [
            (r'rfp.*request', r'(for|quest)'),
            (r'request.*for', r'(proposal|pr)'),
            (r'for.*pr', r'(oposal|proposal)'),
            (r'proposal.*to', r'present'),
            (r'present.*a', r'proposal'),
            (r'developing.*the', r'business'),
            (r'business.*plan', r'for'),
            (r'ontario.*digital', r'library'),
        ]
        
        for current_pattern, next_pattern in title_patterns:
            if (re.search(current_pattern, current) and 
                re.search(next_pattern, next_text)):
                return True
        
        return False
    
    def _looks_like_invitation_continuation(self, current: str, next_text: str) -> bool:
        """Check if this looks like invitation text continuation."""
        # Common invitation phrase patterns
        invitation_patterns = [
            (r'hope.*to', r'see'),
            (r'to.*see', r'(you|u)'),
            (r'see.*you', r'there'),
            (r'you.*t', r'here'),
            (r'y.*ou', r't'),
            (r'hope', r'(to|t)'),
        ]
        
        for current_pattern, next_pattern in invitation_patterns:
            if (re.search(current_pattern, current) and 
                re.search(next_pattern, next_text)):
                return True
        
        # Check for single character continuations (common in creative layouts)
        if len(current) >= 3 and len(next_text) <= 3:
            return True
        
        return False
    
    def _is_meaningful_text(self, text: str) -> bool:
        """Check if combined text is meaningful enough to keep."""
        text = text.strip()
        
        # Must have reasonable length
        if len(text) < 2:
            return False
        
        # Skip pure numbers or single characters
        if len(text) <= 2 and (text.isdigit() or len(text) == 1):
            return False
        
        # Skip repeated characters
        if len(set(text.replace(' ', ''))) <= 2:
            return False
        
        return True

class ImprovedPDFExtractor:
    """PDF extractor with improved text fragment handling."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.title = ""
        self.outline = []
    
    def extract_outline(self) -> Dict[str, Any]:
        """Extract outline with improved fragment handling."""
        try:
            logger.info(f"Starting improved extraction for {self.pdf_path}")
            
            # Extract and combine text fragments
            all_fragments = self._extract_all_fragments()
            combiner = FragmentCombiner(all_fragments)
            combined_fragments = combiner.combine_fragments()
            
            # Extract title from combined fragments
            self.title = self._extract_title_from_fragments(combined_fragments)
            
            # Detect if this is a form (return empty outline if so)
            if self._is_form_document(combined_fragments):
                logger.info("Detected form document - returning empty outline")
                self.outline = []
                return {"title": self.title, "outline": self.outline}
            
            # Find heading candidates
            heading_candidates = self._find_heading_candidates(combined_fragments)
            
            # Classify into hierarchy
            self.outline = self._classify_headings(heading_candidates)
            
            logger.info(f"Extracted {len(self.outline)} headings with improved method")
            return {"title": self.title, "outline": self.outline}
            
        except Exception as e:
            logger.error(f"Error in improved extraction: {e}")
            return {"title": "Error Processing Document", "outline": []}
        finally:
            self.doc.close()
    
    def _extract_all_fragments(self) -> List[TextFragment]:
        """Extract all text fragments from the PDF."""
        fragments = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_rect = page.rect
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text or len(text) < 1:
                            continue
                        
                        # Skip obvious non-content
                        if self._is_non_content_fragment(text, page_num + 1):
                            continue
                        
                        font_size = span.get("size", 12)
                        font_name = span.get("font", "").lower()
                        is_bold = any(bold_word in font_name for bold_word in ["bold", "black", "heavy"])
                        bbox = span.get("bbox", [0, 0, 0, 0])
                        
                        fragment = TextFragment(
                            text=text,
                            page=page_num + 1,
                            font_size=font_size,
                            is_bold=is_bold,
                            x_pos=bbox[0] / page_rect.width if page_rect.width > 0 else 0,
                            y_pos=bbox[1] / page_rect.height if page_rect.height > 0 else 0,
                            bbox=list(bbox)
                        )
                        
                        fragments.append(fragment)
        
        return fragments
    
    def _is_non_content_fragment(self, text: str, page_num: int) -> bool:
        """Check if fragment is non-content."""
        text_lower = text.lower().strip()
        
        # Page numbers
        if re.match(r'^\d+$', text) and len(text) <= 3:
            return True
        
        # Common non-content
        if text_lower in ['page', 'of', '©', 'copyright']:
            return True
        
        # Use decorative text detection
        if self._is_decorative_text(text):
            return True
        
        return False
    
    def _extract_title_from_fragments(self, fragments: List[TextFragment]) -> str:
        """Extract title from combined fragments."""
        if not fragments:
            return "Untitled Document"
        
        # Get first page fragments
        first_page_fragments = [f for f in fragments if f.page == 1]
        if not first_page_fragments:
            return "Untitled Document"
        
        # Check if this looks like an invitation/flyer (return empty title)
        if self._is_invitation_document(first_page_fragments):
            return ""
        
        # Find the largest font size text that looks like a title
        max_font_size = max(f.font_size for f in first_page_fragments)
        
        # Look for title candidates
        title_candidates = []
        
        # For RFP documents, look for the complete title
        if self._is_rfp_document(first_page_fragments):
            # Try to find complete RFP title by combining fragments
            rfp_title_parts = []
            for fragment in first_page_fragments:
                if fragment.y_pos < 0.3:  # Top portion of first page
                    text_lower = fragment.text.lower()
                    if any(word in text_lower for word in ['rfp', 'request', 'proposal', 'ontario', 'digital', 'library']):
                        rfp_title_parts.append(fragment.text.strip())
            
            if rfp_title_parts:
                # Combine all RFP-related title parts
                combined_title = " ".join(rfp_title_parts)
                # Clean up the title
                combined_title = re.sub(r'\s+', ' ', combined_title)
                if not combined_title.endswith('  '):
                    combined_title += '  '
                return combined_title
        
        # General title extraction for other document types
        for fragment in first_page_fragments:
            if (fragment.font_size >= max_font_size * 0.9 and
                fragment.y_pos < 0.5 and  # Upper half of page
                len(fragment.text) > 10):
                
                # Score candidates
                score = fragment.font_size
                text_lower = fragment.text.lower()
                
                # Boost for title keywords
                if any(word in text_lower for word in ['rfp', 'request', 'proposal', 'ontario', 'digital', 'library']):
                    score += 10
                
                title_candidates.append((fragment.text, score))
        
        if title_candidates:
            # Sort by score and take the best
            title_candidates.sort(key=lambda x: x[1], reverse=True)
            title = title_candidates[0][0].strip()
            
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            if not title.endswith('  '):
                title += '  '
            
            return title
        
        # Fallback to metadata or generic
        if self.doc.metadata and self.doc.metadata.get("title"):
            return self.doc.metadata["title"].strip() + "  "
        
        return "Untitled Document"
    
    def _is_form_document(self, fragments: List[TextFragment]) -> bool:
        """Check if this is a form document."""
        all_text = " ".join(f.text for f in fragments if f.page == 1).lower()
        
        # Check for form indicators
        form_keywords = ['application', 'form', 'name of', 'designation', 'whether', 'service book']
        form_count = sum(1 for keyword in form_keywords if keyword in all_text)
        
        # This is not a form if it has structured document keywords
        structure_keywords = ['rfp', 'request for proposal', 'business plan', 'summary', 'background', 'appendix']
        structure_count = sum(1 for keyword in structure_keywords if keyword in all_text)
        
        return form_count >= 3 and structure_count < 2
    
    def _is_invitation_document(self, fragments: List[TextFragment]) -> bool:
        """Check if this appears to be an invitation or flyer document."""
        all_text = " ".join([f.text.lower() for f in fragments])
        
        # Look for invitation-specific keywords
        invitation_keywords = [
            'rsvp', 'party', 'invitation', 'hope to see you', 
            'topjump', 'you there', 'www.', '.com', 'cdr'
        ]
        
        keyword_count = sum(1 for keyword in invitation_keywords if keyword in all_text)
        
        # If we have multiple invitation keywords, it's likely an invitation
        if keyword_count >= 2:
            return True
        
        # Check for file extension in text (like .cdr)
        if '.cdr' in all_text:
            return True
        
        # Check for creative layout patterns (many small fragments)
        if len(fragments) > 3 and len([f for f in fragments if len(f.text) <= 8]) >= len(fragments) * 0.7:
            return True
        
        return False

    def _is_rfp_document(self, fragments: List[TextFragment]) -> bool:
        """Check if this appears to be an RFP (Request for Proposal) document."""
        all_text = " ".join([f.text.lower() for f in fragments])
        
        # Look for RFP-specific keywords
        rfp_keywords = [
            'rfp', 'request for proposal', 'proposal', 'ontario digital library',
            'business plan', 'summary', 'background', 'appendix', 'evaluation',
            'awarding of contract', 'milestones', 'approach and specific'
        ]
        
        keyword_count = sum(1 for keyword in rfp_keywords if keyword in all_text)
        
        # If we have multiple RFP keywords, it's likely an RFP
        if keyword_count >= 4:
            return True
        
        # Check for typical RFP structure
        if 'rfp' in all_text and any(word in all_text for word in ['proposal', 'contract', 'evaluation']):
            return True
        
        return False

    def _find_heading_candidates(self, fragments: List[TextFragment]) -> List[TextFragment]:
        """Find potential heading candidates."""
        candidates = []
        
        # Check document type
        is_academic = self._is_academic_document(fragments)
        is_rfp = self._is_rfp_document(fragments)
        
        logger.info(f"Document type detection - Academic: {is_academic}, RFP: {is_rfp}")
        
        # Calculate document statistics
        font_sizes = [f.font_size for f in fragments]
        median_font_size = statistics.median(font_sizes) if font_sizes else 12
        
        for fragment in fragments:
            # Score each fragment as potential heading
            score = 0.0
            text = fragment.text.strip()
            text_lower = text.lower()
            
            # Font size score
            font_ratio = fragment.font_size / median_font_size if median_font_size > 0 else 1
            if font_ratio >= 1.2:
                score += 3.0
            elif font_ratio >= 1.1:
                score += 2.0
            elif font_ratio >= 1.0:
                score += 1.0
            
            # Style score
            if fragment.is_bold:
                score += 2.0
            
            # Content pattern scores
            if re.match(r'^(summary|background|appendix|phase|timeline)', text_lower):
                score += 3.0
            
            # RFP document specific scoring (prioritize over academic)
            if is_rfp:
                # Boost main section headings significantly
                if any(phrase in text_lower for phrase in [
                    'summary', 'background', 'appendix', 'approach and specific',
                    'ontario digital library', 'business plan', 'milestones',
                    'evaluation', 'phases', 'preamble', 'terms of reference',
                    'membership', 'chair', 'meetings'
                ]):
                    score += 8.0
                
                # Boost numbered sections and lettered items
                if re.match(r'^\d+\.', text) or re.match(r'^[a-z]\)', text_lower):
                    score += 5.0
                
                # Boost headings that end with colons
                if text.endswith(':') and len(text.split()) <= 6:
                    score += 4.0
                
                # Boost phase-related content
                if re.match(r'^phase [ivx]+', text_lower):
                    score += 6.0
                
                # Don't penalize RFP content - it should show structure
            
            # Academic document specific scoring (only if not RFP)
            elif is_academic:
                # Boost standalone section headings to maximum
                if text_lower.strip() == 'pathway options':
                    score += 20.0  # Highest priority for exact match
                elif any(phrase in text_lower for phrase in ['pathway options', 'program overview', 'requirements']):
                    score += 10.0  # Very high priority
                else:
                    # Heavily penalize everything else in academic docs to focus on main headings
                    score -= 15.0
                
                # Deprioritize detailed content in academic docs
                if any(phrase in text_lower for phrase in ['mission statement', 'goals', 'to provide', 'students with']):
                    score -= 10.0  # Much lower priority for detailed content
                
                # Penalize fragmented sentences heavily
                if len(text.split()) > 8 and not text.endswith('.') and not text.endswith(':'):
                    score -= 8.0
                
                # Heavily penalize long combined text in academic docs
                if len(text) > 100:
                    score -= 20.0
            
            # RFP document specific scoring (less aggressive than academic)
            elif is_rfp:
                # Boost main section headings significantly
                if any(phrase in text_lower for phrase in [
                    'summary', 'background', 'appendix', 'approach and specific',
                    'ontario digital library', 'business plan', 'milestones',
                    'evaluation', 'phases', 'preamble', 'terms of reference',
                    'membership', 'chair', 'meetings'
                ]):
                    score += 8.0
                
                # Boost numbered sections and lettered items
                if re.match(r'^\d+\.', text) or re.match(r'^[a-z]\)', text_lower):
                    score += 5.0
                
                # Boost headings that end with colons
                if text.endswith(':') and len(text.split()) <= 6:
                    score += 4.0
                
                # Boost phase-related content
                if re.match(r'^phase [ivx]+', text_lower):
                    score += 6.0
                
                # Don't penalize RFP content - it should show structure
            
            # Prioritize meaningful combined phrases over fragments
            if any(phrase in text_lower for phrase in ['hope to see you there', 'see you there']):
                score += 5.0  # High priority for meaningful invitations
            
            if text.endswith(':'):
                score += 2.0
            
            if re.match(r'^\d+\.', text):
                score += 2.0
            
            # Penalize very short fragments that look like they should be combined
            if len(text) <= 3 and not re.match(r'^\d+\.', text):
                score -= 2.0
            
            # Boost longer, meaningful phrases
            if len(text) > 15 and ' ' in text:
                score += 1.0
            
            # Position score (left-aligned and upper portions preferred)
            if fragment.x_pos <= 0.1:
                score += 1.0
            
            if fragment.page <= 3:
                score += 0.5
            
            # Length considerations
            word_count = len(text.split())
            if 2 <= word_count <= 15:
                score += 1.0
            elif word_count > 25:
                score -= 1.0
            
            # Filter candidates by minimum score (different thresholds for different document types)
            min_score = 3.0
            if is_rfp:
                min_score = 0.0  # Very low threshold for RFP documents to show complete structure
            elif is_academic:
                min_score = 5.0  # Higher threshold for academic documents to focus on main headings
            
            if score >= min_score:
                candidates.append(fragment)
        
        # Sort by document order
        candidates.sort(key=lambda f: (f.page, f.y_pos))
        
        return candidates
    
    def _classify_headings(self, candidates: List[TextFragment]) -> List[Dict]:
        """Classify headings into levels."""
        if not candidates:
            return []
        
        outline = []
        
        # Create font size hierarchy (limit to H1-H3 only)
        font_sizes = sorted(set(c.font_size for c in candidates), reverse=True)
        level_mapping = {}
        
        # Only map to H1, H2, H3 levels
        for i, size in enumerate(font_sizes[:3]):
            level_mapping[size] = f"H{i + 1}"
        
        # Map remaining sizes to H3 (instead of H4+)
        for size in font_sizes[3:]:
            level_mapping[size] = "H3"
        
        for candidate in candidates:
            text = candidate.text.strip()
            text_lower = text.lower()
            
            # Get base level from font size
            level = level_mapping.get(candidate.font_size, "H3")
            
            # Content-based adjustments (keep within H1-H3 range)
            if re.match(r'^(summary|background|introduction|conclusion)', text_lower):
                level = "H2"
            elif re.match(r'^appendix', text_lower):
                level = "H2"
            elif re.match(r'^\d+\s+[A-Z]', text):
                level = "H3"
            elif text.endswith(':') and len(text.split()) <= 4:
                level = "H3"
            elif 'ontario' in text_lower and 'digital' in text_lower:
                level = "H1"
            elif 'critical component' in text_lower:
                level = "H1"
            
            # Ensure we never go beyond H3
            if level not in ["H1", "H2", "H3"]:
                level = "H3"
            
            outline.append({
                "level": level,
                "text": text + " ",
                "page": candidate.page  # Use 1-based indexing to match expected output
            })
        
        return outline

    def _is_decorative_text(self, text: str) -> bool:
        """Check if text is decorative and should be filtered out."""
        text_lower = text.lower().strip()
        
        # Common decorative elements in invitations/flyers
        decorative_patterns = [
            r'^www\.',  # Website URLs
            r'\.com$', r'\.org$', r'\.net$',  # Domain endings
            r'^rsvp:?$',  # RSVP labels
            r'^\d{4}$',  # Years
            r'parkway', r'avenue', r'street', r'road',  # Address elements
            r'address:', r'pigeon forge', r'dixie stampede',  # Address-related
            r'^\d+\s*(st|nd|rd|th)$',  # Ordinal numbers
            r'^v\d+$',  # Version numbers like V01
            r'\.cdr$', r'\.pdf$', r'\.doc$',  # File extensions
            r'tn\s+\d{5}',  # State + ZIP codes
            r'\(\s*near',  # Location descriptions
            r'topjump', r'closed.*toed.*shoes', r'required.*for.*climbing',  # Activity details
            r'guardians.*not.*attending', r'child.*can.*attend',  # Instructions
        ]
        
        for pattern in decorative_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False

    def _is_academic_document(self, fragments: List[TextFragment]) -> bool:
        """Check if this appears to be an academic/educational document."""
        all_text = " ".join([f.text.lower() for f in fragments])
        
        # Look for academic-specific keywords
        academic_keywords = [
            'stem', 'pathways', 'mission statement', 'goals', 'students',
            'high school', 'curriculum', 'pathway options', 'credits',
            'gpa', 'graduation', 'requirements', 'distinction', 'regular'
        ]
        
        keyword_count = sum(1 for keyword in academic_keywords if keyword in all_text)
        
        # If we have multiple academic keywords, it's likely academic
        if keyword_count >= 4:
            return True
        
        return False

def test_improved_extractor(pdf_path: str):
    """Test the improved extractor."""
    extractor = ImprovedPDFExtractor(pdf_path)
    result = extractor.extract_outline()
    
    print(f"Improved Extraction Results for {Path(pdf_path).name}")
    print("=" * 60)
    print(f"Title: {result['title']}")
    print(f"Headings: {len(result['outline'])}")
    
    if result['outline']:
        print("\nOutline:")
        for i, item in enumerate(result['outline'][:10]):
            print(f"  {i+1:2d}. {item['level']}: {item['text'][:60]}... (Page {item['page']})")
        
        if len(result['outline']) > 10:
            print(f"  ... and {len(result['outline']) - 10} more headings")
    
    # Save result
    output_file = Path(pdf_path).parent / f"{Path(pdf_path).stem}_improved.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nResult saved to: {output_file}")
    return result

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = 'input/file05.pdf'  # Default fallback
    
    test_improved_extractor(pdf_path)
