"""
NorthStar CX - Accuracy Scoring

Runs churn_risk_score against every customer in the account, compares the
LLM's at-risk determination to the private ground_truth.csv labels, and
reports precision/recall/accuracy - for the Impact Statement slide.

ground_truth.csv is LOCAL ONLY. It is never loaded into Snowflake and the
LLM never sees it - this script is the only place it's used, purely to
measure how well the pipeline performs against known outcomes.

Run: python score_accuracy.py
"""

import csv
import os
import time

from skills.customer_360 import get_connection
from skills.churn_risk import churn_risk_score

GROUND_TRUTH_PATH = os.path.join(os.path.dirname(__file__), "data", "ground_truth.csv")


def load_ground_truth():
    with open(GROUND_TRUTH_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {r["customer_id"]: r["is_at_risk"] == "True" for r in rows}


def main():
    ground_truth = load_ground_truth()
    customer_ids = sorted(ground_truth.keys())

    conn = get_connection()

    true_positive = 0
    false_positive = 0
    true_negative = 0
    false_negative = 0
    errors = []

    print(f"Scoring {len(customer_ids)} customers against ground truth...\n")

    for i, cid in enumerate(customer_ids, start=1):
        try:
            result = churn_risk_score(cid, conn=conn)
            # Treat Medium or High as "predicted at-risk", Low as "predicted not at-risk"
            predicted_at_risk = result["risk_level"] in ("Medium", "High")
            actual_at_risk = ground_truth[cid]

            if predicted_at_risk and actual_at_risk:
                true_positive += 1
            elif predicted_at_risk and not actual_at_risk:
                false_positive += 1
            elif not predicted_at_risk and actual_at_risk:
                false_negative += 1
            else:
                true_negative += 1

            print(f"[{i}/{len(customer_ids)}] {cid}: predicted={result['risk_level']} "
                  f"({'at-risk' if predicted_at_risk else 'not at-risk'}), "
                  f"actual={'at-risk' if actual_at_risk else 'not at-risk'}")

        except Exception as e:
            errors.append((cid, str(e)))
            print(f"[{i}/{len(customer_ids)}] {cid}: ERROR - {e}")

    conn.close()

    total_scored = true_positive + false_positive + true_negative + false_negative
    accuracy = (true_positive + true_negative) / total_scored if total_scored else 0
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"Total customers scored: {total_scored}")
    print(f"True Positives (correctly flagged at-risk):     {true_positive}")
    print(f"False Positives (wrongly flagged at-risk):      {false_positive}")
    print(f"True Negatives (correctly cleared):             {true_negative}")
    print(f"False Negatives (missed a real at-risk case):   {false_negative}")
    print(f"\nAccuracy:  {accuracy:.1%}")
    print(f"Precision: {precision:.1%}")
    print(f"Recall:    {recall:.1%}")
    print(f"F1 Score:  {f1:.1%}")
    if errors:
        print(f"\n{len(errors)} customers errored out: {[e[0] for e in errors]}")


if __name__ == "__main__":
    main()
