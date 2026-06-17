"""Vehicle catalogue with country-specific market shares.

W8 Batch E.  Each EVAgent samples a vehicle from a country-specific
distribution and inherits the vehicle's battery chemistry and usable
capacity.  Chemistry then drives the aging coefficients in
`battery_aging.py`.

Market-share sources (rough 2024-25 figures):
  Israel: BYD 25%+, Tesla, MG, Jaecoo (Chinese-heavy market)
    Xinhua Jan 2025: Chinese OEMs ~69% of EV market; BYD top with 16,690
    units in 2024; Tesla 8,202; MG 6,276.
  United Kingdom: Tesla Model Y top with 32,862 registrations in 2024;
    Audi Q4 e-tron and Tesla Model 3 next; BMW i4 entered top 5.
    Reference: best-selling-cars.com / Mer 2024 / SMMT.
"""

# Catalogue of representative EV models in the IL + UK 2024-25 market.
# `battery_kwh` is the usable battery capacity (manufacturer specs).
# `chemistry` is the battery cathode chemistry (NMC or LFP).

VEHICLE_CATALOG = {
    # ---- Chinese OEMs (mostly LFP) ----
    "BYD Atto 3":           {"chemistry": "LFP", "battery_kwh": 60.0},
    "BYD Seal":             {"chemistry": "LFP", "battery_kwh": 82.0},
    "MG 4":                 {"chemistry": "LFP", "battery_kwh": 64.0},
    "Jaecoo 7":             {"chemistry": "LFP", "battery_kwh": 65.0},
    # ---- Tesla (mixed; SR LFP, LR NMC) ----
    "Tesla Model Y NMC":    {"chemistry": "NMC", "battery_kwh": 75.0},
    "Tesla Model Y LFP":    {"chemistry": "LFP", "battery_kwh": 60.0},
    "Tesla Model 3 LFP":    {"chemistry": "LFP", "battery_kwh": 60.0},
    # ---- Korean / Japanese OEMs (NMC) ----
    "Hyundai Ioniq 5":      {"chemistry": "NMC", "battery_kwh": 77.0},
    "Hyundai Kona":         {"chemistry": "NMC", "battery_kwh": 65.0},
    "Kia EV6":              {"chemistry": "NMC", "battery_kwh": 77.0},
    # ---- European OEMs (NMC) ----
    "VW ID.4":              {"chemistry": "NMC", "battery_kwh": 77.0},
    "VW ID.3":              {"chemistry": "NMC", "battery_kwh": 58.0},
    "Audi Q4 e-tron":       {"chemistry": "NMC", "battery_kwh": 82.0},
    "BMW i4":               {"chemistry": "NMC", "battery_kwh": 80.0},
    "BMW iX1":              {"chemistry": "NMC", "battery_kwh": 64.0},
    "Volvo EX30":           {"chemistry": "NMC", "battery_kwh": 64.0},
}

# Country-specific market shares (2024-25 weighted estimates).
# Both dictionaries must sum to ~1.0; tiny rounding is acceptable.

MARKET_SHARES_ISRAEL = {
    "BYD Atto 3":           0.20,
    "Jaecoo 7":             0.18,
    "MG 4":                 0.12,
    "Tesla Model Y NMC":    0.08,
    "Tesla Model Y LFP":    0.06,
    "Tesla Model 3 LFP":    0.05,
    "BYD Seal":             0.05,
    "Hyundai Ioniq 5":      0.06,
    "Hyundai Kona":         0.04,
    "VW ID.4":              0.05,
    "VW ID.3":              0.03,
    "Audi Q4 e-tron":       0.03,
    "BMW i4":               0.02,
    "Kia EV6":              0.02,
    "BMW iX1":              0.01,
}

MARKET_SHARES_UK = {
    "Tesla Model Y NMC":    0.20,
    "Tesla Model Y LFP":    0.08,
    "Audi Q4 e-tron":       0.13,
    "Tesla Model 3 LFP":    0.10,
    "MG 4":                 0.07,
    "BMW i4":               0.06,
    "Hyundai Ioniq 5":      0.06,
    "Kia EV6":              0.05,
    "VW ID.4":              0.05,
    "Hyundai Kona":         0.05,
    "Volvo EX30":           0.04,
    "BMW iX1":              0.04,
    "BYD Atto 3":           0.02,
    "VW ID.3":              0.03,
    "Jaecoo 7":             0.01,
    "BYD Seal":             0.01,
}

COUNTRY_MARKET_SHARES = {
    "Israel":          MARKET_SHARES_ISRAEL,
    "United Kingdom":  MARKET_SHARES_UK,
    "UK":              MARKET_SHARES_UK,   # short alias
}


def sample_vehicle(rng, country: str = "Israel") -> str:
    """Pick a vehicle model from the country's market-share distribution."""
    shares = COUNTRY_MARKET_SHARES[country]
    names = list(shares.keys())
    weights = list(shares.values())
    return rng.choices(names, weights=weights, k=1)[0]


def chemistry_share_per_country() -> dict:
    """Compute aggregate LFP vs NMC share per country, for diagnostics."""
    out = {}
    for country, shares in COUNTRY_MARKET_SHARES.items():
        lfp = sum(s for v, s in shares.items() if VEHICLE_CATALOG[v]["chemistry"] == "LFP")
        nmc = sum(s for v, s in shares.items() if VEHICLE_CATALOG[v]["chemistry"] == "NMC")
        out[country] = {"LFP": lfp, "NMC": nmc}
    return out
