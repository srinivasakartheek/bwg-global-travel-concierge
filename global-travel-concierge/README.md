# 🌍 Global Travel Concierge & Itinerary Planner

A conversational, agent-first travel assistant built on Google Cloud's Agent Development Kit (ADK) and Agent Platform. It plans personalized, day-by-day city itineraries, tracks travel preferences across conversations, searches curated attractions, checks live weather and currency exchange rates, generates destination postcards, and calculates trip expense breakdowns.

---

## 🧭 What This Agent Does

Based on the implemented codebase in `app/`, the agent provides the following real capabilities:

- **🧠 Cross-Session Memory (Vertex AI Memory Bank)**: Automatically records and recalls user travel styles (budget, moderate, luxury), preferred currencies, home locations, and spending limits across multiple sessions using `PreloadMemoryTool` and an automated memory callback.
- **🗄️ Curated Destination Catalog (Cloud Firestore)**: Manages and queries tourist attractions, landmarks, and activities stored in Google Cloud Firestore (`search_destinations`, `add_destination`).
- **🌦️ Real-Time Weather Forecasts**: Fetches live current temperatures, conditions, and 3-to-5-day weather forecasts for cities worldwide via the Open-Meteo API (`get_weather_forecast`).
- **💱 Live Currency Conversion**: Converts monetary amounts across global currencies with live exchange rates via open ExchangeRate-API (`convert_currency`).
- **💰 Trip Expense Calculation**: Calculates structured trip budget estimates (lodging, dining & transit, attraction entrance fees) tailored to traveler count, trip length, and travel tier (`calculate_trip_budget`).
- **🎨 AI Postcard & Landmark Generation (Gemini Image Generation)**: Generates visual travel postcards and landmark preview images on demand using `gemini-3.1-flash-lite-image` on Vertex AI (`generate_destination_image`).
- **🖼️ Asset Storage (Google Cloud Storage)**: Uploads generated destination imagery directly to a dedicated Cloud Storage bucket and generates public web URLs for the user interface.
- **🧪 Secure Code Execution (Agent Engine Sandbox)**: Runs custom math and complex calculations within an isolated Vertex AI Agent Engine sandbox environment (`AgentEngineSandboxCodeExecutor`).
- **🪟 Agent-First User Interface (A2UI v0.8)**: Generates structured, responsive A2UI cards, columns, rows, images, and text items displayed seamlessly in the chat interface.
- **🌐 Web Chat Interface**: Lightweight FastAPI proxy and HTML5/CSS3 chat application communicating with the agent via the Agent-to-Agent (A2A) protocol.

> [!NOTE]
> **Planned, Not Yet Implemented**:
> - Direct Google Maps / Places API live navigation routing (currently using catalog geocoordinates and sandbox distance approximations).
> - End-to-end flight booking and live hotel reservation checkouts.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Frontend (Chat UI)                   │
│         FastAPI Proxy + A2UI Mini-Renderer + A2A SDK        │
└──────────────────────────────┬──────────────────────────────┘
                               │ A2A Protocol
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Google ADK Agent (Agent Platform)              │
│                 Gemini 3.8 Flash Core Brain                 │
├──────────────────────────────┬──────────────────────────────┤
│ Cross-Session Memory         │ Vertex AI Memory Bank        │
│ Destination Catalog          │ Google Cloud Firestore       │
│ Image Generation             │ gemini-3.1-flash-lite-image  │
│ Image Storage                │ Google Cloud Storage         │
│ Code Execution Sandbox       │ Agent Engine Sandbox         │
│ Live Data Tools              │ Weather & Exchange Rate APIs │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 📁 Repository Structure

```
global-travel-concierge/
├── app/
│   ├── agent.py               # Main agent definition, tools, and callbacks
│   ├── a2ui_utils.py          # A2UI v0.8 callback and parser for ADK Web
│   ├── fast_api_app.py        # ADK backend server
│   └── app_utils/             # A2A and Reasoning Engine adapters
├── frontend/
│   ├── main.py                # FastAPI proxy connecting browser to agent via A2A
│   ├── Dockerfile             # Container configuration for Cloud Run
│   └── static/
│       └── index.html         # Themed chat dialogue UI with A2UI card renderer
├── agents-cli-manifest.yaml   # Agent deployment manifest
├── seed_firestore.py          # Script to populate initial attractions catalog
└── pyproject.toml             # Python dependencies and project settings
```

---

## 🚀 Running Locally

### Prerequisites

1. **Python 3.11+** and **[uv](https://docs.astral.sh/uv/)**
2. **Google Cloud SDK (`gcloud`)** authenticated with an active project:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

### 1. Seed the Firestore Catalog

Populate sample attractions for Tokyo, Paris, Rome, and San Francisco:

```bash
cd global-travel-concierge
uv run seed_firestore.py
```

### 2. Run the Agent in ADK Playground

Start the local ADK developer playground with your Memory Bank instance:

```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://projects/PROJECT_NUMBER/locations/REGION/reasoningEngines/RESOURCE_ID
```

Open your browser to test tools, memory persistence, and raw A2UI card generation.

### 3. Run the Web Frontend & A2A Proxy

In a separate terminal, start the dedicated chat frontend:

```bash
cd global-travel-concierge/frontend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export AGENT_ENGINE_RESOURCE_NAME="projects/PROJECT_NUMBER/locations/REGION/reasoningEngines/RESOURCE_ID"
export AGENT_DIRECTORY="app"
python main.py
```

---

## 🛠️ Built With

- **[Google ADK](https://google.github.io/adk-docs/)**: Agent Development Kit
- **[Google Cloud Vertex AI](https://cloud.google.com/vertex-ai)**: Gemini models, Agent Engine, and Memory Bank
- **[Google Cloud Firestore](https://cloud.google.com/firestore)**: Serverless NoSQL document database
- **[Google Cloud Storage](https://cloud.google.com/storage)**: Scalable object storage for generated postcards
- **[A2A Protocol & SDK](https://github.com/google/a2a-sdk)**: Agent-to-Agent communication
