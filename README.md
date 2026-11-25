# SourceWise AI
**Agentic Supplier Intelligence & Procurement Platform**

A clean, lightweight procurement decision-support application built module by module.

## Module 1 — Project foundation
- FastAPI application entry point
- Centralized environment configuration
- Health-check endpoint
- Dependency list and environment template

## Setup (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/docs`.

Add your API keys to `.env` when we implement supplier research. Never commit `.env`.

## Roadmap
1. Project foundation
2. Supplier research
3. Supplier verification and evidence
4. Supplier scoring and risk assessment
5. RFQ and quotation comparison
6. Human approval and decision history
7. Persistence, security, testing and deployment
