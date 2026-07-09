"""
Deterministic rules engine for violation detection.

LLM-only violation scanning hallucinates and misses precise numeric
thresholds. This engine runs explicit, testable checks (thresholds,
required-field presence, deadlines) and is treated as the authoritative
gate: an LLM-flagged issue that contradicts a rules-engine pass is
downgraded, never the reverse.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class RuleHit:
    rule_id: str
    description: str
    severity: str
    evidence: str


@dataclass
class Rule:
    rule_id: str
    description: str
    severity: str
    check: Callable[[dict], str | None]   # returns evidence string if violated, else None


class RulesEngine:
    def __init__(self):
        self.rules: list[Rule] = []

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def check(self, policy_facts: dict) -> list[RuleHit]:
        """
        `policy_facts` is a dict of extracted structured facts about a
        policy document, e.g. {"affiliate_transaction_pct": 12.5,
        "has_board_reporting": False, ...}. In production these facts
        come from a document-extraction step upstream.
        """
        hits = []
        for rule in self.rules:
            evidence = rule.check(policy_facts)
            if evidence:
                hits.append(RuleHit(
                    rule_id=rule.rule_id,
                    description=rule.description,
                    severity=rule.severity,
                    evidence=evidence,
                ))
        return hits


def default_rules() -> RulesEngine:
    """A starter rule set based on the sample regulations in fetch_sources.py."""
    engine = RulesEngine()

    engine.add_rule(Rule(
        rule_id="REG-W-SINGLE-AFFILIATE-LIMIT",
        description="Covered transactions with a single affiliate must not exceed 10% of capital and surplus",
        severity="critical",
        check=lambda facts: (
            f"single-affiliate exposure at {facts['affiliate_single_pct']}% exceeds the 10% limit"
            if facts.get("affiliate_single_pct", 0) > 10 else None
        ),
    ))

    engine.add_rule(Rule(
        rule_id="REG-W-ALL-AFFILIATES-LIMIT",
        description="Covered transactions with all affiliates combined must not exceed 20% of capital and surplus",
        severity="critical",
        check=lambda facts: (
            f"combined affiliate exposure at {facts['affiliate_combined_pct']}% exceeds the 20% limit"
            if facts.get("affiliate_combined_pct", 0) > 20 else None
        ),
    ))

    engine.add_rule(Rule(
        rule_id="BASEL-CET1-MINIMUM",
        description="Common Equity Tier 1 ratio must be at least 4.5% of risk-weighted assets",
        severity="critical",
        check=lambda facts: (
            f"CET1 ratio at {facts['cet1_ratio_pct']}% is below the 4.5% minimum"
            if facts.get("cet1_ratio_pct", 100) < 4.5 else None
        ),
    ))

    engine.add_rule(Rule(
        rule_id="BASEL-CAPITAL-CONSERVATION-BUFFER",
        description="An additional 2.5% capital conservation buffer must be maintained above minimums",
        severity="high",
        check=lambda facts: (
            f"capital conservation buffer at {facts['conservation_buffer_pct']}% is below the required 2.5%"
            if facts.get("conservation_buffer_pct", 100) < 2.5 else None
        ),
    ))

    engine.add_rule(Rule(
        rule_id="FCA-BOARD-REPORTING",
        description="Firms must report Consumer Duty outcomes to the board annually",
        severity="medium",
        check=lambda facts: (
            "no evidence of annual board reporting on Consumer Duty outcomes"
            if facts.get("has_annual_board_reporting") is False else None
        ),
    ))

    return engine
