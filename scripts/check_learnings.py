from ai_system.learn import list_recent_learnings, summarize_learnings
import json

items = list_recent_learnings(10)
print('Found:', len(items))
print(json.dumps(items, indent=2, ensure_ascii=False))
print('\nResumen:\n')
print(summarize_learnings(5))
