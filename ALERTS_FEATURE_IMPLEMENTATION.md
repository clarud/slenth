# Alerts Feature Implementation

## Overview
Added a comprehensive alerts system to the compliance report display with:
1. Backend API endpoints for fetching and managing alerts
2. Frontend modal component for viewing and managing alerts
3. Remediation workflow controls (trigger/reject)

## Backend Changes

### 1. API Endpoints (`app/api/alerts.py`)

#### New Endpoint: Get Transaction Alerts
```python
GET /alerts/transaction/{transaction_id}
```
- Fetches all alerts for a specific transaction
- Returns alerts with role, severity, status, and remediation workflow information

#### New Endpoints: Remediation Workflow
```python
POST /alerts/{alert_id}/remediation/trigger
POST /alerts/{alert_id}/remediation/reject
```
- Placeholder endpoints that return status messages
- Ready for future implementation of actual workflow logic
- Return structure:
  ```json
  {
    "success": true,
    "message": "Remediation workflow has been triggered/rejected",
    "alert_id": "...",
    "workflow_status": "triggered|rejected",
    "note": "This is a placeholder - actual workflow not yet implemented"
  }
  ```

### 2. Schema Updates (`app/schemas/alert.py`)
- Added `remediation_workflow` field to `AlertResponse`
- Field is optional and contains the remediation workflow description

### 3. Database Model
Already existed in `db/models.py`:
- `Alert` table with fields:
  - `role`: Enum (front, compliance, legal)
  - `severity`: Enum (low, medium, high, critical)
  - `status`: Enum (pending, acknowledged, in_progress, resolved, escalated)
  - `remediation_workflow`: Text field with workflow description
  - `transaction_id`: Foreign key to Transaction
  - `sla_deadline`: DateTime for SLA tracking

## Frontend Changes

### 1. API Client (`frontend/src/api/client.ts`)

Added three new API functions:
```typescript
fetchTransactionAlerts(transactionId: string): Promise<AlertListResponse>
triggerRemediationWorkflow(alertId: string): Promise<RemediationResponse>
rejectRemediationWorkflow(alertId: string): Promise<RemediationResponse>
```

### 2. Type Definitions (`frontend/src/types/api.ts`)

Added new interfaces:
```typescript
interface Alert {
  alert_id: string;
  title: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  role: "front" | "compliance" | "legal";
  status: "pending" | "acknowledged" | "in_progress" | "resolved" | "escalated";
  remediation_workflow?: string | null;
  sla_deadline: string;
  // ... other fields
}

interface AlertListResponse {
  total: number;
  alerts: Alert[];
  page: number;
  page_size: number;
}

interface RemediationResponse {
  success: boolean;
  message: string;
  alert_id: string;
  workflow_status: "triggered" | "rejected";
  note: string;
}
```

### 3. Alerts Modal Component (`frontend/src/components/AlertsModal.tsx`)

New modal component with features:
- **Automatic alert fetching** when opened
- **Color-coded severity badges**: Critical (red), High (orange), Medium (yellow), Low (blue)
- **Role badges**: Compliance (purple), Legal (indigo), Front (green)
- **Status badges**: Resolved (green), In Progress (blue), Acknowledged (yellow), Escalated (red)
- **Alert details display**:
  - Title and description
  - Role, status, and severity badges
  - Created date and SLA deadline
  - Acknowledgment and resolution timestamps
  - Remediation workflow description (if available)
- **Remediation workflow controls**:
  - Two action buttons per alert:
    - ✅ "Trigger Remediation Workflow" (green)
    - ❌ "Reject Remediation Workflow" (red)
  - After clicking, displays status message
  - Placeholder implementation with informative note
- **Responsive design** with scrollable content
- **Keyboard support**: ESC to close
- **Empty state**: Shows friendly message when no alerts exist

### 4. ReportView Integration (`frontend/src/components/ReportView.tsx`)

Added:
- **"View Alerts" button** in the report header
  - Positioned at top-right with alert icon
  - Orange color to stand out
  - Only visible when transaction is selected
- **Modal state management**
- **Modal rendering** at component level

## UI/UX Features

### Alert Display
- Clean card-based layout with color-coded borders
- Severity indicators with intuitive colors
- Role-specific badges for assignment visibility
- Timestamp information for audit trail
- Remediation workflow in highlighted box

### Remediation Controls
- Side-by-side buttons for clear decision making
- Green for approve/trigger, red for reject
- Immediate visual feedback after action
- Informative placeholder messages

### Empty States
- No alerts: Shows success icon with friendly message
- Loading state: Animated spinner
- Error state: Clear error message in red alert box

## Testing

### Backend Testing
```bash
# Test alerts endpoint
curl http://localhost:8000/alerts/transaction/{transaction_id}

# Test trigger workflow
curl -X POST http://localhost:8000/alerts/{alert_id}/remediation/trigger

# Test reject workflow
curl -X POST http://localhost:8000/alerts/{alert_id}/remediation/reject
```

### Expected Responses
- Alerts endpoint returns empty array if no alerts exist (working as expected)
- Remediation endpoints return success messages with placeholder notes

## Future Enhancements

To implement actual remediation workflows:

1. **Backend**:
   - Implement actual workflow logic in the remediation endpoints
   - Update alert status when workflow is triggered/rejected
   - Add workflow state tracking in database
   - Integrate with case management system
   - Send notifications to assigned roles

2. **Frontend**:
   - Add workflow progress tracking
   - Show workflow history/timeline
   - Add comments/notes functionality
   - Implement real-time updates via WebSocket
   - Add alert filtering and sorting in modal

3. **Integration**:
   - Connect to existing case management
   - Integrate with email/notification system
   - Add workflow approval chains
   - Implement SLA monitoring and alerts

## File Summary

### Modified Files
1. `app/api/alerts.py` - Added 3 new endpoints
2. `app/schemas/alert.py` - Added remediation_workflow field
3. `frontend/src/api/client.ts` - Added 3 API functions
4. `frontend/src/types/api.ts` - Added Alert types
5. `frontend/src/components/ReportView.tsx` - Added Alerts button and modal

### New Files
1. `frontend/src/components/AlertsModal.tsx` - Complete alerts modal component

## Implementation Status
✅ Backend API endpoints working
✅ Frontend modal component created
✅ Integration with ReportView complete
✅ Placeholder remediation workflow implemented
✅ All types and interfaces defined
⏳ Actual workflow implementation (future)
