"""
NLPValidationAgent - Semantic validation using LLM

Responsibilities:
1. Semantic consistency checking (does the content make sense?)
2. Contradiction detection (conflicting information)
3. Entity relationship validation (do dates/amounts align?)
4. Content vs document type validation
5. Timeline coherence checking
6. Cross-field consistency validation

Uses LLM for intelligent semantic analysis beyond rule-based checks.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from agents import Part2Agent

logger = logging.getLogger(__name__)


class NLPValidationAgent(Part2Agent):
    """Agent: Semantic validation and consistency checking using LLM"""

    # Document type specific validation prompts
    VALIDATION_PROMPTS = {
        "purchase_agreement": """Analyze this purchase agreement document for semantic issues:

1. CONSISTENCY: Are all dates, amounts, and parties mentioned consistently throughout?
2. COMPLETENESS: Does the document seem complete or are there logical gaps?
3. CONTRADICTIONS: Are there any contradicting statements?
4. TIMELINE: Do the dates make logical sense (signing date, effective date, etc.)?
5. AMOUNTS: Are monetary amounts consistent and reasonable?
6. PARTIES: Are buyer and seller clearly identified and consistent?

Document text:
{text}

Respond in JSON format:
{{
    "is_consistent": true/false,
    "consistency_score": 0-100,
    "contradictions": [
        {{"type": "...", "description": "...", "severity": "high/medium/low"}}
    ],
    "timeline_issues": [],
    "missing_logic": [],
    "suspicious_patterns": []
}}""",

        "bank_statement": """Analyze this bank statement for semantic issues:

1. CONSISTENCY: Are transaction dates in chronological order?
2. AMOUNTS: Do debits/credits balance correctly?
3. TIMELINE: Are dates realistic and in proper sequence?
4. PATTERNS: Are there any suspicious transaction patterns?
5. COMPLETENESS: Does it appear to be a complete statement?

Document text:
{text}

Respond in JSON format with consistency_score, contradictions, and timeline_issues.""",

        "id_document": """Analyze this ID document for semantic issues:

1. CONSISTENCY: Are all personal details consistent?
2. DATES: Is date of birth reasonable? Is expiry date valid?
3. COMPLETENESS: Are all required fields present?
4. LOGIC: Do the details make logical sense?

Document text:
{text}

Respond in JSON format with consistency_score, contradictions, and issues.""",

        "proof_of_address": """Analyze this proof of address document:

1. CONSISTENCY: Are name and address consistent throughout?
2. DATE: Is the document date recent and valid?
3. COMPLETENESS: Does it contain all necessary information?
4. CREDIBILITY: Does the content seem authentic?

Document text:
{text}

Respond in JSON format with consistency_score, contradictions, and issues.""",

        "contract": """Analyze this contract document for semantic issues:

1. CONSISTENCY: Are parties, terms, and dates consistent?
2. CONTRADICTIONS: Are there conflicting clauses?
3. TIMELINE: Do dates make sense (signing, effective, expiry)?
4. COMPLETENESS: Does it seem like a complete contract?
5. LOGIC: Are the terms logical and coherent?

Document text:
{text}

Respond in JSON format with consistency_score, contradictions, timeline_issues, and suspicious_patterns.""",

        "invoice": """Analyze this invoice for semantic issues:

1. CONSISTENCY: Are amounts, dates, and parties consistent?
2. CALCULATIONS: Do line items add up correctly?
3. DATE: Is the invoice date valid?
4. LOGIC: Does the invoice make sense?

Document text:
{text}

