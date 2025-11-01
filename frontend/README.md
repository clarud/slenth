# Slenth - Compliance Intelligence Platform

A modern React frontend for compliance monitoring, transaction analysis, and rule management.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 🎨 Features

- **Dashboard**: Real-time transaction monitoring with auto-polling, compliance reports, and document upload
- **Rules Management**: Searchable, filterable rule cards with detailed views and bulk import
- **Add Internal Rules**: Paste JSON directly into a modal to bulk-upload internal compliance rules
- **Responsive Design**: Mobile-first, accessible UI built with Tailwind CSS
- **URL State Sync**: All filters and pagination persist in the URL for easy sharing

## 🔧 Configuration

### Brand & API Endpoints

All configuration is centralized in `src/config.ts`:

```typescript
export const BRAND = {
  name: "Slenth",
  tagline: "Compliance Intelligence Platform",
  logoUrl: "https://...", // Update with your logo
};

export const API = {
  BASE_URL: "http://localhost:8000", // Change for production
  // ... all endpoints
};
```

### Color Theme

Customize colors in `src/index.css`:

```css
:root {
  --charcoal: 199 42% 20%;      /* Primary dark text */
  --tiffany-blue: 156 42% 68%;  /* Primary accent */
  --white: 180 100% 99%;        /* Background */
  --cadet-gray: 195 13% 57%;    /* Muted/borders */
}
```

## 📋 JSON Format for "Add Internal Rules"

The modal accepts two formats:

### Option A: Wrapper Object (recommended)

```json
{
  "rules": [
    {
      "title": "Large Cash Transaction Reporting",
      "description": "Report cash transactions over threshold",
      "text": "All cash transactions exceeding CHF 100,000 must be reported within 24 hours...",
      "section": "AML_CASH_REPORTING",
      "obligation_type": "mandatory",
      "conditions": ["amount > 100000", "currency == CHF"],
      "expected_evidence": ["Transaction receipt", "Customer ID"],
      "penalty_level": "high",
      "effective_date": "2025-01-01",
      "version": "v1.0",
      "source": "Internal Policy Manual"
    }
  ]
}
```

### Option B: Bare Array (auto-wrapped)

```json
[
  {
    "title": "Rule Title",
    "text": "Full rule text...",
    "section": "SECTION_CODE"
  }
]
```

The UI automatically normalizes bare arrays into the wrapper format before submission.

## 🛠️ Tech Stack

- **React 18** + **TypeScript** + **Vite**
- **Tailwind CSS** for styling
- **Framer Motion** for animations
- **Axios** for API calls
- **React Router** for navigation
- **React Hot Toast** for notifications
- **React Dropzone** for file uploads

## 📁 Project Structure

```
src/
├── api/
│   └── client.ts           # API functions
├── components/
│   ├── layout/
│   │   └── Shell.tsx       # Navigation & layout
│   ├── rules/
│   │   ├── RulesFilters.tsx
│   │   ├── RuleCard.tsx
│   │   ├── RuleDetailModal.tsx
│   │   ├── InternalRulesModal.tsx  # Bulk JSON upload
│   │   └── Pagination.tsx
│   ├── TransactionsPanel.tsx
│   ├── ReportView.tsx
│   └── ui/                 # Reusable UI components
├── hooks/
│   ├── usePolling.ts
│   └── useDebouncedValue.ts
├── pages/
│   ├── Home.tsx            # Dashboard
│   └── Rules.tsx           # Rules management
├── types/
│   └── api.ts              # TypeScript interfaces
├── config.ts               # Centralized config
└── index.css               # Design system
```

## 🎯 Key Features Explained

### Dashboard

- **Transactions Panel**: Auto-polls `/transactions` every 10s (toggle on/off)
- **Report View**: Switch between transaction details and document upload
- **Document Upload**: Drag & drop PDF/JPEG/PNG files

### Rules Tab

- **Search**: Debounced search (300ms) across rule titles and text
- **Filters**: Rule type, regulator, jurisdiction, section, active status
- **Page Size**: 25, 50, or 100 results per page
- **Add Internal Rules Button**: Opens modal with big textarea for JSON paste
  - Validates JSON structure in real-time
  - Prefers POST to `/internal_rules` (JSON body)
  - Falls back to POST to `/internal_rules/upload` (multipart file) if needed
  - Shows upload summary (created/updated/skipped counts)

### API Behavior

The "Add Internal Rules" feature tries two approaches:

1. **Preferred**: `POST /internal_rules` with JSON body
2. **Fallback**: `POST /internal_rules/upload` with multipart form-data (generates a virtual `internal_rules.json` file)

## 🌐 Deployment

Update `API.BASE_URL` in `src/config.ts` to point to your production backend.

```typescript
export const API = {
  BASE_URL: "https://api.yourdomain.com",
  // ...
};
```

## 📄 License

MIT

---

Built with ❤️ for modern compliance teams.
