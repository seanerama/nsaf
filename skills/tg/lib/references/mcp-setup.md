# Perplexity MCP Setup

## Configuration

Add to `.claude/settings.json` (project-level or global `~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "perplexity": {
      "command": "npx",
      "args": ["-y", "@perplexity-ai/mcp-server"],
      "env": {
        "PERPLEXITY_API_KEY": "${PERPLEXITY_API_KEY}"
      }
    }
  }
}
```

## API Key

Set in your shell environment:

```bash
export PERPLEXITY_API_KEY="pplx-..."
```

Or add to `.env` in the project directory (must be gitignored).

## Model

SWS uses Perplexity Sonar Pro for research queries. The MCP server handles model selection.

## Cost

Approximately $0.006 per query. A 10-chapter topic with 2-3 queries per chapter costs ~$0.06 for research.
