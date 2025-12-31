"""
Enhanced Recurring Transaction Classifier

Based on industry best practices from:
- Plaid's Personal Finance Category (PFC) taxonomy
- Belvo's categorization approach
- User feedback and real-world transaction patterns

Primary Categories (aligned with Plaid):
- LOAN_PAYMENTS: All debt repayments (mortgage, auto, student, personal, credit card, BNPL)
- RENT_AND_UTILITIES: Housing costs and utility bills
- SUBSCRIPTIONS: Discretionary recurring services
- INCOME: Recurring income (paycheck, dividends, etc.)
- TRANSFERS: Internal/external transfers

Key distinction:
- Loans/Bills = Essential (must pay)
- Subscriptions = Discretionary (can cancel)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class RecurringCategory(Enum):
    """Primary categories aligned with Plaid's PFC taxonomy."""
    LOAN_PAYMENTS = "loan_payments"
    RENT_AND_UTILITIES = "rent_and_utilities"
    SUBSCRIPTIONS = "subscriptions"
    INSURANCE = "insurance"
    INCOME = "income"
    TRANSFERS = "transfers"
    UNKNOWN = "unknown"


class LoanSubcategory(Enum):
    """Loan payment subcategories."""
    MORTGAGE = "mortgage"
    AUTO_LOAN = "auto_loan"
    STUDENT_LOAN = "student_loan"
    PERSONAL_LOAN = "personal_loan"
    CREDIT_CARD = "credit_card"
    BNPL = "bnpl"  # Buy Now Pay Later
    OTHER_LOAN = "other_loan"


class UtilitySubcategory(Enum):
    """Rent and utilities subcategories."""
    RENT = "rent"
    ELECTRIC = "electric"
    GAS = "gas"
    WATER = "water"
    SEWAGE = "sewage"
    TRASH = "trash"
    INTERNET = "internet"
    CABLE = "cable"
    PHONE = "phone"
    OTHER_UTILITY = "other_utility"


class SubscriptionSubcategory(Enum):
    """Subscription subcategories."""
    STREAMING_VIDEO = "streaming_video"
    STREAMING_MUSIC = "streaming_music"
    CLOUD_STORAGE = "cloud_storage"
    SOFTWARE = "software"
    AI_SERVICES = "ai_services"
    GAMING = "gaming"
    FITNESS = "fitness"
    WELLNESS = "wellness"
    NEWS_MEDIA = "news_media"
    CREATOR_PLATFORMS = "creator_platforms"
    MEMBERSHIP = "membership"
    IDENTITY_PROTECTION = "identity_protection"
    FINTECH = "fintech"
    EDUCATION = "education"
    PET_SERVICES = "pet_services"
    OTHER_SUBSCRIPTION = "other_subscription"


class InsuranceSubcategory(Enum):
    """Insurance subcategories."""
    AUTO = "auto"
    HOME = "home"
    RENTERS = "renters"
    LIFE = "life"
    HEALTH = "health"
    PET = "pet"
    OTHER_INSURANCE = "other_insurance"


@dataclass
class ClassificationResult:
    """Result of recurring transaction classification."""
    category: RecurringCategory
    subcategory: Optional[str]
    merchant_name: Optional[str]
    is_essential: bool
    confidence: float
    match_type: str  # pattern, amount, fallback


# =============================================================================
# PATTERN DEFINITIONS
# Organized by category with (pattern, subcategory, clean_name, is_essential, confidence)
# =============================================================================

