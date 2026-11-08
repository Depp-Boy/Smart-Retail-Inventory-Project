# Smart Retail Inventory Management and Demand Forecasting System

A unified retail management platform featuring a React + Vite + Tailwind CSS frontend and a Python FastAPI backend powered by Supabase PostgreSQL.

## Directory Structure

```
project-root/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── navigation/
│   │   │   └── ui/
│   │   ├── context/
│   │   ├── data/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   │   ├── auth/
│   │   │   ├── common/
│   │   │   ├── public/
│   │   │   ├── shop/
│   │   │   ├── warehouse/
│   │   │   └── worker/
│   │   ├── routes/
│   │   ├── services/
│   │   └── utils/
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
├── README.md
└── .gitignore
```

## Quick Start

### Backend (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate virtual environment:
   ```bash
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```
3. Run tests:
   ```bash
   pytest -v
   ```
4. Start development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend (React + Vite)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies (if not already installed):
   ```bash
   npm install
   ```
3. Run production build:
   ```bash
   npm run build
   ```
4. Start development server:
   ```bash
   npm run dev
   ```