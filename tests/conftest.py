import os
import sys

# Ensure the package-relative absolute imports like `from modules import ...` resolve
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
GEN_AGENT_ROOT = os.path.join(REPO_ROOT, "generative_agents")

for p in [REPO_ROOT, GEN_AGENT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Provide a lightweight dummy 'start' module to avoid importing the real start.py (which parses CLI args)
import types as _types
_dummy_start = _types.ModuleType("start")
_dummy_start.personas = ["Alice", "Bob", "Charlie"]
sys.modules.setdefault("start", _dummy_start)

# Prevent third-party scripts (e.g., start.py) from parsing pytest CLI args at import-time
try:
    sys.argv = [sys.argv[0]]
except Exception:
    pass

# Map the top-level alias 'modules' to 'generative_agents.modules' for absolute imports inside code
try:
    import generative_agents.modules as _ga_modules
    sys.modules.setdefault("modules", _ga_modules)
except Exception:
    pass