LOAN_PATTERNS: Dict[str, Tuple[str, str, bool, float]] = {
    # -------------------------------------------------------------------------
    # MORTGAGE (Essential - housing)
    # -------------------------------------------------------------------------
    r"carrington\s*(mortgage|mtg|s)?": (LoanSubcategory.MORTGAGE.value, "Carrington Mortgage", True, 0.95),
    r"rocket\s*(mortgage|homes)": (LoanSubcategory.MORTGAGE.value, "Rocket Mortgage", True, 0.95),
    r"quicken\s*loans?": (LoanSubcategory.MORTGAGE.value, "Quicken Loans", True, 0.95),
    r"wells\s*fargo\s*(home|mort)": (LoanSubcategory.MORTGAGE.value, "Wells Fargo Home", True, 0.95),
    r"chase\s*(home|mort)": (LoanSubcategory.MORTGAGE.value, "Chase Mortgage", True, 0.95),
    r"bank\s*of\s*america\s*(mort|home)": (LoanSubcategory.MORTGAGE.value, "Bank of America Mortgage", True, 0.95),
    r"nationstar|mr\.?\s*cooper": (LoanSubcategory.MORTGAGE.value, "Mr. Cooper", True, 0.95),
    r"pennymac": (LoanSubcategory.MORTGAGE.value, "PennyMac", True, 0.95),
    r"freedom\s*mortgage": (LoanSubcategory.MORTGAGE.value, "Freedom Mortgage", True, 0.95),
    r"loancare": (LoanSubcategory.MORTGAGE.value, "LoanCare", True, 0.95),
    r"newrez|shellpoint": (LoanSubcategory.MORTGAGE.value, "NewRez", True, 0.95),
    r"phh\s*mortgage": (LoanSubcategory.MORTGAGE.value, "PHH Mortgage", True, 0.95),
    r"flagstar\s*(bank|mort)": (LoanSubcategory.MORTGAGE.value, "Flagstar", True, 0.95),
    r"guild\s*mortgage": (LoanSubcategory.MORTGAGE.value, "Guild Mortgage", True, 0.95),
    r"caliber\s*home": (LoanSubcategory.MORTGAGE.value, "Caliber Home Loans", True, 0.95),
    r"usaa\s*(mort|home)": (LoanSubcategory.MORTGAGE.value, "USAA Mortgage", True, 0.95),
    r"navy\s*federal.*(mort|home)": (LoanSubcategory.MORTGAGE.value, "Navy Federal Mortgage", True, 0.95),
    r"escrow\s*(payment|pymt)?": (LoanSubcategory.MORTGAGE.value, "Escrow Payment", True, 0.90),

    # -------------------------------------------------------------------------
    # AUTO LOANS (Essential - transportation)
    # -------------------------------------------------------------------------
    r"ally\s*(auto|bank|financial)?(?!\s*ins)": (LoanSubcategory.AUTO_LOAN.value, "Ally Auto", True, 0.95),
    r"toyota\s*(financial|motor\s*credit)": (LoanSubcategory.AUTO_LOAN.value, "Toyota Financial", True, 0.95),
    r"honda\s*financial": (LoanSubcategory.AUTO_LOAN.value, "Honda Financial", True, 0.95),
    r"capital\s*one\s*auto": (LoanSubcategory.AUTO_LOAN.value, "Capital One Auto", True, 0.95),
    r"santander\s*(consumer|auto)?": (LoanSubcategory.AUTO_LOAN.value, "Santander", True, 0.95),
    r"carmax\s*(auto)?": (LoanSubcategory.AUTO_LOAN.value, "CarMax Auto Finance", True, 0.95),
    r"ford\s*(motor\s*)?credit": (LoanSubcategory.AUTO_LOAN.value, "Ford Credit", True, 0.95),
    r"gm\s*financial": (LoanSubcategory.AUTO_LOAN.value, "GM Financial", True, 0.95),
    r"bmw\s*financial": (LoanSubcategory.AUTO_LOAN.value, "BMW Financial", True, 0.95),
    r"mercedes[\s-]*benz\s*financial": (LoanSubcategory.AUTO_LOAN.value, "Mercedes-Benz Financial", True, 0.95),
    r"nissan\s*motor\s*accept": (LoanSubcategory.AUTO_LOAN.value, "Nissan Motor Acceptance", True, 0.95),
    r"hyundai\s*(capital|motor\s*fin)": (LoanSubcategory.AUTO_LOAN.value, "Hyundai Capital", True, 0.95),
    r"kia\s*(motors\s*)?finance": (LoanSubcategory.AUTO_LOAN.value, "Kia Finance", True, 0.95),
    r"chrysler\s*capital": (LoanSubcategory.AUTO_LOAN.value, "Chrysler Capital", True, 0.95),
    r"westlake\s*financial": (LoanSubcategory.AUTO_LOAN.value, "Westlake Financial", True, 0.95),
    r"roadrunner\s*fina": (LoanSubcategory.AUTO_LOAN.value, "Roadrunner Financial", True, 0.95),
    r"americredit|gm\s*financial": (LoanSubcategory.AUTO_LOAN.value, "AmeriCredit", True, 0.95),
    r"exeter\s*finance": (LoanSubcategory.AUTO_LOAN.value, "Exeter Finance", True, 0.95),
    r"world\s*omni\s*financial": (LoanSubcategory.AUTO_LOAN.value, "World Omni", True, 0.95),
    r"chase\s*auto": (LoanSubcategory.AUTO_LOAN.value, "Chase Auto", True, 0.95),
    r"usaa\s*auto\s*(loan|fin)": (LoanSubcategory.AUTO_LOAN.value, "USAA Auto", True, 0.95),
    r"pnc\s*auto": (LoanSubcategory.AUTO_LOAN.value, "PNC Auto", True, 0.95),

    # -------------------------------------------------------------------------
    # STUDENT LOANS (Essential - education debt)
    # -------------------------------------------------------------------------
    r"navient": (LoanSubcategory.STUDENT_LOAN.value, "Navient", True, 0.95),
    r"nelnet": (LoanSubcategory.STUDENT_LOAN.value, "Nelnet", True, 0.95),
    r"fed\s*loan|fedloan": (LoanSubcategory.STUDENT_LOAN.value, "FedLoan", True, 0.95),
    r"great\s*lakes\s*(edu)?": (LoanSubcategory.STUDENT_LOAN.value, "Great Lakes", True, 0.95),
    r"mohela": (LoanSubcategory.STUDENT_LOAN.value, "MOHELA", True, 0.95),
    r"aidvantage": (LoanSubcategory.STUDENT_LOAN.value, "Aidvantage", True, 0.95),
    r"sallie\s*mae": (LoanSubcategory.STUDENT_LOAN.value, "Sallie Mae", True, 0.95),
    r"dept\.?\s*of\s*ed|education\s*dep": (LoanSubcategory.STUDENT_LOAN.value, "Dept of Education", True, 0.95),
    r"sofi\s*student": (LoanSubcategory.STUDENT_LOAN.value, "SoFi Student Loans", True, 0.95),
    r"earnest\s*(student)?": (LoanSubcategory.STUDENT_LOAN.value, "Earnest", True, 0.95),
    r"college\s*ave": (LoanSubcategory.STUDENT_LOAN.value, "College Ave", True, 0.95),
    r"commonbond": (LoanSubcategory.STUDENT_LOAN.value, "CommonBond", True, 0.95),

    # -------------------------------------------------------------------------
    # PERSONAL LOANS (Essential - debt obligation)
    # -------------------------------------------------------------------------
    r"sofi(?!\s*student)": (LoanSubcategory.PERSONAL_LOAN.value, "SoFi", True, 0.90),
    r"lending\s*club": (LoanSubcategory.PERSONAL_LOAN.value, "LendingClub", True, 0.95),
    r"prosper\s*(marketplace)?": (LoanSubcategory.PERSONAL_LOAN.value, "Prosper", True, 0.95),
    r"upstart": (LoanSubcategory.PERSONAL_LOAN.value, "Upstart", True, 0.95),
    r"marcus\s*(by\s*gs|goldman)?": (LoanSubcategory.PERSONAL_LOAN.value, "Marcus", True, 0.95),
    r"avant\s*(llc)?": (LoanSubcategory.PERSONAL_LOAN.value, "Avant", True, 0.95),
    r"best\s*egg": (LoanSubcategory.PERSONAL_LOAN.value, "Best Egg", True, 0.95),
    r"lightstream": (LoanSubcategory.PERSONAL_LOAN.value, "LightStream", True, 0.95),
    r"upgrade\s*(inc)?": (LoanSubcategory.PERSONAL_LOAN.value, "Upgrade", True, 0.95),
    r"payoff": (LoanSubcategory.PERSONAL_LOAN.value, "Payoff", True, 0.95),
    r"achieve\s*(personal)?": (LoanSubcategory.PERSONAL_LOAN.value, "Achieve", True, 0.95),
    r"happy\s*money|payoff": (LoanSubcategory.PERSONAL_LOAN.value, "Happy Money", True, 0.95),
    r"oportun": (LoanSubcategory.PERSONAL_LOAN.value, "Oportun", True, 0.95),

    # -------------------------------------------------------------------------
    # CREDIT CARD PAYMENTS (Essential - avoid interest)
    # Patterns match both explicit card references AND ACH-style "issuer + name + co"
    # -------------------------------------------------------------------------
    # Chase - match card/pymt/bank OR ACH pattern (name + co), exclude auto/home/mort loans
    r"chase\s*(card|pymt|payment|bank)(?!\s*auto)(?!\s*home)(?!\s*mort)": (LoanSubcategory.CREDIT_CARD.value, "Chase Card", True, 0.90),
    r"chase\s+\w+\s+co\b(?!.*(?:auto|home|mort))": (LoanSubcategory.CREDIT_CARD.value, "Chase Card", True, 0.85),
    # Amex - broad match
    r"amex|american\s*express": (LoanSubcategory.CREDIT_CARD.value, "American Express", True, 0.95),
    # Capital One - exclude auto loans
    r"capital\s*one(?!\s*auto)": (LoanSubcategory.CREDIT_CARD.value, "Capital One", True, 0.90),
    # Citi - match card/bank/pymt OR ACH pattern, exclude mortgage/group
    r"citi\s*(card|bank|pymt|payment)": (LoanSubcategory.CREDIT_CARD.value, "Citi Card", True, 0.90),
    r"citi\s+\w+\s+co\b(?!.*(?:group|mortgage|realty))": (LoanSubcategory.CREDIT_CARD.value, "Citi Card", True, 0.85),
    # Discover
    r"discover\s*(card|financial|bank)?(?!\s*student)": (LoanSubcategory.CREDIT_CARD.value, "Discover", True, 0.90),
    # Wells Fargo
    r"wells\s*fargo\s*(card|pymt|\w+\s+co)": (LoanSubcategory.CREDIT_CARD.value, "Wells Fargo Card", True, 0.90),
    # Bank of America
    r"bank\s*of\s*america\s*(card|pymt)": (LoanSubcategory.CREDIT_CARD.value, "Bank of America Card", True, 0.95),
    r"bofa\s*(card|pymt|\w+\s+co)": (LoanSubcategory.CREDIT_CARD.value, "Bank of America Card", True, 0.90),
    # Credit unions and other issuers
    r"usaa\s*(card|pymt|\w+\s+co)": (LoanSubcategory.CREDIT_CARD.value, "USAA Card", True, 0.90),
    r"navy\s*federal\s*(card|pymt|\w+\s+co)": (LoanSubcategory.CREDIT_CARD.value, "Navy Federal Card", True, 0.90),
    r"synchrony\s*(bank|financial)?": (LoanSubcategory.CREDIT_CARD.value, "Synchrony", True, 0.90),
    r"barclays?\s*(card|bank|pymt|\w+\s+co)?": (LoanSubcategory.CREDIT_CARD.value, "Barclays", True, 0.85),
    r"apple\s*card": (LoanSubcategory.CREDIT_CARD.value, "Apple Card", True, 0.95),
    r"td\s*bank\s*(card|pymt)": (LoanSubcategory.CREDIT_CARD.value, "TD Bank Card", True, 0.95),
    r"pnc\s*(card|pymt|\w+\s+co)": (LoanSubcategory.CREDIT_CARD.value, "PNC Card", True, 0.90),
    r"us\s*bank\s*(card|pymt)": (LoanSubcategory.CREDIT_CARD.value, "US Bank Card", True, 0.95),

    # -------------------------------------------------------------------------
    # BUY NOW PAY LATER (Discretionary - short-term financing)
    # -------------------------------------------------------------------------
    r"affirm": (LoanSubcategory.BNPL.value, "Affirm", False, 0.95),
    r"best\s*buy\s*(pymt|payment|financing)": (LoanSubcategory.BNPL.value, "Best Buy Financing", False, 0.90),
    r"klarna": (LoanSubcategory.BNPL.value, "Klarna", False, 0.95),
    r"afterpay": (LoanSubcategory.BNPL.value, "Afterpay", False, 0.95),
    r"sezzle": (LoanSubcategory.BNPL.value, "Sezzle", False, 0.95),
    r"zip\s*(pay|money)": (LoanSubcategory.BNPL.value, "Zip", False, 0.95),
    r"quadpay|zip": (LoanSubcategory.BNPL.value, "QuadPay", False, 0.95),
    r"splitit": (LoanSubcategory.BNPL.value, "Splitit", False, 0.95),
    r"bread\s*(pay|financial)?": (LoanSubcategory.BNPL.value, "Bread Pay", False, 0.95),
}

