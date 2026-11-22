"""Company-name standardization for the CER medallion pipeline.

The same legal entity is sometimes written in more than one way in the CER data (for example
a stray comma, "Ltd." versus "Limited", or an added "carrying on business as ..." phrase).
Splitting one company across several names makes it look smaller than it is.

The rules here are deliberately conservative: an explicit, reviewable alias map, not fuzzy
matching. Distinct legal entities (for example "Trans Mountain Pipeline Inc." and
"Trans Mountain Pipeline ULC", or a general partner acting for a limited partnership) are
NOT merged. The same map is copied into notebook 02 so it runs on Databricks without
installing this package.
"""

COMPANY_ALIASES = {
    "NGTL GP Ltd., as general partner, on behalf of NGTL Limited Partnership":
        "NGTL GP Ltd., as general partner on behalf of NGTL Limited Partnership",
    "Westcoast Energy Inc., carrying on business as Spectra Energy Transmission":
        "Westcoast Energy Inc.",
    "Alliance Pipeline Ltd., as General Partner for and on behalf of Alliance Pipeline Limited Partnership":
        "Alliance Pipeline Ltd.",
    "Minell Pipeline Limited":
        "Minell Pipeline Ltd.",
    "TransCanada PipeLines Limited B.C. System":
        "TransCanada PipeLines Limited",
}


def clean_company(name):
    """Collapse repeated whitespace, then apply the alias map. None stays None."""
    if name is None:
        return None
    collapsed = " ".join(str(name).split())
    return COMPANY_ALIASES.get(collapsed, collapsed)