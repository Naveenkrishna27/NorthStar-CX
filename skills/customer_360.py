"""
NorthStar CX - Skill 1: customer_360_assemble

Given a customer_id, this pulls:
  - structured data (policies, claims) via plain SQL
  - unstructured data (call transcripts) via plain SQL, filtered by customer_id
Then feeds all of it into Snowflake Cortex COMPLETE to synthesize a single,
plain-English unified customer profile.

Run standalone for testing: python customer_360.py CUST0001
"""

import os
import sys
import json

import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    # A Personal Access Token (PAT) is passed as the password - no special
    # authenticator setting is needed for the standard connector.
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PAT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


def fetch_customer_data(conn, customer_id):
    """Pull structured + unstructured data for one customer via plain SQL."""
    cur = conn.cursor(snowflake.connector.DictCursor)

    cur.execute(
        "SELECT * FROM CUSTOMERS WHERE customer_id = %s", (customer_id,)
    )
    customer = cur.fetchone()
    if not customer:
        return None

    cur.execute(
        "SELECT * FROM POLICIES WHERE customer_id = %s", (customer_id,)
    )
    policies = cur.fetchall()

    cur.execute(
        """
        SELECT c.* FROM CLAIMS c
        JOIN POLICIES p ON c.policy_id = p.policy_id
        WHERE p.customer_id = %s
        """,
        (customer_id,),
    )
    claims = cur.fetchall()

    cur.execute(
        """
        SELECT interaction_date, channel, sentiment, transcript
        FROM INTERACTIONS
        WHERE customer_id = %s
        ORDER BY interaction_date DESC
        """,
        (customer_id,),
    )
    interactions = cur.fetchall()

    cur.close()
    return {
        "customer": customer,
        "policies": policies,
        "claims": claims,
        "interactions": interactions,
    }


def build_prompt(data):
    """Turn the raw retrieved data into a clear prompt for Cortex COMPLETE."""
    customer = data["customer"]
    policies = data["policies"]
    claims = data["claims"]
    interactions = data["interactions"]

    policies_text = "\n".join(
        f"- {p['POLICY_TYPE']} policy, premium INR {p['ANNUAL_PREMIUM_INR']}, "
        f"status: {p['STATUS']}, renewal: {p['RENEWAL_DATE']}"
        for p in policies
    ) or "No policies on file."

    claims_text = "\n".join(
        f"- {c['CLAIM_TYPE']} claim, amount INR {c['CLAIM_AMOUNT_INR']}, "
        f"status: {c['STATUS']}, date: {c['CLAIM_DATE']}"
        for c in claims
    ) or "No claims on file."

    interactions_text = "\n".join(
        f"- [{i['INTERACTION_DATE']}, {i['CHANNEL']}, sentiment: {i['SENTIMENT']}] "
        f"{i['TRANSCRIPT']}"
        for i in interactions
    ) or "No interaction history."

    prompt = f"""You are a customer intelligence assistant for an insurance company.
Given the structured and unstructured data below for one customer, write a
concise, plain-English unified profile (4-6 sentences). Cover: who they are,
their policy standing, any claims friction, and the overall tone of their
recent interactions. Be factual and specific - reference actual details
(policy types, claim outcomes, sentiment patterns), not generic statements.

CUSTOMER
Name: {customer['NAME']}, Age: {customer['AGE']}, City: {customer['CITY']}
Segment: {customer['SEGMENT']}, Tenure: {customer['TENURE_YEARS']} years

POLICIES
{policies_text}

CLAIMS
{claims_text}

RECENT CALL/INTERACTION HISTORY
{interactions_text}

Write the unified profile now:"""

    return prompt


def call_cortex_complete(conn, prompt, model="llama3.1-70b"):
    """Call Snowflake Cortex COMPLETE with the given prompt."""
    cur = conn.cursor()
    # Using bind params for the prompt avoids SQL-escaping issues with
    # quotes/newlines inside the transcript text.
    cur.execute(
        "SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s)", (model, prompt)
    )
    result = cur.fetchone()[0]
    cur.close()
    return result


def customer_360_assemble(customer_id):
    """Main entry point for skill 1."""
    conn = get_connection()
    try:
        data = fetch_customer_data(conn, customer_id)
        if data is None:
            return {"error": f"Customer {customer_id} not found."}

        prompt = build_prompt(data)
        profile_text = call_cortex_complete(conn, prompt)

        return {
            "customer_id": customer_id,
            "raw_data": data,
            "unified_profile": profile_text,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CUST0001"
    result = customer_360_assemble(cid)
    if "error" in result:
        print(result["error"])
    else:
        print(f"\n=== Unified Profile for {cid} ===\n")
        print(result["unified_profile"])
        print(f"\n(Based on {len(result['raw_data']['policies'])} policies, "
              f"{len(result['raw_data']['claims'])} claims, "
              f"{len(result['raw_data']['interactions'])} interactions)")