UTILITY_PATTERNS: Dict[str, Tuple[str, str, bool, float]] = {
    # -------------------------------------------------------------------------
    # RENT (Essential - housing)
    # -------------------------------------------------------------------------
    r"rent\s*(payment|pymt)": (UtilitySubcategory.RENT.value, "Rent Payment", True, 0.90),
    r"zillow\s*rent": (UtilitySubcategory.RENT.value, "Zillow Rent", True, 0.95),
    r"apartments\.?com": (UtilitySubcategory.RENT.value, "Apartments.com", True, 0.95),
    r"cozy\s*(rent)?": (UtilitySubcategory.RENT.value, "Cozy", True, 0.95),
    r"rentpayment": (UtilitySubcategory.RENT.value, "RentPayment", True, 0.95),
    r"avail\s*(rent)?": (UtilitySubcategory.RENT.value, "Avail", True, 0.95),

    # -------------------------------------------------------------------------
    # ELECTRIC (Essential - utility)
    # -------------------------------------------------------------------------
    r"duke\s*energy|dukeenergycorpor": (UtilitySubcategory.ELECTRIC.value, "Duke Energy", True, 0.95),
    r"dominion\s*(energy)?": (UtilitySubcategory.ELECTRIC.value, "Dominion Energy", True, 0.95),
    r"pg&?e|pacific\s*gas": (UtilitySubcategory.ELECTRIC.value, "PG&E", True, 0.95),
    r"con\s*ed(ison)?": (UtilitySubcategory.ELECTRIC.value, "Con Edison", True, 0.95),
    r"fpl|florida\s*power": (UtilitySubcategory.ELECTRIC.value, "FPL", True, 0.95),
    r"sce|socal\s*edison|southern\s*calif.*edison": (UtilitySubcategory.ELECTRIC.value, "SCE", True, 0.95),
    r"xcel\s*energy": (UtilitySubcategory.ELECTRIC.value, "Xcel Energy", True, 0.95),
    r"aps|arizona\s*public\s*service": (UtilitySubcategory.ELECTRIC.value, "APS", True, 0.95),
    r"pseg|public\s*service\s*electric": (UtilitySubcategory.ELECTRIC.value, "PSEG", True, 0.95),
    r"dte\s*energy": (UtilitySubcategory.ELECTRIC.value, "DTE Energy", True, 0.95),
    r"entergy": (UtilitySubcategory.ELECTRIC.value, "Entergy", True, 0.95),
    r"georgia\s*power": (UtilitySubcategory.ELECTRIC.value, "Georgia Power", True, 0.95),
    r"southern\s*company": (UtilitySubcategory.ELECTRIC.value, "Southern Company", True, 0.95),
    r"ameren": (UtilitySubcategory.ELECTRIC.value, "Ameren", True, 0.95),
    r"consumers\s*energy": (UtilitySubcategory.ELECTRIC.value, "Consumers Energy", True, 0.95),
    r"eversource": (UtilitySubcategory.ELECTRIC.value, "Eversource", True, 0.95),
    r"firstenergy": (UtilitySubcategory.ELECTRIC.value, "FirstEnergy", True, 0.95),
    r"oncor": (UtilitySubcategory.ELECTRIC.value, "Oncor", True, 0.95),
    r"rocky\s*mountain\s*power": (UtilitySubcategory.ELECTRIC.value, "Rocky Mountain Power", True, 0.95),
    r"peco\s*(energy)?": (UtilitySubcategory.ELECTRIC.value, "PECO", True, 0.95),
    r"nv\s*energy": (UtilitySubcategory.ELECTRIC.value, "NV Energy", True, 0.95),
    r"city\s*(of\s*)?.*\s*electric": (UtilitySubcategory.ELECTRIC.value, None, True, 0.85),

    # -------------------------------------------------------------------------
    # GAS (Essential - utility)
    # -------------------------------------------------------------------------
    r"national\s*grid": (UtilitySubcategory.GAS.value, "National Grid", True, 0.95),
    r"atmos\s*energy": (UtilitySubcategory.GAS.value, "Atmos Energy", True, 0.95),
    r"centerpoint\s*(energy)?": (UtilitySubcategory.GAS.value, "CenterPoint Energy", True, 0.95),
    r"nicor\s*gas": (UtilitySubcategory.GAS.value, "Nicor Gas", True, 0.95),
    r"spire\s*(energy)?": (UtilitySubcategory.GAS.value, "Spire", True, 0.95),
    r"southwest\s*gas": (UtilitySubcategory.GAS.value, "Southwest Gas", True, 0.95),
    r"piedmont\s*natural\s*gas": (UtilitySubcategory.GAS.value, "Piedmont Natural Gas", True, 0.95),
    r"peoples\s*gas": (UtilitySubcategory.GAS.value, "Peoples Gas", True, 0.95),
    r"washington\s*gas": (UtilitySubcategory.GAS.value, "Washington Gas", True, 0.95),

    # -------------------------------------------------------------------------
    # WATER (Essential - utility)
    # -------------------------------------------------------------------------
    r"city\s*of.*water": (UtilitySubcategory.WATER.value, None, True, 0.85),
    r"water\s*(dept|department|utility|district)": (UtilitySubcategory.WATER.value, None, True, 0.85),
    r"municipal\s*water": (UtilitySubcategory.WATER.value, None, True, 0.85),
    r"american\s*water": (UtilitySubcategory.WATER.value, "American Water", True, 0.95),
    r"aqua\s*(america|water)": (UtilitySubcategory.WATER.value, "Aqua America", True, 0.95),

    # -------------------------------------------------------------------------
    # SEWAGE/TRASH (Essential - utility)
    # -------------------------------------------------------------------------
    r"sewer": (UtilitySubcategory.SEWAGE.value, None, True, 0.85),
    r"waste\s*management": (UtilitySubcategory.TRASH.value, "Waste Management", True, 0.95),
    r"republic\s*services": (UtilitySubcategory.TRASH.value, "Republic Services", True, 0.95),
    r"waste\s*connections": (UtilitySubcategory.TRASH.value, "Waste Connections", True, 0.95),

    # -------------------------------------------------------------------------
    # INTERNET (Essential in modern life)
    # -------------------------------------------------------------------------
    r"spectrum": (UtilitySubcategory.INTERNET.value, "Spectrum", True, 0.95),
    r"comcast|xfinity": (UtilitySubcategory.INTERNET.value, "Xfinity", True, 0.95),
    r"google\s*\*?\s*fiber": (UtilitySubcategory.INTERNET.value, "Google Fiber", True, 0.95),
    r"cox\s*(comm|cable|internet)": (UtilitySubcategory.INTERNET.value, "Cox", True, 0.95),
    r"frontier\s*(comm)?": (UtilitySubcategory.INTERNET.value, "Frontier", True, 0.95),
    r"centurylink|lumen": (UtilitySubcategory.INTERNET.value, "Lumen", True, 0.95),
    r"optimum|altice": (UtilitySubcategory.INTERNET.value, "Optimum", True, 0.95),
    r"mediacom": (UtilitySubcategory.INTERNET.value, "Mediacom", True, 0.95),
    r"windstream": (UtilitySubcategory.INTERNET.value, "Windstream", True, 0.95),
    r"att\s*(internet|uverse|fiber)": (UtilitySubcategory.INTERNET.value, "AT&T Internet", True, 0.95),
    r"verizon\s*fios": (UtilitySubcategory.INTERNET.value, "Verizon Fios", True, 0.95),
    r"starlink": (UtilitySubcategory.INTERNET.value, "Starlink", True, 0.95),
    r"hughesnet": (UtilitySubcategory.INTERNET.value, "HughesNet", True, 0.95),
    r"earthlink": (UtilitySubcategory.INTERNET.value, "EarthLink", True, 0.95),

    # -------------------------------------------------------------------------
    # PHONE (Essential for many)
    # -------------------------------------------------------------------------
    r"at&?t(?!\s*internet|\s*fiber|\s*uverse)|att\s+mobility": (UtilitySubcategory.PHONE.value, "AT&T Wireless", True, 0.90),
    r"verizon\s*wireless": (UtilitySubcategory.PHONE.value, "Verizon Wireless", True, 0.95),
    r"t-?\s*mobile": (UtilitySubcategory.PHONE.value, "T-Mobile", True, 0.95),
    r"google\s*\*?\s*fi\b": (UtilitySubcategory.PHONE.value, "Google Fi", True, 0.95),
    r"sprint": (UtilitySubcategory.PHONE.value, "Sprint", True, 0.95),
    r"us\s*cellular": (UtilitySubcategory.PHONE.value, "US Cellular", True, 0.95),
    r"visible\s*(wireless)?": (UtilitySubcategory.PHONE.value, "Visible", True, 0.95),
    r"mint\s*mobile": (UtilitySubcategory.PHONE.value, "Mint Mobile", True, 0.95),
    r"cricket\s*wireless": (UtilitySubcategory.PHONE.value, "Cricket", True, 0.95),
    r"metro\s*by\s*t-?mobile|metropcs": (UtilitySubcategory.PHONE.value, "Metro by T-Mobile", True, 0.95),
    r"boost\s*mobile": (UtilitySubcategory.PHONE.value, "Boost Mobile", True, 0.95),

    # -------------------------------------------------------------------------
    # HOME SERVICES (Essential for many)
    # -------------------------------------------------------------------------
    r"pest\s*(control|pros?|mgmt)": (UtilitySubcategory.OTHER_UTILITY.value, None, True, 0.85),
    r"solve\s*pest": (UtilitySubcategory.OTHER_UTILITY.value, "Solve Pest Pros", True, 0.95),
    r"orkin": (UtilitySubcategory.OTHER_UTILITY.value, "Orkin", True, 0.95),
    r"terminix": (UtilitySubcategory.OTHER_UTILITY.value, "Terminix", True, 0.95),
    r"rentokil": (UtilitySubcategory.OTHER_UTILITY.value, "Rentokil", True, 0.95),
    r"trugreen": (UtilitySubcategory.OTHER_UTILITY.value, "TruGreen", True, 0.95),
    r"lawn\s*(care|service|doctor)": (UtilitySubcategory.OTHER_UTILITY.value, None, True, 0.85),
    r"hoa\s*(fee|dues)?": (UtilitySubcategory.OTHER_UTILITY.value, "HOA", True, 0.95),
    r"homeowners\s*assoc": (UtilitySubcategory.OTHER_UTILITY.value, "HOA", True, 0.95),
}

