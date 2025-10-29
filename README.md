# 🤖 AI Research Assistant

> 🧠 A LangGraph powered AI workspace that answers research questions with concise summaries, implementation plans, and document-backed insights.

---

## 🌟 Overview

**AI Research Assistant** is an intelligent web app built with **Flask**, **LangGraph**, and **LLMs (via OpenRouter or local models)**.

It allows users to:

- 👤 Create a **personal workspace** by entering their name  
- 💬 Ask any research-style or technical question  
- 📚 Get **concise AI-generated summaries** and **short step-by-step implementation plans**  
- 🔁 Toggle between **LLM-only** or **RAG (Retrieval-Augmented Generation)** modes  
- 💾 View and export **chat history** as a formatted **PDF report**

The design follows a **dark, glassy, neon-glow aesthetic** for a modern research dashboard experience.

---

## 🧩 Features

| Feature | Description |
|----------|--------------|
| 🧠 **LangGraph Integration** | Manages the full RAG pipeline (retriever → summarizer → planner). |
| 🔍 **RAG Workflow** | Retrieves info from local docs, Wikipedia, or web (DuckDuckGo). |
| 💬 **LLM Chat Mode** | Lets users talk to the model without retrieval. |
| 📄 **PDF Export** | Exports user’s history in a well-formatted PDF with bold, readable text. |
| 🌙 **Modern Dark UI** | Sleek UI with glowing buttons, hover effects, and smooth gradients. |
| 👤 **Private Workspaces** | Each user’s history is isolated by name (`state.json`). |
| 📜 **Session History** | Shows all previous queries, summaries, and plans. |
| ⚡ **Local + Web Search** | Uses local text files first, then Wikipedia or DuckDuckGo if needed. |

---

## ⚙️ System Architecture

```text
 ┌──────────────┐
 │   User Query │
 └──────┬───────┘
        ↓
 ┌───────────────────────┐
 │  Retriever Node       │
 │  (Local / Wiki / Web) │
 └────────┬──────────────┘
          ↓
 ┌────────────────────────────┐
 │  Summarizer Node           │
 │  → Generates concise answer│
 │    using LLM (RAG)         │
 └────────┬───────────────────┘
          ↓
 ┌────────────────────────────┐
 │  Planner Node              │
 │  → Produces short 3-step   │
 │    implementation plan     │
 └────────┬───────────────────┘
          ↓
 ┌────────────────────────────┐
 │  Flask Backend             │
 │  → Returns summary, plan & │
 │    docs to frontend        │
 └────────┬───────────────────┘
          ↓
 ┌────────────────────────────┐
 │  Frontend (UI)             │
 │  → Displays results & saves│
 │    session history         │
 └────────────────────────────┘
```

### 🧠 LangGraph Integration
LangGraph is used to **structure the reasoning workflow**:
- Each step (retrieval, summarization, planning) is represented as a node.
- Data flows between nodes automatically.
- This modular design makes it easy to add new nodes (e.g., “Web Search”, “Critic”, etc.) later.

---

## 🧱 File Structure

AI-Research-Assistant/
├── app.py # Flask app: routes, UI, PDF export
├── graph.py # LangGraph-like pipeline (retriever, summarizer, planner)
├── llm.py # LLM wrapper for OpenRouter or local models
├── state.json # Stores user sessions and history
├── knowledge/ # Local text documents used for retrieval
│ ├── ai-research.txt
│ └── summary-tips.txt
├── README.md # Project documentation
└── requirements.txt # Dependencies list

---

## 🪄 Tech Stack

| Layer | Technology |
|--------|-------------|
| **Frontend** | HTML, CSS (dark gradient + neon UI), Vanilla JS |
| **Backend** | Flask (Python) |
| **AI Engine** | LangGraph pipeline (custom nodes) |
| **Language Model** | LLaMA / OpenRouter API |
| **Document Sources** | Local `.txt` files + Wikipedia + DuckDuckGo API |
| **Export Engine** | ReportLab (PDF generation) |

---

## 💡 Modes Explained

### 🔷 LLM Mode (Chat-only)
- The app directly queries the model.
- No retrieval, purely generative answers.
- Best for open-ended or conversational queries.

### 🟣 RAG Mode (Retrieval-Augmented Generation)
- The app retrieves related documents from:
  - Local `knowledge/` files
  - Wikipedia
  - DuckDuckGo Instant Answer API
- The retrieved snippets are added to the prompt before calling the model.
- Results are grounded and can show document references.

---

## 🚀 Setup Guide

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/ai-research-assistant.git
cd ai-research-assistant

2️⃣ Create a Virtual Environment
python -m venv venv
source venv/bin/activate   # on Linux/Mac
venv\Scripts\activate      # on Windows

3️⃣ Install Dependencies
pip install -r requirements.txt

Example requirements.txt:
nginx
Copy code
flask
requests
wikipedia
reportlab

4️⃣ Set Your OpenRouter API Key (or local LLaMA model)
In PowerShell or terminal:

$env:OPENROUTER_API_KEY="your_api_key_here"

5️⃣ Run the App
python app.py

6️⃣ Open in Browser

http://127.0.0.1:5000/

