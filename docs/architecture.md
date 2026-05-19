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

## Bounded Autonomy Philosophy

The LLM operates within a defined analysis loop — it does not wander freely.

Each iteration works as follows:

1. LLM receives the user query plus the current analysis state
2. LLM evaluates prior results and decides the next tool call, or declares analysis complete
3. Backend validates parameters, executes the chosen tool safely
4. Tool returns a structured response with data and metadata
5. LLM evaluates the result and decides the next action
6. Repeat or finalize

"Bounded" means:

* Finite maximum iterations per request (enforced by backend)
* Predefined tool set — the LLM cannot invent new operations
* Structured response contracts — every tool returns a predictable envelope
* Human oversight — the user remains in control via the frontend

The backend enforces iteration limits, tool availability, response validation, and error boundaries.

---

# Agentic Level

## Chosen Approach: Bounded Autonomy — Agent Architecture

The system will support:

* Structured tool calling
* Bounded iterative multi-step orchestration
* Iterative analysis loops with conditional branching
* Retry and alternate analysis path selection
* Autonomous insight generation from tool results
* Structured tool response contracts
* Safe orchestration with backend-enforced limits

The system will NOT support:

* Fully autonomous open-ended agents
* Unrestricted code execution
* Self-modifying workflows
* Open-ended recursive planning
* Tools that directly manipulate dataframes without predefined contracts
* The LLM writing or executing arbitrary code

The backend remains the orchestrator, safety layer, and loop enforcer.

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
LLM API
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
* LLM API communication

The backend acts as the control layer between:

* User requests
* LLM reasoning
* Tool execution

---

# Agent Layer

## Technology

* LLM API
* Structured prompting

## Responsibilities

The agent layer is responsible for:

* Understanding natural language queries
* Mapping user intent to tools
* Generating tool parameters
* Selecting chart types
* Generating insights
* Performing lightweight multi-step reasoning

## Example Flow (Iterative Multi-Turn)

User Prompt:

```text
Plot revenue by month and show top-performing regions.
```

### Turn 1 — Schema Inspection

LLM decides to inspect the dataset first.

```json
{
  "analysis": "I need to understand the dataset columns before operating.",
  "next_tool": "schema_inspector",
  "params": {}
}
```

Backend executes `schema_inspector`, returns:

```json
{
  "success": true,
  "data": {
    "columns": ["month", "revenue", "region", "profit", "sales"],
    "dtypes": {"month": "object", "revenue": "float64", "region": "object", "profit": "float64", "sales": "int64"},
    "row_count": 500
  },
  "metadata": {
    "tool": "schema_inspector",
    "execution_time_ms": 3
  },
  "error": null
}
```

### Turn 2 — Group By

LLM evaluates the schema and decides to group revenue by month.

```json
{
  "analysis": "Schema confirmed. 'month' and 'revenue' columns exist. Grouping revenue by month to identify trends.",
  "next_tool": "groupby",
  "params": {
    "group_col": "month",
    "metric": "revenue",
    "aggregation": "sum"
  }
}
```

Backend executes `groupby`, returns:

```json
{
  "success": true,
  "data": {
    "grouped": [{"month": "Jan", "revenue": 45000}, {"month": "Feb", "revenue": 52000}],
    "aggregation": "sum"
  },
  "metadata": {
    "tool": "groupby",
    "execution_time_ms": 8,
    "rows_affected": 12
  },
  "error": null
}
```

### Turn 3 — Top Regions

LLM evaluates the grouped data and decides to identify top-performing regions.

```json
{
  "analysis": "Revenue by month shows an upward trend. Now identifying top 5 regions by revenue.",
  "next_tool": "top_n",
  "params": {
    "column": "region",
    "metric": "revenue",
    "n": 5
  }
}
```

Backend executes `top_n`, returns:

```json
{
  "success": true,
  "data": {
    "top": [{"region": "North", "revenue": 120000}, {"region": "South", "revenue": 98000}],
    "ranked_by": "revenue"
  },
  "metadata": {
    "tool": "top_n",
    "execution_time_ms": 5,
    "rows_affected": 5
  },
  "error": null
}
```