INSURANCE_PATTERNS: Dict[str, Tuple[str, str, bool, float]] = {
    # -------------------------------------------------------------------------
    # AUTO INSURANCE (Essential)
    # -------------------------------------------------------------------------
    r"geico": (InsuranceSubcategory.AUTO.value, "GEICO", True, 0.95),
    r"progressive(?!\s*leasing)": (InsuranceSubcategory.AUTO.value, "Progressive", True, 0.95),
    r"state\s*farm": (InsuranceSubcategory.AUTO.value, "State Farm", True, 0.95),
    r"allstate(?!\s*protect)": (InsuranceSubcategory.AUTO.value, "Allstate", True, 0.95),
    r"farmers\s*(ins|insurance)": (InsuranceSubcategory.AUTO.value, "Farmers", True, 0.95),
    r"liberty\s*mutual": (InsuranceSubcategory.AUTO.value, "Liberty Mutual", True, 0.95),
    r"usaa\s*ins": (InsuranceSubcategory.AUTO.value, "USAA Insurance", True, 0.95),
    r"nationwide\s*(ins)?": (InsuranceSubcategory.AUTO.value, "Nationwide", True, 0.95),
    r"amica": (InsuranceSubcategory.AUTO.value, "Amica", True, 0.95),
    r"travelers\s*(ins)?": (InsuranceSubcategory.AUTO.value, "Travelers", True, 0.95),
    r"esurance": (InsuranceSubcategory.AUTO.value, "Esurance", True, 0.95),
    r"the\s*general\s*ins": (InsuranceSubcategory.AUTO.value, "The General", True, 0.95),
    r"root\s*ins": (InsuranceSubcategory.AUTO.value, "Root Insurance", True, 0.95),
    r"metromile": (InsuranceSubcategory.AUTO.value, "Metromile", True, 0.95),
    r"clearcover": (InsuranceSubcategory.AUTO.value, "Clearcover", True, 0.95),

    # -------------------------------------------------------------------------
    # HOME/RENTERS INSURANCE (Essential)
    # -------------------------------------------------------------------------
    r"lemonade\s*(ins)?": (InsuranceSubcategory.RENTERS.value, "Lemonade", True, 0.95),
    r"assurant\s*(renters)?": (InsuranceSubcategory.RENTERS.value, "Assurant", True, 0.95),
    r"hippo\s*(ins)?": (InsuranceSubcategory.HOME.value, "Hippo", True, 0.95),

    # -------------------------------------------------------------------------
    # HEALTH INSURANCE (Essential)
    # -------------------------------------------------------------------------
    r"blue\s*cross|bcbs|anthem": (InsuranceSubcategory.HEALTH.value, "Blue Cross Blue Shield", True, 0.95),
    r"united\s*health|uhc": (InsuranceSubcategory.HEALTH.value, "UnitedHealthcare", True, 0.95),
    r"aetna": (InsuranceSubcategory.HEALTH.value, "Aetna", True, 0.95),
    r"cigna": (InsuranceSubcategory.HEALTH.value, "Cigna", True, 0.95),
    r"humana": (InsuranceSubcategory.HEALTH.value, "Humana", True, 0.95),
    r"kaiser": (InsuranceSubcategory.HEALTH.value, "Kaiser Permanente", True, 0.95),
    r"oscar\s*health": (InsuranceSubcategory.HEALTH.value, "Oscar Health", True, 0.95),

    # -------------------------------------------------------------------------
    # LIFE INSURANCE (Essential for many)
    # -------------------------------------------------------------------------
    r"northwestern\s*mutual": (InsuranceSubcategory.LIFE.value, "Northwestern Mutual", True, 0.95),
    r"prudential": (InsuranceSubcategory.LIFE.value, "Prudential", True, 0.95),
    r"new\s*york\s*life": (InsuranceSubcategory.LIFE.value, "New York Life", True, 0.95),
    r"mass\s*mutual|massmutual": (InsuranceSubcategory.LIFE.value, "MassMutual", True, 0.95),
    r"lincoln\s*financial": (InsuranceSubcategory.LIFE.value, "Lincoln Financial", True, 0.95),
    r"transamerica": (InsuranceSubcategory.LIFE.value, "Transamerica", True, 0.95),
    r"term\s*life|bestow|ladder\s*life|ethos": (InsuranceSubcategory.LIFE.value, None, True, 0.90),

    # -------------------------------------------------------------------------
    # PET INSURANCE (Discretionary)
    # -------------------------------------------------------------------------
    r"trupanion": (InsuranceSubcategory.PET.value, "Trupanion", False, 0.95),
    r"healthy\s*paws": (InsuranceSubcategory.PET.value, "Healthy Paws", False, 0.95),
    r"embrace\s*pet": (InsuranceSubcategory.PET.value, "Embrace Pet", False, 0.95),
    r"nationwide\s*pet": (InsuranceSubcategory.PET.value, "Nationwide Pet", False, 0.95),
    r"petplan": (InsuranceSubcategory.PET.value, "Petplan", False, 0.95),
    r"lemonade\s*pet": (InsuranceSubcategory.PET.value, "Lemonade Pet", False, 0.95),
    r"pumpkin\s*pet": (InsuranceSubcategory.PET.value, "Pumpkin Pet", False, 0.95),
    r"figo\s*pet": (InsuranceSubcategory.PET.value, "Figo Pet", False, 0.95),
}

