#!/bin/bash
# Detect available MCP tools from Claude Code configuration.
# Writes detected-tools.json to the NSAF root directory.
set -euo pipefail

NSAF_DIR="${NSAF_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
OUTPUT="$NSAF_DIR/detected-tools.json"

# Locations Claude Code stores MCP server configs
CONFIG_FILES=(
  "$HOME/.claude.json"
  "$HOME/.claude/settings.json"
  "$HOME/.claude/settings.local.json"
)

python3 -c "
import json, os, sys

servers = {}
config_files = sys.argv[1:]

for f in config_files:
    if not os.path.exists(f):
        continue
    try:
        with open(f) as fh:
            data = json.load(fh)
        for name, config in data.get('mcpServers', {}).items():
            if name not in servers:
                servers[name] = {'source': f}
    except Exception:
        pass

# Categorize known tools
categories = {
    'deployment': [],
    'art_generation': [],
    'code_hosting': [],
    'infrastructure': [],
    'other': [],
}

known = {
    'render': 'deployment',
    'cloudflare': 'infrastructure',
    'github': 'code_hosting',
    'pixellab': 'art_generation',
    'leonardo-ai': 'art_generation',
}

for name in servers:
    cat = known.get(name, 'other')
    categories[cat].append(name)

result = {
    'tools': list(servers.keys()),
    'categories': {k: v for k, v in categories.items() if v},
    'count': len(servers),
}

print(json.dumps(result, indent=2))
" "${CONFIG_FILES[@]}" > "$OUTPUT"

echo "Detected $(python3 -c "import json; print(json.load(open('$OUTPUT'))['count'])") MCP tools → $OUTPUT"
cat "$OUTPUT"
