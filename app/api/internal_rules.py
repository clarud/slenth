"""
Internal Rules API Endpoints

Endpoints for managing internal compliance rules.
"""

import logging
import os
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
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
from services.embeddings import EmbeddingService
from services.vector_db import VectorDBService
from config import settings

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

        # Embed in vector DB
        try:
            embedding_service = EmbeddingService()
            vector_service = VectorDBService()

            embedding = embedding_service.embed_text(rule.text)
            vector_service.upsert_vectors(
                collection_name="internal_rules",
                texts=[rule.text],
                vectors=[embedding],
                metadata=[
                    {
                        "rule_id": db_rule.rule_id,
                        "title": rule.title,
                        "section": rule.section,
                        "effective_date": rule.effective_date,
                        "version": rule.version,
                        "is_active": True,
                    }
                ],
            )
        except Exception as e:
            logger.error(f"Error embedding rule: {e}")
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


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_internal_rules_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """
    Upload internal rules document (JSON format) and batch ingest to PostgreSQL + Pinecone.
    
    Expected JSON format:
    {
        "rules": [
            {
                "title": "Rule Title",
                "description": "Rule description",
                "text": "Full rule text",
                "section": "Section name",
                "obligation_type": "mandatory",
                "conditions": ["condition1", "condition2"],
                "expected_evidence": ["evidence1"],
                "penalty_level": "high",
                "effective_date": "2024-01-01",
                "version": "v1.0",
                "source": "internal_policy_manual"
            }
        ]
    }
    
    Args:
        file: JSON file with rules array
        db: Database session
        
    Returns:
        Success message with ingestion stats
    """
    filename = file.filename
    logger.info(f"Uploading internal rules document: {filename}")

    try:
        # Validate file type
        if not filename.endswith('.json'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JSON files are supported"
            )

        # Read and parse JSON
        content = await file.read()
        try:
            rules_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON format: {str(e)}"
            )

        # Validate structure
        if "rules" not in rules_data or not isinstance(rules_data["rules"], list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON must contain 'rules' array"
            )

        rules = rules_data["rules"]
        if not rules:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rules array cannot be empty"
            )

        # Initialize services
        embedding_service = EmbeddingService()
        vector_service = VectorDBService()
        audit_service = AuditService(db)

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        # Process each rule
        for idx, rule_data in enumerate(rules):
            try:
                # Validate required fields
                required_fields = ["title", "text", "effective_date"]
                missing_fields = [f for f in required_fields if f not in rule_data]
                if missing_fields:
                    errors.append(f"Rule {idx}: Missing required fields: {missing_fields}")
                    skipped_count += 1
                    continue

                title = rule_data["title"]
                text = rule_data["text"]
                
                # Check if rule already exists (by title)
                existing = db.query(InternalRule).filter(
                    InternalRule.title == title
                ).first()

                if existing:
                    # Update existing rule
                    existing.description = rule_data.get("description", existing.description)
                    existing.text = text
                    existing.section = rule_data.get("section", existing.section)
                    existing.obligation_type = rule_data.get("obligation_type", existing.obligation_type)
                    existing.conditions = rule_data.get("conditions", existing.conditions)
                    existing.expected_evidence = rule_data.get("expected_evidence", existing.expected_evidence)
                    existing.penalty_level = rule_data.get("penalty_level", existing.penalty_level)
                    existing.effective_date = rule_data.get("effective_date", existing.effective_date)
                    existing.sunset_date = rule_data.get("sunset_date", existing.sunset_date)
                    existing.version = rule_data.get("version", existing.version)
                    existing.source = rule_data.get("source", existing.source)
                    existing.metadata = rule_data.get("metadata", existing.metadata)
                    existing.updated_at = datetime.utcnow()
                    
                    db.commit()
                    db.refresh(existing)
                    
                    rule_id = existing.rule_id
                    updated_count += 1
                    logger.info(f"Updated rule: {title}")
                else:
                    # Create new rule
                    db_rule = InternalRule(
                        title=title,
                        description=rule_data.get("description", ""),
                        text=text,
                        section=rule_data.get("section"),
                        obligation_type=rule_data.get("obligation_type"),
                        conditions=rule_data.get("conditions", []),
                        expected_evidence=rule_data.get("expected_evidence", []),
                        penalty_level=rule_data.get("penalty_level"),
                        effective_date=rule_data.get("effective_date"),
                        sunset_date=rule_data.get("sunset_date"),
                        version=rule_data.get("version", "v1.0"),
                        source=rule_data.get("source", "internal_policy_manual"),
                        metadata=rule_data.get("metadata", {}),
                    )
                    db.add(db_rule)
                    db.commit()
                    db.refresh(db_rule)
                    
                    rule_id = db_rule.rule_id
                    created_count += 1
                    logger.info(f"Created rule: {title}")

                # Embed in vector DB
                try:
                    embedding = embedding_service.embed_text(text)
                    vector_service.upsert_vectors(
                        collection_name="internal_rules",
                        texts=[text],
                        vectors=[embedding],
                        metadata=[
                            {
                                "rule_id": rule_id,
                                "title": title,
                                "section": rule_data.get("section", ""),
                                "effective_date": rule_data.get("effective_date", ""),
                                "version": rule_data.get("version", "v1.0"),
                                "is_active": True,
                            }
                        ],
                    )
                except Exception as e:
                    logger.warning(f"Failed to embed rule '{title}': {e}")
                    # Continue - rule is still saved in database

            except Exception as e:
                errors.append(f"Rule {idx} ('{rule_data.get('title', 'Unknown')}'): {str(e)}")
                skipped_count += 1
                logger.error(f"Error processing rule {idx}: {e}")
                db.rollback()
                continue

        # Log audit trail
        audit_service.log_action(
            action_type="UPLOAD_INTERNAL_RULES",
            entity_type="internal_rules",
            entity_id=filename,
            user_id="system",
            details={
                "filename": filename,
                "total_rules": len(rules),
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": errors[:10],  # Limit error messages
            },
        )

        logger.info(
            f"Internal rules upload complete: {created_count} created, "
            f"{updated_count} updated, {skipped_count} skipped"
        )

        return {
            "message": "Internal rules uploaded successfully",
            "filename": filename,
            "total_rules": len(rules),
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": errors if errors else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading internal rules: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading internal rules: {str(e)}",
        )
