# Tri9T AI - CT-200 Document Parser & QA Traceability System

This system parses CardioTrack CT-200 User Manuals into versioned hierarchical trees, generates QA test case ideas via LLM integrations, and provides real-time staleness and traceability flagging across document updates.

## Setup & Running Instructions

1. **Environment Setup:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install fastapi uvicorn pydantic sqlalchemy pdfplumber httpx pytest python-dotenv