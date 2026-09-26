"""
NorthStar CX - Skill 4: action_audit_trail

Takes the full pipeline output (profile + risk + action) and renders it as
an audit-ready record: exactly which data points, which model, when, and
what confidence - the governance layer that makes this defensible in a
regulated insurance/lending context, not just an AI suggestion.

Run standalone for testing: python audit_trail.py CUST0001
"""

import sys
import json
from datetime import datetime, timezone

try:
    from customer_360 import get_connection, fetch_customer_data
    from churn_risk import churn_risk_score
    from next_best_action import next_best_action
except ImportError:
    from skills.customer_360 import get_connection, fetch_customer_data
    from skills.churn_risk import churn_risk_score
    from skills.next_best_action import next_best_action


def build_audit_record(customer_id, data, risk_result, action_result):
    policies = data["policies"]
    claims = data["claims"]
    interactions = data["interactions"]

    evidence = {
        "policies_reviewed": len(policies),
        "lapsed_policies": [p["POLICY_ID"] for p in policies if p["STATUS"] == "Lapsed"],
        "claims_reviewed": len(claims),
        "denied_claims": [c["CLAIM_ID"] for c in claims if c["STATUS"] == "Denied"],
        "interactions_reviewed": len(interactions),
        "negative_interactions": [
            i["INTERACTION_DATE"].isoformat() if hasattr(i["INTERACTION_DATE"], "isoformat") else str(i["INTERACTION_DATE"])
            for i in interactions if i["SENTIMENT"] == "negative"
        ],
    }

    record = {
        "audit_id": f"AUD-{customer_id}-{int(datetime.now(timezone.utc).timestamp())}",
        "customer_id": customer_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_used": "snowflake-cortex/llama3.1-70b",
        "pipeline_version": "northstar-cx-v1",
        "decision": {
            "risk_level": risk_result["risk_level"],
            "risk_score": risk_result["risk_score"],
            "recommended_action": action_result["action"],
        },
        "evidence": evidence,
        "reasoning_trail": {
            "risk_reasoning": risk_result["reasoning"],
            "action_justification": action_result["justification"],
        },
    }
    return record


def action_audit_trail(customer_id, conn=None):
    """Main entry point for skill 4. Runs the full chain: 1 -> 2 -> 3 -> 4."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    try:
        data = fetch_customer_data(conn, customer_id)
        if data is None:
            return {"error": f"Customer {customer_id} not found."}

        risk_result = churn_risk_score(customer_id, data=data, conn=conn)
        action_result = next_best_action(
            customer_id, data=data, risk_result=risk_result, conn=conn
        )

        record = build_audit_record(customer_id, data, risk_result, action_result)
        return record
    finally:
        if own_conn:
            conn.close()


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CUST0001"
    result = action_audit_trail(cid)
    if "error" in result:
        print(result["error"])
    else:
        print(f"\n=== Audit Trail for {cid} ===\n")
        print(json.dumps(result, indent=2, default=str))