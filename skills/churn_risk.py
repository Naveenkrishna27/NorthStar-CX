"""
NorthStar CX - Skill 2: churn_risk_score

Takes a customer's unified profile (from skill 1) and produces a churn/
retention risk assessment: a risk level (Low/Medium/High), a numeric score
0-100, and specific evidence-based reasoning tied to the actual data -
not a black-box number.

Run standalone for testing: python churn_risk.py CUST0001
"""

import os
import sys
import json
import re

try:
    from customer_360 import get_connection, fetch_customer_data, call_cortex_complete
except ImportError:
    from skills.customer_360 import get_connection, fetch_customer_data, call_cortex_complete


def build_risk_prompt(data):
    customer = data["customer"]
    policies = data["policies"]
    claims = data["claims"]
    interactions = data["interactions"]

    lapsed_policies = [p for p in policies if p["STATUS"] == "Lapsed"]
    denied_claims = [c for c in claims if c["STATUS"] == "Denied"]
    negative_interactions = [i for i in interactions if i["SENTIMENT"] == "negative"]

    facts = f"""
- Total policies: {len(policies)}, of which {len(lapsed_policies)} are lapsed
- Total claims: {len(claims)}, of which {len(denied_claims)} were denied
- Total interactions: {len(interactions)}, of which {len(negative_interactions)} had negative sentiment
- Customer tenure: {customer['TENURE_YEARS']} years
- Customer segment: {customer['SEGMENT']}
"""

    prompt = f"""You are a churn risk analyst for an insurance company. Based on the
factual signals below for one customer, assess their churn/retention risk.

SIGNALS
{facts}

Respond in EXACTLY this format, nothing else:
RISK_LEVEL: <Low, Medium, or High>
RISK_SCORE: <a number from 0 to 100, where 100 is certain to churn>
REASONING: <2-3 sentences citing the SPECIFIC signals above that drove this assessment - not generic statements>

IMPORTANT: When citing numbers in your reasoning, use EXACTLY the numbers
given in the SIGNALS section above. Do not recalculate or restate them
differently - copy the exact figures given.
"""
    return prompt


def parse_risk_response(text):
    """Extract structured fields from the LLM's formatted response."""
    level_match = re.search(r"RISK_LEVEL:\s*(\w+)", text)
    score_match = re.search(r"RISK_SCORE:\s*(\d+)", text)
    reasoning_match = re.search(r"REASONING:\s*(.+)", text, re.DOTALL)

    return {
        "risk_level": level_match.group(1) if level_match else "Unknown",
        "risk_score": int(score_match.group(1)) if score_match else None,
        "reasoning": reasoning_match.group(1).strip() if reasoning_match else text.strip(),
    }


def churn_risk_score(customer_id, data=None, conn=None):
    """
    Main entry point for skill 2.
    Can be called standalone (fetches its own data/connection) or chained
    from another skill by passing an existing conn and data dict.
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    try:
        if data is None:
            data = fetch_customer_data(conn, customer_id)
            if data is None:
                return {"error": f"Customer {customer_id} not found."}

        prompt = build_risk_prompt(data)
        raw_response = call_cortex_complete(conn, prompt)
        parsed = parse_risk_response(raw_response)

        return {
            "customer_id": customer_id,
            **parsed,
            "raw_llm_response": raw_response,
        }
    finally:
        if own_conn:
            conn.close()


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CUST0001"
    result = churn_risk_score(cid)
    if "error" in result:
        print(result["error"])
    else:
        print(f"\n=== Churn Risk Assessment for {cid} ===\n")
        print(f"Risk Level: {result['risk_level']}")
        print(f"Risk Score: {result['risk_score']}/100")
        print(f"Reasoning: {result['reasoning']}")