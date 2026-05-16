# AI Data Analyst Agent — Architecture (v1)

## Project Goal

Build an AI-assisted data analysis system that allows users to:

* Upload CSV datasets
* Explore datasets interactively
* Ask natural language analysis questions
* Generate insights and visualizations
* Perform safe dataframe operations through predefined tools

The system should combine:

* Modern AI-assisted engineering workflow
* Structured backend orchestration
* Safe tool-calling architecture
* Interactive frontend visualizations

This project is both:

1. A portfolio-worthy AI analytics application
2. A learning project for AI-native software engineering workflows

---

# Core Philosophy

## The LLM does NOT directly manipulate dataframes

The LLM is responsible for:

* Understanding user intent
* Selecting tools
* Generating tool parameters
* Choosing chart types
* Generating insights and explanations

The backend tools are responsible for:

* Actual dataframe operations
* Safe execution
* Validation
* Aggregations
* Filtering
* Chart data preparation

This creates a safer and more maintainable architecture.

---

# Agentic Level

## Chosen Approach: Level 2.5 Agent Architecture

The system will support:

* Structured tool calling
* Limited multi-step reasoning
* Safe orchestration
* Deterministic backend execution

The system will NOT support:

* Fully autonomous agents
* Unrestricted code execution
* Self-modifying workflows
* Open-ended recursive planning

The backend remains the orchestrator and safety layer.

---

# High-Level Architecture

```text
Frontend (Streamlit)
        ↓
FastAPI Backend
        ↓
Agent Layer
        ↓
Tool Layer
        ↓
DataFrame Operations
        ↓
Gemini API
```

---

# Frontend Architecture

## Technology

* Streamlit
* Plotly

## Responsibilities

The frontend is responsible for:

* File upload UI
* Natural language prompt interface
* Rendering tables
* Rendering charts
* Session state management
* User interaction and filtering
* Displaying insights

## Visualization Philosophy

Charts should be rendered on the frontend.

The backend should NOT generate matplotlib image files.

Instead:

* Backend returns structured chart data/specifications
* Frontend renders interactive Plotly charts

This improves:

* Performance
* Interactivity
* Scalability
* Separation of concerns

---

# Backend Architecture

## Technology

* FastAPI
* pandas

## Responsibilities

The backend is responsible for:

* API endpoints
* Session/dataframe management
* Orchestration
* Tool execution
* Validation
* Structured responses
* Gemini API communication

The backend acts as the control layer between:

* User requests
* LLM reasoning
* Tool execution

---

# Agent Layer

## Technology

* Gemini API
* Structured prompting

## Responsibilities

The agent layer is responsible for:

* Understanding natural language queries
* Mapping user intent to tools
* Generating tool parameters
* Selecting chart types
* Generating insights
* Performing lightweight multi-step reasoning

## Example Flow

User Prompt:

```text
Plot revenue by month and show top-performing regions.
```

LLM Output:

```json
{
  "steps": [
    {
      "tool": "groupby",
      "params": {
        "group_col": "month",
        "metric": "revenue",
        "aggregation": "sum"
      }
    },
    {
      "tool": "top_n",
      "params": {
        "column": "region",
        "metric": "revenue",
        "n": 5
      }
    }
  ],
  "chart_type": "line"
}
```

Backend tools execute these operations safely.

---

# Tool Layer

## Initial Tool Set (v1)

### Dataset Inspection

* schema_inspector
* missing_value_analyzer
* summary_statistics
* candidate_target_detector

### Data Operations

* groupby
* aggregation
* filtering
* sorting
* correlation
* joins (future extension)

### Visualization Support

* chart_spec_generator
* chart_data_preparer

---

# Visualization Architecture

## Backend

Returns:

* Processed data
* Chart metadata
* Recommended chart type

## Frontend

Uses Plotly to render:

* Line charts
* Bar charts
* Scatter plots
* Histograms
* Heatmaps

The frontend owns rendering.

The backend owns data preparation.

---

# Initial MVP Scope

## V1 Features

### CSV Upload

* Upload a dataset
* Store dataframe in session

### Automatic Dataset Analysis

* Column names
* Data types
* Missing values
* Row/column counts
* Basic statistics
* Candidate target suggestions

### Natural Language Queries

Examples:

* "Group revenue by month"
* "Show top customers"
* "Plot sales trend"
* "Find correlations"

### Visualization Requests

Examples:

* "Create a scatter plot of sales vs profit"
* "Plot monthly revenue"

### Insight Generation

Examples:

* Trend summaries
* Anomaly observations
* Correlation insights

---

# Development Workflow

## Core Development Stack

### Environment

* WSL
* Python virtual environment

### Terminal Workflow

* tmux
* Helix
* OpenCode

### AI Coding Workflow

Human Role:

* Architect
* Orchestrator
* Reviewer
* Decision-maker

OpenCode Role:

* Assistant
* Implementation collaborator
* Repo-aware coding helper

Gemini Role:

* Reasoning engine
* Tool-calling intelligence

---

# Repo Structure (Planned)

```text
ai-data-analyst-agent/
│
├── frontend/
│   └── streamlit_app.py
│
├── backend/
│   ├── agent/
│   ├── tools/
│   ├── services/
│   ├── models/
│   └── api/
│
├── docs/
│   ├── architecture.md
│   └── workflow.md
│
├── tests/
├── data/
│
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

---

# Security Philosophy

API keys are NEVER committed to GitHub.

Secrets are stored using:

* .env locally
* Deployment environment variables in production

The repository must remain safe for public GitHub hosting.

---

# Long-Term Possibilities (Post-v1)

Potential future features:

* Multi-table analysis
* Smarter schema linking
* Conversation memory
* Cached analysis
* Exportable reports
* More advanced chart recommendations
* Multi-model routing
* Docker deployment

These are intentionally OUT OF SCOPE for v1.

---

# Current Priority

Focus on:

* Clean architecture
* Reliable tool execution
* Strong frontend/backend separation
* Practical AI orchestration
* Learning modern AI-native engineering workflow

Avoid:

* Overengineering
* Excessive abstractions
* Autonomous agent complexity
* Framework bloat
