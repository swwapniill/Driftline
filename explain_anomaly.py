import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

sample = {
    "date": "20201210",
    "driver_status": "concentrated",
    "top_driver": {
        "dimension": "device_type",
        "value": "mobile",
        "delta": 22.5,
        "contribution_pct": 65.0,
        "is_catchall_bucket": False
    },
    "secondary_driver": {
        "dimension": "traffic_source",
        "value": "google",
        "delta": -9.3,
        "contribution_pct": -27.0,
        "is_catchall_bucket": False
    }
}

system_prompt = """You are an analytics assistant that explains e-commerce metric anomalies.

Rules you MUST follow:
1. Only use the numbers and dimensions given to you in the JSON input. Never invent causes (no holidays, promotions, news events, or external factors) unless they appear in the data itself.
2. Always cite specific numbers from the input (contribution percentages, deltas) in your explanation.
3. If driver_status is "distributed, no dominant driver", explicitly say there is no single clear cause. Do not force a top_driver into sounding like a confident explanation.
4. Keep the explanation to 2-3 sentences. Plain business language, no jargon.
5. If a driver's value is a catch-all bucket like "other_country" or "<Other>" (is_catchall_bucket: true), say the exact category is unclear rather than treating it as a specific, named cause.
6. Never write phrases like "together these explain", "combined they account for", "in total", or "overall" when referring to top_driver and secondary_driver — they are from different dimensions and are NOT additive. Describe them as two separate, independent observations instead. For example, write "Desktop was the largest single factor (57.2%); separately, the United States also saw a notable increase (46.0%)" — NOT "together these explain 103% of the change."
7. If driver_status is "insufficient baseline data", do NOT attempt to name a driver or explain a cause. State plainly that there isn't enough historical data yet to reliably assess this day, and say when reliable detection will become possible if that information is given.
8. If top_driver and secondary_driver have deltas with OPPOSITE signs (one positive, one negative), explicitly point out that the signals conflict — one dimension moved up while another moved down — rather than blending them into a single narrative.
"""

user_prompt = f"Explain this anomaly using only the data below:\n\n{json.dumps(sample, indent=2)}"

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.2
)

print("INPUT ANOMALY (SYNTHETIC - conflicting signals):")
print(json.dumps(sample, indent=2))
print("\nLLM EXPLANATION:")
print(response.choices[0].message.content)
