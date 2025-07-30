# extractor_memory.py
import os
import json

MEMORY_FILE = "memory_store/extractor_memory.json"
os.makedirs("memory_store", exist_ok=True)

def get_header_fingerprint(headers):
    return "|".join([h.strip().lower() for h in headers])

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"patterns": []}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def find_matching_pattern(headers):
    fp = get_header_fingerprint(headers)
    memory = load_memory()
    for item in memory["patterns"]:
        if item["header_fingerprint"] == fp:
            return item
    return None

def add_pattern_entry(headers, accepted_sections, feedback_prompt, final_prompt):
    memory = load_memory()
    fp = get_header_fingerprint(headers)
    for item in memory["patterns"]:
        if item["header_fingerprint"] == fp:
            item["accepted_sections"] = accepted_sections
            item["feedback_prompt"] = feedback_prompt
            item["final_prompt"] = final_prompt
            save_memory(memory)
            return
    memory["patterns"].append({
        "header_fingerprint": fp,
        "accepted_sections": accepted_sections,
        "feedback_prompt": feedback_prompt,
        "final_prompt": final_prompt
    })
    save_memory(memory)
