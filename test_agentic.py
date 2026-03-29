"""Quick smoke test for the agentic workflow."""
import py_compile
import sys

files = [
    "audit_logger.py",
    "agent_orchestrator.py",
    "agents/__init__.py",
    "agents/base_agent.py",
    "agents/ingestion_agent.py",
    "agents/extraction_agent.py",
    "agents/analysis_agent.py",
    "agents/strategy_agent.py",
    "agents/compliance_agent.py",
    "agents/fast_track_agent.py",
    "agents/redirect_agent.py",
    "app.py",
    "pipeline.py",
    "implication_engine.py",
]

errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  OK  {f}")
    except py_compile.PyCompileError as e:
        print(f"  FAIL {f}: {e}")
        errors.append(f)

# Test config loading
import json, os
config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
for cfg in ["thresholds.json", "blocklist.json", "anchors.json"]:
    path = os.path.join(config_dir, cfg)
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
        print(f"  OK  config/{cfg} ({len(data)} keys)")
    except Exception as e:
        print(f"  FAIL config/{cfg}: {e}")
        errors.append(cfg)

# Test audit logger (no heavy deps)
from audit_logger import AuditLogger, DecisionType
logger = AuditLogger("test-session")
logger.log_agent_start("TestAgent", "test input")
logger.log_routing("Orchestrator", "Test routing decision", alternatives=["A", "B"])
logger.log_agent_complete("TestAgent", "test output", confidence=0.95, duration_ms=100)
summary = logger.to_summary()
json_out = logger.to_json()
stats = logger.get_agent_stats()
print(f"  OK  AuditLogger: {len(logger.entries)} entries, {len(stats)} agents")

if errors:
    print(f"\nFAILED: {errors}")
    sys.exit(1)
else:
    print(f"\nALL {len(files)} files + 3 configs + AuditLogger OK")
