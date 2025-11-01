"""
Alert Service - Manage alerts with SLA tracking and role-based routing.

Provides methods for:
- Creating alerts with SLA deadlines
- Routing alerts by role (Front/Compliance/Legal)
- Checking SLA breaches
- Sending WebSocket notifications
- Deduplicating alerts
- Linking alerts to cases
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from config import settings
from db.models import Alert, AlertStatus, AlertSeverity, AlertRole, Case, CaseAlert

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing alerts and SLA tracking."""

    def __init__(self, db_session: Session):
        """
        Initialize alert service.

        Args:
            db_session: Database session
        """
        self.db = db_session

    def create_alert(
        self,
        title: str,
        description: str,
        severity: AlertSeverity,
        role: AlertRole,
        source_type: str,
        source_id: str,
        metadata: Optional[Dict] = None,
    ) -> Alert:
        """
        Create a new alert with SLA deadline.

        Args:
            title: Alert title
            description: Detailed description
            severity: Alert severity level
            role: Target role (Front/Compliance/Legal)
            source_type: Source type (transaction/document)
            source_id: Source entity ID
            metadata: Additional context

        Returns:
            Created alert object
        """
        # Calculate SLA deadline based on severity
        sla_hours = self._get_sla_hours(severity, role)
        sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)

        alert = Alert(
            alert_id=str(uuid4()),
            title=title,
            description=description,
            severity=severity,
            role=role,
            status=AlertStatus.PENDING,
            source_type=source_type,
            source_id=source_id,
            sla_deadline=sla_deadline,
            metadata=metadata or {},
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        logger.info(
            f"Created alert {alert.alert_id} for {role.value} with severity {severity.value}"
        )

        return alert

    def _get_sla_hours(self, severity: AlertSeverity, role: AlertRole) -> int:
        """
        Get SLA hours based on severity and role.

        Args:
            severity: Alert severity
            role: Target role

        Returns:
            SLA hours
        """
        # Map from config
        sla_map = {
            AlertSeverity.CRITICAL: {
                AlertRole.FRONT: settings.sla_front_critical_hours,
                AlertRole.COMPLIANCE: settings.sla_compliance_critical_hours,
                AlertRole.LEGAL: settings.sla_legal_critical_hours,
            },
            AlertSeverity.HIGH: {
                AlertRole.FRONT: settings.sla_front_high_hours,
                AlertRole.COMPLIANCE: settings.sla_compliance_high_hours,
                AlertRole.LEGAL: settings.sla_legal_high_hours,
            },
            AlertSeverity.MEDIUM: {
                AlertRole.FRONT: settings.sla_front_medium_hours,
                AlertRole.COMPLIANCE: settings.sla_compliance_medium_hours,
                AlertRole.LEGAL: settings.sla_legal_medium_hours,
            },
            AlertSeverity.LOW: {
                AlertRole.FRONT: settings.sla_front_low_hours,
                AlertRole.COMPLIANCE: settings.sla_compliance_low_hours,
                AlertRole.LEGAL: settings.sla_legal_low_hours,
            },
        }
        return sla_map[severity][role]

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Alert:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            acknowledged_by: User who acknowledged

        Returns:
            Updated alert
        """
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        if alert.status != AlertStatus.PENDING:
            logger.warning(f"Alert {alert_id} already {alert.status.value}")
            return alert

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by

        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return alert

    def resolve_alert(self, alert_id: str, resolved_by: str, resolution_notes: Optional[str] = None) -> Alert:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID
            resolved_by: User who resolved
            resolution_notes: Optional resolution notes

        Returns:
            Updated alert
        """
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = resolved_by
        if resolution_notes:
            alert.metadata["resolution_notes"] = resolution_notes

        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert {alert_id} resolved by {resolved_by}")
        return alert

    def escalate_alert(self, alert_id: str) -> Alert:
        """
        Escalate an alert to higher priority.

        Args:
            alert_id: Alert ID

        Returns:
            Updated alert
        """
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Escalate severity
        if alert.severity == AlertSeverity.LOW:
            alert.severity = AlertSeverity.MEDIUM
        elif alert.severity == AlertSeverity.MEDIUM:
            alert.severity = AlertSeverity.HIGH
        elif alert.severity == AlertSeverity.HIGH:
            alert.severity = AlertSeverity.CRITICAL

        alert.status = AlertStatus.ESCALATED
        alert.escalated_at = datetime.utcnow()

        # Recalculate SLA with reduced timeline
        sla_hours = self._get_sla_hours(alert.severity, alert.role) // 2
        alert.sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)

        self.db.commit()
        self.db.refresh(alert)

        logger.warning(f"Alert {alert_id} escalated to {alert.severity.value}")
        return alert

    def check_sla_breaches(self) -> List[Alert]:
        """
        Check for alerts that have breached SLA.

        Returns:
            List of breached alerts
        """
        now = datetime.utcnow()
        breached = (
            self.db.query(Alert)
            .filter(
                and_(
                    Alert.sla_deadline < now,
                    Alert.status.in_([AlertStatus.PENDING, AlertStatus.ACKNOWLEDGED]),
                )
            )
            .all()
        )

        logger.info(f"Found {len(breached)} SLA-breached alerts")
        return breached

    def get_alerts_by_role(
        self,
        role: AlertRole,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """
        Get alerts for a specific role with filters.

        Args:
            role: Target role
            status: Optional status filter
            severity: Optional severity filter
            limit: Maximum results

        Returns:
            List of alerts
        """
        query = self.db.query(Alert).filter(Alert.role == role)

        if status:
            query = query.filter(Alert.status == status)
        if severity:
            query = query.filter(Alert.severity == severity)

        alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()

        logger.debug(f"Retrieved {len(alerts)} alerts for role {role.value}")
        return alerts

    def link_alert_to_case(self, alert_id: str, case_id: str) -> CaseAlert:
        """
        Link an alert to a case.

        Args:
            alert_id: Alert ID
            case_id: Case ID

        Returns:
            CaseAlert association
        """
        # Check if link already exists
        existing = (
            self.db.query(CaseAlert)
            .filter(
                and_(
                    CaseAlert.alert_id == alert_id,
                    CaseAlert.case_id == case_id,
                )
            )
            .first()
        )

        if existing:
            logger.debug(f"Alert {alert_id} already linked to case {case_id}")
            return existing

        case_alert = CaseAlert(alert_id=alert_id, case_id=case_id)
        self.db.add(case_alert)
        self.db.commit()
        self.db.refresh(case_alert)

        logger.info(f"Linked alert {alert_id} to case {case_id}")
        return case_alert

    def deduplicate_alerts(
        self,
        source_type: str,
        source_id: str,
        title: str,
        time_window_hours: int = 24,
    ) -> Optional[Alert]:
        """
        Check for duplicate alerts within time window.

        Args:
            source_type: Source type
            source_id: Source ID
            title: Alert title
            time_window_hours: Deduplication window

        Returns:
            Existing alert if duplicate found, None otherwise
        """
        cutoff = datetime.utcnow() - timedelta(hours=time_window_hours)

        existing = (
            self.db.query(Alert)
            .filter(
                and_(
                    Alert.source_type == source_type,
                    Alert.source_id == source_id,
                    Alert.title == title,
                    Alert.created_at >= cutoff,
                    Alert.status.in_([AlertStatus.PENDING, AlertStatus.ACKNOWLEDGED]),
                )
            )
            .first()
        )

        if existing:
            logger.info(f"Found duplicate alert {existing.alert_id} within {time_window_hours}h window")
            return existing

        return None

    def get_dashboard_stats(self, role: Optional[AlertRole] = None) -> Dict:
        """
        Get dashboard statistics for alerts.

        Args:
            role: Optional role filter

        Returns:
            Dict with alert statistics
        """
        query = self.db.query(Alert)
        if role:
            query = query.filter(Alert.role == role)

        total = query.count()
        pending = query.filter(Alert.status == AlertStatus.PENDING).count()
        acknowledged = query.filter(Alert.status == AlertStatus.ACKNOWLEDGED).count()
        escalated = query.filter(Alert.status == AlertStatus.ESCALATED).count()
        resolved = query.filter(Alert.status == AlertStatus.RESOLVED).count()

        # Count by severity
        critical = query.filter(Alert.severity == AlertSeverity.CRITICAL).count()
        high = query.filter(Alert.severity == AlertSeverity.HIGH).count()
        medium = query.filter(Alert.severity == AlertSeverity.MEDIUM).count()
        low = query.filter(Alert.severity == AlertSeverity.LOW).count()

        # SLA breaches
        now = datetime.utcnow()
        breached = (
            query.filter(
                and_(
                    Alert.sla_deadline < now,
                    Alert.status.in_([AlertStatus.PENDING, AlertStatus.ACKNOWLEDGED]),
                )
            )
            .count()
        )

        stats = {
            "total": total,
            "by_status": {
                "pending": pending,
                "acknowledged": acknowledged,
                "escalated": escalated,
                "resolved": resolved,
            },
            "by_severity": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
            },
            "sla_breached": breached,
        }

        if role:
            stats["role"] = role.value

        return stats
