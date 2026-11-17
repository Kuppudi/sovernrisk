"""Units are explicitly curated; definitions and names are retrieved from the provider."""

INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": {"category": "Economic", "unit": "% annual growth"},
    "NY.GDP.PCAP.CD": {"category": "Economic", "unit": "current US$ per person"},
    "FP.CPI.TOTL.ZG": {"category": "Economic", "unit": "% annual change"},
    "NE.EXP.GNFS.ZS": {"category": "External", "unit": "% of GDP"},
    "NE.IMP.GNFS.ZS": {"category": "External", "unit": "% of GDP"},
    "BN.CAB.XOKA.GD.ZS": {"category": "External", "unit": "% of GDP"},
}

GLOBAL_INDICATORS = {
    **INDICATORS,
    "FI.RES.TOTL.MO": {"category": "External", "unit": "months of imports"},
    "DT.TDS.DECT.EX.ZS": {"category": "External debt", "unit": "% of exports"},
    "DT.DOD.DECT.GN.ZS": {"category": "External debt", "unit": "% of GNI"},
}

# The dashboard also shows total GDP. Keep the research model's feature schema stable.
WORLD_BANK_INDICATORS = {
    "NY.GDP.MKTP.CD": {"category": "Economic", "unit": "current US$"},
    **GLOBAL_INDICATORS,
}
