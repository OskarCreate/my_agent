# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a LangGraph-based AI agent project that supports multiple agent configurations. The project uses LangGraph's graph-based architecture to build stateful, multi-actor applications with LLMs.

## Development Commands

### Environment Setup
```powershell
# Install dependencies using uv (Python package installer)
uv sync

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

### Running Agents

The project defines multiple agents in `langgraph.json`:
- **agent**: Main agent (Galleta) with weather tool - defined in `src/main.py`
- **simple**: Simple stateful agent - defined in `src/simple.py`

```powershell
# Start LangGraph development server
langgraph dev

# Run specific agent in dev mode
langgraph dev --graph agent
langgraph dev --graph simple
```

### Working with Notebooks
Jupyter notebooks are in the `notebooks/` directory for experimentation:
- `01-notebook.ipynb` - Introduction
- `03-messages.ipynb` - Message handling
- `04-llm.ipynb` - LLM interactions

```powershell
# Start Jupyter
jupyter notebook notebooks/
```

## Code Architecture

### Agent Configuration System
- **langgraph.json**: Defines available graphs/agents and their entry points
- Each agent is a compiled StateGraph exported from its respective module
- Environment variables are loaded from `.env` via python-dotenv

### State Management
Agents use typed state classes that extend `MessagesState`:
```python
class State(MessagesState):
    customer_name: str
    my_age: int
```

State is passed between nodes and updated immutably - return dictionaries merge into existing state.

### Agent Architecture Patterns

**Pattern 1: Tool-based Agent** (`src/main.py`)
- Uses `create_agent()` helper from langchain.agents
- Declarative approach with model string, tools list, and system prompt
- Tools are Python functions with docstrings (used for LLM understanding)

**Pattern 2: Graph-based Agent** (`src/simple.py`)
- Manual StateGraph construction with `StateGraph(State)`
- Explicit node definition with state transformation functions
- Explicit edge routing (START → node → END)
- More control over execution flow and state transitions

### LLM Provider Configuration
The project supports multiple LLM providers via model strings:
- Groq: `"groq:llama-3.1-8b-instant"`
- OpenAI: Use with `langchain-openai`
- Google GenAI: Use with `langchain-google-genai`

Initialize models with: `init_chat_model(model_string, temperature=...)`

### Environment Variables
Required API keys in `.env`:
- `GROQ_API_KEY` - For Groq models
- `OPENAI_API_KEY` - For OpenAI models
- `GENAI_API_KEY` - For Google GenAI models
- `LANGCHAIN_API_KEY` - For LangSmith tracing
- `LANGCHAIN_TRACING_V2=true` - Enable tracing
- `LANGCHAIN_PROJECT` - Project name for LangSmith

## Key Dependencies

- **langgraph**: Core graph framework for building agents
- **langchain**: LLM abstraction and agent utilities
- **langgraph-cli**: Development server and deployment tools
- **Provider SDKs**: langchain-groq, langchain-openai, langchain-google-genai

## Project Structure

```
my_agent/
├── src/                    # Agent implementations
│   ├── main.py            # Tool-based agent (Galleta)
│   └── simple.py          # Graph-based agent
├── notebooks/             # Jupyter notebooks for experimentation
├── .langgraph_api/        # LangGraph runtime state (checkpoints, ops)
├── langgraph.json         # Agent graph definitions and configuration
├── pyproject.toml         # Python dependencies and project metadata
└── .env                   # API keys and environment configuration
```

## Adding New Agents

1. Create new Python file in `src/` with agent implementation
2. Export compiled graph as `agent` variable
3. Register in `langgraph.json` under `"graphs"`:
   ```json
   "your_agent_name": "./src/your_file.py:agent"
   ```
4. Access via `langgraph dev --graph your_agent_name`

## Development Notes

- LangGraph uses checkpointing for persistence (stored in `.langgraph_api/`)
- Node functions receive state and return partial state updates (merge semantics)
- Tools must have docstrings - they're used to generate LLM tool descriptions
- The `MessagesState` base class provides message history management
- Use `langgraph dev` for hot-reloading during development
