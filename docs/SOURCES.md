# Integrated sources

This repository consolidates the five repositories supplied for the project. The final codebase keeps the latest useful behavior from each stage rather than carrying five duplicate applications.

| Source | Material incorporated | Replaced or corrected |
|---|---|---|
| [AI Travel Planning System using LangGraph](https://github.com/AnshMadanpuriya/AI-Travel-Planning-System-using-LangGraph) | Initial flight → hotel → itinerary workflow, Groq, Tavily, AviationStack, Streamlit, PostgreSQL memory | Removed committed `.env`, import-time database requirement, blocking HTTP without timeouts, and the unfiltered flight query |
| [AI Travel Planning App using LangGraph and MCP](https://github.com/AnshMadanpuriya/AI-Travel-Planning-App-using-LangGraph-and-MCP) | Tavily remote MCP, local aviation/weather MCP processes, destination-aware research | Removed machine-specific Windows Python paths, inconsistent `AVIATIONSTACK_API_KEY` spelling, and all-or-nothing MCP initialization |
| [Multi Agent System Part 3](https://github.com/AnshMadanpuriya/Multi_agent_system_part_3) | Supervisor, guardrail, budget agent, human-in-the-loop review, dynamic routing | Fixed brittle JSON extraction, unsafe logging, and guardrail routing that could continue into itinerary generation |
| [Multi Agent System Part 4](https://github.com/AnshMadanpuriya/Multi_agent_system_part_4) | VPS deployment guidance | Replaced incomplete systemd instructions with repeatable containers, health checks, CI, and a deployment runbook |
| [Multi Agent System Part 5](https://github.com/AnshMadanpuriya/Multi_agent_system_part_5) | Docker direction, final multi-agent shape, PostgreSQL checkpointing | Fixed the Docker build that referenced a missing `aviationstack-mcp/` directory by implementing a local FastMCP aviation server |

## Tutorial resources found in the supplied repositories

| Part | Topic | Video |
|---|---|---|
| 1 | Multi-agent system + memory + APIs (Hindi) | [YouTube](https://youtu.be/ctHby5vhDqg) |
| 1 | Multi-agent system + memory + APIs (English) | [YouTube](https://youtu.be/_5XF5CCnbDk) |
| 2 | LangGraph + MCP | [YouTube](https://youtu.be/DjMX7o2EeV0) |
| 3 | Supervisor + guardrails + human review | [YouTube](https://youtu.be/ZULVHkPa4xk) |
| 4 | VPS deployment | [YouTube](https://youtu.be/84LbJElhfL4) |
| 5 | Docker deployment | [YouTube](https://youtu.be/XsJxUBjxIqU) |

## Integration decisions

- The hosted web runtime is TypeScript and uses `@langchain/langgraph` so it can run at the edge without raw TCP connections.
- The `python_backend/` runtime preserves the Python LangGraph, FastMCP, Streamlit, PostgreSQL, and `interrupt()` learning path from the tutorials.
- Both runtimes implement the same safety contract: no automatic booking, clear estimate labels, human review, server-side keys, timeouts, and graceful provider fallback.
- Generated caches, virtual environments, `.env` files, and machine-specific paths are intentionally excluded.

## Attribution and licensing note

The supplied repositories point back to the `codewithaarohi` tutorial series and did not contain a `LICENSE` file during this audit. Attribution is preserved here. Before commercial redistribution, confirm that you have permission to reuse every upstream code asset and add the appropriate project license.
