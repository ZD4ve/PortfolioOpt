"""Ticker universe constants separated out for easier editing.

This module exports `RAW_TICKERS` as a list of ticker symbols (strings).
Suffixes are already hardcoded where needed (e.g. ".DE").
"""

US_TICKERS: list[str] = [
    "SXR8.DE",
    "ZPRR.DE",
]
ANTI_US_TICKERS: list[str] = [
    "LGQM.DE",
    "IUSC.DE",
    "LU1681045024",
    "IQQF.DE",
    "CEBL.DE",
    "LASP.DE",
    "XCS5.DE",
]
BRAVOS_TICKERS: list[str] = [
    "CCJ",
    "UEC",
    "NXE",
    "CEG",
    "VST",
    "MTZ",
    "EME",
    "FCX",
    "TECK",
    "BHP",
]

RAW_TICKERS: list[str] = US_TICKERS + ANTI_US_TICKERS + BRAVOS_TICKERS
