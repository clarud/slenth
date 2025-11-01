"""
Internal Rules API Endpoints

Endpoints for managing internal compliance rules.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.schemas.rule import (
    InternalRuleCreate,
    InternalRuleListResponse,
    InternalRuleResponse,
    InternalRuleUpdate,
)
from db.database import get_db
from db.models import InternalRule
from services.audit import AuditService
from services.pinecone_db import PineconeService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=InternalRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_internal_rule(
    rule: InternalRuleCreate,
    db: Session = Depends(get_db),
) -> InternalRuleResponse:
    """Create a new internal rule and embed it in vector DB."""
    logger.info(f"Creating internal rule: {rule.title}")

    try:
        # Create rule in database
        db_rule = InternalRule(
            title=rule.title,
            description=rule.description,
            text=rule.text,
            section=rule.section,
            obligation_type=rule.obligation_type,
            conditions=rule.conditions or [],
            expected_evidence=rule.expected_evidence or [],
            penalty_level=rule.penalty_level,
            effective_date=rule.effective_date,
            sunset_date=rule.sunset_date,
            version=rule.version,
            source=rule.source,
            metadata=rule.metadata or {},
        )
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)

        # Embed in Pinecone using integrated embeddings
        try:
            pinecone_service = PineconeService(index_type="internal")

            # Use Pinecone's upsert_records which generates embeddings automatically
            pinecone_service.upsert_records(
                records=[
                    {
                        "_id": db_rule.rule_id,
                        "text": rule.text,
                        "metadata": {
                            "rule_id": db_rule.rule_id,
                            "title": rule.title,
                            "section": rule.section,
                            "effective_date": str(rule.effective_date) if rule.effective_date else None,
                            "version": rule.version,
                            "is_active": True,
                            "obligation_type": rule.obligation_type,
                            "penalty_level": rule.penalty_level,
                        }
                    }
                ],
                namespace="internal-rules"
            )
            logger.info(f"Embedded rule {db_rule.rule_id} in Pinecone")
        except Exception as e:
            logger.error(f"Error embedding rule in Pinecone: {e}")
            # Continue anyway - rule is in DB

        # Log audit
        audit_service = AuditService(db)
        audit_service.log_rule_update(
            rule_id=db_rule.rule_id,
            rule_type="internal_rule",
            user_id="system",
            changes={"action": "created"},
        )

        return InternalRuleResponse(
            rule_id=db_rule.rule_id,
            title=db_rule.title,
            description=db_rule.description,
            text=db_rule.text,
            section=db_rule.section,
            obligation_type=db_rule.obligation_type,
            conditions=db_rule.conditions,
            expected_evidence=db_rule.expected_evidence,
            penalty_level=db_rule.penalty_level,
            effective_date=db_rule.effective_date,
            sunset_date=db_rule.sunset_date,
            version=db_rule.version,
            source=db_rule.source,
            is_active=db_rule.is_active,
            metadata=db_rule.metadata,
            created_at=db_rule.created_at,
            updated_at=db_rule.updated_at,
        )

    except Exception as e:
        logger.error(f"Error creating internal rule: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("", response_model=InternalRuleListResponse)
async def list_internal_rules(
    section: Optional[str] = Query(None),
    is_active: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> InternalRuleListResponse:
    """List internal rules with optional filtering."""
    query = db.query(InternalRule).filter(InternalRule.is_active == is_active)

    if section:
        query = query.filter(InternalRule.section == section)

    total = query.count()

    rules = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return InternalRuleListResponse(
        total=total,
        rules=[
            InternalRuleResponse(
                rule_id=rule.rule_id,
                title=rule.title,
                description=rule.description,
                text=rule.text,
                section=rule.section,
                obligation_type=rule.obligation_type,
                conditions=rule.conditions,
                expected_evidence=rule.expected_evidence,
                penalty_level=rule.penalty_level,
                effective_date=rule.effective_date,
                sunset_date=rule.sunset_date,
                version=rule.version,
                source=rule.source,
                is_active=rule.is_active,
                metadata=rule.metadata,
                created_at=rule.created_at,
                updated_at=rule.updated_at,
            )
            for rule in rules
        ],
        page=page,
        page_size=page_size,
    )


@router.get("/{rule_id}", response_model=InternalRuleResponse)
async def get_internal_rule(
    rule_id: str,
    db: Session = Depends(get_db),
) -> InternalRuleResponse:
    """Get a specific internal rule."""
    rule = db.query(InternalRule).filter(InternalRule.rule_id == rule_id).first()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )

    return InternalRuleResponse(
        rule_id=rule.rule_id,
        title=rule.title,
        description=rule.description,
        text=rule.text,
        section=rule.section,
        obligation_type=rule.obligation_type,
        conditions=rule.conditions,
        expected_evidence=rule.expected_evidence,
        penalty_level=rule.penalty_level,
        effective_date=rule.effective_date,
        sunset_date=rule.sunset_date,
        version=rule.version,
        source=rule.source,
        is_active=rule.is_active,
        metadata=rule.metadata,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.put("/{rule_id}", response_model=InternalRuleResponse)
async def update_internal_rule(
    rule_id: str,
    rule_update: InternalRuleUpdate,
    db: Session = Depends(get_db),
) -> InternalRuleResponse:
    """Update an internal rule (creates new version)."""
    rule = db.query(InternalRule).filter(InternalRule.rule_id == rule_id).first()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )

    # Update fields
    update_data = rule_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)

    # Log audit
    audit_service = AuditService(db)
    audit_service.log_rule_update(
        rule_id=rule_id,
        rule_type="internal_rule",
        user_id="system",
        changes=update_data,
    )

    return InternalRuleResponse(
        rule_id=rule.rule_id,
        title=rule.title,
        description=rule.description,
        text=rule.text,
        section=rule.section,
        obligation_type=rule.obligation_type,
        conditions=rule.conditions,
        expected_evidence=rule.expected_evidence,
        penalty_level=rule.penalty_level,
        effective_date=rule.effective_date,
        sunset_date=rule.sunset_date,
        version=rule.version,
        source=rule.source,
        is_active=rule.is_active,
        metadata=rule.metadata,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_internal_rule(
    rule_id: str,
    db: Session = Depends(get_db),
):
    """Deactivate an internal rule (soft delete)."""
    rule = db.query(InternalRule).filter(InternalRule.rule_id == rule_id).first()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )

    rule.is_active = False
    db.commit()

    # Log audit
    audit_service = AuditService(db)
    audit_service.log_rule_update(
        rule_id=rule_id,
        rule_type="internal_rule",
        user_id="system",
        changes={"action": "deactivated"},
    )

    return None
