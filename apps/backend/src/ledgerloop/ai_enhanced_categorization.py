"""
Enhanced AI Categorization Service

Provides improved transaction categorization with:
- Better merchant recognition patterns
- Context-aware categorization logic  
- Confidence-based scoring
- Machine learning features
- Amount-based classification
"""

from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .db import get_conn
from .ai import CategorySuggestion, MerchantInfo

logger = logging.getLogger(__name__)


@dataclass
class EnhancedCategorySuggestion:
    """Enhanced category suggestion with detailed scoring"""
    category_name: str
    confidence: float
    reasoning: str
    match_type: str  # 'merchant', 'keyword', 'pattern', 'context', 'amount'
    keywords_matched: List[str]
    confidence_factors: Dict[str, float]
    merchant_name: Optional[str] = None  # Clean extracted merchant name


class EnhancedCategorizationService:
    """Enhanced AI categorization with improved accuracy"""

    def __init__(self):
        self.enhanced_merchant_patterns = self._load_enhanced_merchant_patterns()
        self.merchant_name_map = self._load_merchant_name_map()
        self.context_patterns = self._load_context_patterns()
        self.amount_based_categories = self._load_amount_categories()
        self.category_keywords = self._load_enhanced_category_keywords()
        self.confidence_weights = self._load_confidence_weights()

    def _load_merchant_name_map(self) -> Dict[str, str]:
        """Map regex patterns to clean merchant display names"""
        return {
            # Food & Dining
            r'MCDONALD.*': "McDonald's",
            r'STARBUCKS.*': 'Starbucks',
            r'SUBWAY.*': 'Subway',
            r'BURGER\s*KING.*': 'Burger King',
            r'TACO\s*BELL.*': 'Taco Bell',
            r'CHIPOTLE.*': 'Chipotle',
            r'DOMINO.*': "Domino's",
            r'PIZZA\s*HUT.*': 'Pizza Hut',
            r'KFC.*': 'KFC',
            r'WENDY.*': "Wendy's",
            r'CHICK[- ]?FIL[- ]?A.*': 'Chick-fil-A',
            r'BOJANGLES.*': "Bojangles'",
            r'OUTBACK.*': 'Outback Steakhouse',
            r'RED\s*LOBSTER.*': 'Red Lobster',
            r'PANERA.*': 'Panera Bread',
            r'DUNKIN.*': "Dunkin'",
            r'PANDA\s*EXPRESS.*': 'Panda Express',
            r'BUFFALO\s*WILD\s*WINGS.*': 'Buffalo Wild Wings',
            r'OLIVE\s*GARDEN.*': 'Olive Garden',
            r'APPLEBEE.*': "Applebee's",
            r'CRACKER\s*BARREL.*': 'Cracker Barrel',
            r'IHOP.*': 'IHOP',
            r'DENNY.*': "Denny's",
            r'WAFFLE\s*HOUSE.*': 'Waffle House',
            r'FIVE\s*GUYS.*': 'Five Guys',
            r'POPEYES.*': 'Popeyes',
            r'SONIC\s*DRIVE.*': 'Sonic Drive-In',
            r'JACK\s*IN\s*THE\s*BOX.*': 'Jack in the Box',
            r'ARBY.*': "Arby's",
            r'COOK\s*OUT.*': 'Cook Out',
            r'RAISING\s*CANE.*': "Raising Cane's",
            r'JERSEY\s*MIKE.*': "Jersey Mike's",
            r'JIMMY\s*JOHN.*': "Jimmy John's",
            r'FIREHOUSE\s*SUB.*': 'Firehouse Subs',
            r'CHEESECAKE\s*FACTORY.*': 'Cheesecake Factory',
            r'TEXAS\s*ROADHOUSE.*': 'Texas Roadhouse',
            r'LITTLE\s*CAESAR.*': "Little Caesars",
            r'QDOBA.*': 'Qdoba',
            r'WHATABURGER.*': 'Whataburger',
            r'IN[- ]?N[- ]?OUT.*': 'In-N-Out Burger',
            r'ZAXBY.*': "Zaxby's",
            r'SHAKE\s*SHACK.*': 'Shake Shack',
            r'WINGSTOP.*': 'Wingstop',

            # Grocery
            r'AL[- ]?BASHA.*MARK.*': 'Al-Basha Market',
            r'HARRIS\s+TE.*': 'Harris Teeter',
            r'WHOLE\s*FOODS.*': 'Whole Foods',
            r'KROGER.*': 'Kroger',
            r'PUBLIX.*': 'Publix',
            r'ALDI.*': 'Aldi',
            r'SAFEWAY.*': 'Safeway',
            r'TRADER\s*JOE.*': "Trader Joe's",
            r'FOOD\s*LION.*': 'Food Lion',
            r'ALBERTSONS.*': "Albertsons",
            r'WEGMANS.*': 'Wegmans',
            r'COSTCO.*': 'Costco',
            r'SAM.*CLUB.*': "Sam's Club",
            r'BJ.*WHOLESALE.*': "BJ's Wholesale",
            r'ALMADINA.*': 'Almadina Supermarket',

            # Gas & Automotive
            r'SHEETZ.*': 'Sheetz',
            r'SHELL.*': 'Shell',
            r'EXXON.*': 'Exxon',
            r'CHEVRON.*': 'Chevron',
            r'BP\s.*': 'BP',
            r'MOBIL.*': 'Mobil',
            r'WAWA.*': 'Wawa',
            r'SPEEDWAY.*': 'Speedway',
            r'QUIKTRIP.*': 'QuikTrip',
            r'RACETRAC.*': 'RaceTrac',
            r'AUTOZONE.*': 'AutoZone',
            r'O\'?REILLY.*AUTO.*': "O'Reilly Auto Parts",
            r'ADVANCE\s*AUTO.*': 'Advance Auto Parts',
            r'JIFFY\s*LUBE.*': 'Jiffy Lube',

            # Shopping
            r'AMAZON.*': 'Amazon',
            r'WALMART.*': 'Walmart',
            r'TARGET.*': 'Target',
            r'HOME\s*DEPOT.*': 'Home Depot',
            r'LOWES.*': "Lowe's",
            r'BEST\s*BUY.*': 'Best Buy',
            r'DOLLAR\s*(GENERAL|TREE).*': 'Dollar Store',
            r'TJ\s*MAXX.*': 'TJ Maxx',
            r'MARSHALLS.*': 'Marshalls',
            r'ROSS.*': 'Ross',
            r'IKEA.*': 'IKEA',
            r'WAYFAIR.*': 'Wayfair',
            r'EBAY.*': 'eBay',
            r'ETSY.*': 'Etsy',

            # Entertainment
            r'NETFLIX.*': 'Netflix',
            r'SPOTIFY.*': 'Spotify',
            r'HULU.*': 'Hulu',
            r'DISNEY\s*\+.*': 'Disney+',
            r'HBO\s*MAX.*': 'HBO Max',
            r'YOUTUBE\s*(PREMIUM|TV|MUSIC).*': 'YouTube',
            r'STEAM\s*GAMES.*': 'Steam',
            r'PLAYSTATION.*': 'PlayStation',
            r'XBOX.*': 'Xbox',
            r'NINTENDO.*': 'Nintendo',
            r'RACELAB.*': 'Racelab',
            r'APEX\s*RACING.*': 'Apex Racing',
            r'IRACING.*': 'iRacing',
            r'TWITCH.*': 'Twitch',
            r'AUDIBLE.*': 'Audible',

            # Software
            r'OPENAI.*': 'OpenAI',
            r'CLAUDE\.AI.*': 'Claude AI',
            r'MICROSOFT.*': 'Microsoft',
            r'GOOGLE.*PLAY.*': 'Google Play',
            r'APPLE\s*(?!TV).*': 'Apple',
            r'ADOBE.*': 'Adobe',
            r'DROPBOX.*': 'Dropbox',
            r'ZOOM\s*VIDEO.*': 'Zoom',
            r'SLACK.*': 'Slack',
            r'CANVA.*': 'Canva',
            r'SHOPIFY.*': 'Shopify',
            r'GODADDY.*': 'GoDaddy',
            r'NOTION.*': 'Notion',

            # Bills & Utilities
            r'DUKE\s*ENERGY.*': 'Duke Energy',
            r'DOMINION\s*ENERGY.*': 'Dominion Energy',
            r'GOOGLE\s*FIBER.*': 'Google Fiber',
            r'SPECTRUM.*': 'Spectrum',
            r'VERIZON.*': 'Verizon',
            r'AT&T.*': 'AT&T',
            r'XFINITY.*': 'Xfinity',
            r'COMCAST.*': 'Comcast',
            r'T-MOBILE.*': 'T-Mobile',
            r'TMOBILE.*': 'T-Mobile',

            # Transportation
            r'UBER.*': 'Uber',
            r'LYFT.*': 'Lyft',

            # Healthcare
            r'CVS.*': 'CVS',
            r'WALGREENS.*': 'Walgreens',
            r'RITE\s*AID.*': 'Rite Aid',

            # Home Services
            r'SOLVE\s*PEST.*': 'Solve Pest Pros',
            r'TERMINIX.*': 'Terminix',
            r'ORKIN.*': 'Orkin',

            # Financial
            r'GEICO.*': 'GEICO',
            r'STATE\s*FARM.*': 'State Farm',
            r'AVANT.*': 'Avant',
            r'AFFIRM.*': 'Affirm',
            r'KLARNA.*': 'Klarna',
        }
    
    def _load_enhanced_merchant_patterns(self) -> Dict[str, Tuple[str, float]]:
        """Enhanced merchant patterns with confidence scores"""
        return {
            # Food & Dining (High confidence patterns)
            r'MCDONALD.*': ('Food & Dining', 0.95),
            r'AL[- ]?BASHA.*MARK.*': ('Grocery', 0.95),
            r'HARRIS\s+TE.*': ('Grocery', 0.95),
            r'STARBUCKS.*': ('Food & Dining', 0.95),
            r'SUBWAY.*': ('Food & Dining', 0.95),
            r'BURGER\s*KING.*': ('Food & Dining', 0.95),
            r'TACO\s*BELL.*': ('Food & Dining', 0.95),
            r'CHIPOTLE.*': ('Food & Dining', 0.95),
            r'DOMINO.*': ('Food & Dining', 0.95),
            r'PIZZA\s*HUT.*': ('Food & Dining', 0.95),
            r'KFC.*': ('Food & Dining', 0.95),
            r'WENDY.*': ('Food & Dining', 0.95),
            r'CHICK[- ]?FIL[- ]?A.*': ('Food & Dining', 0.95),
            r'BOJANGLES.*': ('Food & Dining', 0.95),
            r'OUTBACK.*': ('Food & Dining', 0.95),
            r'RED\s*LOBSTER.*': ('Food & Dining', 0.95),
            r'PANERA.*': ('Food & Dining', 0.95),
            
            # Gas & Automotive  
            r'SHEETZ.*': ('Gas & Automotive', 0.95),
            r'SHELL.*': ('Gas & Automotive', 0.95),
            r'EXXON.*': ('Gas & Automotive', 0.95),
            r'CHEVRON.*': ('Gas & Automotive', 0.95),
            r'BP\s.*': ('Gas & Automotive', 0.95),
            r'MOBIL.*': ('Gas & Automotive', 0.95),
            r'WAWA.*': ('Gas & Automotive', 0.95),
            
            # Shopping
            r'AMAZON.*': ('Shopping', 0.95),
            r'WALMART.*': ('Shopping', 0.95),
            r'TARGET.*': ('Shopping', 0.95),
            r'COSTCO.*': ('Shopping', 0.95),
            r'BEST\s*BUY.*': ('Electronics', 0.95),
            r'HOME\s*DEPOT.*': ('Shopping', 0.95),
            r'LOWES.*': ('Shopping', 0.95),
            r'DOLLAR\s*(GENERAL|TREE).*': ('Shopping', 0.95),
            r'FAMILY\s*DOLLAR.*': ('Shopping', 0.95),
            r'FIVE\s*BELOW.*': ('Shopping', 0.95),
            r'BIG\s*LOTS.*': ('Shopping', 0.95),
            r'ROSS.*': ('Shopping', 0.95),
            r'TJ\s*MAXX.*': ('Shopping', 0.95),
            r'MARSHALLS.*': ('Shopping', 0.95),

            # Tobacco & Convenience Stores (Shopping category)
            r'MAXX\s*TOBACCO.*': ('Shopping', 0.95),
            r'TOBACCO.*': ('Shopping', 0.90),
            r'SMOKE\s*SHOP.*': ('Shopping', 0.90),
            r'VAPE\s*SHOP.*': ('Shopping', 0.90),
            r'CIGAR.*': ('Shopping', 0.90),
            r'7[-\s]*ELEVEN.*': ('Shopping', 0.90),
            r'CIRCLE\s*K.*': ('Shopping', 0.90),
            r'QUICKSTOP.*': ('Shopping', 0.90),
            r'QUIKTRIP.*': ('Shopping', 0.90),

            # Auto Services
            r'.*AUTO\s*SPA.*': ('Gas & Automotive', 0.95),
            r'CAR\s*WASH.*': ('Gas & Automotive', 0.95),
            r'JIFFY\s*LUBE.*': ('Gas & Automotive', 0.95),
            r'AUTOZONE.*': ('Gas & Automotive', 0.95),
            r'O\'?REILLY.*AUTO.*': ('Gas & Automotive', 0.95),
            r'ADVANCE\s*AUTO.*': ('Gas & Automotive', 0.95),
            r'TIRE.*': ('Gas & Automotive', 0.90),

            # Personal Care
            r'.*SALON.*': ('Personal Care', 0.95),
            r'BARBER.*': ('Personal Care', 0.95),
            r'HAIR\s*(CUT|SALON).*': ('Personal Care', 0.95),
            r'NAIL\s*(SALON)?.*': ('Personal Care', 0.90),
            r'SPA\s.*': ('Personal Care', 0.85),
            
            # Entertainment & Streaming
            r'NETFLIX.*': ('Entertainment', 0.95),
            r'SPOTIFY.*': ('Entertainment', 0.95),
            r'HULU.*': ('Entertainment', 0.95),
            r'DISNEY\s*\+.*': ('Entertainment', 0.95),
            r'HBO\s*MAX.*': ('Entertainment', 0.95),
            r'YOUTUBE\s*(PREMIUM|TV|MUSIC).*': ('Entertainment', 0.95),
            r'NEBULA.*': ('Entertainment', 0.95),
            r'CURIOSITY\s*STREAM.*': ('Entertainment', 0.95),
            r'F1\.COM.*': ('Entertainment', 0.95),
            r'F1\s*TV.*': ('Entertainment', 0.95),
            r'WWW\.F1\.COM.*': ('Entertainment', 0.95),
            r'ESPN\s*\+.*': ('Entertainment', 0.95),
            r'PARAMOUNT\s*\+.*': ('Entertainment', 0.95),
            r'PEACOCK.*': ('Entertainment', 0.95),
            r'APPLE\s*TV.*': ('Entertainment', 0.95),
            r'PLEX.*': ('Entertainment', 0.95),
            r'STEAM\s*GAMES.*': ('Entertainment', 0.95),
            r'PLAYSTATION.*': ('Entertainment', 0.95),
            r'XBOX.*': ('Entertainment', 0.95),
            r'EA\s*(INC|SPORTS).*': ('Entertainment', 0.95),

            # Technology & Software
            r'OPENAI.*': ('Software', 0.95),
            r'CLAUDE\.AI.*': ('Software', 0.95),
            r'MICROSOFT.*': ('Software', 0.95),
            r'GOOGLE.*PLAY.*': ('Software', 0.95),
            r'APPLE\s*(?!TV).*': ('Software', 0.95),
            r'REPLIT.*': ('Software', 0.95),
            r'CURSOR.*AI.*': ('Software', 0.95),
            r'MIDJOURNEY.*': ('Software', 0.95),
            r'CANVA.*': ('Software', 0.95),
            r'SHOPIFY.*': ('Software', 0.95),
            r'GODADDY.*': ('Software', 0.95),
            r'TEIKAMETRICS.*': ('Software', 0.95),
            r'LEONARDO\.AI.*': ('Software', 0.95),
            r'REPURPOSE\.IO.*': ('Software', 0.95),
            r'GOOGLE\s*ADS.*': ('Software', 0.95),
            
            # Utilities & Bills
            r'DUKE\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'DOMINION\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'GOOGLE\s*FIBER.*': ('Bills & Utilities', 0.95),
            r'SPECTRUM.*': ('Bills & Utilities', 0.95),
            r'VERIZON.*': ('Bills & Utilities', 0.95),
            r'AT&T.*': ('Bills & Utilities', 0.95),
            
            # Transportation
            r'UBER.*': ('Transportation', 0.95),
            r'LYFT.*': ('Transportation', 0.95),
            
            # Financial Services
            r'GEICO.*': ('Insurance', 0.95),
            r'STATE\s*FARM.*': ('Insurance', 0.95),
            r'CARRINGTON.*MORTGAGE.*': ('Mortgage Payment', 0.95),
            
            # Professional Services
            r'INVENTORYLAB.*': ('Professional Services', 0.95),
            r'TEIKAMETRICS.*': ('Professional Services', 0.95),
            r'GODADDY.*': ('Professional Services', 0.95),

            # ============================================
            # OPENAI ENHANCED PATTERNS (Auto-generated)
            # ============================================

            # Food & Dining - Extended
            r'DUNKIN.*': ('Food & Dining', 0.95),
            r'PANDA\s*EXPRESS.*': ('Food & Dining', 0.95),
            r'BUFFALO\s*WILD\s*WINGS.*': ('Food & Dining', 0.95),
            r'OLIVE\s*GARDEN.*': ('Food & Dining', 0.95),
            r'APPLEBEE.*': ('Food & Dining', 0.95),
            r'CRACKER\s*BARREL.*': ('Food & Dining', 0.95),
            r'IHOP.*': ('Food & Dining', 0.95),
            r'DENNY.*': ('Food & Dining', 0.95),
            r'WAFFLE\s*HOUSE.*': ('Food & Dining', 0.95),
            r'FIVE\s*GUYS.*': ('Food & Dining', 0.95),
            r'POPEYES.*': ('Food & Dining', 0.95),
            r'SONIC\s*DRIVE.*': ('Food & Dining', 0.95),
            r'JACK\s*IN\s*THE\s*BOX.*': ('Food & Dining', 0.95),
            r'ARBY.*': ('Food & Dining', 0.95),
            r'COOK\s*OUT.*': ('Food & Dining', 0.95),
            r'RAISING\s*CANE.*': ('Food & Dining', 0.95),
            r'JERSEY\s*MIKE.*': ('Food & Dining', 0.95),
            r'JIMMY\s*JOHN.*': ('Food & Dining', 0.95),
            r'FIREHOUSE\s*SUB.*': ('Food & Dining', 0.95),
            r'NOODLES\s*&\s*CO.*': ('Food & Dining', 0.95),
            r'CHEESECAKE\s*FACTORY.*': ('Food & Dining', 0.95),
            r'TEXAS\s*ROADHOUSE.*': ('Food & Dining', 0.95),
            r'LONGHORN\s*STEAK.*': ('Food & Dining', 0.95),
            r'RUTH.*CHRIS.*': ('Food & Dining', 0.95),
            r'MAGGIANO.*': ('Food & Dining', 0.95),
            # OpenAI Expansion - Food & Dining
            r'LITTLE\s*CAESAR.*': ('Food & Dining', 0.95),
            r'QDOBA.*': ('Food & Dining', 0.95),
            r'WHATABURGER.*': ('Food & Dining', 0.95),
            r'IN[- ]?N[- ]?OUT.*': ('Food & Dining', 0.95),
            r'ZAXBY.*': ('Food & Dining', 0.95),
            r'SHAKE\s*SHACK.*': ('Food & Dining', 0.95),
            r'WINGSTOP.*': ('Food & Dining', 0.95),
            r'EL\s*POLLO\s*LOCO.*': ('Food & Dining', 0.95),
            r'TIM\s*HORTON.*': ('Food & Dining', 0.95),
            r'CHECKER.*': ('Food & Dining', 0.95),
            r'STEAK.*SHAKE.*': ('Food & Dining', 0.95),
            r'BOSTON\s*MARKET.*': ('Food & Dining', 0.95),
            r'RUBY\s*TUESDAY.*': ('Food & Dining', 0.95),

            # Grocery - Extended
            r'WHOLE\s*FOODS.*': ('Grocery', 0.95),
            r'KROGER.*': ('Grocery', 0.95),
            r'PUBLIX.*': ('Grocery', 0.95),
            r'ALDI.*': ('Grocery', 0.95),
            r'SAFEWAY.*': ('Grocery', 0.95),
            r'TRADER\s*JOE.*': ('Grocery', 0.95),
            r'FOOD\s*LION.*': ('Grocery', 0.95),
            r'ALBERTSONS.*': ('Grocery', 0.95),
            r'WINN.DIXIE.*': ('Grocery', 0.95),
            r'MEIJER.*': ('Grocery', 0.95),
            r'GIANT\s*(EAGLE|FOOD).*': ('Grocery', 0.95),
            r'STOP\s*.?\s*SHOP.*': ('Grocery', 0.95),
            r'SHOPRITE.*': ('Grocery', 0.95),
            r'SAM.*CLUB.*': ('Grocery', 0.95),
            r'BJ.*WHOLESALE.*': ('Grocery', 0.95),
            r'PIGGLY\s*WIGGLY.*': ('Grocery', 0.95),
            r'FRESH\s*MARKET.*': ('Grocery', 0.95),
            r'SPROUTS.*': ('Grocery', 0.95),
            r'WEGMANS.*': ('Grocery', 0.95),
            r'HEB\s.*': ('Grocery', 0.95),
            r'ALMADINA.*': ('Grocery', 0.95),
            r'MECCA\s*MARKET.*': ('Grocery', 0.95),
            # OpenAI Expansion - Grocery
            r'HY[- ]?VEE.*': ('Grocery', 0.95),
            r'RALPHS.*': ('Grocery', 0.95),
            r'VONS.*': ('Grocery', 0.95),
            r'KING\s*SOOPERS.*': ('Grocery', 0.95),
            r'FRY.*FOOD.*': ('Grocery', 0.95),
            r'SMITH.*FOOD.*': ('Grocery', 0.95),
            r'FRED\s*MEYER.*': ('Grocery', 0.95),
            r'QFC\s.*': ('Grocery', 0.95),
            r'HANNAFORD.*': ('Grocery', 0.95),
            r'SHAW.*SUPERMARKET.*': ('Grocery', 0.95),
            r'ACME\s*MARKET.*': ('Grocery', 0.95),
            r'JEWEL[- ]?OSCO.*': ('Grocery', 0.95),
            r'RANDALL.*': ('Grocery', 0.95),
            r'TOM\s*THUMB.*': ('Grocery', 0.95),
            r'CARRS.*': ('Grocery', 0.90),
            r'FOOD\s*4\s*LESS.*': ('Grocery', 0.95),
            r'PRICE\s*CHOPPER.*': ('Grocery', 0.95),
            r'MARKET\s*BASKET.*': ('Grocery', 0.95),
            r'STATER\s*BROS.*': ('Grocery', 0.95),
            r'WEIS\s*MARKET.*': ('Grocery', 0.95),
            r'PRICE\s*RITE.*': ('Grocery', 0.95),
            r'SAVE[- ]?A[- ]?LOT.*': ('Grocery', 0.95),
            r'WINCO.*': ('Grocery', 0.95),

            # Gas & Automotive - Extended
            r'VALERO.*': ('Gas & Automotive', 0.95),
            r'RACETRAC.*': ('Gas & Automotive', 0.95),
            r'QUIKTRIP.*': ('Gas & Automotive', 0.95),
            r'QT\s+.*': ('Gas & Automotive', 0.95),
            r'SUNOCO.*': ('Gas & Automotive', 0.95),
            r'MARATHON.*GAS.*': ('Gas & Automotive', 0.95),
            r'CITGO.*': ('Gas & Automotive', 0.95),
            r'TEXACO.*': ('Gas & Automotive', 0.95),
            r'SPEEDWAY.*': ('Gas & Automotive', 0.95),
            r'HESS.*': ('Gas & Automotive', 0.95),
            r'GULF.*GAS.*': ('Gas & Automotive', 0.95),
            r'PHILLIPS\s*66.*': ('Gas & Automotive', 0.95),
            r'CASEY.*GENERAL.*': ('Gas & Automotive', 0.95),
            r'MURPHY.*USA.*': ('Gas & Automotive', 0.95),
            r'PILOT.*TRAVEL.*': ('Gas & Automotive', 0.95),
            r'LOVES.*TRAVEL.*': ('Gas & Automotive', 0.95),
            r'FLYING\s*J.*': ('Gas & Automotive', 0.95),
            r'DISCOUNT\s*TIRE.*': ('Gas & Automotive', 0.95),
            r'FIRESTONE.*': ('Gas & Automotive', 0.95),
            r'GOODYEAR.*': ('Gas & Automotive', 0.95),
            r'MEINEKE.*': ('Gas & Automotive', 0.95),
            r'MIDAS.*': ('Gas & Automotive', 0.95),
            r'PEP\s*BOYS.*': ('Gas & Automotive', 0.95),
            r'NAPA\s*AUTO.*': ('Gas & Automotive', 0.95),
            # OpenAI Expansion - Gas & Automotive
            r'KWIK\s*TRIP.*': ('Gas & Automotive', 0.95),
            r'GETGO.*': ('Gas & Automotive', 0.95),
            r'KUM.*GO.*': ('Gas & Automotive', 0.95),
            r'ROYAL\s*FARMS.*': ('Gas & Automotive', 0.95),
            r'FLEET\s*FARM.*': ('Gas & Automotive', 0.90),
            r'ARCO.*': ('Gas & Automotive', 0.95),
            r'SINCLAIR.*': ('Gas & Automotive', 0.95),
            r'CONOCO.*': ('Gas & Automotive', 0.95),
            r'LES\s*SCHWAB.*': ('Gas & Automotive', 0.95),
            r'CARQUEST.*': ('Gas & Automotive', 0.95),
            r'TIRE\s*KINGDOM.*': ('Gas & Automotive', 0.95),
            r'NTB\s.*': ('Gas & Automotive', 0.95),
            r'VALVOLINE.*': ('Gas & Automotive', 0.95),
            r'AAMCO.*': ('Gas & Automotive', 0.95),

            # Shopping - Extended
            r'MACYS.*': ('Shopping', 0.95),
            r'NORDSTROM.*': ('Shopping', 0.95),
            r'KOHLS.*': ('Shopping', 0.95),
            r'SEARS.*': ('Shopping', 0.95),
            r'JC\s*PENNEY.*': ('Shopping', 0.95),
            r'JCPENNEY.*': ('Shopping', 0.95),
            r'BED\s*BATH.*BEYOND.*': ('Shopping', 0.95),
            r'WAYFAIR.*': ('Shopping', 0.95),
            r'EBAY.*': ('Shopping', 0.95),
            r'ETSY.*': ('Shopping', 0.95),
            r'NEWEGG.*': ('Shopping', 0.95),
            r'DICK.*SPORTING.*': ('Shopping', 0.95),
            r'ACADEMY\s*SPORT.*': ('Shopping', 0.95),
            r'BASS\s*PRO.*': ('Shopping', 0.95),
            r'CABELA.*': ('Shopping', 0.95),
            r'REI\s.*': ('Shopping', 0.95),
            r'IKEA.*': ('Shopping', 0.95),
            r'MENARDS.*': ('Shopping', 0.95),
            r'ACE\s*HARDWARE.*': ('Shopping', 0.95),
            r'HARBOR\s*FREIGHT.*': ('Shopping', 0.95),
            r'MICHAELS.*': ('Shopping', 0.95),
            r'HOBBY\s*LOBBY.*': ('Shopping', 0.95),
            r'JOANN.*': ('Shopping', 0.95),
            r'ULTA.*': ('Shopping', 0.95),
            r'SEPHORA.*': ('Shopping', 0.95),
            r'BATH\s*.?\s*BODY.*': ('Shopping', 0.95),
            r'VICTORIA.*SECRET.*': ('Shopping', 0.95),
            r'GAP\s.*': ('Shopping', 0.95),
            r'OLD\s*NAVY.*': ('Shopping', 0.95),
            r'BANANA\s*REPUBLIC.*': ('Shopping', 0.95),
            r'H&M.*': ('Shopping', 0.95),
            r'ZARA.*': ('Shopping', 0.95),
            r'FOREVER\s*21.*': ('Shopping', 0.95),
            r'BURLINGTON.*': ('Shopping', 0.95),
            # OpenAI Expansion - Shopping
            r'ANTHROPOLOGIE.*': ('Shopping', 0.95),
            r'URBAN\s*OUTFITTERS.*': ('Shopping', 0.95),
            r'FOOT\s*LOCKER.*': ('Shopping', 0.95),
            r'GAMESTOP.*': ('Shopping', 0.95),
            r'BARNES.*NOBLE.*': ('Shopping', 0.95),
            r'STAPLES.*': ('Shopping', 0.95),
            r'OFFICE\s*DEPOT.*': ('Shopping', 0.95),
            r'OFFICEMAX.*': ('Shopping', 0.95),
            r'GUITAR\s*CENTER.*': ('Shopping', 0.95),
            r'ZAPPOS.*': ('Shopping', 0.95),
            r'OVERSTOCK.*': ('Shopping', 0.95),
            r'QVC.*': ('Shopping', 0.95),
            r'HSN.*': ('Shopping', 0.90),
            r'AMERICAN\s*EAGLE.*': ('Shopping', 0.95),
            r'KMART.*': ('Shopping', 0.95),
            r'PETSMART.*': ('Shopping', 0.95),
            r'PETCO.*': ('Shopping', 0.95),

            # Entertainment - Extended
            r'AMAZON\s*PRIME\s*VIDEO.*': ('Entertainment', 0.95),
            r'PRIME\s*VIDEO.*': ('Entertainment', 0.95),
            r'APPLE\s*MUSIC.*': ('Entertainment', 0.95),
            r'TIDAL.*': ('Entertainment', 0.95),
            r'PANDORA.*': ('Entertainment', 0.95),
            r'SLING\s*TV.*': ('Entertainment', 0.95),
            r'VUDU.*': ('Entertainment', 0.95),
            r'FUBOTV.*': ('Entertainment', 0.95),
            r'CRUNCHYROLL.*': ('Entertainment', 0.95),
            r'FUNIMATION.*': ('Entertainment', 0.95),
            r'SHUDDER.*': ('Entertainment', 0.95),
            r'BRITBOX.*': ('Entertainment', 0.95),
            r'STARZ.*': ('Entertainment', 0.95),
            r'SHOWTIME.*': ('Entertainment', 0.95),
            r'AMC\s*PLUS.*': ('Entertainment', 0.95),
            r'DISCOVERY\s*PLUS.*': ('Entertainment', 0.95),
            r'PHILO.*': ('Entertainment', 0.95),
            r'MUBI.*': ('Entertainment', 0.95),
            r'CRITERION.*': ('Entertainment', 0.95),
            r'RACELAB.*': ('Entertainment', 0.95),
            r'APEX\s*RACING.*': ('Entertainment', 0.95),
            r'IRACING.*': ('Entertainment', 0.95),
            r'SIM\s*RACING.*': ('Entertainment', 0.95),
            r'NINTENDO.*': ('Entertainment', 0.95),
            r'EPIC\s*GAMES.*': ('Entertainment', 0.95),
            r'BLIZZARD.*': ('Entertainment', 0.95),
            r'RIOT\s*GAMES.*': ('Entertainment', 0.95),
            r'TWITCH.*': ('Entertainment', 0.95),
            r'YOUTUBE\s*(?!PREMIUM|TV|MUSIC).*': ('Entertainment', 0.90),
            # OpenAI Expansion - Entertainment
            r'AUDIBLE.*': ('Entertainment', 0.95),
            r'SIRIUS\s*XM.*': ('Entertainment', 0.95),
            r'SOUNDCLOUD.*': ('Entertainment', 0.95),
            r'BANDCAMP.*': ('Entertainment', 0.95),
            r'REDBOX.*': ('Entertainment', 0.95),
            r'FANDANGO.*': ('Entertainment', 0.95),
            r'AMC\s*THEATRE.*': ('Entertainment', 0.95),
            r'REGAL\s*CINEMA.*': ('Entertainment', 0.95),
            r'CINEMARK.*': ('Entertainment', 0.95),
            r'ALAMO\s*DRAFTHOUSE.*': ('Entertainment', 0.95),
            r'TICKETMASTER.*': ('Entertainment', 0.95),
            r'STUBHUB.*': ('Entertainment', 0.95),
            r'LIVE\s*NATION.*': ('Entertainment', 0.95),
            r'EVENTBRITE.*': ('Entertainment', 0.95),
            r'PATREON.*': ('Entertainment', 0.90),
            r'KICKSTARTER.*': ('Entertainment', 0.85),
            r'DEEZER.*': ('Entertainment', 0.95),
            r'NAPSTER.*': ('Entertainment', 0.95),

            # Software/Subscriptions - Extended
            r'DROPBOX.*': ('Software', 0.95),
            r'ZOOM\s*VIDEO.*': ('Software', 0.95),
            r'SLACK.*': ('Software', 0.95),
            r'SALESFORCE.*': ('Software', 0.95),
            r'QUICKBOOKS.*': ('Software', 0.95),
            r'INTUIT.*': ('Software', 0.95),
            r'MAILCHIMP.*': ('Software', 0.95),
            r'EVERNOTE.*': ('Software', 0.95),
            r'NOTION.*': ('Software', 0.95),
            r'ASANA.*': ('Software', 0.95),
            r'TRELLO.*': ('Software', 0.95),
            r'MONDAY\.COM.*': ('Software', 0.95),
            r'GRAMMARLY.*': ('Software', 0.95),
            r'NORDVPN.*': ('Software', 0.95),
            r'EXPRESSVPN.*': ('Software', 0.95),
            r'NORTON.*': ('Software', 0.95),
            r'MCAFEE.*': ('Software', 0.95),
            r'KASPERSKY.*': ('Software', 0.95),
            r'LINKEDIN\s*PREMIUM.*': ('Software', 0.95),
            r'COURSERA.*': ('Software', 0.95),
            r'UDEMY.*': ('Software', 0.95),
            r'SKILLSHARE.*': ('Software', 0.95),
            r'MASTERCLASS.*': ('Software', 0.95),
            r'EASYNEWS.*': ('Software', 0.95),
            r'USENET.*': ('Software', 0.95),
            # OpenAI Expansion - Software
            r'SAP\s.*': ('Software', 0.95),
            r'ORACLE.*': ('Software', 0.95),
            r'HUBSPOT.*': ('Software', 0.95),
            r'ZENDESK.*': ('Software', 0.95),
            r'SMARTSHEET.*': ('Software', 0.95),
            r'DOCUSIGN.*': ('Software', 0.95),
            r'HELLOSIGN.*': ('Software', 0.95),
            r'LASTPASS.*': ('Software', 0.95),
            r'1PASSWORD.*': ('Software', 0.95),
            r'BITDEFENDER.*': ('Software', 0.95),
            r'AVG.*ANTIVIRUS.*': ('Software', 0.95),
            r'AVAST.*': ('Software', 0.95),
            r'ESET.*': ('Software', 0.95),
            r'MALWAREBYTES.*': ('Software', 0.95),
            r'TEAMVIEWER.*': ('Software', 0.95),
            r'LOGMEIN.*': ('Software', 0.95),
            r'GOTOMEETING.*': ('Software', 0.95),
            r'WEBEX.*': ('Software', 0.95),
            r'BLUEJEANS.*': ('Software', 0.95),
            r'RINGCENTRAL.*': ('Software', 0.95),
            r'FRESHBOOKS.*': ('Software', 0.95),
            r'XERO.*': ('Software', 0.95),
            r'WAVE\s*ACCOUNTING.*': ('Software', 0.95),
            r'ZOHO.*': ('Software', 0.95),
            r'BASECAMP.*': ('Software', 0.95),
            r'TODOIST.*': ('Software', 0.95),
            r'POCKET\s.*': ('Software', 0.90),
            r'FEEDLY.*': ('Software', 0.95),
            r'ACAST.*': ('Software', 0.95),
            r'BUZZSPROUT.*': ('Software', 0.95),
            r'ANCHOR\s*FM.*': ('Software', 0.95),
            r'PODBEAN.*': ('Software', 0.95),
            r'LIBSYN.*': ('Software', 0.95),
            r'ADOBE.*': ('Software', 0.95),

            # Bills & Utilities - Extended
            r'XFINITY.*': ('Bills & Utilities', 0.95),
            r'COMCAST.*': ('Bills & Utilities', 0.95),
            r'PG&E.*': ('Bills & Utilities', 0.95),
            r'CON\s*EDISON.*': ('Bills & Utilities', 0.95),
            r'SOUTHERN\s*COMPANY.*': ('Bills & Utilities', 0.95),
            r'T-MOBILE.*': ('Bills & Utilities', 0.95),
            r'TMOBILE.*': ('Bills & Utilities', 0.95),
            r'SPRINT.*': ('Bills & Utilities', 0.95),
            r'FRONTIER.*COMM.*': ('Bills & Utilities', 0.95),
            r'COX\s*COMM.*': ('Bills & Utilities', 0.95),
            r'CENTURYLINK.*': ('Bills & Utilities', 0.95),
            r'NATIONAL\s*GRID.*': ('Bills & Utilities', 0.95),
            r'CITY\s*OF\s*RALEIGH.*': ('Bills & Utilities', 0.95),
            r'CITY\s*OF\s*.*UTIL.*': ('Bills & Utilities', 0.95),
            r'WATER\s*UTILITY.*': ('Bills & Utilities', 0.95),
            r'SEWER\s*UTILITY.*': ('Bills & Utilities', 0.95),
            r'REPUBLIC\s*SERVICES.*': ('Bills & Utilities', 0.95),
            r'WASTE\s*MANAGEMENT.*': ('Bills & Utilities', 0.95),
            r'ADT\s*SECURITY.*': ('Bills & Utilities', 0.95),
            r'VIVINT.*': ('Bills & Utilities', 0.95),
            r'SIMPLISAFE.*': ('Bills & Utilities', 0.95),
            # OpenAI Expansion - Bills & Utilities
            r'FLORIDA\s*POWER.*': ('Bills & Utilities', 0.95),
            r'FPL\s.*': ('Bills & Utilities', 0.95),
            r'PSE&G.*': ('Bills & Utilities', 0.95),
            r'PSEG.*': ('Bills & Utilities', 0.95),
            r'AMEREN.*': ('Bills & Utilities', 0.95),
            r'ENTERGY.*': ('Bills & Utilities', 0.95),
            r'FIRSTENERGY.*': ('Bills & Utilities', 0.95),
            r'DTE\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'CONSUMERS\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'XCEL\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'PUGET\s*SOUND\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'AVISTA.*': ('Bills & Utilities', 0.95),
            r'NV\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'ROCKY\s*MOUNTAIN\s*POWER.*': ('Bills & Utilities', 0.95),
            r'PIEDMONT\s*NATURAL.*': ('Bills & Utilities', 0.95),
            r'ATMOS\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'CENTERPOINT\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'NICOR\s*GAS.*': ('Bills & Utilities', 0.95),
            r'PEOPLES\s*GAS.*': ('Bills & Utilities', 0.95),
            r'SEMPRA\s*ENERGY.*': ('Bills & Utilities', 0.95),
            r'SDGE.*': ('Bills & Utilities', 0.95),
            r'SAN\s*DIEGO\s*GAS.*': ('Bills & Utilities', 0.95),
            r'LADWP.*': ('Bills & Utilities', 0.95),

            # Financial Services - Extended
            r'AFFIRM.*': ('Financial Services', 0.95),
            r'KLARNA.*': ('Financial Services', 0.95),
            r'AFTERPAY.*': ('Financial Services', 0.95),
            r'AVANT.*': ('Financial Services', 0.95),
            r'SOFI.*': ('Financial Services', 0.95),
            r'LENDING\s*CLUB.*': ('Financial Services', 0.95),
            r'UPSTART.*': ('Financial Services', 0.95),
            r'MARCUS.*': ('Financial Services', 0.95),
            r'ALLY\s*(BANK)?.*': ('Financial Services', 0.95),
            r'SYNCHRONY.*': ('Financial Services', 0.95),
            r'DISCOVER\s*(CARD)?.*': ('Financial Services', 0.95),
            r'CAPITAL\s*ONE.*': ('Financial Services', 0.95),
            r'AMERICAN\s*EXPRESS.*': ('Financial Services', 0.95),
            r'AMEX.*': ('Financial Services', 0.95),
            r'CHASE\s*(CARD)?.*': ('Financial Services', 0.95),
            r'CITI\s*(CARD)?.*': ('Financial Services', 0.95),
            r'WELLS\s*FARGO.*': ('Financial Services', 0.95),
            r'IDENTITYIQ.*': ('Financial Services', 0.95),
            r'IIQ\s*.*': ('Financial Services', 0.95),
            r'CREDIT\s*KARMA.*': ('Financial Services', 0.95),
            r'EXPERIAN.*': ('Financial Services', 0.95),
            r'EQUIFAX.*': ('Financial Services', 0.95),
            r'TRANSUNION.*': ('Financial Services', 0.95),

            # Healthcare - Extended
            r'CVS.*': ('Healthcare', 0.95),
            r'WALGREENS.*': ('Healthcare', 0.95),
            r'RITE\s*AID.*': ('Healthcare', 0.95),
            r'PHARMACY.*': ('Healthcare', 0.90),
            r'EXPRESS\s*SCRIPTS.*': ('Healthcare', 0.95),
            r'CAREMARK.*': ('Healthcare', 0.95),
            r'OPTUM.*': ('Healthcare', 0.95),
            r'UNITED\s*HEALTH.*': ('Healthcare', 0.95),
            r'ANTHEM.*': ('Healthcare', 0.95),
            r'AETNA.*': ('Healthcare', 0.95),
            r'CIGNA.*': ('Healthcare', 0.95),
            r'HUMANA.*': ('Healthcare', 0.95),
            r'BLUE\s*CROSS.*': ('Healthcare', 0.95),
            r'BCBS.*': ('Healthcare', 0.95),
            r'KAISER.*': ('Healthcare', 0.95),
            r'DENTAL.*': ('Healthcare', 0.90),
            r'VISION.*': ('Healthcare', 0.85),
            r'CLINIC.*': ('Healthcare', 0.85),
            r'HOSPITAL.*': ('Healthcare', 0.90),
            r'URGENT\s*CARE.*': ('Healthcare', 0.95),
            r'LABCORP.*': ('Healthcare', 0.95),
            r'QUEST\s*DIAG.*': ('Healthcare', 0.95),

            # Home Services
            r'SOLVE\s*PEST.*': ('Home Services', 0.95),
            r'TERMINIX.*': ('Home Services', 0.95),
            r'ORKIN.*': ('Home Services', 0.95),
            r'PEST\s*CONTROL.*': ('Home Services', 0.95),
            r'LAWN\s*CARE.*': ('Home Services', 0.95),
            r'LANDSCAP.*': ('Home Services', 0.95),
            r'CLEANING\s*SERVICE.*': ('Home Services', 0.95),
            r'MAID.*SERVICE.*': ('Home Services', 0.95),
            r'MERRY\s*MAIDS.*': ('Home Services', 0.95),
            r'PLUMB.*': ('Home Services', 0.85),
            r'ELECTRIC.*SERVICE.*': ('Home Services', 0.85),
            r'HVAC.*': ('Home Services', 0.90),

            # Transfers - Extended
            r'WESTERN\s*UNION.*': ('Transfers', 0.95),
            r'MONEYGRAM.*': ('Transfers', 0.95),
            r'WISE\s*(TRANSFER)?.*': ('Transfers', 0.95),
            r'TRANSFERWISE.*': ('Transfers', 0.95),
            r'REMITLY.*': ('Transfers', 0.95),
            r'XOOM.*': ('Transfers', 0.95),
            r'WORLDREMIT.*': ('Transfers', 0.95),
            r'COINBASE.*': ('Transfers', 0.95),
            r'ROBINHOOD.*': ('Transfers', 0.95),
            r'CHIME.*': ('Transfers', 0.95),
            r'SQUARE\s*CASH.*': ('Transfers', 0.95),
        }
    
    def _load_context_patterns(self) -> Dict[str, Tuple[str, float]]:
        """Context-aware patterns for better categorization

        IMPORTANT: Order matters! Income patterns are checked first to avoid
        misclassifying payroll as transfers. Patterns are returned in a dict
        but we process them in priority order in _match_context_patterns_ordered.
        """
        return {
            # ==========================================
            # INCOME PATTERNS (HIGHEST PRIORITY - 0.99)
            # These MUST match before transfer patterns
            # ==========================================
            r'PAYROLL.*': ('Income', 0.99),
            r'DIRECT\s*DEPOSIT.*': ('Income', 0.99),
            r'SALARY.*': ('Income', 0.99),
            r'WAGES.*': ('Income', 0.99),
            # ACH payroll from employers (DES: indicates ACH with employer name)
            r'.*DES:\s*(PAYROLL|SALARY|WAGES|PAY\s).*': ('Income', 0.99),
            # Employer direct deposits - match "DES:COMPANY_NAME" pattern for credits
            r'.*DES:\s*[A-Z]{2,}.*ID:\d+.*': ('Income', 0.85),  # Generic ACH from company
            # Bank rewards and cashback (these are income!)
            r'BANKAMERIDEALS\s*CASHBACK.*': ('Income', 0.98),
            r'PREFERRED\s*REWARDS.*REBATE.*': ('Income', 0.98),
            r'.*CASHREWARD.*': ('Income', 0.98),
            r'CASH\s*BACK.*REWARD.*': ('Income', 0.95),
            r'CASHBACK.*': ('Income', 0.90),
            r'.*REBATE.*REFUND.*': ('Income', 0.90),
            r'INTEREST\s*(PAYMENT|EARNED).*': ('Income', 0.95),
            r'DIVIDEND.*': ('Income', 0.95),
            r'TAX\s*REFUND.*': ('Income', 0.98),

            # ==========================================
            # P2P TRANSFER PATTERNS (HIGH PRIORITY - 0.98)
            # Cash App, Venmo, PayPal person-to-person
            # ==========================================
            r'CASH\s*APP\s*\*.*': ('Transfers', 0.98),
            r'PMNT\s*SENT.*CASH\s*APP.*': ('Transfers', 0.98),
            r'VENMO\s*\*.*': ('Transfers', 0.98),
            r'PMNT\s*SENT.*VENMO.*': ('Transfers', 0.98),
            r'PAYPAL\s*TRANSFER.*': ('Transfers', 0.95),
            # Zelle patterns
            r'ZELLE\s*(PAYMENT|TRANSFER|FROM|TO).*': ('Zelle', 0.98),

            # ==========================================
            # INTERNAL TRANSFER PATTERNS (HIGH PRIORITY)
            # Only match INTERNAL account transfers (SAV, CHK, etc.)
            # ==========================================
            r'ONLINE\s*BANKING\s*TRANSFER\s*FROM\s*SAV.*': ('Internal Transfer', 0.98),
            r'ONLINE\s*BANKING\s*TRANSFER\s*TO\s*SAV.*': ('Internal Transfer', 0.98),
            r'ONLINE\s*BANKING\s*TRANSFER\s*FROM\s*CHK.*': ('Internal Transfer', 0.98),
            r'ONLINE\s*BANKING\s*TRANSFER\s*TO\s*CHK.*': ('Internal Transfer', 0.98),
            r'ONLINE\s*BANKING\s*TRANSFER\s*FROM\s*BRK.*': ('Internal Transfer', 0.98),
            r'ONLINE\s*BANKING\s*TRANSFER\s*TO\s*BRK.*': ('Internal Transfer', 0.98),
            r'KEEP\s*THE\s*CHANGE\s*TRANSFER.*': ('Internal Transfer', 0.98),
            r'AUTO(MATIC)?\s*TRANSFER\s*TO\s*(SAV|SAVINGS).*': ('Internal Transfer', 0.98),
            r'TRANSFER\s*FROM\s*(CHK|SAV|BRK)\s*\d+.*': ('Internal Transfer', 0.95),
            r'TRANSFER\s*TO\s*(CHK|SAV|BRK)\s*\d+.*': ('Internal Transfer', 0.95),

            # ==========================================
            # BANKING PATTERNS
            # ==========================================
            r'ATM\s*(WITHDRAWAL|DEPOSIT).*': ('Banking', 0.95),
            r'BKOFAMERICA\s*ATM.*DEPOSIT.*': ('Banking', 0.95),
            r'OVERDRAFT.*': ('Banking', 0.95),
            r'MAINTENANCE\s*FEE.*': ('Banking', 0.95),
            r'WIRE\s*TRANSFER\s*FEE.*': ('Banking', 0.95),
            r'MONTHLY\s*SERVICE\s*FEE.*': ('Banking', 0.95),

            # ==========================================
            # FINANCIAL SERVICES (Loans, payments, etc.)
            # ==========================================
            r'AVANT\s*LLC.*': ('Financial Services', 0.95),
            r'.*LOAN\s*PAYMENT.*': ('Financial Services', 0.90),
            r'CITI\s*AUTOPAY.*': ('Financial Services', 0.95),
            r'ROCKET\s*MONEY.*': ('Financial Services', 0.95),
            r'ALBERT\s*GENIUS.*': ('Financial Services', 0.95),
            r'IRS\s*.*USATAXPYMT.*': ('Financial Services', 0.98),

            # ==========================================
            # PURCHASE PATTERNS (LOW CONFIDENCE - FALLBACK)
            # ==========================================
            r'CHECKCARD.*PURCHASE.*': ('Shopping', 0.60),
            r'PURCHASE\s+\d+.*': ('Shopping', 0.50),
        }
    
    def _load_amount_categories(self) -> List[Tuple[Tuple[float, float], str, float]]:
        """Amount-based categorization rules"""
        return [
            # (amount_range, category, confidence_boost)
            ((-10000, -3000), 'Mortgage Payment', 0.3),  # Large negative amounts
            ((-3000, -1000), 'Bills & Utilities', 0.2),  # Medium-large bills
            ((-200, -50), 'Shopping', 0.1),              # Shopping range
            ((-50, -10), 'Food & Dining', 0.1),          # Meal range
            ((-10, -1), 'Food & Dining', 0.2),           # Small purchases
            ((0.01, 10), 'Income', 0.2),                 # Small credits
            ((10, 100), 'Income', 0.1),                  # Medium credits
            ((1000, 10000), 'Income', 0.3),              # Large credits (salary)
        ]
    
    def _load_enhanced_category_keywords(self) -> Dict[str, List[Tuple[str, float]]]:
        """Enhanced keywords with individual confidence weights"""
        return {
            'Food & Dining': [
                ('restaurant', 0.8), ('cafe', 0.8), ('coffee', 0.7), ('pizza', 0.9),
                ('burger', 0.8), ('food', 0.6), ('dining', 0.8), ('kitchen', 0.7),
                ('grill', 0.8), ('bistro', 0.8), ('diner', 0.8), ('bar', 0.6),
                ('pub', 0.7), ('tavern', 0.7), ('steakhouse', 0.9)
            ],
            'Grocery': [
                ('market', 0.8), ('grocery', 0.9), ('groceries', 0.9), ('supermarket', 0.9),
                ('fresh', 0.6), ('produce', 0.8), ('organic', 0.7)
            ],
            'Gas & Automotive': [
                ('gas', 0.8), ('fuel', 0.8), ('automotive', 0.7), ('auto', 0.6),
                ('service', 0.5), ('repair', 0.7), ('tire', 0.8), ('oil', 0.7)
            ],
            'Transportation': [
                ('uber', 0.9), ('lyft', 0.9), ('taxi', 0.9), ('rideshare', 0.9),
                ('metro', 0.8), ('bus', 0.8), ('train', 0.8), ('subway', 0.8),
                ('parking', 0.8), ('toll', 0.8), ('airport', 0.6)
            ],
            'Entertainment': [
                ('movie', 0.8), ('theater', 0.8), ('cinema', 0.8), ('game', 0.6),
                ('gaming', 0.7), ('streaming', 0.8), ('music', 0.6), ('concert', 0.8),
                ('show', 0.6), ('event', 0.5), ('tickets', 0.6)
            ],
            'Bills & Utilities': [
                ('electric', 0.9), ('electricity', 0.9), ('water', 0.9), ('sewer', 0.9),
                ('internet', 0.8), ('cable', 0.8), ('phone', 0.7), ('wireless', 0.7),
                ('utility', 0.8), ('energy', 0.8), ('power', 0.7)
            ],
            'Healthcare': [
                ('doctor', 0.9), ('medical', 0.8), ('health', 0.7), ('hospital', 0.9),
                ('clinic', 0.8), ('pharmacy', 0.9), ('dental', 0.9), ('dentist', 0.9),
                ('prescription', 0.8), ('medicine', 0.8), ('urgent', 0.7)
            ],
            'Shopping': [
                ('store', 0.7), ('shop', 0.7), ('retail', 0.7), ('purchase', 0.5),
                ('buy', 0.5), ('mall', 0.7), ('outlet', 0.7), ('marketplace', 0.7)
            ],
            'Technology': [
                ('software', 0.8), ('app', 0.7), ('digital', 0.6), ('online', 0.5),
                ('tech', 0.7), ('computer', 0.8), ('laptop', 0.8), ('phone', 0.6)
            ]
        }
    
    def _load_confidence_weights(self) -> Dict[str, float]:
        """Confidence weights for different matching types"""
        return {
            'exact_merchant': 0.95,
            'merchant_pattern': 0.90,
            'context_pattern': 0.85,
            'keyword_strong': 0.75,
            'keyword_medium': 0.65,
            'keyword_weak': 0.50,
            'amount_based': 0.30,
            'fallback': 0.40
        }
    
    def categorize_transaction(self, description: str, amount: float) -> List[EnhancedCategorySuggestion]:
        """Enhanced transaction categorization"""
        suggestions = []
        description_clean = description.strip()
        description_upper = description_clean.upper()
        description_lower = description_clean.lower()
        
        # Step 1: Enhanced merchant pattern matching
        merchant_suggestions = self._match_merchant_patterns(description_upper, description_lower)
        suggestions.extend(merchant_suggestions)

        # Step 2: Context-aware pattern matching (pass amount for income detection)
        context_suggestions = self._match_context_patterns(description_upper, description_lower, amount)
        suggestions.extend(context_suggestions)
        
        # Step 3: Enhanced keyword matching (only if no high-confidence matches)
        if not any(s.confidence > 0.8 for s in suggestions):
            keyword_suggestions = self._match_keywords(description_lower, amount)
            suggestions.extend(keyword_suggestions)
        
        # Step 4: Amount-based classification boost
        suggestions = self._apply_amount_boosts(suggestions, amount)

        # Step 5: Remove duplicates, apply tie-breaking, and sort by confidence
        suggestions = self._deduplicate_and_rank(suggestions, amount)
        
        # Step 6: Ensure we have at least one suggestion
        if not suggestions:
            suggestions.append(self._fallback_categorization(description_lower, amount))
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def _match_merchant_patterns(self, desc_upper: str, desc_lower: str) -> List[EnhancedCategorySuggestion]:
        """Match against enhanced merchant patterns"""
        suggestions = []

        for pattern, (category, base_confidence) in self.enhanced_merchant_patterns.items():
            if re.search(pattern, desc_upper, re.IGNORECASE):
                # Get clean merchant name from mapping, or derive from pattern
                merchant_name = self.merchant_name_map.get(pattern)
                if not merchant_name:
                    # Fallback: try to extract from pattern (e.g., "RACELAB.*" -> "Racelab")
                    merchant_name = self._extract_merchant_from_pattern(pattern)

                suggestions.append(EnhancedCategorySuggestion(
                    category_name=category,
                    confidence=base_confidence,
                    reasoning=f"Merchant pattern matched: {pattern}",
                    match_type='merchant_pattern',
                    keywords_matched=[pattern],
                    confidence_factors={'merchant_pattern': base_confidence},
                    merchant_name=merchant_name
                ))
                break  # Take first match for specificity

        return suggestions

    def _extract_merchant_from_pattern(self, pattern: str) -> Optional[str]:
        """Extract a readable merchant name from a regex pattern"""
        # Remove regex special chars and extract core word
        # e.g., r'RACELAB.*' -> 'Racelab', r'BURGER\s*KING.*' -> 'Burger King'
        cleaned = pattern.replace(r'\s*', ' ').replace(r'\s+', ' ')
        cleaned = re.sub(r'[\.\*\+\?\[\]\(\)\{\}\|\^\\$]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if cleaned:
            # Title case it
            return cleaned.title()
        return None

    def _extract_p2p_counterparty(self, description: str) -> Optional[str]:
        """Extract counterparty name from P2P transaction descriptions.

        Examples:
        - "pmnt sent 1210 venmo *mai elm new york ny" -> "Mai Elm"
        - "zelle payment from marwan s moftah conf#..." -> "Marwan S Moftah"
        - "cash app *john doe" -> "John Doe"
        - "paypal *jane smith" -> "Jane Smith"
        """
        desc_upper = description.upper()
        desc_clean = description.strip()

        # Venmo: "VENMO *NAME" or "PMNT SENT ... VENMO *NAME CITY STATE"
        # Strategy: Find "VENMO *" then capture 1-3 words, stop before STATE code pattern
        # Common pattern: "VENMO *FIRST LAST CITY ST" where ST is 2-letter state code
        # Look for pattern ending with " XX" where XX is a 2-letter state code
        venmo_match = re.search(r'VENMO\s*\*\s*([A-Z][A-Z]+(?:\s+[A-Z]+)?)\s+[A-Z]+\s+[A-Z]{2}\b', desc_upper)
        if venmo_match:
            name = venmo_match.group(1).strip()
            name = re.sub(r'\s+', ' ', name).strip()
            if len(name) >= 2:
                return name.title()
        # Fallback: capture 1-2 words after VENMO *
        venmo_match2 = re.search(r'VENMO\s*\*\s*([A-Z][A-Z]+(?:\s+[A-Z]+)?)', desc_upper)
        if venmo_match2:
            name = venmo_match2.group(1).strip()
            name = re.sub(r'\s+', ' ', name).strip()
            # Avoid capturing city names (usually 4+ letters, common patterns)
            words = name.split()
            if len(words) >= 2:
                # Take first two words as first/last name
                name = ' '.join(words[:2])
            if len(name) >= 2:
                return name.title()

        # Zelle: "ZELLE PAYMENT FROM/TO NAME CONF#..."
        zelle_match = re.search(r'ZELLE\s+(?:PAYMENT\s+)?(?:FROM|TO)\s+([A-Z][A-Z\s]+?)(?:\s+CONF|$)', desc_upper)
        if zelle_match:
            name = zelle_match.group(1).strip()
            name = re.sub(r'\s+', ' ', name).strip()
            if len(name) >= 2:
                return name.title()

        # Cash App: "CASH APP *NAME" or "CASHAPP *NAME"
        cashapp_match = re.search(r'CASH\s*APP\s*\*\s*([A-Z][A-Z\s]+?)(?:\s+\d|$)', desc_upper)
        if cashapp_match:
            name = cashapp_match.group(1).strip()
            name = re.sub(r'\s+', ' ', name).strip()
            if len(name) >= 2:
                return name.title()

        # PayPal person-to-person: "PAYPAL *NAME" (not PAYPAL *MERCHANT)
        paypal_match = re.search(r'PAYPAL\s*\*\s*([A-Z][A-Z\s]+?)(?:\s+\d|$)', desc_upper)
        if paypal_match:
            name = paypal_match.group(1).strip()
            # Skip if it looks like a merchant (all caps common words)
            merchant_indicators = ['LLC', 'INC', 'CORP', 'STORE', 'SHOP', 'GAMES', 'RACING']
            if not any(ind in name for ind in merchant_indicators):
                name = re.sub(r'\s+', ' ', name).strip()
                if len(name) >= 2:
                    return name.title()

        return None
    
    def _match_context_patterns(self, desc_upper: str, desc_lower: str, amount: float = 0) -> List[EnhancedCategorySuggestion]:
        """Match against context-aware patterns with priority ordering.

        IMPORTANT: This method now considers amount sign for income detection.
        Income patterns only match for credits (amount > 0).
        Transfer patterns only match for debits (amount < 0) when it's a payment sent.
        """
        suggestions = []

        # Define priority groups - process in this order
        income_patterns = {}
        transfer_patterns = {}
        other_patterns = {}

        for pattern, (category, base_confidence) in self.context_patterns.items():
            if category == 'Income':
                income_patterns[pattern] = (category, base_confidence)
            elif category in ('Transfers', 'Internal Transfer', 'Zelle'):
                transfer_patterns[pattern] = (category, base_confidence)
            else:
                other_patterns[pattern] = (category, base_confidence)

        # STEP 1: Check income patterns FIRST (only for credits)
        if amount > 0:  # Credits - could be income
            for pattern, (category, base_confidence) in income_patterns.items():
                if re.search(pattern, desc_upper, re.IGNORECASE):
                    # Boost confidence for large recurring amounts (likely salary)
                    conf = base_confidence
                    if amount > 1000:
                        conf = min(0.99, conf + 0.05)
                    suggestions.append(EnhancedCategorySuggestion(
                        category_name=category,
                        confidence=conf,
                        reasoning=f"Income pattern matched (credit ${amount:.2f}): {pattern[:40]}...",
                        match_type='context_pattern_income',
                        keywords_matched=[pattern],
                        confidence_factors={'context_pattern': conf, 'is_credit': True}
                    ))

        # STEP 2: Check transfer patterns
        for pattern, (category, base_confidence) in transfer_patterns.items():
            if re.search(pattern, desc_upper, re.IGNORECASE):
                # For P2P transfers, only high confidence if it's a debit (payment sent)
                conf = base_confidence
                if amount < 0 and 'PMNT SENT' in desc_upper:
                    conf = min(0.99, conf + 0.05)  # Boost for confirmed outgoing

                # Extract P2P counterparty name for display
                # Use original description (not upper) for better name extraction
                original_desc = desc_lower  # This preserves case better
                counterparty = self._extract_p2p_counterparty(desc_upper)
                merchant_name = None
                if counterparty:
                    # Format as "Venmo - John Doe" or "Zelle - Jane Smith"
                    if 'VENMO' in desc_upper:
                        merchant_name = f"Venmo → {counterparty}"
                    elif 'ZELLE' in desc_upper:
                        merchant_name = f"Zelle → {counterparty}"
                    elif 'CASH APP' in desc_upper or 'CASHAPP' in desc_upper:
                        merchant_name = f"Cash App → {counterparty}"
                    elif 'PAYPAL' in desc_upper:
                        merchant_name = f"PayPal → {counterparty}"
                    else:
                        merchant_name = counterparty
                else:
                    # Fallback to service name
                    if 'VENMO' in desc_upper:
                        merchant_name = 'Venmo'
                    elif 'ZELLE' in desc_upper:
                        merchant_name = 'Zelle'
                    elif 'CASH APP' in desc_upper or 'CASHAPP' in desc_upper:
                        merchant_name = 'Cash App'
                    elif 'WESTERN UNION' in desc_upper:
                        merchant_name = 'Western Union'

                suggestions.append(EnhancedCategorySuggestion(
                    category_name=category,
                    confidence=conf,
                    reasoning=f"Transfer pattern matched: {pattern[:40]}...",
                    match_type='context_pattern_transfer',
                    keywords_matched=[pattern],
                    confidence_factors={'context_pattern': conf},
                    merchant_name=merchant_name
                ))

        # STEP 3: Check other patterns (banking, financial services, etc.)
        for pattern, (category, base_confidence) in other_patterns.items():
            if re.search(pattern, desc_upper, re.IGNORECASE):
                suggestions.append(EnhancedCategorySuggestion(
                    category_name=category,
                    confidence=base_confidence,
                    reasoning=f"Context pattern matched: {pattern[:40]}...",
                    match_type='context_pattern',
                    keywords_matched=[pattern],
                    confidence_factors={'context_pattern': base_confidence}
                ))

        return suggestions
    
    def _match_keywords(self, desc_lower: str, amount: float) -> List[EnhancedCategorySuggestion]:
        """Enhanced keyword matching with weighted confidence"""
        category_scores = {}
        category_matches = {}
        
        for category, keyword_weights in self.category_keywords.items():
            total_score = 0
            matched_keywords = []
            
            for keyword, weight in keyword_weights:
                if keyword in desc_lower:
                    total_score += weight
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                # Calculate confidence based on total score and number of matches
                base_confidence = min(0.9, total_score / len(keyword_weights) * 2)
                match_boost = min(0.2, len(matched_keywords) * 0.05)
                final_confidence = min(0.9, base_confidence + match_boost)
                
                category_scores[category] = final_confidence
                category_matches[category] = matched_keywords
        
        # Convert to suggestions
        suggestions = []
        for category, confidence in sorted(category_scores.items(), key=lambda x: x[1], reverse=True):
            if confidence > 0.4:  # Minimum threshold
                suggestions.append(EnhancedCategorySuggestion(
                    category_name=category,
                    confidence=confidence,
                    reasoning=f"Keywords matched: {', '.join(category_matches[category][:3])}",
                    match_type='keyword_matching',
                    keywords_matched=category_matches[category],
                    confidence_factors={'keyword_score': confidence}
                ))
        
        return suggestions
    
    def _apply_amount_boosts(self, suggestions: List[EnhancedCategorySuggestion], amount: float) -> List[EnhancedCategorySuggestion]:
        """Apply amount-based confidence boosts"""
        for suggestion in suggestions:
            for (min_amt, max_amt), category, boost in self.amount_based_categories:
                if min_amt <= amount <= max_amt and suggestion.category_name == category:
                    suggestion.confidence = min(0.95, suggestion.confidence + boost)
                    suggestion.confidence_factors['amount_boost'] = boost
                    suggestion.reasoning += f" [Amount range match: ${min_amt}-${max_amt}]"
                    break
        
        return suggestions
    
    def _deduplicate_and_rank(self, suggestions: List[EnhancedCategorySuggestion], amount: float = 0) -> List[EnhancedCategorySuggestion]:
        """Remove duplicates and rank by confidence with tie-breaking.

        TIE-BREAKING RULES:
        1. For credits (amount > 0): Income beats Transfers/Banking if within 0.1 confidence
        2. For debits with "pmnt sent": Transfers beats Financial Services
        3. context_pattern_income match type gets priority for credits
        """
        seen_categories = {}

        for suggestion in suggestions:
            if suggestion.category_name not in seen_categories:
                seen_categories[suggestion.category_name] = suggestion
            else:
                # Keep the one with higher confidence
                existing = seen_categories[suggestion.category_name]
                if suggestion.confidence > existing.confidence:
                    seen_categories[suggestion.category_name] = suggestion
                else:
                    # Merge the reasoning and keywords
                    existing.reasoning += f"; {suggestion.reasoning}"
                    existing.keywords_matched.extend(suggestion.keywords_matched)
                    existing.confidence_factors.update(suggestion.confidence_factors)

        # Apply tie-breaking rules
        ranked = list(seen_categories.values())

        # TIE-BREAKER 1: For credits, boost Income if it's close to top
        if amount > 0:
            income_suggestion = seen_categories.get('Income')
            if income_suggestion:
                top_conf = max(s.confidence for s in ranked)
                # If Income is within 0.15 of top and it's from income pattern, boost it
                if (top_conf - income_suggestion.confidence) <= 0.15:
                    if income_suggestion.match_type == 'context_pattern_income':
                        income_suggestion.confidence = top_conf + 0.01
                        income_suggestion.reasoning += " [BOOSTED: Credit with income pattern]"
                    elif income_suggestion.confidence_factors.get('is_credit'):
                        income_suggestion.confidence = top_conf + 0.01
                        income_suggestion.reasoning += " [BOOSTED: Credit transaction]"

        # TIE-BREAKER 2: Transfers beats Financial Services for P2P payments
        transfers = seen_categories.get('Transfers')
        financial = seen_categories.get('Financial Services')
        if transfers and financial:
            # If both have similar confidence and it looks like P2P, boost Transfers
            if abs(transfers.confidence - financial.confidence) <= 0.1:
                if transfers.match_type == 'context_pattern_transfer':
                    transfers.confidence = financial.confidence + 0.01
                    transfers.reasoning += " [BOOSTED: P2P transfer pattern]"

        return sorted(seen_categories.values(), key=lambda x: x.confidence, reverse=True)
    
    def _fallback_categorization(self, desc_lower: str, amount: float) -> EnhancedCategorySuggestion:
        """Fallback categorization for unmatched transactions"""
        if amount > 0:
            if amount > 1000:
                return EnhancedCategorySuggestion(
                    category_name='Income',
                    confidence=0.6,
                    reasoning='Large credit amount suggests income',
                    match_type='amount_fallback',
                    keywords_matched=[],
                    confidence_factors={'amount_heuristic': 0.6}
                )
            else:
                return EnhancedCategorySuggestion(
                    category_name='Income',
                    confidence=0.4,
                    reasoning='Credit transaction - likely income or refund',
                    match_type='amount_fallback',
                    keywords_matched=[],
                    confidence_factors={'amount_heuristic': 0.4}
                )
        else:
            # Negative amounts
            if abs(amount) > 1000:
                return EnhancedCategorySuggestion(
                    category_name='Bills & Utilities',
                    confidence=0.5,
                    reasoning='Large debit amount suggests major bill',
                    match_type='amount_fallback',
                    keywords_matched=[],
                    confidence_factors={'amount_heuristic': 0.5}
                )
            elif abs(amount) < 50:
                return EnhancedCategorySuggestion(
                    category_name='Food & Dining',
                    confidence=0.4,
                    reasoning='Small debit amount suggests food/dining',
                    match_type='amount_fallback',
                    keywords_matched=[],
                    confidence_factors={'amount_heuristic': 0.4}
                )
            else:
                return EnhancedCategorySuggestion(
                    category_name='Shopping',
                    confidence=0.4,
                    reasoning='Medium debit amount suggests shopping',
                    match_type='amount_fallback',
                    keywords_matched=[],
                    confidence_factors={'amount_heuristic': 0.4}
                )
    
    def convert_to_category_suggestions(self, enhanced_suggestions: List[EnhancedCategorySuggestion]) -> List[CategorySuggestion]:
        """Convert to standard CategorySuggestion format for compatibility"""
        return [
            CategorySuggestion(
                category_id=None,
                category_name=s.category_name,
                confidence=s.confidence,
                reasoning=s.reasoning,
                merchant_name=s.merchant_name
            )
            for s in enhanced_suggestions
        ]


# Global instance
_enhanced_categorization_service = None

def get_enhanced_categorization_service() -> EnhancedCategorizationService:
    """Get the global enhanced categorization service instance"""
    global _enhanced_categorization_service
    if _enhanced_categorization_service is None:
        _enhanced_categorization_service = EnhancedCategorizationService()
    return _enhanced_categorization_service


def categorize_transaction_enhanced(description: str, amount: float) -> List[CategorySuggestion]:
    """Enhanced transaction categorization - main function to use"""
    service = get_enhanced_categorization_service()
    enhanced_suggestions = service.categorize_transaction(description, amount)
    return service.convert_to_category_suggestions(enhanced_suggestions)