SUBSCRIPTION_PATTERNS: Dict[str, Tuple[str, str, bool, float]] = {
    # -------------------------------------------------------------------------
    # STREAMING VIDEO (Discretionary)
    # -------------------------------------------------------------------------
    r"netflix": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Netflix", False, 0.95),
    r"hulu": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Hulu", False, 0.95),
    r"disney\s*\+?(?!\s*bundle)": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Disney+", False, 0.95),
    r"disney\s*bundle": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Disney Bundle", False, 0.95),
    r"hbo\s*max|max\.com": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Max", False, 0.95),
    r"amazon\s*prime\s*video": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Prime Video", False, 0.95),
    r"peacock": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Peacock", False, 0.95),
    r"paramount\s*\+": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Paramount+", False, 0.95),
    r"apple\s*tv": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Apple TV+", False, 0.95),
    r"youtube\s*(premium|tv)": (SubscriptionSubcategory.STREAMING_VIDEO.value, "YouTube Premium", False, 0.95),
    r"crunchyroll": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Crunchyroll", False, 0.95),
    r"fubo": (SubscriptionSubcategory.STREAMING_VIDEO.value, "FuboTV", False, 0.95),
    r"sling\s*tv": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Sling TV", False, 0.95),
    r"plex": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Plex", False, 0.95),
    r"nebula": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Nebula", False, 0.95),
    r"curiosity\s*stream": (SubscriptionSubcategory.STREAMING_VIDEO.value, "CuriosityStream", False, 0.95),
    r"mubi": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Mubi", False, 0.95),
    r"criterion\s*channel": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Criterion Channel", False, 0.95),
    r"showtime": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Showtime", False, 0.95),
    r"starz": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Starz", False, 0.95),
    r"britbox": (SubscriptionSubcategory.STREAMING_VIDEO.value, "BritBox", False, 0.95),
    r"shudder": (SubscriptionSubcategory.STREAMING_VIDEO.value, "Shudder", False, 0.95),
    r"amc\s*\+": (SubscriptionSubcategory.STREAMING_VIDEO.value, "AMC+", False, 0.95),
    r"espn\s*\+": (SubscriptionSubcategory.STREAMING_VIDEO.value, "ESPN+", False, 0.95),
    r"f1\s*tv|www\.f1\.com": (SubscriptionSubcategory.STREAMING_VIDEO.value, "F1 TV", False, 0.95),
    r"dazn": (SubscriptionSubcategory.STREAMING_VIDEO.value, "DAZN", False, 0.95),

    # -------------------------------------------------------------------------
    # STREAMING MUSIC (Discretionary)
    # -------------------------------------------------------------------------
    r"spotify": (SubscriptionSubcategory.STREAMING_MUSIC.value, "Spotify", False, 0.95),
    r"apple\s*music": (SubscriptionSubcategory.STREAMING_MUSIC.value, "Apple Music", False, 0.95),
    r"tidal": (SubscriptionSubcategory.STREAMING_MUSIC.value, "Tidal", False, 0.95),
    r"pandora": (SubscriptionSubcategory.STREAMING_MUSIC.value, "Pandora", False, 0.95),
    r"amazon\s*music": (SubscriptionSubcategory.STREAMING_MUSIC.value, "Amazon Music", False, 0.95),
    r"deezer": (SubscriptionSubcategory.STREAMING_MUSIC.value, "Deezer", False, 0.95),
    r"sirius\s*xm": (SubscriptionSubcategory.STREAMING_MUSIC.value, "SiriusXM", False, 0.95),
    r"audible": (SubscriptionSubcategory.STREAMING_MUSIC.value, "Audible", False, 0.95),
    r"soundcloud": (SubscriptionSubcategory.STREAMING_MUSIC.value, "SoundCloud", False, 0.95),

    # -------------------------------------------------------------------------
    # CLOUD STORAGE (Discretionary)
    # -------------------------------------------------------------------------
    r"icloud|apple\.com/bill": (SubscriptionSubcategory.CLOUD_STORAGE.value, "iCloud", False, 0.95),
    r"google\s*(one|drive|storage)": (SubscriptionSubcategory.CLOUD_STORAGE.value, "Google One", False, 0.95),
    r"dropbox": (SubscriptionSubcategory.CLOUD_STORAGE.value, "Dropbox", False, 0.95),
    r"onedrive|microsoft\s*storage": (SubscriptionSubcategory.CLOUD_STORAGE.value, "OneDrive", False, 0.95),
    r"box\.com": (SubscriptionSubcategory.CLOUD_STORAGE.value, "Box", False, 0.95),
    r"backblaze": (SubscriptionSubcategory.CLOUD_STORAGE.value, "Backblaze", False, 0.95),
    r"idrive": (SubscriptionSubcategory.CLOUD_STORAGE.value, "iDrive", False, 0.95),

    # -------------------------------------------------------------------------
    # SOFTWARE/PRODUCTIVITY (Discretionary)
    # -------------------------------------------------------------------------
    r"microsoft\s*365|office\s*365": (SubscriptionSubcategory.SOFTWARE.value, "Microsoft 365", False, 0.95),
    r"adobe": (SubscriptionSubcategory.SOFTWARE.value, "Adobe", False, 0.95),
    r"github": (SubscriptionSubcategory.SOFTWARE.value, "GitHub", False, 0.95),
    r"jetbrains": (SubscriptionSubcategory.SOFTWARE.value, "JetBrains", False, 0.95),
    r"notion": (SubscriptionSubcategory.SOFTWARE.value, "Notion", False, 0.95),
    r"slack": (SubscriptionSubcategory.SOFTWARE.value, "Slack", False, 0.95),
    r"zoom\s*(video)?": (SubscriptionSubcategory.SOFTWARE.value, "Zoom", False, 0.95),
    r"1password|onepassword": (SubscriptionSubcategory.SOFTWARE.value, "1Password", False, 0.95),
    r"lastpass": (SubscriptionSubcategory.SOFTWARE.value, "LastPass", False, 0.95),
    r"bitwarden": (SubscriptionSubcategory.SOFTWARE.value, "Bitwarden", False, 0.95),
    r"dashlane": (SubscriptionSubcategory.SOFTWARE.value, "Dashlane", False, 0.95),
    r"nordvpn": (SubscriptionSubcategory.SOFTWARE.value, "NordVPN", False, 0.95),
    r"expressvpn": (SubscriptionSubcategory.SOFTWARE.value, "ExpressVPN", False, 0.95),
    r"surfshark": (SubscriptionSubcategory.SOFTWARE.value, "Surfshark", False, 0.95),
    r"proton\s*(mail|vpn)": (SubscriptionSubcategory.SOFTWARE.value, "Proton", False, 0.95),
    r"evernote": (SubscriptionSubcategory.SOFTWARE.value, "Evernote", False, 0.95),
    r"todoist": (SubscriptionSubcategory.SOFTWARE.value, "Todoist", False, 0.95),
    r"asana": (SubscriptionSubcategory.SOFTWARE.value, "Asana", False, 0.95),
    r"trello": (SubscriptionSubcategory.SOFTWARE.value, "Trello", False, 0.95),
    r"monday\.com": (SubscriptionSubcategory.SOFTWARE.value, "Monday.com", False, 0.95),
    r"canva": (SubscriptionSubcategory.SOFTWARE.value, "Canva", False, 0.95),
    r"figma": (SubscriptionSubcategory.SOFTWARE.value, "Figma", False, 0.95),
    r"grammarly": (SubscriptionSubcategory.SOFTWARE.value, "Grammarly", False, 0.95),
    r"easynews|giganews": (SubscriptionSubcategory.SOFTWARE.value, "Usenet", False, 0.95),
    r"vidiq": (SubscriptionSubcategory.SOFTWARE.value, "VidIQ", False, 0.95),
    r"tubebuddy": (SubscriptionSubcategory.SOFTWARE.value, "TubeBuddy", False, 0.95),
    r"replit": (SubscriptionSubcategory.SOFTWARE.value, "Replit", False, 0.95),
    r"vercel": (SubscriptionSubcategory.SOFTWARE.value, "Vercel", False, 0.95),
    r"netlify": (SubscriptionSubcategory.SOFTWARE.value, "Netlify", False, 0.95),
    r"heroku": (SubscriptionSubcategory.SOFTWARE.value, "Heroku", False, 0.95),
    r"digitalocean": (SubscriptionSubcategory.SOFTWARE.value, "DigitalOcean", False, 0.95),
    r"aws|amazon\s*web\s*services": (SubscriptionSubcategory.SOFTWARE.value, "AWS", False, 0.95),
    r"cloudflare": (SubscriptionSubcategory.SOFTWARE.value, "Cloudflare", False, 0.95),
    # E-commerce / Amazon seller tools
    r"teikametrics": (SubscriptionSubcategory.SOFTWARE.value, "Teikametrics", False, 0.95),
    r"threecolts|three\s*colts": (SubscriptionSubcategory.SOFTWARE.value, "ThreeColts", False, 0.95),
    r"jungle\s*scout": (SubscriptionSubcategory.SOFTWARE.value, "Jungle Scout", False, 0.95),
    r"helium\s*10|helium10": (SubscriptionSubcategory.SOFTWARE.value, "Helium 10", False, 0.95),
    r"seller\s*labs": (SubscriptionSubcategory.SOFTWARE.value, "Seller Labs", False, 0.95),
    r"viral\s*launch": (SubscriptionSubcategory.SOFTWARE.value, "Viral Launch", False, 0.95),
    r"sellerboard": (SubscriptionSubcategory.SOFTWARE.value, "Sellerboard", False, 0.95),
    r"keepa": (SubscriptionSubcategory.SOFTWARE.value, "Keepa", False, 0.95),

    # -------------------------------------------------------------------------
    # AI SERVICES (Discretionary - New category!)
    # -------------------------------------------------------------------------
    r"openai|chatgpt": (SubscriptionSubcategory.AI_SERVICES.value, "OpenAI", False, 0.95),
    r"anthropic|claude\.ai": (SubscriptionSubcategory.AI_SERVICES.value, "Anthropic", False, 0.95),
    r"cursor.*ide|cursor\.ai": (SubscriptionSubcategory.AI_SERVICES.value, "Cursor", False, 0.95),
    r"midjourney": (SubscriptionSubcategory.AI_SERVICES.value, "Midjourney", False, 0.95),
    r"runway\s*ml|runwayml": (SubscriptionSubcategory.AI_SERVICES.value, "Runway", False, 0.95),
    r"stability\.ai|stable\s*diffusion": (SubscriptionSubcategory.AI_SERVICES.value, "Stability AI", False, 0.95),
    r"jasper\s*(ai)?": (SubscriptionSubcategory.AI_SERVICES.value, "Jasper AI", False, 0.95),
    r"copy\.ai": (SubscriptionSubcategory.AI_SERVICES.value, "Copy.ai", False, 0.95),
    r"writesonic": (SubscriptionSubcategory.AI_SERVICES.value, "Writesonic", False, 0.95),
    r"perplexity": (SubscriptionSubcategory.AI_SERVICES.value, "Perplexity", False, 0.95),
    r"eleven\s*labs|elevenlabs": (SubscriptionSubcategory.AI_SERVICES.value, "ElevenLabs", False, 0.95),
    r"synthesia": (SubscriptionSubcategory.AI_SERVICES.value, "Synthesia", False, 0.95),
    r"descript": (SubscriptionSubcategory.AI_SERVICES.value, "Descript", False, 0.95),
    r"otter\.ai": (SubscriptionSubcategory.AI_SERVICES.value, "Otter.ai", False, 0.95),
    r"superhuman": (SubscriptionSubcategory.AI_SERVICES.value, "Superhuman", False, 0.95),
    r"leonardo\.?ai|leonardo\s*ai": (SubscriptionSubcategory.AI_SERVICES.value, "Leonardo.AI", False, 0.95),

    # -------------------------------------------------------------------------
    # GAMING (Discretionary)
    # -------------------------------------------------------------------------
    r"xbox\s*(live|game\s*pass)": (SubscriptionSubcategory.GAMING.value, "Xbox", False, 0.95),
    r"playstation\s*(plus|now|network)": (SubscriptionSubcategory.GAMING.value, "PlayStation", False, 0.95),
    r"nintendo\s*(online|switch)": (SubscriptionSubcategory.GAMING.value, "Nintendo", False, 0.95),
    r"ea\s*(play|games|inc)": (SubscriptionSubcategory.GAMING.value, "EA", False, 0.95),
    r"steam": (SubscriptionSubcategory.GAMING.value, "Steam", False, 0.90),
    r"epic\s*games": (SubscriptionSubcategory.GAMING.value, "Epic Games", False, 0.95),
    r"humble\s*bundle": (SubscriptionSubcategory.GAMING.value, "Humble Bundle", False, 0.95),
    r"ubisoft": (SubscriptionSubcategory.GAMING.value, "Ubisoft+", False, 0.95),
    r"geforce\s*now": (SubscriptionSubcategory.GAMING.value, "GeForce Now", False, 0.95),
    r"iracing": (SubscriptionSubcategory.GAMING.value, "iRacing", False, 0.95),
    r"racelab|simracing": (SubscriptionSubcategory.GAMING.value, "Sim Racing", False, 0.95),

    # -------------------------------------------------------------------------
    # FITNESS/WELLNESS (Discretionary)
    # -------------------------------------------------------------------------
    r"planet\s*fitness": (SubscriptionSubcategory.FITNESS.value, "Planet Fitness", False, 0.95),
    r"la\s*fitness": (SubscriptionSubcategory.FITNESS.value, "LA Fitness", False, 0.95),
    r"anytime\s*fitness": (SubscriptionSubcategory.FITNESS.value, "Anytime Fitness", False, 0.95),
    r"24\s*hour\s*fitness": (SubscriptionSubcategory.FITNESS.value, "24 Hour Fitness", False, 0.95),
    r"equinox": (SubscriptionSubcategory.FITNESS.value, "Equinox", False, 0.95),
    r"orange\s*theory|orangetheory": (SubscriptionSubcategory.FITNESS.value, "Orangetheory", False, 0.95),
    r"crossfit": (SubscriptionSubcategory.FITNESS.value, "CrossFit", False, 0.95),
    r"peloton": (SubscriptionSubcategory.FITNESS.value, "Peloton", False, 0.95),
    r"classpass": (SubscriptionSubcategory.FITNESS.value, "ClassPass", False, 0.95),
    r"strava": (SubscriptionSubcategory.FITNESS.value, "Strava", False, 0.95),
    r"fitbit\s*premium": (SubscriptionSubcategory.FITNESS.value, "Fitbit Premium", False, 0.95),
    r"whoop": (SubscriptionSubcategory.FITNESS.value, "Whoop", False, 0.95),
    r"headspace": (SubscriptionSubcategory.WELLNESS.value, "Headspace", False, 0.95),
    r"calm": (SubscriptionSubcategory.WELLNESS.value, "Calm", False, 0.95),
    r"noom": (SubscriptionSubcategory.WELLNESS.value, "Noom", False, 0.95),
    r"betterhelp": (SubscriptionSubcategory.WELLNESS.value, "BetterHelp", False, 0.95),
    r"talkspace": (SubscriptionSubcategory.WELLNESS.value, "Talkspace", False, 0.95),

    # -------------------------------------------------------------------------
    # NEWS/MEDIA (Discretionary)
    # -------------------------------------------------------------------------
    r"new\s*york\s*times|nytimes": (SubscriptionSubcategory.NEWS_MEDIA.value, "NY Times", False, 0.95),
    r"washington\s*post": (SubscriptionSubcategory.NEWS_MEDIA.value, "Washington Post", False, 0.95),
    r"wall\s*street\s*journal|wsj": (SubscriptionSubcategory.NEWS_MEDIA.value, "WSJ", False, 0.95),
    r"the\s*athletic": (SubscriptionSubcategory.NEWS_MEDIA.value, "The Athletic", False, 0.95),
    r"economist": (SubscriptionSubcategory.NEWS_MEDIA.value, "The Economist", False, 0.95),
    r"bloomberg": (SubscriptionSubcategory.NEWS_MEDIA.value, "Bloomberg", False, 0.95),
    r"financial\s*times": (SubscriptionSubcategory.NEWS_MEDIA.value, "Financial Times", False, 0.95),
    r"medium": (SubscriptionSubcategory.NEWS_MEDIA.value, "Medium", False, 0.95),
    r"substack": (SubscriptionSubcategory.NEWS_MEDIA.value, "Substack", False, 0.95),

    # -------------------------------------------------------------------------
    # CREATOR PLATFORMS (Discretionary)
    # -------------------------------------------------------------------------
    r"patreon": (SubscriptionSubcategory.CREATOR_PLATFORMS.value, "Patreon", False, 0.95),
    r"ko-?fi": (SubscriptionSubcategory.CREATOR_PLATFORMS.value, "Ko-fi", False, 0.95),
    r"gumroad": (SubscriptionSubcategory.CREATOR_PLATFORMS.value, "Gumroad", False, 0.95),
    r"onlyfans": (SubscriptionSubcategory.CREATOR_PLATFORMS.value, "OnlyFans", False, 0.95),
    r"twitch": (SubscriptionSubcategory.CREATOR_PLATFORMS.value, "Twitch", False, 0.95),
    r"youtube\s*member": (SubscriptionSubcategory.CREATOR_PLATFORMS.value, "YouTube Membership", False, 0.95),

    # -------------------------------------------------------------------------
    # MEMBERSHIP CLUBS (Discretionary)
    # -------------------------------------------------------------------------
    r"amazon\s*prime(?!\s*video)": (SubscriptionSubcategory.MEMBERSHIP.value, "Amazon Prime", False, 0.95),
    r"costco\s*(membership)?": (SubscriptionSubcategory.MEMBERSHIP.value, "Costco", False, 0.95),
    r"sam'?s\s*club": (SubscriptionSubcategory.MEMBERSHIP.value, "Sam's Club", False, 0.95),
    r"bj'?s\s*(wholesale)?": (SubscriptionSubcategory.MEMBERSHIP.value, "BJ's", False, 0.95),
    r"aaa\s*(membership)?": (SubscriptionSubcategory.MEMBERSHIP.value, "AAA", False, 0.95),
    r"walmart\s*\+|walmart\s*plus": (SubscriptionSubcategory.MEMBERSHIP.value, "Walmart+", False, 0.95),
    r"instacart\s*express": (SubscriptionSubcategory.MEMBERSHIP.value, "Instacart Express", False, 0.95),
    r"doordash\s*dashpass": (SubscriptionSubcategory.MEMBERSHIP.value, "DashPass", False, 0.95),
    r"uber\s*(one|pass)": (SubscriptionSubcategory.MEMBERSHIP.value, "Uber One", False, 0.95),
    r"grubhub\s*\+": (SubscriptionSubcategory.MEMBERSHIP.value, "Grubhub+", False, 0.95),

    # -------------------------------------------------------------------------
    # IDENTITY PROTECTION (Discretionary)
    # -------------------------------------------------------------------------
    r"identityiq|iiq": (SubscriptionSubcategory.IDENTITY_PROTECTION.value, "IdentityIQ", False, 0.95),
    r"lifelock": (SubscriptionSubcategory.IDENTITY_PROTECTION.value, "LifeLock", False, 0.95),
    r"experian\s*(identity)?": (SubscriptionSubcategory.IDENTITY_PROTECTION.value, "Experian", False, 0.95),
    r"credit\s*karma": (SubscriptionSubcategory.IDENTITY_PROTECTION.value, "Credit Karma", False, 0.95),
    r"identity\s*guard": (SubscriptionSubcategory.IDENTITY_PROTECTION.value, "Identity Guard", False, 0.95),
    r"aura\s*(identity)?": (SubscriptionSubcategory.IDENTITY_PROTECTION.value, "Aura", False, 0.95),

    # -------------------------------------------------------------------------
    # FINTECH SERVICES (Discretionary)
    # -------------------------------------------------------------------------
    r"rocket\s*money": (SubscriptionSubcategory.FINTECH.value, "Rocket Money", False, 0.95),
    r"ynab|you\s*need\s*a\s*budget": (SubscriptionSubcategory.FINTECH.value, "YNAB", False, 0.95),
    r"copilot\s*money": (SubscriptionSubcategory.FINTECH.value, "Copilot", False, 0.95),
    r"monarch\s*money": (SubscriptionSubcategory.FINTECH.value, "Monarch Money", False, 0.95),
    r"simplifi": (SubscriptionSubcategory.FINTECH.value, "Simplifi", False, 0.95),
    r"personal\s*capital": (SubscriptionSubcategory.FINTECH.value, "Empower", False, 0.95),
    r"acorns": (SubscriptionSubcategory.FINTECH.value, "Acorns", False, 0.95),
    r"stash": (SubscriptionSubcategory.FINTECH.value, "Stash", False, 0.95),
    r"albert\s*(genius|savings)?": (SubscriptionSubcategory.FINTECH.value, "Albert", False, 0.95),
    r"chime": (SubscriptionSubcategory.FINTECH.value, "Chime", False, 0.95),
    r"robinhood\s*gold": (SubscriptionSubcategory.FINTECH.value, "Robinhood Gold", False, 0.95),

    # -------------------------------------------------------------------------
    # EDUCATION (Discretionary)
    # -------------------------------------------------------------------------
    r"coursera": (SubscriptionSubcategory.EDUCATION.value, "Coursera", False, 0.95),
    r"udemy": (SubscriptionSubcategory.EDUCATION.value, "Udemy", False, 0.95),
    r"linkedin\s*learning": (SubscriptionSubcategory.EDUCATION.value, "LinkedIn Learning", False, 0.95),
    r"skillshare": (SubscriptionSubcategory.EDUCATION.value, "Skillshare", False, 0.95),
    r"masterclass": (SubscriptionSubcategory.EDUCATION.value, "MasterClass", False, 0.95),
    r"brilliant": (SubscriptionSubcategory.EDUCATION.value, "Brilliant", False, 0.95),
    r"duolingo": (SubscriptionSubcategory.EDUCATION.value, "Duolingo", False, 0.95),
    r"babbel": (SubscriptionSubcategory.EDUCATION.value, "Babbel", False, 0.95),
    r"rosetta\s*stone": (SubscriptionSubcategory.EDUCATION.value, "Rosetta Stone", False, 0.95),
    r"pluralsight": (SubscriptionSubcategory.EDUCATION.value, "Pluralsight", False, 0.95),
    r"treehouse": (SubscriptionSubcategory.EDUCATION.value, "Treehouse", False, 0.95),
    r"codecademy": (SubscriptionSubcategory.EDUCATION.value, "Codecademy", False, 0.95),
    r"datacamp": (SubscriptionSubcategory.EDUCATION.value, "DataCamp", False, 0.95),
    r"khan\s*academy": (SubscriptionSubcategory.EDUCATION.value, "Khan Academy", False, 0.95),

    # -------------------------------------------------------------------------
    # PET SERVICES (Discretionary)
    # -------------------------------------------------------------------------
    r"chewy": (SubscriptionSubcategory.PET_SERVICES.value, "Chewy", False, 0.95),
    r"barkbox": (SubscriptionSubcategory.PET_SERVICES.value, "BarkBox", False, 0.95),
    r"petco\s*vital\s*care": (SubscriptionSubcategory.PET_SERVICES.value, "Petco Vital Care", False, 0.95),
    r"rover": (SubscriptionSubcategory.PET_SERVICES.value, "Rover", False, 0.95),
    r"wag!?": (SubscriptionSubcategory.PET_SERVICES.value, "Wag!", False, 0.95),
    r"ollie\s*dog": (SubscriptionSubcategory.PET_SERVICES.value, "Ollie", False, 0.95),
    r"farmer'?s\s*dog": (SubscriptionSubcategory.PET_SERVICES.value, "The Farmer's Dog", False, 0.95),
}


