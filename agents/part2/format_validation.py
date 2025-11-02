"""
FormatValidationAgent - Detect formatting errors, spelling, missing sections

Responsibilities:
1. Structure validation (required sections, formatting consistency)
2. Spelling and grammar checking
3. Completeness verification (all expected fields present)
4. Red flag detection (inconsistencies, fraud indicators)
5. Document quality scoring
"""

import logging
import re
from collections import Counter
from typing import Any, Dict, List, Set, Tuple

from agents import Part2Agent

logger = logging.getLogger(__name__)


class FormatValidationAgent(Part2Agent):
    """Agent: Detect formatting errors, spelling, missing sections"""

    # Document type templates - expected sections for each type
    DOCUMENT_TEMPLATES = {
        "purchase_agreement": {
            "required_sections": ["buyer", "seller", "purchase", "price", "property", "date", "signature"],
            "optional_sections": ["witness", "notary", "conditions"],
            "min_length": 500,  # characters
            "expected_pages": (1, 50)  # min, max pages
        },
        "proof_of_address": {
            "required_sections": ["address", "name", "date"],
            "optional_sections": ["account", "amount"],
            "min_length": 200,
            "expected_pages": (1, 5)
        },
        "id_document": {
            "required_sections": ["name", "date of birth", "number", "expiry"],
            "optional_sections": ["nationality", "sex"],
            "min_length": 100,
            "expected_pages": (1, 2)
        },
        "bank_statement": {
            "required_sections": ["account", "balance", "date", "transactions"],
            "optional_sections": ["interest", "fees"],
            "min_length": 300,
            "expected_pages": (1, 20)
        },
        "contract": {
            "required_sections": ["parties", "terms", "date", "signature"],
            "optional_sections": ["clauses", "amendments"],
            "min_length": 500,
            "expected_pages": (1, 100)
        },
        "invoice": {
            "required_sections": ["invoice", "number", "date", "amount", "items"],
            "optional_sections": ["tax", "discount"],
            "min_length": 200,
            "expected_pages": (1, 10)
        },
        "other": {
            "required_sections": [],
            "optional_sections": [],
            "min_length": 50,
            "expected_pages": (1, 1000)
        }
    }

    # Common English words for basic spell checking
    COMMON_WORDS = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
        'agreement', 'contract', 'party', 'parties', 'date', 'signature',
        'buyer', 'seller', 'purchase', 'price', 'property', 'amount', 'total',
        'name', 'address', 'city', 'state', 'country', 'bank', 'account'
    }
    
    # Banking and legal terminology whitelist
    DOMAIN_TERMS = {
        # Banking terms
        'iban', 'swift', 'bic', 'ach', 'wire', 'sepa', 'clearing', 'settlement',
        'aml', 'kyc', 'cdd', 'edd', 'pep', 'sanction', 'ofac', 'fatf',
        'compliance', 'due', 'diligence', 'beneficial', 'owner', 'ubo',
        'remittance', 'correspondent', 'nostro', 'vostro', 'forex',
        
        # Legal terms
        'herein', 'hereof', 'thereof', 'whereby', 'whereas', 'witnesseth',
        'aforementioned', 'heretofore', 'hereafter', 'therein', 'thereto',
        'notary', 'affidavit', 'deposition', 'testament', 'executor',
        
        # Document types
        'invoice', 'receipt', 'voucher', 'statement', 'certificate',
        'attestation', 'declaration', 'acknowledgment', 'waiver',
        
        # Common abbreviations
        'ltd', 'llc', 'inc', 'corp', 'plc', 'gmbh', 'sarl', 'bv',
        'attn', 'dept', 'ref', 'doc', 'annex', 'appendix', 'exhibit'
    }
    
    # Common proper noun patterns (cities, countries, etc.)
    PROPER_NOUN_PATTERNS = [
        # Common cities
        r'\b(zurich|geneva|basel|bern|london|paris|berlin|munich|vienna|milan|rome)\b',
        # Countries
        r'\b(switzerland|swiss|germany|german|austria|austrian|france|french|italy|italian)\b',
        # Banks
        r'\b(helvetia|ubs|credit|suisse|deutsche|hsbc|barclays|santander)\b',
    ]
    
    # Foreign language common words (German, French, Italian for Swiss docs)
    FOREIGN_WORDS = {
        # German
        'und', 'oder', 'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine',
        'von', 'zu', 'im', 'am', 'beim', 'zum', 'zur', 'mit', 'fur', 'uber',
        'herr', 'frau', 'str', 'strasse', 'platz', 'weg', 'gasse',
        
        # French  
        'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'ou',
        'pour', 'par', 'avec', 'sur', 'dans', 'rue', 'avenue', 'place',
        
        # Italian
        'il', 'lo', 'la', 'di', 'da', 'in', 'con', 'su', 'per', 'tra',
        'via', 'piazza', 'corso', 'viale'
    }

    def __init__(self):
        super().__init__("format_validation")
        
        # Initialize spell checker
        self.spell = None
        self.last_misspelled_words = []
        try:
            from spellchecker import SpellChecker
            self.spell = SpellChecker()
            self.logger.info("Spell checker initialized")
        except ImportError:
            self.logger.warning("pyspellchecker not available - spell checking disabled")
        except Exception as e:
            self.logger.warning(f"Failed to initialize spell checker: {e}")

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute format validation: check structure, spelling, completeness.

        Args:
            state: Workflow state containing:
                - ocr_text: Extracted text from document
                - page_texts: List of text per page
                - document_type: Classified document type
                - metadata: Document metadata

        Returns:
            Updated state with:
                - format_valid: Boolean validation result
                - spelling_errors: Number of spelling errors
                - missing_sections: List of missing required sections
                - completeness_score: Score 0-100
                - format_issues: List of detected issues
                - format_quality_score: Overall quality 0-100
        """
        self.logger.info("Executing FormatValidationAgent")

        ocr_text = state.get("ocr_text", "")
        page_texts = state.get("page_texts", [])
        document_type = state.get("document_type", "other")
        metadata = state.get("metadata", {})
        errors = state.get("errors", [])

        # Initialize results
        format_issues = []
        missing_sections = []
        spelling_errors = 0
        spelling_error_rate = 0.0
        misspelled_words = []
        completeness_score = 100
        format_valid = True

        try:
            # Step 1: Get document template
            template = self.DOCUMENT_TEMPLATES.get(document_type, self.DOCUMENT_TEMPLATES["other"])

            # Step 2: Check text length
            text_length = len(ocr_text.strip())
            if text_length < template["min_length"]:
                format_issues.append({
                    "type": "length",
                    "severity": "high",
                    "details": f"Document too short: {text_length} chars (expected min {template['min_length']})"
                })
                completeness_score -= 20
                format_valid = False

            # Step 3: Check page count
            page_count = len(page_texts)
            min_pages, max_pages = template["expected_pages"]
            if page_count < min_pages or page_count > max_pages:
                format_issues.append({
                    "type": "page_count",
                    "severity": "medium",
                    "details": f"Unexpected page count: {page_count} (expected {min_pages}-{max_pages})"
                })
                completeness_score -= 10

            # Step 4: Check for required sections
            missing_sections = self._check_required_sections(ocr_text, template["required_sections"])
            if missing_sections:
                for section in missing_sections:
                    format_issues.append({
                        "type": "missing_section",
                        "severity": "high",
                        "details": f"Missing required section: {section}"
                    })
                completeness_score -= len(missing_sections) * 10
                format_valid = False

            # Step 5: Spelling check
            spelling_errors, spelling_issues = self._check_spelling(ocr_text)
            misspelled_words = getattr(self, 'last_misspelled_words', [])
            
            if spelling_errors > 20:  # High error count
                format_issues.append({
                    "type": "spelling",
                    "severity": "medium",
                    "details": f"High spelling error count: {spelling_errors} errors"
                })
                completeness_score -= min(20, spelling_errors // 5)
            
            # Extract spelling error rate from issues
            for issue in spelling_issues:
                if "spelling error rate" in issue.get("details", ""):
                    # Extract rate from details string
                    try:
                        details = issue["details"]
                        rate_str = details.split(": ")[1].split("%")[0]
                        spelling_error_rate = float(rate_str)
                    except:
                        pass
            
            format_issues.extend(spelling_issues)

            # Step 6: Check for formatting red flags
            red_flags = self._detect_red_flags(ocr_text, page_texts)
            format_issues.extend(red_flags)
            if red_flags:
                completeness_score -= len(red_flags) * 5
            
            # Step 7: Check for capitalization issues
            cap_issues = self._check_capitalization_patterns(ocr_text)
            format_issues.extend(cap_issues)
            if cap_issues:
                completeness_score -= len(cap_issues) * 3

            # Step 7: Check for capitalization issues
            cap_issues = self._check_capitalization_patterns(ocr_text)
            format_issues.extend(cap_issues)
            if cap_issues:
                completeness_score -= len(cap_issues) * 3

            # Step 8: Check document structure consistency
            structure_issues = self._check_structure_consistency(ocr_text, page_texts)
            format_issues.extend(structure_issues)
            if structure_issues:
                completeness_score -= len(structure_issues) * 3

            # Step 9: Calculate overall format quality score
            format_quality_score = max(0, min(100, completeness_score))

            # Determine if document passes validation
            if format_quality_score < 50:
                format_valid = False

            self.logger.info(
                f"Format validation completed: valid={format_valid}, "
                f"issues={len(format_issues)}, quality={format_quality_score}"
            )

        except Exception as e:
            self.logger.error(f"Error in format validation: {e}")
            errors.append(f"Format validation error: {str(e)}")
            format_valid = False
            format_quality_score = 0

        # Update state
        state["format_valid"] = format_valid
        state["spelling_errors"] = spelling_errors
        state["spelling_error_rate"] = spelling_error_rate
        state["misspelled_words"] = misspelled_words
        state["missing_sections"] = missing_sections
        state["completeness_score"] = max(0, min(100, completeness_score))
        state["format_issues"] = format_issues
        state["format_quality_score"] = format_quality_score
        
        # NEW: Add findings to format_findings list for workflow state
        state["format_findings"] = format_issues  # Map format_issues to format_findings
        
        state["errors"] = errors
        state["format_validation_executed"] = True

        return state

    def _check_required_sections(self, text: str, required_sections: List[str]) -> List[str]:
        """
        Check if all required sections are present in the document.

        Args:
            text: Document text
            required_sections: List of required section keywords

        Returns:
            List of missing sections
        """
        text_lower = text.lower()
        missing = []

        for section in required_sections:
            # Check if section keyword appears in text
            if section.lower() not in text_lower:
                missing.append(section)

        return missing

    def _check_spelling(self, text: str) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Perform basic spelling check on text.

        Args:
            text: Document text

        Returns:
            Tuple of (error_count, list of issues)
        """
        issues = []
        error_count = 0

        # Extract words (letters only, lowercase)
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        if not words:
            return 0, issues

        # Count word frequencies
        word_counts = Counter(words)
        total_words = len(words)
        unique_words = len(word_counts)

        # Use pyspellchecker if available
        actual_misspelled = []
        if self.spell:
            try:
                # Find misspelled words
                misspelled_set = self.spell.unknown(words)
                
                # Filter out false positives
                filtered_misspelled = []
                for word in misspelled_set:
                    # Skip if in domain terms
                    if word in self.DOMAIN_TERMS or word in self.FOREIGN_WORDS:
                        continue
                    
                    # Skip if matches proper noun pattern
                    is_proper_noun = False
                    for pattern in self.PROPER_NOUN_PATTERNS:
                        if re.search(pattern, word, re.IGNORECASE):
                            is_proper_noun = True
                            break
                    if is_proper_noun:
                        continue
                    
                    # Skip if likely a proper noun (starts with capital and only appears capitalized)
                    # This catches names like "Muller", "Schmid", etc.
                    if word[0].isupper() and text.count(word.capitalize()) > 0 and text.count(word.lower()) == 0:
                        continue
                    
                    # Skip very short "words" (likely codes/abbreviations)
                    if len(word) < 4:
                        continue
                    
                    # Skip if contains numbers (likely reference codes)
                    if any(c.isdigit() for c in word):
                        continue
                    
                    # This is likely a real typo
                    filtered_misspelled.append(word)
                
                actual_misspelled = filtered_misspelled
                
                if actual_misspelled:
                    error_count = len(actual_misspelled)
                    error_rate = (error_count / total_words) * 100
                    
                    # Store in state for later display
                    self.last_misspelled_words = actual_misspelled[:50]  # Store up to 50
                    
                    if error_rate > 10:
                        issues.append({
                            "type": "spelling",
                            "severity": "high",
                            "details": f"High spelling error rate: {error_rate:.1f}% ({error_count} misspelled words)"
                        })
                    elif error_rate > 5:
                        issues.append({
                            "type": "spelling",
                            "severity": "medium",
                            "details": f"Moderate spelling errors: {error_rate:.1f}% ({error_count} misspelled words)"
                        })
                    elif error_count > 0:
                        issues.append({
                            "type": "spelling",
                            "severity": "low",
                            "details": f"Minor spelling errors: {error_count} typos found"
                        })
            except Exception as e:
                self.logger.error(f"Spell check error: {e}")

        # Check for suspicious patterns
        # 1. Too many unique words (possible gibberish)
        if total_words > 50 and unique_words / total_words > 0.8:
            issues.append({
                "type": "spelling",
                "severity": "high",
                "details": "Unusually high unique word ratio - possible gibberish text"
            })
            error_count += 10

        # 2. Check for very uncommon words (not in common word list)
        uncommon_words = [w for w in words if len(w) > 3 and w not in self.COMMON_WORDS]
        uncommon_ratio = len(uncommon_words) / total_words if total_words > 0 else 0

        if uncommon_ratio > 0.7:  # More than 70% uncommon words
            issues.append({
                "type": "spelling",
                "severity": "medium",
                "details": f"High ratio of uncommon words: {uncommon_ratio:.1%}"
            })
            if not actual_misspelled:  # Only add to count if spell checker didn't run
                error_count += 5

        # 3. Check for repeated character patterns (aaa, bbb, etc.)
        gibberish_pattern = r'\b([a-z])\1{3,}\b'  # 4+ repeated chars
        gibberish_matches = re.findall(gibberish_pattern, text.lower())
        if gibberish_matches:
            issues.append({
                "type": "spelling",
                "severity": "high",
                "details": f"Detected gibberish patterns: {len(gibberish_matches)} occurrences"
            })
            error_count += len(gibberish_matches) * 2

        # 4. Check for numbers mixed with letters (l33t speak or OCR errors)
        mixed_pattern = r'\b[a-z]+\d+[a-z]+\b|\b\d+[a-z]+\d+\b'
        mixed_matches = re.findall(mixed_pattern, text.lower())
        if len(mixed_matches) > 5:
            issues.append({
                "type": "spelling",
                "severity": "low",
                "details": f"Multiple mixed alphanumeric words: {len(mixed_matches)} found (possible OCR errors)"
            })
            error_count += 2

        return error_count, issues

    def _detect_red_flags(self, text: str, page_texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect red flags that might indicate fraud or tampering.

        Args:
            text: Full document text
            page_texts: List of page text objects

        Returns:
            List of red flag issues
        """
        red_flags = []

        # 1. Check for blank pages
        blank_pages = [p for p in page_texts if len(p.get("text", "").strip()) < 50]
        if blank_pages:
            red_flags.append({
                "type": "blank_pages",
                "severity": "medium",
                "details": f"Found {len(blank_pages)} blank or near-blank pages"
            })

        # 2. Check for inconsistent text density across pages
        if len(page_texts) > 1:
            char_counts = [p.get("char_count", 0) for p in page_texts]
            avg_chars = sum(char_counts) / len(char_counts)
            
            # Find pages with significantly different character counts
            outliers = [i+1 for i, count in enumerate(char_counts) if abs(count - avg_chars) > avg_chars * 0.7]
            if outliers:
                red_flags.append({
                    "type": "inconsistent_density",
                    "severity": "low",
                    "details": f"Pages with unusual text density: {outliers}"
                })

        # 3. Check for suspicious keyword combinations
        text_lower = text.lower()
        suspicious_patterns = [
            (r'\b(urgent|immediately|asap)\b.*\b(transfer|send|wire)\b', "urgency+transfer"),
            (r'\b(temporary|provisional|interim)\b.*\b(account|address)\b', "temporary credentials"),
            (r'\b(do not|don\'t)\b.*\b(verify|check|validate)\b', "anti-verification"),
        ]

        for pattern, description in suspicious_patterns:
            if re.search(pattern, text_lower):
                red_flags.append({
                    "type": "suspicious_language",
                    "severity": "medium",
                    "details": f"Detected suspicious pattern: {description}"
                })

        # 4. Check for placeholder text
        placeholders = ['xxx', 'tbd', 'to be determined', '[placeholder]', 'lorem ipsum']
        found_placeholders = [p for p in placeholders if p in text_lower]
        if found_placeholders:
            red_flags.append({
                "type": "placeholder_text",
                "severity": "high",
                "details": f"Found placeholder text: {', '.join(found_placeholders)}"
            })

        return red_flags

    def _check_capitalization_patterns(self, text: str) -> List[Dict[str, Any]]:
        """
        Check for unusual capitalization patterns that may indicate tampering or OCR errors.
        
        Args:
            text: Document text
            
        Returns:
            List of capitalization issues
        """
        issues = []
        
        # Extract words (excluding single letters)
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
        
        if not words:
            return issues
        
        # 1. Check for "WeIrD CaPs" pattern (alternating or random caps mid-word)
        weird_caps = []
        for word in words:
            # Skip if all uppercase (acronyms) or all lowercase or proper capitalization
            if word.isupper() or word.islower() or word.istitle():
                continue
            
            # Check for mixed case (not just first letter capitalized)
            if any(c.isupper() for c in word[1:]) and any(c.islower() for c in word[1:]):
                weird_caps.append(word)
        
        if weird_caps:
            # Get unique weird caps (limit to first 10 for display)
            unique_weird = list(set(weird_caps))[:10]
            issues.append({
                "type": "capitalization",
                "severity": "medium",
                "details": f"Unusual capitalization detected: {', '.join(unique_weird)}"
            })
        
        # 2. Check for excessive ALL CAPS (more than 20% of words)
        all_caps_words = [w for w in words if w.isupper() and len(w) > 1]
        caps_ratio = len(all_caps_words) / len(words) if words else 0
        
        if caps_ratio > 0.2:  # More than 20% all caps
            issues.append({
                "type": "capitalization",
                "severity": "low",
                "details": f"Excessive use of ALL CAPS: {caps_ratio:.1%} of words"
            })
        
        # 3. Check for words starting with lowercase in sentence positions
        # (indicates poor OCR or typing)
        sentences = re.split(r'[.!?]\s+', text)
        lowercase_starts = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 0:
                # Check if first character is lowercase letter
                if sentence[0].islower():
                    lowercase_starts += 1
        
        if lowercase_starts > len(sentences) * 0.3:  # More than 30% lowercase sentence starts
            issues.append({
                "type": "capitalization",
                "severity": "low",
                "details": f"Many sentences start with lowercase letters ({lowercase_starts} sentences)"
            })
        
        return issues

    def _check_structure_consistency(
        self, 
        text: str, 
        page_texts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Check for structural inconsistencies in the document.

        Args:
            text: Full document text
            page_texts: List of page text objects

        Returns:
            List of structure issues
        """
        issues = []

        # 1. Check for excessive line breaks (formatting issues)
        line_breaks = text.count('\n\n\n')  # Triple line breaks
        if line_breaks > 10:
            issues.append({
                "type": "formatting",
                "severity": "low",
                "details": f"Excessive line breaks detected: {line_breaks} occurrences"
            })

        # 2. Check for date consistency
        dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
        if len(dates) > 1:
            # Check if dates are in multiple formats (inconsistent)
            formats = set()
            for date in dates:
                if '/' in date:
                    formats.add('slash')
                if '-' in date:
                    formats.add('dash')
            
            if len(formats) > 1:
                issues.append({
                    "type": "date_format",
                    "severity": "low",
                    "details": "Inconsistent date formats detected"
                })

        # 3. Check for number formatting consistency
        amounts = re.findall(r'\$[\d,]+\.?\d*|\d+[,\d]*\.\d{2}', text)
        if amounts:
            comma_style = sum(1 for a in amounts if ',' in a)
            no_comma_style = len(amounts) - comma_style
            
            # If mix of styles and both > 20% of amounts
            if comma_style > 0 and no_comma_style > 0:
                if min(comma_style, no_comma_style) / len(amounts) > 0.2:
                    issues.append({
                        "type": "number_format",
                        "severity": "low",
                        "details": "Inconsistent number formatting"
                    })

        return issues
