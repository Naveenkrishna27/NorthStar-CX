"""
NorthStar CX - Synthetic Data Generator v2
Improvement over v1: sentiment is now CAUSALLY linked to claims/policy outcomes,
not randomly assigned. This gives the churn-risk skill real signal to detect,
and lets you report an honest accuracy number in the submission deck.

Outputs 5 CSVs into ./data/:
  - customers.csv
  - policies.csv
  - claims.csv
  - interactions.csv       (call transcripts)
  - ground_truth.csv       (internal only - NOT fed to the LLM, used to score your model)

Run: python generate_data_v2.py
"""

import csv
import os
import random
from datetime import datetime, timedelta

from faker import Faker

fake = Faker("en_IN")
Faker.seed(7)
random.seed(7)

OUT_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUT_DIR, exist_ok=True)

NUM_CUSTOMERS = 120
POLICY_TYPES = ["Auto", "Home", "Life", "Health"]
CLAIM_TYPES = ["Accident", "Theft", "Fire", "Medical", "Natural Disaster"]
SEGMENTS = ["Standard", "Premium", "High-Value"]

COMPLAINT_OPENERS = [
    "I've been a customer for {tenure} years and I'm really unhappy with how my last claim was handled.",
    "This is the third time I'm calling about the same issue and nothing has been resolved.",
    "I want to understand why my premium went up without any notice.",
    "The service I received at the branch was extremely disappointing.",
    "I'm seriously considering switching providers after this experience.",
    "My claim got denied and nobody has properly explained why.",
    "I feel like I'm being ignored every time I raise this issue.",
]

NEUTRAL_OPENERS = [
    "Hi, I wanted to check the status of my recent claim submission.",
    "Can you confirm when my policy renewal is due?",
    "I'd like to update my contact details on file.",
    "I have a question about what my policy actually covers.",
    "Just calling to confirm my last payment went through.",
]

POSITIVE_OPENERS = [
    "I just wanted to say the support team resolved my issue really quickly, thank you.",
    "I'm happy with the service so far and wanted to ask about upgrading my plan.",
    "Everything has been smooth with my policy, just checking on a few details.",
    "I recommended your services to a friend and wanted to ask about referral benefits.",
    "My claim was approved fast and I wanted to say I appreciated that.",
]

CLOSING_LINES = [
    "Agent: I understand, let me look into this and get back to you.",
    "Agent: I've noted this down and escalated it to the relevant team.",
    "Agent: Thank you for your patience, we'll resolve this within 48 hours.",
    "Agent: I've updated your details, is there anything else I can help with?",
    "Agent: I appreciate you sharing that feedback, it's been logged.",
]


def random_date(start_year=2023, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 9, 18)
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def generate_customers(n):
    customers = []
    for i in range(1, n + 1):
        tenure_years = random.randint(1, 12)
        join_date = datetime(2026, 9, 18) - timedelta(days=tenure_years * 365)
        customers.append(
            {
                "customer_id": f"CUST{i:04d}",
                "name": fake.name(),
                "age": random.randint(22, 68),
                "city": fake.city(),
                "segment": random.choices(SEGMENTS, weights=[0.5, 0.35, 0.15])[0],
                "tenure_years": tenure_years,
                "join_date": join_date.strftime("%Y-%m-%d"),
                "email": fake.email(),
                "phone": fake.phone_number(),
            }
        )
    return customers


def generate_policies(customers):
    policies = []
    policy_counter = 1
    cust_policy_map = {}
    for cust in customers:
        num_policies = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
        chosen_types = random.sample(POLICY_TYPES, num_policies)
        cust_policy_map[cust["customer_id"]] = []
        for ptype in chosen_types:
            premium = {
                "Auto": random.randint(8000, 25000),
                "Home": random.randint(10000, 40000),
                "Life": random.randint(15000, 60000),
                "Health": random.randint(12000, 35000),
            }[ptype]
            status = random.choices(
                ["Active", "Lapsed", "Renewal Due"], weights=[0.7, 0.12, 0.18]
            )[0]
            renewal_date = random_date(2026, 2027)
            pol = {
                "policy_id": f"POL{policy_counter:05d}",
                "customer_id": cust["customer_id"],
                "policy_type": ptype,
                "annual_premium_inr": premium,
                "status": status,
                "renewal_date": renewal_date.strftime("%Y-%m-%d"),
            }
            policies.append(pol)
            cust_policy_map[cust["customer_id"]].append(pol)
            policy_counter += 1
    return policies, cust_policy_map


