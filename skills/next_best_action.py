"""
NorthStar CX - Skill 3: next_best_action

Takes the unified profile + churn risk assessment and recommends ONE
specific, justified next action for a retention/ops team to take.

Run standalone for testing: python next_best_action.py CUST0001
"""

import sys
import re

try:
    from customer_360 import get_connection, fetch_customer_data, call_cortex_complete
    from churn_risk import churn_risk_score
except ImportError:
    from skills.customer_360 import get_connection, fetch_customer_data, call_cortex_complete
    from skills.churn_risk import churn_risk_score

ACTIONS = [
    "Retention outreach call",
    "Escalate denied claim for review",
    "Offer loyalty/renewal discount",
    "Send policy renewal reminder",
    "No action needed - monitor",
]


def build_action_prompt(data, risk_result):
    customer = data["customer"]
    policies = data["policies"]
    claims = data["claims"]

    lapsed_policies = [p for p in policies if p["STATUS"] == "Lapsed"]
    denied_claims = [c for c in claims if c["STATUS"] == "Denied"]

    context = f"""
CUSTOMER: {customer['NAME']}, segment: {customer['SEGMENT']}, tenure: {customer['TENURE_YEARS']} years
CHURN RISK: {risk_result['risk_level']} ({risk_result['risk_score']}/100)
RISK REASONING: {risk_result['reasoning']}
LAPSED POLICIES: {len(lapsed_policies)}
DENIED CLAIMS: {len(denied_claims)}
"""

    action_list = "\n".join(f"- {a}" for a in ACTIONS)

    prompt = f"""You are a retention operations advisor for an insurance company.
Based on the customer context below, recommend exactly ONE next action from
this list:
{action_list}

CONTEXT
{context}

Respond in EXACTLY this format, nothing else:
ACTION: <one action from the list above, verbatim>
JUSTIFICATION: <2-3 sentences explaining why THIS action, citing the specific risk level and evidence above>
"""
    return prompt


def parse_action_response(text):
    action_match = re.search(r"ACTION:\s*(.+)", text)
    justification_match = re.search(r"JUSTIFICATION:\s*(.+)", text, re.DOTALL)

    return {
        "action": action_match.group(1).strip() if action_match else "Unknown",
        "justification": justification_match.group(1).strip() if justification_match else text.strip(),
    }


def next_best_action(customer_id, data=None, risk_result=None, conn=None):
    """
    Main entry point for skill 3.
    Chains skill 1 (data) and skill 2 (risk) if not already provided.
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    try:
        if data is None:
            data = fetch_customer_data(conn, customer_id)
            if data is None:
                return {"error": f"Customer {customer_id} not found."}

        if risk_result is None:
            risk_result = churn_risk_score(customer_id, data=data, conn=conn)

        prompt = build_action_prompt(data, risk_result)
        raw_response = call_cortex_complete(conn, prompt)
        parsed = parse_action_response(raw_response)

        return {
            "customer_id": customer_id,
            "risk_result": risk_result,
            **parsed,
            "raw_llm_response": raw_response,
        }
    finally:
        if own_conn:
            conn.close()


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CUST0001"
    result = next_best_action(cid)
    if "error" in result:
        print(result["error"])
    else:
        print(f"\n=== Next Best Action for {cid} ===\n")
        print(f"Risk: {result['risk_result']['risk_level']} ({result['risk_result']['risk_score']}/100)")
        print(f"Recommended Action: {result['action']}")
        print(f"Justification: {result['justification']}")