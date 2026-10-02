import json

data = []
with open('tests/eval/datasets/golden_v1.jsonl') as f:
    for line in f:
        if line.strip():
            data.append(json.loads(line))

for row in data:
    if row['id'] == 'routing-medium-01':
        row['query'] = "Can you compare the difference between SQL and NoSQL databases and when I should use each one for my application"
        row['warmup_query'] = "Can you compare the difference between SQL and NoSQL databases and when I should use each one for my application"
    
    if row['id'] == 'code-question-01':
        row['expected_model_tier'] = 'qwen-plus'
        row['expectations']['expected_model_tier'] = 'qwen-plus'
        row['query'] = "Write a Python function to calculate fibonacci numbers using dynamic programming def fibonacci(n): Please analyze and compare its performance to the recursive approach."
        
    if row['id'] in ('compression-history-01', 'long-history-compression-01'):
        # Expand history to force aggressive truncation
        for h in row['history']:
            if h['role'] == 'assistant':
                h['content'] = h['content'] * 15 # make it very long

with open('tests/eval/datasets/golden_v1.jsonl', 'w') as f:
    for row in data:
        f.write(json.dumps(row) + "\n")
