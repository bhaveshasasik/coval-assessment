# Workflow Verification System

> A system that evaluates whether conversational AI agents correctly follow defined workflows during conversations.

**Built with:** FastAPI + LangGraph + Anthropic Claude (backend) | Next.js + TypeScript (frontend)

---

## 📋 Quick Overview

**Input:**
1. Workflow Graph (JSON) - defines expected conversation flow
2. Conversation Transcript (JSON) - timestamped user/assistant dialogue

**Output:**
- Overall compliance score (0-1)
- Node-level results (visited, skipped, partial, etc.)
- Multi-dimensional metrics (coverage, sequence, semantic, efficiency)
- Skip rate & response latency analytics
- Human-readable summary

**Use Cases:** AI agent QA, call center compliance, healthcare protocols, customer service monitoring

---

## 🚀 Quick Start

```bash
# 1. Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure (add your Anthropic API key)
cp .env.example .env
# Edit .env: ANTHROPIC_API_KEY=sk-ant-your-key-here

# 3. Run
uvicorn src.main:app --reload

# 4. Test
open http://localhost:8000/docs
```

**Full instructions:** [Setup Guide](docs/SETUP.md)

---

## 📚 Documentation

### Getting Started
- **[Setup & Installation](docs/SETUP.md)** - Installation, configuration, running the app
- **[Testing Guide](docs/TESTING.md)** - Test with example data, validation checks

### Core Concepts
- **[Key Features](docs/FEATURES.md)** - Semantic matching, multi-dimensional scoring, streaming
- **[Architecture](docs/ARCHITECTURE.md)** - System design, components, data flow
- **[Design Decisions](docs/DESIGN_DECISIONS.md)** - Why we made key choices

### API & Integration
- **[API Documentation](docs/API.md)** - Endpoint specs, request/response formats
- **[Use Cases](docs/USE_CASES.md)** - Real-world applications and code examples

### Development
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Adding features, testing, debugging
- **[Tech Stack](docs/TECH_STACK.md)** - Technologies used and why
- **[Roadmap](docs/ROADMAP.md)** - Current status and future plans

---

## 🎯 Core Features

✅ **Semantic Matching** - LLM-powered analysis with confidence scores  
✅ **Multi-Dimensional Scoring** - Coverage, sequence, semantic quality, efficiency  
✅ **Real-Time Streaming** - Server-Sent Events for live progress  
✅ **Persistent Storage** - SQLite for verification history  
✅ **Detailed Analytics** - Node-level results with timestamps & latency

**Learn more:** [Features Documentation](docs/FEATURES.md)

---

## 📊 Example Output

```json
{
  "overall_score": 0.82,
  "skip_rate": 0.0,
  "avg_response_latency": 2.35,
  "node_results": [
    {
      "node_id": "1",
      "status": "visited",
      "confidence": 0.95,
      "response_latency": 0.8
    }
  ],
  "metadata": {
    "correct_edges": 4,
    "total_transitions": 5,
    "invalid_transitions": ["3->5"]
  }
}
```

---

## 🏗️ Project Structure

```
coval_assessment/
├── src/                    # Backend (FastAPI)
│   ├── models/            # Pydantic schemas
│   ├── services/          # Business logic
│   ├── api/               # API routes
│   ├── db/                # SQLite database
│   └── main.py            # FastAPI app
├── frontend/               # Next.js (in progress)
├── examples/               # Sample data
├── docs/                   # Documentation
└── README.md               # This file
```

**Details:** [Architecture Documentation](docs/ARCHITECTURE.md)

---

## 🔍 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/verify` | POST | Batch verification |
| `/api/verify/stream` | POST | Streaming verification (SSE) |
| `/api/verify/{id}` | GET | Get past verification |
| `/api/verify/recent` | GET | List recent verifications |

**Interactive docs:** http://localhost:8000/docs  
**Full specs:** [API Documentation](docs/API.md)

---

## 🧪 Testing

```bash
# Start backend
uvicorn src.main:app --reload

# Option 1: Swagger UI (easiest)
open http://localhost:8000/docs

# Option 2: cURL
curl -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d @examples/test_request.json

# Option 3: Python
python scripts/test_verification.py
```

**Full guide:** [Testing Documentation](docs/TESTING.md)

---

## 💡 Use Cases

- **AI Agent QA** - Monitor production performance
- **Call Center Compliance** - Healthcare/financial protocols
- **Agent Training** - Identify knowledge gaps
- **A/B Testing** - Compare agent versions
- **Performance Monitoring** - Track response times

**Real examples:** [Use Cases Documentation](docs/USE_CASES.md)

---

## 🛠️ Tech Stack

**Backend:** FastAPI, LangGraph, Anthropic Claude, SQLite, Pydantic  
**Frontend:** Next.js 15, TypeScript, TailwindCSS, ReactFlow (planned)

**Details:** [Tech Stack Documentation](docs/TECH_STACK.md)

---

## 🚧 Current Status

### ✅ Complete (MVP)
- Backend API with semantic matching
- Multi-dimensional scoring
- SQLite persistence & SSE streaming
- Comprehensive documentation

### 🔨 In Progress
- Frontend UI (Next.js basic setup)
- Graph visualization
- Interactive transcript viewer

### 📋 Planned
- Multi-conversation analytics
- Unit & integration tests
- Workflow optimization recommendations

**Full roadmap:** [Roadmap Documentation](docs/ROADMAP.md)

---

## 🎓 For Developers

- **Adding a new metric?** See [Developer Guide](docs/DEVELOPER_GUIDE.md#1-adding-a-new-metric)
- **Custom LLM integration?** See [Developer Guide](docs/DEVELOPER_GUIDE.md#3-custom-llm-integration)
- **New API endpoint?** See [Developer Guide](docs/DEVELOPER_GUIDE.md#4-adding-api-endpoints)

---

## 📞 Quick Links

- **Documentation:** [docs/](docs/)
- **API Docs (Interactive):** http://localhost:8000/docs
- **Examples:** [examples/](examples/)
- **Setup Guide:** [docs/SETUP.md](docs/SETUP.md)

---

## 👤 About

**Created by:** Bhavesha  
**For:** Workflow Verification Take-Home Assignment  
**Version:** 1.0.0 (MVP)  
**Last Updated:** June 23, 2026

---

## 🙏 Acknowledgments

- **Anthropic** - Claude API for semantic matching
- **FastAPI** - Modern Python web framework
- **Next.js** - React framework
- **LangChain/LangGraph** - LLM orchestration
