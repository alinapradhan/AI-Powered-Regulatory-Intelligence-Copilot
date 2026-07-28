"""
Fetches raw regulatory text from external sources.

This is a stub with a clean interface: in production, each function
would call the actual regulator's API/RSS feed or scrape published
rule text (Federal Register, OCC bulletins, FCA handbook, ECB
guidelines, etc.). Swap the body of `fetch` with real HTTP calls;
everything downstream (chunker, embedder, vector store) is unaffected.
"""

from dataclasses import dataclass


@dataclass
class RawDocument:
    doc_id: str
    text: str
    jurisdiction: str
    regulator: str
    title: str
    effective_date: str | None = None
    source_url: str | None = None


class SourceFetcher:
    """
    In production: one method per regulator/source, each hitting the
    real feed and normalizing the response into a RawDocument.
    """

    def fetch_by_id(self, doc_id: str) -> RawDocument:
        """Stub lookup — replace with a real fetch (HTTP/API/DB)."""
        return self._sample_library().get(doc_id) or self._not_found(doc_id)

    def fetch_all_sample(self) -> list[RawDocument]:
        """Returns the built-in sample library, useful for demos/tests."""
        return list(self._sample_library().values())

    def _not_found(self, doc_id: str) -> RawDocument:
        return RawDocument(
            doc_id=doc_id, text="", jurisdiction="unknown", regulator="unknown",
            title="Not found",
        )

    def _sample_library(self) -> dict[str, RawDocument]:
        return {
            "reg-w-2024": RawDocument(
                doc_id="reg-w-2024",
                title="Regulation W - Transactions with Affiliates",
                jurisdiction="US-Fed",
                regulator="Federal Reserve",
                effective_date="2024-01-01",
                source_url="https://www.federalreserve.gov/regulation-w",
                text=(
                    "Section 1 (Purpose). This regulation implements sections 23A and 23B of the "
                    "Federal Reserve Act, governing transactions between a member bank and its affiliates.\n"
                    "Section 2 (Quantitative Limits). A bank's covered transactions with any single "
                    "affiliate may not exceed 10 percent of the bank's capital stock and surplus; "
                    "transactions with all affiliates combined may not exceed 20 percent.\n"
                    "Section 3 (Collateral Requirements). Covered credit transactions with an affiliate "
                    "must be secured by collateral with a market value ranging from 100 to 130 percent "
                    "of the transaction, depending on collateral type.\n"
                    "Section 4 (Market Terms). All transactions with affiliates must be on terms and "
                    "conditions consistent with safe and sound banking practices, and at least as "
                    "favorable to the bank as terms with a non-affiliate."
                ),
            ),
            "basel-iii-2023": RawDocument(
                doc_id="basel-iii-2023",
                title="Basel III: Capital Adequacy Framework",
                jurisdiction="Basel",
                regulator="Basel Committee on Banking Supervision",
                effective_date="2023-01-01",
                source_url="https://www.bis.org/basel_framework",
                text=(
                    "Section 1 (Minimum Capital Ratios). Banks must maintain a minimum Common Equity "
                    "Tier 1 ratio of 4.5%, Tier 1 capital ratio of 6%, and total capital ratio of 8% "
                    "of risk-weighted assets.\n"
                    "Section 2 (Capital Conservation Buffer). An additional buffer of 2.5% of "
                    "risk-weighted assets must be maintained in the form of Common Equity Tier 1 capital.\n"
                    "Section 3 (Liquidity Coverage Ratio). Banks must hold high-quality liquid assets "
                    "sufficient to cover total net cash outflows over a 30-day stress period.\n"
                    "Section 4 (Leverage Ratio). Banks must maintain a minimum leverage ratio of 3%, "
                    "calculated as Tier 1 capital divided by total exposure."
                ),
            ),
            "fca-consumer-duty-2023": RawDocument(
                doc_id="fca-consumer-duty-2023",
                title="FCA Consumer Duty",
                jurisdiction="UK-FCA",
                regulator="Financial Conduct Authority",
                effective_date="2023-07-31",
                source_url="https://www.fca.org.uk/firms/consumer-duty",
                text=(
                    "Section 1 (Consumer Principle). A firm must act to deliver good outcomes for "
                    "retail customers.\n"
                    "Section 2 (Cross-cutting Rules). Firms must act in good faith, avoid causing "
                    "foreseeable harm, and enable customers to pursue their financial objectives.\n"
                    "Section 3 (Four Outcomes). Firms must ensure: products and services are fit for "
                    "purpose, price and value are fair, communications support understanding, and "
                    "customer support meets customer needs.\n"
                    "Section 4 (Monitoring). Firms must monitor and evidence outcomes for retail "
                    "customers on an ongoing basis and report to the board annually."
                ),
            ),
        }