Respond in JSON format with consistency_score, contradictions, and calculation_errors."""
    }

    def __init__(self, llm_service=None):
        super().__init__("nlp_validation")
        self.llm_service = llm_service

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute semantic validation using LLM.

        Args:
            state: Workflow state containing:
                - ocr_text: Extracted text
                - document_type: Type of document
                - extracted_entities: Basic entities from OCR

        Returns:
            Updated state with:
                - nlp_validation_results: Validation results
                - consistency_score: 0-100
                - contradictions: List of contradictions found
                - semantic_issues: List of semantic problems
                - nlp_valid: Boolean validation result
        """
        self.logger.info("Executing NLPValidationAgent")

        ocr_text = state.get("ocr_text", "")
        document_type = state.get("document_type", "other")
        entities = state.get("extracted_entities", {})
        errors = state.get("errors", [])

        # Initialize results
        nlp_valid = True
        consistency_score = 100
        contradictions = []
        semantic_issues = []
        timeline_issues = []
        
        try:
            # Check if we have enough text
            if len(ocr_text.strip()) < 100:
                semantic_issues.append({
                    "type": "insufficient_text",
                    "severity": "high",
                    "description": "Insufficient text for semantic validation"
                })
                consistency_score = 0
                nlp_valid = False
            
            elif self.llm_service:
                # Use LLM for semantic validation
                validation_results = await self._validate_with_llm(
                    ocr_text, document_type
                )
                
                if validation_results:
                    consistency_score = validation_results.get("consistency_score", 100)
                    contradictions = validation_results.get("contradictions", [])
                    timeline_issues = validation_results.get("timeline_issues", [])
                    suspicious_patterns = validation_results.get("suspicious_patterns", [])
                    missing_logic = validation_results.get("missing_logic", [])
                    
                    # Aggregate all issues
                    semantic_issues.extend(contradictions)
                    semantic_issues.extend(timeline_issues)
                    
                    if suspicious_patterns:
                        semantic_issues.extend(suspicious_patterns)
                    
                    if missing_logic:
                        semantic_issues.extend(missing_logic)
                    
                    # Determine if valid based on score and severity
                    high_severity_issues = [i for i in semantic_issues if i.get("severity") == "high"]
                    if consistency_score < 70 or len(high_severity_issues) > 0:
                        nlp_valid = False
                    
                    self.logger.info(
                        f"LLM validation: score={consistency_score}, "
                        f"issues={len(semantic_issues)}"
                    )
            
            else:
                # Fallback: Basic rule-based validation without LLM
                self.logger.warning("No LLM service available, using basic validation")
                validation_results = self._basic_semantic_validation(
                    ocr_text, document_type, entities
                )
                
                consistency_score = validation_results["consistency_score"]
                semantic_issues = validation_results["issues"]
                
                if consistency_score < 70:
                    nlp_valid = False

        except Exception as e:
            self.logger.error(f"Error in NLP validation: {e}")
            errors.append(f"NLP validation error: {str(e)}")
            nlp_valid = False
            consistency_score = 0

        # Update state
        state["nlp_valid"] = nlp_valid
        state["consistency_score"] = consistency_score
        state["contradictions"] = contradictions
        state["semantic_issues"] = semantic_issues
        state["timeline_issues"] = timeline_issues
        state["errors"] = errors
        state["nlp_validation_executed"] = True

        return state

    async def _validate_with_llm(
        self, 
        text: str, 
        document_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to perform semantic validation.

        Args:
            text: Document text
            document_type: Type of document

        Returns:
            Validation results dictionary or None if error
        """
        try:
            # Get the appropriate prompt for document type
            prompt_template = self.VALIDATION_PROMPTS.get(
                document_type,
                self.VALIDATION_PROMPTS["contract"]  # Default to contract
            )
            
            # Truncate text if too long (keep first 3000 chars)
            if len(text) > 3000:
                text = text[:3000] + "\n...[truncated]"
            
            prompt = prompt_template.format(text=text)
            
            # Call LLM service
            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.3,  # Low temperature for consistent analysis
                max_tokens=1000
            )
            
            # Parse JSON response
            # Try to extract JSON from response
            response_text = response.strip()
            
            # Handle markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            results = json.loads(response_text)
            return results
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            self.logger.error(f"LLM validation error: {e}")
            return None

    def _basic_semantic_validation(
        self, 
        text: str, 
        document_type: str,
        entities: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Fallback: Basic semantic validation without LLM.

        Args:
            text: Document text
            document_type: Type of document
            entities: Extracted entities

        Returns:
            Basic validation results
        """
        issues = []
        score = 100
        
        # Check for basic semantic issues
        text_lower = text.lower()
        
        # Check for placeholder/incomplete content
        placeholders = ['[placeholder]', 'xxx', 'tbd', 'to be determined', 'lorem ipsum']
        for placeholder in placeholders:
            if placeholder in text_lower:
                issues.append({
                    "type": "incomplete",
                    "severity": "high",
                    "description": f"Document contains placeholder: {placeholder}"
                })
                score -= 20
        
        # Check for contradictory language
        import re
        contradictory_patterns = [
            (r'agree.*?disagree', 'Agreement and disagreement mentioned'),
            (r'valid.*?invalid', 'Document states both valid and invalid'),
            (r'accept.*?reject', 'Both acceptance and rejection mentioned'),
            (r'approve.*?deny', 'Both approval and denial mentioned')
        ]
        
        for pattern, description in contradictory_patterns:
            # Search in the full text with DOTALL flag to match across lines
            if re.search(pattern, text_lower, re.DOTALL):
                issues.append({
                    "type": "contradiction",
                    "severity": "high",  # Changed to high severity
                    "description": description
                })
                score -= 20  # Higher penalty for contradictions
        
        # Check for timeline consistency (basic)
        dates = entities.get("dates", [])
        if len(dates) > 1:
            # Just flag if many different dates (may indicate inconsistency)
            unique_dates = len(set(dates))
            if unique_dates > 5:
                issues.append({
                    "type": "timeline",
                    "severity": "low",
                    "description": f"Multiple different dates found ({unique_dates})"
                })
                score -= 5
        
        return {
            "consistency_score": max(0, score),
            "issues": issues
        }
