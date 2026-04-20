# 🌍 WorldMonitor AI

**Real-time Global Intelligence Dashboard powered by AI, Geospatial Analytics, and Interactive 3D Visualization**

WorldMonitor AI is an advanced situational awareness platform designed to monitor global events in real time. It combines live data feeds, AI-assisted analysis, geospatial layers, and an immersive 2D/3D globe interface to help users explore crises, military activity, infrastructure risks, health alerts, and world developments from a single dashboard.

---

## 🚀 Key Features

### 🌐 Interactive Global Visualization

* Switch between **2D Map** and **3D Globe**
* Smooth globe rotation and immersive world view
* Dynamic markers for live global events
* Layer-based intelligence overlays

### 🧠 AI Analyst Panel

* Integrated local AI models (Ollama supported)
* Ask intelligence questions from current event data
* Generate summaries, briefings, and trend analysis
* Custom prompt-driven insights

### 🛰️ Multi-Layer Monitoring System

#### Crisis Intelligence

* Iran Attacks
* Intel Hotspots
* Conflict Zones
* Protests
* Armed Conflict Events
* Displacement Flows
* Disease Outbreaks

#### Military Intelligence

* Military Bases
* Nuclear Sites
* Gamma Irradiators
* Radiation Watch
* Military Activity

#### Infrastructure Monitoring

* Undersea Cables
* Pipelines
* AI Data Centers
* Spaceports
* Trade Routes
* Chokepoints

#### Environment & Global Risk

* Weather / Climate Signals
* Natural Hazards
* Resource Pressure Zones
* Emerging Global Threats

### 📰 Live News Feed

* Real-time event cards
* Global headlines
* Region-specific developments
* Continuous intelligence updates

### 🕒 World Clock Integration

* Multi-region awareness
* Global operations readiness

---

## 🛠️ Technology Stack

* **Backend:** Python, FastAPI
* **Frontend:** HTML, CSS, JavaScript
* **Visualization:** Globe / Map Rendering
* **Database:** SQLite / Local Storage
* **AI Integration:** Ollama (Gemma, Qwen, Llama, etc.)
* **Geospatial Processing:** Custom Geo Layers
* **RAG Support:** Retrieval-Augmented Intelligence Modules

---

## 📂 Project Structure

```text
worldmonitor-ai/
├── app/               # Core backend modules
├── static/            # Frontend assets
├── data/              # Datasets / feeds
├── docs/              # Documentation
├── tests/             # Test modules
├── scripts/           # Utility scripts
├── README.md
├── requirements.txt
└── pyproject.toml
```

---

## ⚡ Installation

```bash
git clone https://github.com/YOUR_USERNAME/worldmonitor-ai.git
cd worldmonitor-ai
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open in browser:

```text
http://localhost:8000
```

---

## 🤖 AI Model Setup (Optional)

Install Ollama and pull a model:

```bash
ollama pull gemma:4b
```

or

```bash
ollama pull qwen2.5:7b
```

Then connect through the AI Analyst panel.

---

## 🎯 Use Cases

* Security & Intelligence Monitoring
* Geopolitical Research
* Crisis Response Dashboards
* OSINT Operations
* Defence Awareness Systems
* Newsroom Intelligence
* Academic Global Studies
* Strategic Risk Analysis

---

## 🔮 Future Roadmap

* Satellite Feed Integration
* Predictive Threat Analytics
* User Authentication
* Alert Notifications
* Historical Replay Mode
* Mobile Responsive Version
* Team Collaboration Tools
* Export Reports / PDF Briefings

---

## 🤝 Contributing

Contributions, ideas, and improvements are welcome.

```bash
fork → clone → improve → pull request
```

---

## 📜 License

Choose your preferred license:

* MIT License
* Apache 2.0
* Private Internal Use

---

## 👤 Author
Murali Kannan
AI Consultant | Builder of Practical AI Systems

---

## ⭐ Support

If you like this project, give it a **star** on GitHub and share it with others.
