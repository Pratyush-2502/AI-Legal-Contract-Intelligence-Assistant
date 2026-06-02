import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

load_dotenv()

# ---------------- LLM ----------------
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is not set in .env")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=api_key
)

# ---------------- APP ----------------
app = FastAPI(title="AI Legal Contract Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DB ----------------
embeddings = FastEmbedEmbeddings()
vector_store = Chroma(
    persist_directory="./chroma_data",
    embedding_function=embeddings
)

# ---------------- MODELS ----------------
class QueryRequest(BaseModel):
    question: str

class ContractSummaryOutput(BaseModel):
    risk_level: str = Field(description="Low, Medium or High")
    summary: str = Field(description="Executive summary of the contract")
    reasoning: str = Field(description="Why the risk level was assigned")
    key_obligations: List[str]

class GapsOutput(BaseModel):
    identified_gaps: List[str] = Field(description="List of missing clauses, undefined terms, or research gaps")
    vulnerability_level: str = Field(description="Low, Medium, or High")
    explanation: str = Field(description="Detailed reasoning for the identified gaps")

class RecommendationsOutput(BaseModel):
    strategic_recommendations: List[str] = Field(description="Actionable advice, negotiation points, or future directions")
    priority_action: str = Field(description="The single most important next step to take")

class CompareOutput(BaseModel):
    key_similarities: List[str] = Field(description="Shared themes or identical clauses across the text")
    key_differences: List[str] = Field(description="Conflicting points, distinct variations, or specific changes")
    summary_conclusion: str = Field(description="Overall verdict of the comparison")

class AgentOutput(BaseModel):
    per_contract_breakdown: str = Field(description="Markdown formatted text breaking down the findings for EACH contract individually (e.g., **Contract 1**: ...)")
    reasoning: str = Field(description="Basic reasoning explaining how the AI arrived at these structured findings")

# ---------------- SETUP ----------------
os.makedirs("temp_uploads", exist_ok=True)

# ---------------- HEALTH ----------------
@app.get("/health")
async def health_check():
    """Health check endpoint required by Tachyon Systems evaluation script."""
    return {
        "status": "healthy", 
        "service": "AI Legal Contract Intelligence Assistant", 
        "version": "1.0.0"
    }

# ---------------- FILE UPLOAD ----------------
@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):

    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

    def is_allowed(filename: str):
        return any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)

    if not is_allowed(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, TXT, and Markdown files are supported."
        )

    file_path = f"temp_uploads/{file.filename}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # ---------------- LOAD FILE ----------------
        if file.filename.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")

        documents = loader.load()

        # ---------------- CHUNKING ----------------
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        chunks = text_splitter.split_documents(documents)

        # ---------------- STORE ----------------
        vector_store.add_documents(chunks)

        return {
            "filename": file.filename,
            "status": "success",
            "chunks_created": len(chunks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# ---------------- Q&A ----------------
@app.post("/query")
async def query_documents(request: QueryRequest):
    """
    Endpoint to search the vector database and generate an AI answer.
    """
    try:
        # 1. Fetch extra chunks (k=5) so we have backups if we find duplicates
        results = vector_store.similarity_search(request.question, k=5)
        
        context_text = ""
        source_references = []
        
        # THE FIX: A Python Set to track unique text
        seen_texts = set()
        
        for doc in results:
            # Only process this chunk if we haven't seen its exact text already
            if doc.page_content not in seen_texts:
                seen_texts.add(doc.page_content)
                context_text += f"\n\n---\n\n{doc.page_content}"
                source_references.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "Unknown")
                })
            
            # Stop once we have exactly 3 UNIQUE chunks
            if len(source_references) == 3:
                break

        # 3. Prompt Engineering
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an intelligent AI Assistant. Answer the user's question directly and accurately using ONLY the provided context.\n\n"
                       "CRITICAL INSTRUCTION: Always format your response beautifully using Markdown. Use bolding for emphasis, and use numbered lists or bullet points with clear line breaks between each point. Do NOT use bold formatting (**text**) for inline emphasis inside your sentences. Only use bold formatting for structural labels or bullet points (e.g., **Notice Period:**).\n\n\n"
                       "Context:\n{context}"),
            ("user", "{question}")
        ])

        # 4. Generate the Answer
        chain = prompt_template | llm
        ai_response = chain.invoke({
            "context": context_text,
            "question": request.question
        })
            
        # 5. Return the cleaned payload
        return {
            "question": request.question,
            "answer": ai_response.content,
            "sources": source_references
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- AGENT SUMMARY ----------------
@app.post("/agent/summary")
async def agent_summarize(request: dict):
    try:
        results = vector_store.similarity_search("This agreement is made between introduction background purpose of contract parties", k=20)
        context_text = "\n\n".join([doc.page_content for doc in results])
        structured_llm = llm.with_structured_output(AgentOutput)
        
        prompt = f"""You are an expert Legal AI Agent.
        Summarise the uploaded contracts individually.
        
        CRITICAL: You must return valid structured data. 
        Inside your 'per_contract_breakdown' string, you MUST use Markdown. You MUST use a bulleted list to separate the contracts so it does not render as a wall of text. 
        Format example: 
        * **Contract 1 (Title)**: [Summary details...]
        * **Contract 2 (Title)**: [Summary details...]
        
        Context:\n{context_text}"""
        
        return structured_llm.invoke(prompt)
    except Exception as e:
        print(f"FAILED PAYLOAD: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/risk")
async def agent_risk(request: dict):
    try:
        results = vector_store.similarity_search("exclusions limitations missing undefined terms loopholes risks liabilities", k=20)
        context_text = "\n\n".join([doc.page_content for doc in results])
        structured_llm = llm.with_structured_output(AgentOutput)
        
        prompt = f"""You are an expert Legal AI Agent.
        Identify legal risks in the uploaded contracts individually.
        
        CRITICAL: You must return valid structured data. 
        Inside your 'per_contract_breakdown' string, you MUST use Markdown. You MUST use a bulleted list to separate the contracts so it does not render as a wall of text. 
        Format example:
        * **Contract 1 (Title)**: [Risk details...]
        * **Contract 2 (Title)**: [Risk details...]
        * **Contract 3 (Title)**: [Risk details...]
        
        Context:\n{context_text}"""
        
        return structured_llm.invoke(prompt)
    except Exception as e:
        print(f"FAILED PAYLOAD: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/obligations")
async def agent_obligations(request: dict):
    try:
        results = vector_store.similarity_search("service provider obligations duties rules payment timeline requirements", k=20)
        context_text = "\n\n".join([doc.page_content for doc in results])
        structured_llm = llm.with_structured_output(AgentOutput)
        
        prompt = f"""You are an expert Legal AI Agent.
        Extract obligations from the uploaded contracts individually.
        
        CRITICAL: You must return valid structured data. 
        Inside your 'per_contract_breakdown' string, you MUST use Markdown. You MUST use a bulleted list to separate the contracts so it does not render as a wall of text. 
        Format example:
        * **Contract 1 (Title)**: [Obligation details...]
        * **Contract 2 (Title)**: [Obligation details...]
        
        Context:\n{context_text}"""
        
        return structured_llm.invoke(prompt)
    except Exception as e:
        print(f"FAILED PAYLOAD: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/compare")
async def agent_compare(request: dict):
    try:
        results = vector_store.similarity_search("agreement terms conditions background summary introduction scope timeline payment", k=25)
        context_text = "\n\n".join([doc.page_content for doc in results])
        structured_llm = llm.with_structured_output(AgentOutput)
        
        prompt = f"""You are an expert Legal AI Agent.
        Compare the clauses (such as Termination, Liability, Payment, etc.) across the uploaded contracts individually.
        
        CRITICAL: You must return valid structured data. 
        Inside your 'per_contract_breakdown' string, you MUST use Markdown. You MUST use a bulleted list to separate the contracts so it does not render as a wall of text. 
        Format example:
        * **Contract 1 (Title)**: [How its clauses compare to the others...]
        * **Contract 2 (Title)**: [How its clauses compare to the others...]
        
        Context:\n{context_text}"""
        
        return structured_llm.invoke(prompt)
    except Exception as e:
        print(f"FAILED PAYLOAD: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/agent/gaps")
async def agent_gaps(request: dict):
    try:
        results = vector_store.similarity_search("omissions missing clauses undefined terms liabilities assumptions", k=20)
        context_text = "\n\n".join([doc.page_content for doc in results])
        structured_llm = llm.with_structured_output(AgentOutput)
        
        prompt = f"""You are an expert AI Agent.
        Identify research gaps or missing critical clauses in the uploaded documents.
        
        CRITICAL: You must return valid structured data. 
        Inside your 'per_contract_breakdown' string, you MUST use Markdown. You MUST use a bulleted list to separate the documents.
        Format example:
        * **Document 1 (Title)**: [Identified gaps...]
        * **Document 2 (Title)**: [Identified gaps...]
        
        Context:\n{context_text}"""
        
        return structured_llm.invoke(prompt)
    except Exception as e:
        print(f"FAILED PAYLOAD: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/recommendations")
async def agent_recommendations(request: dict):
    try:
        results = vector_store.similarity_search("future actions recommendations next steps improvements", k=20)
        context_text = "\n\n".join([doc.page_content for doc in results])
        structured_llm = llm.with_structured_output(AgentOutput)
        
        prompt = f"""You are an expert AI Agent.
        Suggest future research directions or strategic recommendations based on the uploaded documents.
        
        CRITICAL: You must return valid structured data. 
        Inside your 'per_contract_breakdown' string, you MUST use Markdown. You MUST use a bulleted list to separate the documents.
        Format example:
        * **Document 1 (Title)**: [Recommendations...]
        * **Document 2 (Title)**: [Recommendations...]
        
        Context:\n{context_text}"""
        
        return structured_llm.invoke(prompt)
    except Exception as e:
        print(f"FAILED PAYLOAD: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))