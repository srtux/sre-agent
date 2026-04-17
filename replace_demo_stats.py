
filepath = "sre_agent/tools/synthetic/demo_data_generator.py"

with open(filepath) as f:
    text = f.read()

text = text.replace("import statistics\n", "")
text = text.replace(
    'statistics.mean(ns["durations"])', '(sum(ns["durations"]) / len(ns["durations"]))'
)
text = text.replace(
    'statistics.mean(es["durations"])', '(sum(es["durations"]) / len(es["durations"]))'
)
text = text.replace("statistics.mean(durations)", "(sum(durations) / len(durations))")
text = text.replace(
    'statistics.mean([s["turns"] for s in sessions])',
    '(sum(s["turns"] for s in sessions) / len(sessions))',
)
text = text.replace(
    "statistics.mean(prev_session_turns.values())",
    "(sum(prev_session_turns.values()) / len(prev_session_turns.values()))",
)
text = text.replace("statistics.mean(latencies)", "(sum(latencies) / len(latencies))")
text = text.replace(
    'statistics.mean(ts["durations"])', '(sum(ts["durations"]) / len(ts["durations"]))'
)

with open(filepath, "w") as f:
    f.write(text)
