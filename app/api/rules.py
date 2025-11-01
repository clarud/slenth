"""
Unified Rules API Endpoints

Endpoints for fetching both internal and external rules.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.schemas.rule import UnifiedRulesResponse, RuleItem
from db.database import get_db
from db.models import InternalRule, ExternalRule

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/all", response_model=UnifiedRulesResponse)
async def get_all_rules(
    regulator: Optional[str] = Query(None, description="Filter by regulator (HKMA, MAS, FINMA)"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction (HK, SG, CH)"),
    section: Optional[str] = Query(None, description="Filter internal rules by section"),
    is_active: bool = Query(True, description="Filter by active status"),
    rule_type: Optional[str] = Query(None, description="Filter by type: internal, external, or all"),
    search: Optional[str] = Query(None, description="Search in title and text"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> UnifiedRulesResponse:
    """
    Get all rules (both internal and external) with unified filtering.
    
    This endpoint combines internal compliance rules and external regulatory circulars
    into a single response for frontend display.
    
    Args:
        regulator: Filter external rules by regulator (HKMA, MAS, FINMA)
        jurisdiction: Filter external rules by jurisdiction (HK, SG, CH)
        section: Filter internal rules by section
        is_active: Show only active rules
        rule_type: Filter by type (internal, external, or all)
        search: Search text in title and rule text
        page: Page number
        page_size: Results per page
        db: Database session
        
    Returns:
        Unified list of internal and external rules with metadata
    """
    internal_rules = []
    external_rules = []
    
    # Fetch internal rules if requested
    if rule_type in [None, "internal", "all"]:
        internal_query = db.query(InternalRule).filter(InternalRule.is_active == is_active)
        
        if section:
            internal_query = internal_query.filter(InternalRule.section == section)
        
        if search:
            search_pattern = f"%{search}%"
            internal_query = internal_query.filter(
                (InternalRule.title.ilike(search_pattern)) |
                (InternalRule.text.ilike(search_pattern))
            )
        
        internal_rules = internal_query.all()
    
    # Fetch external rules if requested
    if rule_type in [None, "external", "all"]:
        external_query = db.query(ExternalRule)
        
        if regulator:
            external_query = external_query.filter(ExternalRule.regulator == regulator.upper())
        
        if jurisdiction:
            external_query = external_query.filter(ExternalRule.jurisdiction == jurisdiction.upper())
        
        if search:
            search_pattern = f"%{search}%"
            external_query = external_query.filter(
                (ExternalRule.rule_title.ilike(search_pattern)) |
                (ExternalRule.rule_text.ilike(search_pattern))
            )
        
        external_rules = external_query.all()
    
    # Combine and format results
    all_rules = []
    
    # Add internal rules
    for rule in internal_rules:
        all_rules.append(RuleItem(
            rule_id=rule.rule_id,
            rule_type="internal",
            title=rule.title,
            description=rule.description,
            text=rule.text[:500] + "..." if len(rule.text) > 500 else rule.text,  # Truncate for list view
            section=rule.section,
            regulator=None,
            jurisdiction=None,
            source=rule.source,
            effective_date=rule.effective_date,
            version=rule.version,
            is_active=rule.is_active,
            created_at=rule.created_at,
            metadata={
                "obligation_type": rule.obligation_type,
                "penalty_level": rule.penalty_level,
            }
        ))
    
    # Add external rules
    for rule in external_rules:
        all_rules.append(RuleItem(
            rule_id=rule.rule_id,
            rule_type="external",
            title=rule.rule_title,
            description=rule.document_title,
            text=rule.rule_text[:500] + "..." if len(rule.rule_text) > 500 else rule.rule_text,
            section=rule.section_path,
            regulator=rule.regulator,
            jurisdiction=rule.jurisdiction,
            source=rule.source_url,
            effective_date=rule.effective_date,
            version=None,
            is_active=True,
            created_at=rule.scraped_at,
            metadata={
                "published_date": rule.published_date.isoformat() if rule.published_date else None,
                "chunk_index": rule.chunk_index,
            }
        ))
    
    # Sort by effective_date (newest first)
    all_rules.sort(key=lambda x: x.effective_date if x.effective_date else x.created_at, reverse=True)
    
    # Paginate
    total = len(all_rules)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_rules = all_rules[start_idx:end_idx]
    
    return UnifiedRulesResponse(
        total=total,
        internal_count=len(internal_rules),
        external_count=len(external_rules),
        rules=paginated_rules,
        page=page,
        page_size=page_size,
        filters_applied={
            "regulator": regulator,
            "jurisdiction": jurisdiction,
            "section": section,
            "is_active": is_active,
            "rule_type": rule_type,
            "search": search,
        }
    )


@router.get("/external", response_model=UnifiedRulesResponse)
async def get_external_rules_only(
    regulator: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> UnifiedRulesResponse:
    """
    Get only external regulatory rules (HKMA, MAS, FINMA).
    
    This is a convenience endpoint that filters to external rules only.
    """
    external_query = db.query(ExternalRule)
    
    if regulator:
        external_query = external_query.filter(ExternalRule.regulator == regulator.upper())
    
    if jurisdiction:
        external_query = external_query.filter(ExternalRule.jurisdiction == jurisdiction.upper())
    
    if search:
        search_pattern = f"%{search}%"
        external_query = external_query.filter(
            (ExternalRule.rule_title.ilike(search_pattern)) |
            (ExternalRule.rule_text.ilike(search_pattern))
        )
    
    total = external_query.count()
    external_rules = (
        external_query
        .order_by(ExternalRule.published_date.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    # Format results
    rules = []
    for rule in external_rules:
        rules.append(RuleItem(
            rule_id=rule.rule_id,
            rule_type="external",
            title=rule.rule_title,
            description=rule.document_title,
            text=rule.rule_text[:500] + "..." if len(rule.rule_text) > 500 else rule.rule_text,
            section=rule.section_path,
            regulator=rule.regulator,
            jurisdiction=rule.jurisdiction,
            source=rule.source_url,
            effective_date=rule.effective_date,
            version=None,
            is_active=True,
            created_at=rule.scraped_at,
            metadata={
                "published_date": rule.published_date.isoformat() if rule.published_date else None,
                "chunk_index": rule.chunk_index,
                "word_count": rule.meta.get("word_count") if rule.meta else None,
            }
        ))
    
    return UnifiedRulesResponse(
        total=total,
        internal_count=0,
        external_count=total,
        rules=rules,
        page=page,
        page_size=page_size,
        filters_applied={
            "regulator": regulator,
            "jurisdiction": jurisdiction,
            "search": search,
        }
    )


@router.get("/internal", response_model=UnifiedRulesResponse)
async def get_internal_rules_only(
    section: Optional[str] = Query(None),
    is_active: bool = Query(True),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> UnifiedRulesResponse:
    """
    Get only internal compliance rules.
    
    This is a convenience endpoint that filters to internal rules only.
    """
    internal_query = db.query(InternalRule).filter(InternalRule.is_active == is_active)
    
    if section:
        internal_query = internal_query.filter(InternalRule.section == section)
    
    if search:
        search_pattern = f"%{search}%"
        internal_query = internal_query.filter(
            (InternalRule.title.ilike(search_pattern)) |
            (InternalRule.text.ilike(search_pattern))
        )
    
    total = internal_query.count()
    internal_rules = (
        internal_query
        .order_by(InternalRule.effective_date.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    # Format results
    rules = []
    for rule in internal_rules:
        rules.append(RuleItem(
            rule_id=rule.rule_id,
            rule_type="internal",
            title=rule.title,
            description=rule.description,
            text=rule.text[:500] + "..." if len(rule.text) > 500 else rule.text,
            section=rule.section,
            regulator=None,
            jurisdiction=None,
            source=rule.source,
            effective_date=rule.effective_date,
            version=rule.version,
            is_active=rule.is_active,
            created_at=rule.created_at,
            metadata={
                "obligation_type": rule.obligation_type,
                "penalty_level": rule.penalty_level,
                "conditions": rule.conditions,
                "expected_evidence": rule.expected_evidence,
            }
        ))
    
    return UnifiedRulesResponse(
        total=total,
        internal_count=total,
        external_count=0,
        rules=rules,
        page=page,
        page_size=page_size,
        filters_applied={
            "section": section,
            "is_active": is_active,
            "search": search,
        }
    )
