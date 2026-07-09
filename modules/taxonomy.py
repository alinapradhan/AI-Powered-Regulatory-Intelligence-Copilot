"""
A small starter taxonomy of regulatory obligation categories used to
tag mappings between regulations and internal controls/policies.
Extend this list as new regulatory domains are onboarded.
"""

OBLIGATION_CATEGORIES = {
    "capital_adequacy": "Requirements around minimum capital ratios and buffers",
    "liquidity": "Requirements around liquid asset holdings and cash flow coverage",
    "affiliate_transactions": "Restrictions and limits on transactions with affiliates",
    "consumer_protection": "Requirements to ensure fair treatment and outcomes for customers",
    "disclosure": "Requirements to disclose information to customers or regulators",
    "reporting": "Periodic or event-driven reporting obligations to regulators",
    "governance": "Board and senior management oversight requirements",
    "risk_management": "Requirements around identifying, measuring, and mitigating risk",
}


def categorize_by_keywords(text: str) -> list[str]:
    """
    Naive keyword-based categorizer as a placeholder for a trained
    classifier. Good enough to demonstrate the mapping pipeline; swap
    for an LLM-based or fine-tuned classifier for production accuracy.
    """
    text_lower = text.lower()
    keyword_map = {
        "capital_adequacy": ["capital ratio", "tier 1", "risk-weighted", "capital stock"],
        "liquidity": ["liquidity", "liquid assets", "cash outflow"],
        "affiliate_transactions": ["affiliate", "23a", "23b"],
        "consumer_protection": ["consumer", "retail customer", "good outcomes", "fair"],
        "disclosure": ["disclose", "disclosure", "communicate"],
        "reporting": ["report to the board", "annual report", "regulator"],
        "governance": ["board", "senior management", "oversight"],
        "risk_management": ["risk management", "mitigate", "identify and measure"],
    }
    matches = []
    for category, keywords in keyword_map.items():
        if any(kw in text_lower for kw in keywords):
            matches.append(category)
    return matches or ["uncategorized"]