def generate_claims(policies):
    claims = []
    claim_counter = 1
    policy_claims_map = {p["policy_id"]: [] for p in policies}
    for pol in policies:
        num_claims = random.choices([0, 1, 2], weights=[0.5, 0.35, 0.15])[0]
        for _ in range(num_claims):
            claim_date = random_date(2024, 2026)
            status = random.choices(
                ["Approved", "Denied", "Pending", "Under Review"],
                weights=[0.5, 0.2, 0.15, 0.15],
            )[0]
            claim = {
                "claim_id": f"CLM{claim_counter:05d}",
                "policy_id": pol["policy_id"],
                "customer_id": pol["customer_id"],
                "claim_type": random.choice(CLAIM_TYPES),
                "claim_amount_inr": random.randint(5000, 200000),
                "status": status,
                "claim_date": claim_date.strftime("%Y-%m-%d"),
            }
            claims.append(claim)
            policy_claims_map[pol["policy_id"]].append(claim)
            claim_counter += 1
    return claims, policy_claims_map


def compute_risk_signal(customer_id, cust_policy_map, policy_claims_map):
    """
    Ground-truth risk logic (hidden from the LLM at inference time).
    A customer is 'at risk' if they have a meaningful negative experience:
    a denied claim, a lapsed policy, or 2+ claims on one policy (friction).
    This is what your churn-risk skill SHOULD end up approximating from
    the unstructured+structured data, which is exactly the point.
    """
    policies = cust_policy_map.get(customer_id, [])
    has_lapsed = any(p["status"] == "Lapsed" for p in policies)
    denied_claims = 0
    high_friction = False
    for p in policies:
        claims = policy_claims_map.get(p["policy_id"], [])
        denied_claims += sum(1 for c in claims if c["status"] == "Denied")
        if len(claims) >= 2:
            high_friction = True

    risk_score = 0
    if has_lapsed:
        risk_score += 2
    risk_score += denied_claims
    if high_friction:
        risk_score += 1

    is_at_risk = risk_score >= 2
    return is_at_risk, risk_score


def build_transcript(sentiment, tenure_years):
    if sentiment == "negative":
        opener = random.choice(COMPLAINT_OPENERS).format(tenure=tenure_years)
    elif sentiment == "positive":
        opener = random.choice(POSITIVE_OPENERS)
    else:
        opener = random.choice(NEUTRAL_OPENERS)
    closing = random.choice(CLOSING_LINES)
    return f"Customer: {opener}\n{closing}"


def generate_interactions(customers, cust_policy_map, policy_claims_map):
    interactions = []
    ground_truth = []
    interaction_counter = 1

    for cust in customers:
        is_at_risk, risk_score = compute_risk_signal(
            cust["customer_id"], cust_policy_map, policy_claims_map
        )
        ground_truth.append(
            {
                "customer_id": cust["customer_id"],
                "is_at_risk": is_at_risk,
                "risk_score_internal": risk_score,
            }
        )

        num_calls = random.randint(1, 4)
        for _ in range(num_calls):
            # KEY FIX: sentiment probability is now driven by the actual
            # risk signal (claims/policy outcomes), not pure randomness.
            if is_at_risk:
                sentiment = random.choices(
                    ["negative", "neutral", "positive"], weights=[0.7, 0.22, 0.08]
                )[0]
            else:
                sentiment = random.choices(
                    ["negative", "neutral", "positive"], weights=[0.08, 0.42, 0.5]
                )[0]
            call_date = random_date(2025, 2026)
            interactions.append(
                {
                    "interaction_id": f"INT{interaction_counter:05d}",
                    "customer_id": cust["customer_id"],
                    "channel": random.choice(["Call Center", "Branch", "Email"]),
                    "sentiment": sentiment,
                    "interaction_date": call_date.strftime("%Y-%m-%d"),
                    "transcript": build_transcript(sentiment, cust["tenure_years"]),
                }
            )
            interaction_counter += 1

    return interactions, ground_truth


def write_csv(filename, rows, fieldnames):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path}")


def main():
    customers = generate_customers(NUM_CUSTOMERS)
    policies, cust_policy_map = generate_policies(customers)
    claims, policy_claims_map = generate_claims(policies)
    interactions, ground_truth = generate_interactions(
        customers, cust_policy_map, policy_claims_map
    )

    write_csv("customers.csv", customers, list(customers[0].keys()))
    write_csv("policies.csv", policies, list(policies[0].keys()))
    write_csv("claims.csv", claims, list(claims[0].keys()))
    write_csv("interactions.csv", interactions, list(interactions[0].keys()))
    write_csv("ground_truth.csv", ground_truth, list(ground_truth[0].keys()))

    at_risk_count = sum(1 for g in ground_truth if g["is_at_risk"])
    print(f"\n{at_risk_count}/{len(ground_truth)} customers ({at_risk_count/len(ground_truth)*100:.0f}%) are ground-truth at-risk")
    print("ground_truth.csv is for YOUR evaluation only - do not load it into the")
    print("table the LLM reads from. Use it after the fact to compute an accuracy")
    print("number for your Impact Statement slide (e.g. precision/recall of")
    print("your churn-risk skill against this ground truth).")
    print("\nLoad order for Snowflake (LLM-facing tables only):")
    print("customers -> policies -> claims -> interactions")


if __name__ == "__main__":
    main()
