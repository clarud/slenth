"""
Audit Service - Comprehensive audit logging for compliance.

Provides methods for:
- Logging all system actions
- Recording user actions and overrides
- Tracking data access
- Maintaining immutable audit trail
- Querying audit logs
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import and_
from sqlalchemy.orm import Session

from db.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit logging and compliance tracking."""

    def __init__(self, db_session: Session):
        """
        Initialize audit service.

        Args:
            db_session: Database session
        """
        self.db = db_session

    def log_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an action to audit trail.

        Args:
            action_type: Type of action (CREATE, UPDATE, DELETE, VIEW, PROCESS, etc.)
            entity_type: Type of entity (transaction, document, alert, case, etc.)
            entity_id: ID of entity
            user_id: ID of user performing action
            user_role: Role of user
            details: Additional details as JSON
            ip_address: User's IP address
            user_agent: User's user agent string

        Returns:
            Created audit log entry
        """
        # Map to AuditLog model fields
        context = dict(details or {})
        if user_role:
            context["user_role"] = user_role

        audit_log = AuditLog(
            action_type=action_type,
            action_description=None,
            actor=user_id or user_role or "system",
            target_type=entity_type,
            target_id=entity_id,
            context_data=context or None,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        logger.debug(
            f"Audit log: {action_type} on {entity_type}:{entity_id} by user {user_id}"
        )

        return audit_log

    def log_transaction_processing(
        self,
        transaction_id: str,
        status: str,
        details: Dict[str, Any],
    ) -> AuditLog:
        """
        Log transaction processing event.

        Args:
            transaction_id: Transaction ID
            status: Processing status
            details: Processing details

        Returns:
            Audit log entry
        """
        return self.log_action(
            action_type="PROCESS_TRANSACTION",
            entity_type="transaction",
            entity_id=transaction_id,
            user_id="system",
            user_role="system",
            details={"status": status, **details},
        )

    def log_document_upload(
        self,
        document_id: str,
        user_id: str,
        filename: str,
        file_size: int,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Log document upload event.

        Args:
            document_id: Document ID
            user_id: Uploading user
            filename: Uploaded filename
            file_size: File size in bytes
            ip_address: User's IP

        Returns:
            Audit log entry
        """
        return self.log_action(
            action_type="UPLOAD_DOCUMENT",
            entity_type="document",
            entity_id=document_id,
            user_id=user_id,
            details={
                "filename": filename,
                "file_size": file_size,
            },
            ip_address=ip_address,
        )

    def log_alert_acknowledgment(
        self,
        alert_id: str,
        user_id: str,
        user_role: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Log alert acknowledgment.

        Args:
            alert_id: Alert ID
            user_id: Acknowledging user
            user_role: User's role
            ip_address: User's IP

        Returns:
            Audit log entry
        """
        return self.log_action(
            action_type="ACKNOWLEDGE_ALERT",
            entity_type="alert",
            entity_id=alert_id,
            user_id=user_id,
            user_role=user_role,
            ip_address=ip_address,
        )

    def log_case_creation(
        self,
        case_id: str,
        user_id: str,
        case_type: str,
        details: Dict[str, Any],
    ) -> AuditLog:
        """
        Log case creation.

        Args:
            case_id: Case ID
            user_id: Creating user
            case_type: Type of case
            details: Case details

        Returns:
            Audit log entry
        """
        return self.log_action(
            action_type="CREATE_CASE",
            entity_type="case",
            entity_id=case_id,
            user_id=user_id,
            details={"case_type": case_type, **details},
        )

    def log_rule_update(
        self,
        rule_id: str,
        rule_type: str,
        user_id: str,
        changes: Dict[str, Any],
    ) -> AuditLog:
        """
        Log internal rule update.

        Args:
            rule_id: Rule ID
            rule_type: Type of rule (internal/external)
            user_id: Updating user
            changes: Changed fields

        Returns:
            Audit log entry
        """
        return self.log_action(
            action_type="UPDATE_RULE",
            entity_type=rule_type,
            entity_id=rule_id,
            user_id=user_id,
            details={"changes": changes},
        )

    def log_data_access(
        self,
        entity_type: str,
        entity_id: str,
        user_id: str,
        access_type: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Log data access event.

        Args:
            entity_type: Type of entity accessed
            entity_id: ID of entity
            user_id: Accessing user
            access_type: Type of access (VIEW, DOWNLOAD, EXPORT, etc.)
            ip_address: User's IP

        Returns:
            Audit log entry
        """
        return self.log_action(
            action_type=f"ACCESS_{access_type}",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            details={"access_type": access_type},
            ip_address=ip_address,
        )

    def log_system_event(
        self,
        event_type: str,
        details: Dict[str, Any],
    ) -> AuditLog:
        """
        Log system-level event.

        Args:
            event_type: Type of system event
            details: Event details

        Returns:
            Audit log entry
        """
        return self.log_action(
            action_type=f"SYSTEM_{event_type}",
            entity_type="system",
            entity_id="system",
            user_id="system",
            user_role="system",
            details=details,
        )

    def get_entity_audit_trail(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get audit trail for specific entity.

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            limit: Maximum results

        Returns:
            List of audit log entries
        """
        logs = (
            self.db.query(AuditLog)
            .filter(
                and_(
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id == entity_id,
                )
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

        logger.debug(f"Retrieved {len(logs)} audit logs for {entity_type}:{entity_id}")
        return logs

    def get_user_actions(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get all actions by a specific user.

        Args:
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum results

        Returns:
            List of audit log entries
        """
        query = self.db.query(AuditLog).filter(AuditLog.user_id == user_id)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

        logger.debug(f"Retrieved {len(logs)} audit logs for user {user_id}")
        return logs

    def search_audit_logs(
        self,
        action_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Search audit logs with multiple filters.

        Args:
            action_type: Optional action type filter
            entity_type: Optional entity type filter
            user_id: Optional user ID filter
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum results

        Returns:
            List of matching audit logs
        """
        query = self.db.query(AuditLog)

        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

        logger.debug(f"Search returned {len(logs)} audit logs")
        return logs

    def get_recent_logs(self, limit: int = 100) -> List[AuditLog]:
        """
        Get most recent audit logs.

        Args:
            limit: Maximum results

        Returns:
            List of recent audit logs
        """
        logs = (
            self.db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

        return logs
