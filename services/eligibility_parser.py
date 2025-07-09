import requests
import json

def query_self_hosted_zephyr(prompt: str) -> str:
    API_URL = "http://34.60.71.140:8000/search"  # Replace with your actual IP:port if different

    payload = {
        "prompt": prompt,
        "max_tokens": 768  # You can adjust this as your server allows
    }

    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return ""

def extract_first_json_object(text: str) -> dict:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    text = text.replace("}\n{", "},\n{").replace("}\n\"", "},\n\"")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = None
    depth = 0
    for i, ch in enumerate(text):
        if ch == '{':
            if start is None:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    continue
    return {}

def extract_eligibility_json_general(raw_text: str) -> dict:
    prompt = f"""
You are an intelligent assistant that extracts structured eligibility requirements from tender eligibility text.

Respond only with a valid JSON object (no markdown, no explanation).

Expected output format:
{{
  "experience": {{ "required": true, "minimum_years": 3 }},
  "gstin": {{ "required": true }},
  "pan": {{ "required": true }},
  "required_documents": ["EMD", "PAN card"],
  "certifications": ["ISO"],
  "financial_requirements": {{ "annual_turnover_required": true, "minimum_turnover_amount": null }},
  "blacklisting_or_litigation": {{ "mentioned": false }},
  "other_criteria": {{ "registration_on_gem": {{ "required": true }} }}
}}

If a field is not mentioned, mark `required: false`, use `null`, or an empty list as appropriate.

Eligibility Criteria Text:
{raw_text}

Respond only with the JSON.
"""
    zephyr_response = query_self_hosted_zephyr(prompt)
    print("📄 Raw Zephyr output:\n", zephyr_response)
    parsed = extract_first_json_object(zephyr_response)
    print("✅ Final Parsed Output:\n", json.dumps(parsed, indent=2))
    return parsed
