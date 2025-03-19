from enum import Enum
import re
import json
import os
from collections import defaultdict

class BillType(Enum):
    """Enumeration of supported bill types"""
    MOBILE = "mobile"
    INTERNET = "internet"
    UTILITY = "utility"
    CREDIT_CARD = "credit_card"
    CABLE_TV = "cable_tv"
    INSURANCE = "insurance"
    UNKNOWN = "unknown"

class BillTypeHandler:
    """
    Handles detection and processing of different bill types.
    Each bill type may have specific patterns and processing rules.
    """
    
    def __init__(self, config=None):
        """
        Initialize the bill type handler with optional configuration.
        
        Args:
            config (dict, optional): Configuration options.
        """
        self.config = config or {}
        self.bill_type_patterns = self._load_bill_type_patterns()
        self.provider_mappings = self._load_provider_mappings()
    
    def detect_bill_type(self, document_data):
        """
        Detect the type of bill from document text.
        
        Args:
            document_data (dict): Extracted document data.
            
        Returns:
            str: Detected bill type (one of BillType values).
        """
        text = document_data.get('full_text', '').lower()
        
        # Try to detect from service provider first
        provider = document_data.get('structured_data', {}).get('service_provider')
        if provider:
            detected_type = self._detect_from_provider(provider)
            if detected_type != BillType.UNKNOWN.value:
                return detected_type
        
        # Then try to detect from text patterns
        scores = defaultdict(int)
        
        for bill_type, patterns in self.bill_type_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                scores[bill_type] += len(matches)
        
        if not scores:
            return BillType.UNKNOWN.value
        
        # Return the type with highest score
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def get_bill_type_config(self, bill_type):
        """
        Get configuration specific to a bill type.
        
        Args:
            bill_type (str): Type of bill.
            
        Returns:
            dict: Bill type specific configuration.
        """
        # Return specific configuration for the bill type if available
        # This could include fee patterns, typical fees, etc.
        return {
            'questionable_fee_patterns': self._get_questionable_fee_patterns(bill_type),
            'typical_fees': self._get_typical_fees(bill_type),
            'fee_explanations': self._get_fee_explanations(bill_type)
        }
    
    def _detect_from_provider(self, provider):
        """
        Detect bill type based on service provider name.
        
        Args:
            provider (str): Service provider name.
            
        Returns:
            str: Detected bill type or UNKNOWN.
        """
        provider = provider.lower()
        
        for bill_type, providers in self.provider_mappings.items():
            for p in providers:
                if p.lower() in provider:
                    return bill_type
        
        return BillType.UNKNOWN.value
    
    def _load_bill_type_patterns(self):
        """
        Load patterns for detecting bill types.
        
        Returns:
            dict: Patterns by bill type.
        """
        # These would ideally come from a database or configuration file
        return {
            BillType.MOBILE.value: [
                r"(wireless|mobile|cell|phone|minutes|texts|data plan)",
                r"(roaming|international call|long distance)",
                r"(AT&T Mobility|Verizon Wireless|T-Mobile|Sprint)"
            ],
            BillType.INTERNET.value: [
                r"(internet|broadband|wifi|bandwidth|ethernet|fiber)",
                r"(mbps|gbps|speed|download|upload|data usage)",
                r"(comcast|xfinity|spectrum|cox|centurylink)"
            ],
            BillType.UTILITY.value: [
                r"(electricity|gas|water|sewage|utility)",
                r"(kilowatt|kwh|meter reading|therms|gallons)",
                r"(pg&e|edison|duke energy|dominion|national grid)"
            ],
            BillType.CREDIT_CARD.value: [
                r"(credit card|card member|cardholder|statement|payment due)",
                r"(minimum payment|credit limit|available credit|apr|interest rate)",
                r"(visa|mastercard|american express|discover|chase|citi|capital one)"
            ],
            BillType.CABLE_TV.value: [
                r"(cable tv|television|channel|broadcast|streaming)",
                r"(premium channel|bundle|dvr|on demand|set-top box)",
                r"(comcast|xfinity|spectrum|cox|dish|directv)"
            ],
            BillType.INSURANCE.value: [
                r"(insurance|policy|coverage|deductible|premium)",
                r"(claim|beneficiary|insured|underwriting)",
                r"(state farm|allstate|geico|progressive|blue cross|anthem|aetna)"
            ]
        }
    
    def _load_provider_mappings(self):
        """
        Load mappings of providers to bill types.
        
        Returns:
            dict: Provider mappings by bill type.
        """
        # These would ideally come from a database
        return {
            BillType.MOBILE.value: [
                "AT&T", "AT&T Mobility", "Verizon", "Verizon Wireless", 
                "T-Mobile", "Sprint", "Metro", "Cricket",
                "Boost Mobile", "US Cellular"
            ],
            BillType.INTERNET.value: [
                "Comcast", "Xfinity", "Spectrum", "Cox", "CenturyLink",
                "Frontier", "Optimum", "AT&T Internet", "Verizon Fios"
            ],
            BillType.UTILITY.value: [
                "PG&E", "Southern California Edison", "Duke Energy",
                "Dominion Energy", "National Grid", "ConEd", "Exelon",
                "Water Authority", "Gas Company"
            ],
            BillType.CREDIT_CARD.value: [
                "Chase", "Citi", "Capital One", "Bank of America",
                "American Express", "Discover", "Wells Fargo"
            ],
            BillType.CABLE_TV.value: [
                "Comcast", "Xfinity", "Spectrum", "Cox", "Dish",
                "DirecTV", "Optimum", "Verizon Fios TV"
            ],
            BillType.INSURANCE.value: [
                "State Farm", "Allstate", "Geico", "Progressive",
                "Liberty Mutual", "Blue Cross", "Blue Shield", "Anthem",
                "Aetna", "UnitedHealthcare", "Cigna", "Humana"
            ]
        }
    
    def _get_questionable_fee_patterns(self, bill_type):
        """
        Get patterns for questionable fees specific to a bill type.
        
        Args:
            bill_type (str): Type of bill.
            
        Returns:
            list: Patterns for questionable fees.
        """
        # Common questionable fees across all bill types
        common_patterns = [
            r"(administrative|admin)[\s\-]*(fee|charge)",
            r"(service|maintenance)[\s\-]*(fee|charge)",
            r"(processing|transaction)[\s\-]*(fee|charge)",
            r"(convenience|payment)[\s\-]*(fee|charge)"
        ]
        
        # Bill type specific patterns
        specific_patterns = {
            BillType.MOBILE.value: [
                r"(regulatory|compliance)[\s\-]*(fee|charge)",
                r"(line|device|equipment)[\s\-]*(fee|charge)",
                r"(911|emergency)[\s\-]*(fee|charge)"
            ],
            BillType.INTERNET.value: [
                r"(broadcast tv|sports)[\s\-]*(fee|charge)",
                r"(wifi|network)[\s\-]*(fee|charge)",
                r"(modem|router|equipment)[\s\-]*(rental|lease|fee|charge)"
            ],
            BillType.UTILITY.value: [
                r"(environmental|green|renewable)[\s\-]*(fee|charge)",
                r"(infrastructure|system)[\s\-]*(fee|charge)"
            ],
            BillType.CREDIT_CARD.value: [
                r"(paper[\s\-]*statement|online[\s\-]*access)[\s\-]*(fee|charge)",
                r"(inactivity|maintenance)[\s\-]*(fee|charge)"
            ],
            BillType.CABLE_TV.value: [
                r"(broadcast tv|regional sports)[\s\-]*(fee|charge)",
                r"(hd technology|dvr service)[\s\-]*(fee|charge)"
            ],
            BillType.INSURANCE.value: [
                r"(policy[\s\-]*fee|administrative[\s\-]*charge)",
                r"(processing|installment)[\s\-]*(fee|charge)"
            ]
        }
        
        # Combine common patterns with specific ones
        return common_patterns + specific_patterns.get(bill_type, [])
    
    def _get_typical_fees(self, bill_type):
        """
        Get typical fees for a bill type.
        
        Args:
            bill_type (str): Type of bill.
            
        Returns:
            dict: Typical fees with amount ranges.
        """
        # This would come from a database based on aggregated data
        typical_fees = {
            BillType.MOBILE.value: {
                "Administrative Fee": {"min": 1.50, "max": 3.99},
                "Regulatory Cost Recovery Charge": {"min": 0.75, "max": 3.50},
                "911 Service Fee": {"min": 0.50, "max": 1.50}
            },
            BillType.INTERNET.value: {
                "Broadcast TV Fee": {"min": 8.00, "max": 19.95},
                "Regional Sports Fee": {"min": 6.00, "max": 14.95},
                "Equipment Rental Fee": {"min": 5.00, "max": 15.00},
                "WiFi Service Fee": {"min": 3.99, "max": 7.99}
            },
            BillType.UTILITY.value: {
                "Environmental Compliance Fee": {"min": 0.99, "max": 4.99},
                "Infrastructure Maintenance Fee": {"min": 1.50, "max": 7.50},
                "Paper Bill Fee": {"min": 1.00, "max": 3.00}
            },
            BillType.CREDIT_CARD.value: {
                "Paper Statement Fee": {"min": 1.00, "max": 5.00},
                "Foreign Transaction Fee": {"min": "2.7%", "max": "3.5%"},
                "Cash Advance Fee": {"min": "3%", "max": "5%"}
            },
            BillType.CABLE_TV.value: {
                "Broadcast TV Fee": {"min": 8.00, "max": 19.95},
                "Regional Sports Fee": {"min": 6.00, "max": 14.95},
                "HD Technology Fee": {"min": 4.99, "max": 9.99},
                "DVR Service Fee": {"min": 5.00, "max": 10.00}
            },
            BillType.INSURANCE.value: {
                "Policy Fee": {"min": 15.00, "max": 50.00},
                "Installment Processing Fee": {"min": 2.00, "max": 7.50}
            }
        }
        
        return typical_fees.get(bill_type, {})
    
    def _get_fee_explanations(self, bill_type):
        """
        Get explanations for common fees of a bill type.
        
        Args:
            bill_type (str): Type of bill.
            
        Returns:
            dict: Explanations for common fees.
        """
        # Educational content about common fees
        explanations = {
            BillType.MOBILE.value: {
                "Administrative Fee": "This fee is often unregulated and providers use it to increase revenue without advertising higher rates