# rule_based_extractor.py
import os
import json
import pandas as pd

RULE_PATH = "memory_store/rule_memory.json"
os.makedirs("memory_store", exist_ok=True)

def get_header_fingerprint(headers):
    return "|".join([h.strip().lower() for h in headers])

def load_rules():
    if not os.path.exists(RULE_PATH):
        return []
    with open(RULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_rule(headers, rules):
    fingerprint = get_header_fingerprint(headers)
    rule_store = load_rules()
    for item in rule_store:
        if item["header_fingerprint"] == fingerprint:
            item["rules"] = rules
            break
    else:
        rule_store.append({"header_fingerprint": fingerprint, "rules": rules})
    with open(RULE_PATH, "w", encoding="utf-8") as f:
        json.dump(rule_store, f, indent=2, ensure_ascii=False)

def find_rule(headers):
    fingerprint = get_header_fingerprint(headers)
    for item in load_rules():
        if item["header_fingerprint"] == fingerprint:
            return item["rules"]
    return None

def extract_sections_by_rule(df, rules):
    start_keywords = rules.get("start_keywords", [])
    end_keywords = rules.get("end_keywords", [])
    label_keywords = rules.get("label_keywords", {})

    sections = []
    start_row = None
    for i, row in df.iterrows():
        row_text = " ".join([str(cell).lower() for cell in row if pd.notna(cell)])
        if start_row is None and any(kw in row_text for kw in start_keywords):
            start_row = i
        elif start_row is not None and (any(kw in row_text for kw in end_keywords) or row.isnull().all()):
            label = "unknown"
            for k, v in label_keywords.items():
                if k.lower() in row_text:
                    label = v
                    break
            sections.append({
                "start_row": start_row + 1,
                "end_row": i + 1,
                "header_row": start_row + 1,
                "label": label
            })
            start_row = None
    return sections
