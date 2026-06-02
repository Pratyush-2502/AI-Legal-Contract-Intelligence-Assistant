import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

function App() {
  // ---------------- UPLOAD STATE ----------------
  const [files, setFiles] = useState([]);
  const [uploadedList, setUploadedList] = useState([]);
  const [uploadStatus, setUploadStatus] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  // ---------------- Q&A STATE ----------------
  const [question, setQuestion] = useState("");
  const [answerData, setAnswerData] = useState(null);
  const [isAsking, setIsAsking] = useState(false);

  // ---------------- AGENT STATE ----------------
  const [agentData, setAgentData] = useState(null);
  const [activeAction, setActiveAction] = useState(""); 
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // ---------------- 1. UPLOAD HANDLER ----------------
  const handleUpload = async () => {
    if (!files.length) return;

    setIsUploading(true);
    setUploadStatus("Uploading and indexing... please wait.");

    try {
      const newUploads = [];
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append("file", files[i]);

        // Hits the rubric-compliant /documents endpoint
        const response = await fetch("http://localhost:8000/documents", {
          method: "POST",
          body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail);
        }
        newUploads.push(files[i].name);
      }

      setUploadedList([...uploadedList, ...newUploads]);
      setUploadStatus(`✅ Successfully uploaded ${files.length} file(s)!`);
      setFiles([]); 
    } catch (error) {
      setUploadStatus(`❌ Error: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // ---------------- 2. Q&A HANDLER ----------------
  const handleAskQuestion = async () => {
    if (!question) return;

    setIsAsking(true);
    setAnswerData(null);

    try {
      const response = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      const data = await response.json();

      if (response.ok) {
        setAnswerData(data);
      } else {
        setAnswerData({ error: data.detail });
      }
    } catch (error) {
      setAnswerData({ error: "Network error communicating with AI." });
    } finally {
      setIsAsking(false);
    }
  };

  // ---------------- 3. DYNAMIC AGENT HANDLER ----------------
  const handleAgentAction = async (endpoint, actionName) => {
    setIsAnalyzing(true);
    setAgentData(null);
    setActiveAction(actionName);

    try {
      const response = await fetch(`http://localhost:8000/agent/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      const data = await response.json();

      if (response.ok) {
        setAgentData({ type: actionName, payload: data });
      } else {
        setAgentData({ error: data.detail });
      }
    } catch (error) {
      setAgentData({ error: "Network error communicating with Agent." });
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>AI Legal Contract Intelligence Assistant</h1>
        <p>Upload documents, ask questions, compare clauses, and generate insights.</p>
      </header>

      <main className="dashboard">
        {/* ---------------- COMPONENT 1: UPLOAD ---------------- */}
        <section className="card">
          <h2>1. Document Upload</h2>
          <div className="upload-area">
            <input
              type="file"
              accept=".pdf,.txt,.md"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files))}
            />
            <button onClick={handleUpload} disabled={!files.length || isUploading}>
              {isUploading ? "Uploading..." : "Upload Documents"}
            </button>
          </div>
          {uploadStatus && <p className="status-message">{uploadStatus}</p>}
          
          {uploadedList.length > 0 && (
            <div className="document-list">
              <h4>Uploaded Documents:</h4>
              <ul>
                {uploadedList.map((doc, idx) => (
                  <li key={idx}>📄 {doc}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* ---------------- COMPONENT 2: Q&A ---------------- */}
        <section className="card">
          <h2>2. Document Q&A</h2>
          <div className="qa-area">
            <input
              type="text"
              className="text-input"
              placeholder="E.g., What are the termination conditions?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <button onClick={handleAskQuestion} disabled={!question || isAsking}>
              {isAsking ? "Thinking..." : "Ask Question"}
            </button>
          </div>

          {answerData && !answerData.error && (
            <div className="answer-box">
              <h3>Answer</h3>
              <div className="ai-markdown-content">
                <ReactMarkdown>{answerData.answer}</ReactMarkdown>
              </div>
              
              {answerData.sources && answerData.sources.length > 0 && (
                <>
                  <h4 style={{ marginTop: '20px' }}>Sources</h4>
                  <ul style={{ listStyleType: 'none', paddingLeft: 0 }}>
                    {answerData.sources.map((s, i) => {
                      const fileName = s.source ? s.source.split('/').pop().split('\\').pop() : "Unknown Document";
                      return (
                        <li key={i} style={{ marginBottom: "15px", padding: "10px", backgroundColor: "#f9f9f9", borderRadius: "5px" }}>
                          <strong>📄 {fileName}</strong>
                          <div style={{ marginTop: "8px", fontSize: "0.9em", color: "#555" }}>
                            "...{s.content.slice(0, 400)}..."
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </>
              )}
            </div>
          )}
          {answerData?.error && <p className="status-message error">❌ {answerData.error}</p>}
        </section>

       {/* ---------------- COMPONENT 3: AI AGENT ACTIONS ---------------- */}
        <section className="card">
          <h2>3. AI Agent Actions</h2>
          <div className="agent-buttons">
            <button 
              onClick={() => handleAgentAction("summary", "Summarise Contracts")} 
              disabled={isAnalyzing || uploadedList.length === 0}
            >
              📝 Summarise
            </button>
            <button 
              onClick={() => handleAgentAction("risk", "Identify Legal Risk")} 
              disabled={isAnalyzing || uploadedList.length === 0}
            >
              ⚠️ Identify Risk
            </button>
            <button 
              onClick={() => handleAgentAction("obligations", "Extract Obligations")} 
              disabled={isAnalyzing || uploadedList.length === 0}
            >
              📋 Extract Obligations
            </button>
            <button 
              onClick={() => handleAgentAction("compare", "Compare Clauses")} 
              disabled={isAnalyzing || uploadedList.length === 0}
            >
              ⚖️ Compare Clauses
            </button>
            <button 
              onClick={() => handleAgentAction("gaps", "Identify Research Gaps")} 
              disabled={isAnalyzing || uploadedList.length === 0}
              className="agent-btn"
            >
              🔍 Identify Gaps
            </button>
            <button 
              onClick={() => handleAgentAction("recommendations", "Suggest Directions")} 
              disabled={isAnalyzing || uploadedList.length === 0}
              className="agent-btn"
            >
              💡 Suggest Directions
            </button>
          </div>

          {isAnalyzing && <p className="status-message processing">Agent is analyzing documents...</p>}

          {/* DYNAMIC RENDERING FOR ALL AGENT ACTIONS */}
          {agentData && !agentData.error && (
            <div className="summary-box">
              <h3 className="report-title">{activeAction} Report</h3>
              <h4 className="report-subtitle">Findings Breakdown</h4>
              <div className="ai-markdown-content">
                <ReactMarkdown>{agentData.payload.per_contract_breakdown}</ReactMarkdown>
              </div>

              <div style={{ marginTop: "20px", padding: "15px", backgroundColor: "#f8f9fa", borderRadius: "8px", borderLeft: "4px solid #007bff" }}>
                <h4>🤖 Agent Reasoning</h4>
                <p><i>{agentData.payload.reasoning}</i></p>
              </div>
            </div>
          )}

          {agentData?.error && <p className="status-message error">❌ {agentData.error}</p>}
        </section>
      </main>
    </div>
  );
}

export default App;