### Turn 4 — Finalize

LLM has sufficient data and finalizes with a chart specification and insight summary.

```json
{
  "analysis": "Revenue shows monthly growth. North and South regions are top performers.",
  "next_tool": null,
  "complete": true,
  "chart_type": "line",
  "chart_spec": {
    "x": "month",
    "y": "revenue",
    "title": "Monthly Revenue Trend"
  },
  "insights": [
    "Revenue is growing month over month.",
    "North region leads with $120,000 in revenue.",
    "Top 3 regions account for 65% of total revenue."
  ]
}
```

Backend returns the final structured response to the frontend for rendering.

---

# Iterative Analysis Loop

The system follows a bounded orchestration loop that governs every analysis request:

```text
1. User submits query + dataset
2. LLM evaluates query + current state
3. LLM decides next tool (or declares completion)
4. Backend validates parameters against schema
5. Backend executes tool safely on the dataframe
6. Tool returns structured response (data + metadata)
7. LLM evaluates the response
8. If more analysis needed → goto step 3
9. If complete → LLM generates insights + chart spec
10. Backend returns final result to frontend
```

## Loop Boundaries

* Maximum iterations: enforced by backend config (default: 10)
* Maximum execution time: enforced per request
* Tool availability: LLM can only call registered, predefined tools
* Parameter validation: backend validates all tool parameters before execution

## Error Handling

When a tool returns an error:

```json
{
  "success": false,
  "data": null,
  "metadata": { "tool": "groupby", "error_type": "invalid_column" },
  "error": "Column 'revenue' not found. Available: ['sales', 'profit', 'month']"
}
```

The LLM receives the error with context and can:

1. Retry with corrected parameters (e.g., use 'sales' instead of 'revenue')
2. Choose an alternate analysis path (e.g., use a different aggregation)
3. Report the limitation to the user and suggest alternatives

The backend does NOT allow infinite retries — retry count is bounded per request.

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

## Structured Tool Response Contracts

Every tool returns a uniform response envelope. This predictable structure enables the LLM to make informed decisions about next steps, retries, and alternative paths.

### Success Response

```json
{
  "success": true,
  "data": {
    "result_key": "result_value"
  },
  "metadata": {
    "tool": "groupby",
    "execution_time_ms": 12,
    "rows_affected": 150,
    "warning": null
  },
  "error": null
}
```

### Error Response

```json
{
  "success": false,
  "data": null,
  "metadata": {
    "tool": "groupby",
    "error_type": "invalid_column"
  },
  "error": "Column 'revenue' not found. Available columns: ['sales', 'profit', 'month']"
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `success` | bool | Whether the tool executed successfully |
| `data` | object or null | The tool's output data |
| `metadata.tool` | string | Name of the tool that executed |
| `metadata.execution_time_ms` | int | Execution duration in milliseconds |
| `metadata.rows_affected` | int or null | Number of rows impacted |
| `metadata.warning` | string or null | Non-blocking warning message |
| `metadata.error_type` | string or null | Machine-readable error category |
| `error` | string or null | Human-readable error message |

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

### Bounded Autonomous Analysis

The LLM chains multiple operations autonomously within the iterative loop:

* "Analyze revenue trends by region and identify top performers"
* "Show me sales patterns — group by month and find correlations with profit"
* "What's driving growth? Explore the dataset and surface key insights"

The system performs iterative multi-step tool orchestration without requiring the user to specify each step.

### Intelligent Error Recovery

When a tool fails:

* The system automatically suggests corrected parameters
* If a column is misspelled, the LLM uses the schema to pick the right one
* If data is insufficient, the LLM tries an alternative analysis path

### Autonomous Insight Generation

The system proactively identifies and surfaces:

* Trend summaries and growth patterns
* Anomaly and outlier observations
* Correlation insights between numeric columns
* Top/bottom performer identification
* Distribution characteristics

Insights are generated after the analysis loop completes, based on accumulated tool results.

### Visualization Requests

Examples:

* "Create a scatter plot of sales vs profit"
* "Plot monthly revenue"

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

LLM Role:

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
