"""
Quick implementation script for remaining Part 1 agents.
Implements: feature_service, bayesian_engine, pattern_detector, alert_composer, remediation_orchestrator
"""

AGENT_IMPLEMENTATIONS = {
    "feature_service": '''        """
        Execute feature_service agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with extracted features
        """
        self.logger.info("Executing FeatureServiceAgent")

        try:
            transaction = state.get("transaction", {})
            transaction_history = state.get("transaction_history", [])
            
            features = {}
            
            # Basic transaction features
            features["amount"] = float(transaction.get("amount", 0))
            features["is_high_value"] = features["amount"] > 10000
            features["is_round_number"] = features["amount"] % 1000 == 0
            
            # Velocity features from history
            if transaction_history:
                features["transaction_count_24h"] = len([t for t in transaction_history if t.get("hours_ago", 999) < 24])
                features["transaction_count_7d"] = len(transaction_history)
                total_amount = sum([float(t.get("amount", 0)) for t in transaction_history])
                features["total_volume_7d"] = total_amount
                features["avg_amount_7d"] = total_amount / len(transaction_history) if transaction_history else 0
            else:
                features["transaction_count_24h"] = 0
                features["transaction_count_7d"] = 0
                features["total_volume_7d"] = 0
                features["avg_amount_7d"] = 0
            
            # Geographic features
            features["is_cross_border"] = transaction.get("sender_country") != transaction.get("receiver_country")
            features["is_high_risk_country"] = transaction.get("receiver_country") in ["XX", "YY", "ZZ"]  # Placeholder
            
            # Structuring indicators
            features["potential_structuring"] = (
                features["is_high_value"] and 
                features["is_round_number"] and 
                features["transaction_count_24h"] > 3
            )
            
            state["features"] = features
            state["feature_service_completed"] = True
            self.logger.info(f"Extracted {len(features)} features")

        except Exception as e:
            self.logger.error(f"Error in FeatureServiceAgent: {str(e)}", exc_info=True)
            state["features"] = {}
            state["errors"] = state.get("errors", []) + [f"FeatureServiceAgent: {str(e)}"]

        return state''',
    
    "bayesian_engine": '''        """
        Execute bayesian_engine agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with Bayesian posterior probabilities
        """
        self.logger.info("Executing BayesianEngineAgent")

        try:
            features = state.get("features", {})
            control_results = state.get("control_results", [])
            
            # Simple Bayesian update using features and control results
            # Prior probabilities (uniform)
            prior = {"low": 0.50, "medium": 0.30, "high": 0.15, "critical": 0.05}
            
            # Evidence from features
            evidence_score = 0.0
            if features.get("is_high_value"):
                evidence_score += 0.2
            if features.get("is_cross_border"):
                evidence_score += 0.1
            if features.get("potential_structuring"):
                evidence_score += 0.3
            if features.get("transaction_count_24h", 0) > 5:
                evidence_score += 0.2
            if features.get("is_high_risk_country"):
                evidence_score += 0.3
            
            # Evidence from failed controls
            failed_count = len([r for r in control_results if r.get("status") == "fail"])
            critical_failed = len([r for r in control_results if r.get("status") == "fail" and r.get("severity") == "critical"])
            
            if critical_failed > 0:
                evidence_score += 0.4
            elif failed_count > 0:
                evidence_score += 0.2
            
            # Update posterior (simplified Bayesian)
            evidence_score = min(evidence_score, 1.0)
            
            posterior = {
                "low": prior["low"] * (1 - evidence_score),
                "medium": prior["medium"] + (prior["low"] * evidence_score * 0.3),
                "high": prior["high"] + (prior["medium"] * evidence_score * 0.5),
                "critical": prior["critical"] + (evidence_score * 0.3),
            }
            
            # Normalize
            total = sum(posterior.values())
            if total > 0:
                posterior = {k: v/total for k, v in posterior.items()}
            
            state["bayesian_posterior"] = posterior
            state["bayesian_engine_completed"] = True
            self.logger.info(f"Bayesian update: {posterior}")

        except Exception as e:
            self.logger.error(f"Error in BayesianEngineAgent: {str(e)}", exc_info=True)
            state["bayesian_posterior"] = {"low": 0.7, "medium": 0.2, "high": 0.08, "critical": 0.02}
            state["errors"] = state.get("errors", []) + [f"BayesianEngineAgent: {str(e)}"]

        return state''',
    
    "pattern_detector": '''        """
        Execute pattern_detector agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with detected patterns and scores
        """
        self.logger.info("Executing PatternDetectorAgent")

        try:
            transaction = state.get("transaction", {})
            transaction_history = state.get("transaction_history", [])
            features = state.get("features", {})
            
            pattern_scores = {}
            
            # Structuring detection
            structuring_score = 0.0
            if features.get("is_round_number"):
                structuring_score += 30
            if features.get("transaction_count_24h", 0) > 3:
                structuring_score += 40
            if features.get("amount", 0) < 10000 and features.get("amount", 0) > 9000:
                structuring_score += 30
            pattern_scores["structuring"] = min(structuring_score, 100)
            
            # Layering detection (multiple jurisdictions)
            layering_score = 0.0
            if len(transaction_history) > 5:
                countries = set([t.get("receiver_country") for t in transaction_history])
                if len(countries) > 3:
                    layering_score = min(len(countries) * 20, 100)
            pattern_scores["layering"] = layering_score
            
            # Circular transfers (same accounts appearing multiple times)
            circular_score = 0.0
            if transaction_history:
                receiver_counts = {}
                for t in transaction_history:
                    rec = t.get("receiver_account")
                    receiver_counts[rec] = receiver_counts.get(rec, 0) + 1
                max_count = max(receiver_counts.values()) if receiver_counts else 0
                if max_count > 2:
                    circular_score = min(max_count * 25, 100)
            pattern_scores["circular"] = circular_score
            
            # Velocity anomaly
            velocity_score = 0.0
            if features.get("transaction_count_24h", 0) > 10:
                velocity_score = 90
            elif features.get("transaction_count_24h", 0) > 5:
                velocity_score = 60
            elif features.get("transaction_count_24h", 0) > 3:
                velocity_score = 30
            pattern_scores["velocity"] = velocity_score
            
            state["pattern_scores"] = pattern_scores
            state["pattern_detector_completed"] = True
            self.logger.info(f"Pattern scores: {pattern_scores}")

        except Exception as e:
            self.logger.error(f"Error in PatternDetectorAgent: {str(e)}", exc_info=True)
            state["pattern_scores"] = {}
            state["errors"] = state.get("errors", []) + [f"PatternDetectorAgent: {str(e)}"]

        return state''',
    
    "alert_composer": '''        """
        Execute alert_composer agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with composed alerts
        """
        self.logger.info("Executing AlertComposerAgent")

        try:
            transaction_id = state.get("transaction_id")
            risk_score = state.get("risk_score", 0.0)
            risk_band = state.get("risk_band", "Low")
            control_results = state.get("control_results", [])
            
            alerts = []
            
            # Create alert for high/critical risk
            if risk_score >= 60:
                from db.models import AlertSeverity, AlertRole
                
                severity = AlertSeverity.CRITICAL if risk_score >= 80 else AlertSeverity.HIGH
                
                # Compliance alert
                alerts.append({
                    "title": f"{risk_band} Risk Transaction Alert",
                    "description": f"Transaction {transaction_id} flagged with {risk_band} risk (score: {risk_score})",
                    "severity": severity,
                    "role": AlertRole.COMPLIANCE,
                    "source_type": "transaction",
                    "source_id": transaction_id,
                    "metadata": {
                        "risk_score": risk_score,
                        "risk_band": risk_band,
                        "failed_controls": len([r for r in control_results if r.get("status") == "fail"]),
                    }
                })
                
                # Legal alert for critical risks
                if risk_score >= 80:
                    alerts.append({
                        "title": f"CRITICAL: Transaction Requires Legal Review",
                        "description": f"Transaction {transaction_id} has critical risk factors",
                        "severity": AlertSeverity.CRITICAL,
                        "role": AlertRole.LEGAL,
                        "source_type": "transaction",
                        "source_id": transaction_id,
                        "metadata": {"risk_score": risk_score}
                    })
            
            state["alerts"] = alerts
            state["alert_composer_completed"] = True
            self.logger.info(f"Composed {len(alerts)} alerts")

        except Exception as e:
            self.logger.error(f"Error in AlertComposerAgent: {str(e)}", exc_info=True)
            state["alerts"] = []
            state["errors"] = state.get("errors", []) + [f"AlertComposerAgent: {str(e)}"]

        return state''',
    
    "remediation_orchestrator": '''        """
        Execute remediation_orchestrator agent logic.

        Args:
            state: Workflow state

        Returns:
            Updated state with remediation actions
        """
        self.logger.info("Executing RemediationOrchestratorAgent")

        try:
            risk_score = state.get("risk_score", 0.0)
            risk_band = state.get("risk_band", "Low")
            control_results = state.get("control_results", [])
            
            remediation_actions = []
            
            # Generate remediation based on risk level
            if risk_score >= 80:
                remediation_actions.append({
                    "action": "freeze_transaction",
                    "priority": "urgent",
                    "owner": "compliance_officer",
                    "sla_hours": 2,
                    "description": "Immediately freeze transaction pending investigation"
                })
                remediation_actions.append({
                    "action": "escalate_to_senior",
                    "priority": "urgent",
                    "owner": "senior_compliance",
                    "sla_hours": 4,
                    "description": "Escalate to senior management for review"
                })
            
            if risk_score >= 60:
                remediation_actions.append({
                    "action": "request_documentation",
                    "priority": "high",
                    "owner": "front_office",
                    "sla_hours": 24,
                    "description": "Request additional supporting documentation from customer"
                })
                remediation_actions.append({
                    "action": "enhanced_due_diligence",
                    "priority": "high",
                    "owner": "compliance_team",
                    "sla_hours": 48,
                    "description": "Perform enhanced due diligence on customer and counterparty"
                })
            
            # Specific remediation for failed controls
            critical_failures = [r for r in control_results if r.get("status") == "fail" and r.get("severity") == "critical"]
            if critical_failures:
                for failure in critical_failures[:3]:
                    remediation_actions.append({
                        "action": "address_control_failure",
                        "priority": "high",
                        "owner": "compliance_team",
                        "sla_hours": 24,
                        "description": f"Address failed control: {failure.get('rule_title')}"
                    })
            
            state["remediation_actions"] = remediation_actions
            state["remediation_orchestrator_completed"] = True
            self.logger.info(f"Created {len(remediation_actions)} remediation actions")

        except Exception as e:
            self.logger.error(f"Error in RemediationOrchestratorAgent: {str(e)}", exc_info=True)
            state["remediation_actions"] = []
            state["errors"] = state.get("errors", []) + [f"RemediationOrchestratorAgent: {str(e)}"]

        return state'''
}

print("Agent implementation templates ready. Apply manually using replace_string_in_file.")
for agent_name, code in AGENT_IMPLEMENTATIONS.items():
    print(f"\n{'='*60}")
    print(f"Agent: {agent_name}")
    print(f"{'='*60}")
    print(code[:200] + "...")
