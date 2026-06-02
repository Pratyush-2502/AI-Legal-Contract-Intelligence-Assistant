# AI Legal Contract Intelligence Assistant

**Tachyon Systems - Founding AI Engineer (Architect Track) Technical Challenge** **Assignment ID:** TS-NITUK-2026-003  
**Candidate:** Pratyush Raj | NIT Uttarakhand, 2026 Batch  

## 📌 Overview
This repository contains a full-stack Retrieval-Augmented Generation (RAG) application designed to analyze, summarize, and extract insights from legal contracts. It utilizes a decoupled architecture featuring a React frontend, an asynchronous FastAPI backend, and a strictly orchestrated LangChain/Groq AI agent layer.

## ✅ Deliverables Checklist
- [x] **GitHub Repository:** Provided
- [x] **Live Frontend URL:** https://ai-legal-contract-intelligence-assi.vercel.app
- [x] **Backend API URL:** https://ai-legal-contract-intelligence-assistant.onrender.com
- [x] **Architecture Diagram:** Located in `/docs/System_Architecture_Diagram.png`
- [x] **Architecture Decision Records:** Located in `/docs/Architecture_Decision_Records.pdf`
- [x] **Scalability Design Note:** Located in `/docs/Scalability_Design_Note.pdf`
- [x] **API Documentation:** https://ai-legal-contract-intelligence-assistant.onrender.com/docs
- [ ] **Demo Video:** `[Insert Loom/YouTube Link Here]`

## 🚀 Core Features
* **Multi-Format Ingestion:** Supports automated parsing and chunking of PDF, TXT, and Markdown files.
* **Local Privacy by Default:** Utilizes an embedded ChromaDB vector store, ensuring sensitive contract data is never leaked to external cloud databases.
* **Deterministic AI Agents:** Leverages Pydantic structured outputs to force the LLM into strict JSON schemas, preventing UI crashes and enforcing markdown formatting.
* **Advanced RAG Routing:** Dedicated AI endpoints for summarization, risk identification, obligation extraction, clause comparison, and academic gap analysis.

---

## 💻 Local Installation & Setup

### 1. Clone the Repository
```bash
### 1. Clone the Repository
git clone https://github.com/Pratyush-2502/AI-Legal-Contract-Intelligence-Assistant.git
cd AI-Legal-Contract-Intelligence-Assistant
```

### 2. Backend Setup (FastAPI)
Navigate to the backend directory, create a virtual environment, and install dependencies.
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory and add your Groq API Key:
```env
GROQ_API_KEY=your_api_key_here
```

Start the API Server:
```bash
uvicorn main:app --reload
```
The backend will run at `http://localhost:8000`.  
API documentation (Swagger UI) is automatically generated at `http://localhost:8000/docs`.

### 3. Frontend Setup (React)
Navigate to the frontend directory and install the node modules.
```bash
cd ../frontend
npm install
npm run dev
```
The frontend UI will run at `http://localhost:5173`.

---

## 🏗 Architecture & System Design
Please refer to the `docs/` folder for comprehensive documentation, including:
1. **System Architecture Diagram:** Visual data flow and infrastructure mapping.
2. **Architecture Decision Records (ADRs):** Detailed explanations of framework selection, vector database choice, and agent routing logic.
3. **Scalability Design Note:** An architectural roadmap detailing the transition from 100 to 100,000 contracts using event-driven ingestion, semantic caching, and Kubernetes microservices.