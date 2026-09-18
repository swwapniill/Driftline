import os
import json
from dotenv import load_dotenv
from groq import Groq
from prompt_template import SYSTEM_PROMPT

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "").strip())

with open('anomaly_breakdown.json') as f:
    anomalies = json.load(f)

for a in anomalies:
    user_prompt = f"Explain this anomaly using only the data below:\n\n{json.dumps(a, indent=2)}"
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )
    a['explanation'] = response.choices[0].message.content
    print(a['date'], "-> explanation generated")

with open('anomaly_breakdown.json', 'w') as f:
    json.dump(anomalies, f, indent=2)

print("\nSaved explanations for all", len(anomalies), "anomalies.")