def classify_recurring(description: str, amount: float = 0.0) -> ClassificationResult:
    """
    Classify a recurring transaction based on description and amount.

    Uses pattern matching first (fast, accurate for known merchants),
    then falls back to amount-based heuristics.

    Args:
        description: Transaction description
        amount: Transaction amount (helps with classification)

    Returns:
        ClassificationResult with category, subcategory, merchant name, etc.
    """
    desc = (description or "").lower().strip()
    if not desc:
        return ClassificationResult(
            category=RecurringCategory.UNKNOWN,
            subcategory=None,
            merchant_name=None,
            is_essential=False,
            confidence=0.0,
            match_type="fallback",
        )

    # Try LOAN patterns first (highest priority for recurring)
    for pattern, (subcategory, merchant_name, is_essential, confidence) in LOAN_PATTERNS.items():
        if re.search(pattern, desc, re.I):
            return ClassificationResult(
                category=RecurringCategory.LOAN_PAYMENTS,
                subcategory=subcategory,
                merchant_name=merchant_name,
                is_essential=is_essential,
                confidence=confidence,
                match_type="pattern",
            )

    # Try INSURANCE patterns
    for pattern, (subcategory, merchant_name, is_essential, confidence) in INSURANCE_PATTERNS.items():
        if re.search(pattern, desc, re.I):
            return ClassificationResult(
                category=RecurringCategory.INSURANCE,
                subcategory=subcategory,
                merchant_name=merchant_name,
                is_essential=is_essential,
                confidence=confidence,
                match_type="pattern",
            )

    # Try UTILITY patterns
    for pattern, (subcategory, merchant_name, is_essential, confidence) in UTILITY_PATTERNS.items():
        if re.search(pattern, desc, re.I):
            return ClassificationResult(
                category=RecurringCategory.RENT_AND_UTILITIES,
                subcategory=subcategory,
                merchant_name=merchant_name,
                is_essential=is_essential,
                confidence=confidence,
                match_type="pattern",
            )

    # Try SUBSCRIPTION patterns
    for pattern, (subcategory, merchant_name, is_essential, confidence) in SUBSCRIPTION_PATTERNS.items():
        if re.search(pattern, desc, re.I):
            return ClassificationResult(
                category=RecurringCategory.SUBSCRIPTIONS,
                subcategory=subcategory,
                merchant_name=merchant_name,
                is_essential=is_essential,
                confidence=confidence,
                match_type="pattern",
            )

    # Amount-based fallback
    abs_amount = abs(amount)

    # Very large recurring amounts (>$1000) suggest mortgage/loan
    if abs_amount >= 1000:
        return ClassificationResult(
            category=RecurringCategory.LOAN_PAYMENTS,
            subcategory=None,
            merchant_name=None,
            is_essential=True,
            confidence=0.50,
            match_type="amount",
        )

    # Medium amounts ($100-$500) suggest utilities or bills
    if 100 <= abs_amount < 500:
        return ClassificationResult(
            category=RecurringCategory.RENT_AND_UTILITIES,
            subcategory=None,
            merchant_name=None,
            is_essential=True,
            confidence=0.40,
            match_type="amount",
        )

    # Small recurring amounts (<$50) suggest subscriptions
    if abs_amount < 50:
        return ClassificationResult(
            category=RecurringCategory.SUBSCRIPTIONS,
            subcategory=None,
            merchant_name=None,
            is_essential=False,
            confidence=0.40,
            match_type="amount",
        )

    return ClassificationResult(
        category=RecurringCategory.UNKNOWN,
        subcategory=None,
        merchant_name=None,
        is_essential=False,
        confidence=0.0,
        match_type="fallback",
    )


# Convenience function for backwards compatibility
def classify_recurring_type(description: str, amount: float = 0.0) -> dict:
    """Legacy interface for recurring type classification."""
    result = classify_recurring(description, amount)
    return {
        "recurring_type": result.category.value,
        "sub_category": result.subcategory,
        "clean_name": result.merchant_name,
        "is_essential": result.is_essential,
        "confidence": result.confidence,
        "match_type": result.match_type,
    }
