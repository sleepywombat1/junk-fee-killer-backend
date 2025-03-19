import re
import json
import os
from collections import defaultdict

class FeeDetector:
    """
    Analyzes bill text to identify and categorize potential hidden fees.
    """
    
    def __init__(self, config=None):
        """
        Initialize the fee detector with optional configuration.
        
        Args:
            config (dict, optional): Configuration options for the detector.
        """
        self.config = config or {}
        self.fee_patterns = self._load_fee_patterns()
        self.common_fees_by_provider = self._load_common_fees_by_provider()
        self.industry_standards = self._load_industry_standards()
    
    def detect_fees(self, document_data, bill_type):
        """
        Detect potential hidden fees in the document.
        
        Args:
            document_data (dict): Extracted document data from DocumentProcessor.
            bill_type (str): Type of bill (e.g., "mobile", "internet", "utility").
            
        Returns:
            dict: Detected fees and analysis results.
        """
        text = document_data.get('full_text', '')
        structured_data = document_data.get('structured_data', {})
        line_items = structured_data.get('line_items', [])
        provider = structured_data.get('service_provider', '')
        
        # Analyze line items
        analyzed_items = self._analyze_line_items(line_items, bill_type, provider)
        
        # Look for fees in full text if line items don't cover everything
        text_detected_fees = self._detect_fees_in_text(text, bill_type, provider)
        
        # Combine and deduplicate results
        all_fees = self._combine_fee_results(analyzed_items, text_detected_fees)
        
        # Calculate potential savings
        potential_savings = sum(fee['amount'] for fee in all_fees if fee.get('is_questionable', False) and fee.get('amount'))
        
        return {
            'detected_fees': all_fees,
            'potential_savings': potential_savings,
            'summary': self._generate_summary(all_fees, bill_type, provider),
            'provider': provider,
            'bill_type': bill_type
        }
    
    def _load_fee_patterns(self):
        """
        Load fee detection patterns from configuration or default patterns.
        
        Returns:
            dict: Patterns for detecting different types of fees.
        """
        # These would ideally come from a database or configuration file
        # For now, we'll define some common patterns inline
        return {
            'general': [
                r"(administrative|admin)[\s\-]*(fee|charge)",
                r"(service|maintenance)[\s\-]*(fee|charge)",
                r"(processing|transaction)[\s\-]*(fee|charge)",
                r"(regulatory|compliance)[\s\-]*(fee|charge)",
                r"(convenience|payment)[\s\-]*(fee|charge)",
                r"(late|overdue|penalty)[\s\-]*(fee|charge)",
                r"(paper|billing|statement)[\s\-]*(fee|charge)",
                r"(access|connection)[\s\-]*(fee|charge)"
            ],
            'mobile': [
                r"(line|device|equipment)[\s\-]*(fee|charge)",
                r"(activation|deactivation)[\s\-]*(fee|charge)",
                r"(data|usage|overage)[\s\-]*(fee|charge)",
                r"(roaming|international)[\s\-]*(fee|charge)",
                r"(911|emergency)[\s\-]*(fee|charge)"
            ],
            'internet': [
                r"(modem|router|equipment)[\s\-]*(rental|lease|fee|charge)",
                r"(installation|setup)[\s\-]*(fee|charge)",
                r"(data|bandwidth|usage)[\s\-]*(fee|charge)",
                r"(network|infrastructure)[\s\-]*(fee|charge)"
            ],
            'utility': [
                r"(meter|reading|service)[\s\-]*(fee|charge)",
                r"(delivery|transportation)[\s\-]*(fee|charge)",
                r"(environmental|green|renewable)[\s\-]*(fee|charge)",
                r"(fuel|energy|adjustment)[\s\-]*(fee|charge)"
            ],
            'credit_card': [
                r"(annual|membership)[\s\-]*(fee|charge)",
                r"(cash[\s\-]*advance|balance[\s\-]*transfer)[\s\-]*(fee|charge)",
                r"(foreign[\s\-]*transaction|currency[\s\-]*conversion)[\s\-]*(fee|charge)",
                r"(over[\s\-]*limit|returned[\s\-]*payment)[\s\-]*(fee|charge)"
            ]
        }
    
    def _load_common_fees_by_provider(self):
        """
        Load common fees by service provider.
        
        Returns:
            dict: Common fees by provider name.
        """
        # This would ideally come from a database
        # For now, we'll define some examples inline
        return {
            'AT&T': [
                {'name': 'Administrative Fee', 'typical_amount': 1.99, 'is_questionable': True},
                {'name': 'Regulatory Cost Recovery Charge', 'typical_amount': 1.50, 'is_questionable': True},
                {'name': 'Federal Universal Service Charge', 'typical_amount': 4.75, 'is_questionable': False}
            ],
            'Verizon': [
                {'name': 'Administrative Charge', 'typical_amount': 1.95, 'is_questionable': True},
                {'name': 'Regulatory Charge', 'typical_amount': 1.35, 'is_questionable': True}
            ],
            'Comcast': [
                {'name': 'Broadcast TV Fee', 'typical_amount': 14.95, 'is_questionable': True},
                {'name': 'Regional Sports Fee', 'typical_amount': 8.75, 'is_questionable': True},
                {'name': 'Equipment Rental Fee', 'typical_amount': 14.00, 'is_questionable': True}
            ],
            'Spectrum': [
                {'name': 'Broadcast TV Surcharge', 'typical_amount': 16.45, 'is_questionable': True},
                {'name': 'WiFi Service Fee', 'typical_amount': 5.00, 'is_questionable': True}
            ]
        }
    
    def _load_industry_standards(self):
        """
        Load industry standard fee information.
        
        Returns:
            dict: Industry standard fee information by bill type.
        """
        # This would ideally come from a database
        # For now, we'll define some examples inline
        return {
            'mobile': {
                'regulatory_fee_max': 3.00,
                'admin_fee_max': 2.00,
                'questionable_fees': [
                    'Administrative Fee',
                    'Regulatory Cost Recovery Charge',
                    'Line Access Fee',
                    'Device Payment Charge'
                ]
            },
            'internet': {
                'equipment_rental_max': 10.00,
                'broadcast_tv_max': 10.00,
                'questionable_fees': [
                    'Broadcast TV Fee',
                    'Regional Sports Fee',
                    'WiFi Service Fee',
                    'Internet Infrastructure Fee'
                ]
            },
            'utility': {
                'service_fee_max': 5.00,
                'questionable_fees': [
                    'Paper Bill Fee',
                    'Payment Processing Fee',
                    'Environmental Compliance Fee'
                ]
            }
        }
    
    def _analyze_line_items(self, line_items, bill_type, provider):
        """
        Analyze line items to identify potential fees.
        
        Args:
            line_items (list): List of line items with descriptions and amounts.
            bill_type (str): Type of bill.
            provider (str): Service provider name.
            
        Returns:
            list: Analyzed line items with fee information.
        """
        analyzed_items = []
        
        for item in line_items:
            description = item.get('description', '').lower()
            amount = item.get('amount', 0)
            
            # Skip items that are clearly not fees
            if amount <= 0 or any(word in description for word in ['total', 'subtotal', 'payment', 'credit']):
                continue
            
            # Check against known fee patterns
            is_fee = False
            fee_type = 'unknown'
            is_questionable = False
            confidence = 'low'
            
            # Check general patterns
            for pattern in self.fee_patterns.get('general', []):
                if re.search(pattern, description, re.IGNORECASE):
                    is_fee = True
                    fee_type = 'general'
                    confidence = 'medium'
                    break
            
            # Check bill-type specific patterns
            if bill_type in self.fee_patterns:
                for pattern in self.fee_patterns[bill_type]:
                    if re.search(pattern, description, re.IGNORECASE):
                        is_fee = True
                        fee_type = bill_type
                        confidence = 'high'
                        break
            
            # Check against known provider fees
            provider_fees = self.common_fees_by_provider.get(provider, [])
            for known_fee in provider_fees:
                if self._is_similar_description(description, known_fee['name'].lower()):
                    is_fee = True
                    fee_type = 'provider_specific'
                    is_questionable = known_fee.get('is_questionable', False)
                    confidence = 'very_high'
                    break
            
            # Check against industry standards
            if bill_type in self.industry_standards:
                standards = self.industry_standards[bill_type]
                questionable_fees = standards.get('questionable_fees', [])
                
                for q_fee in questionable_fees:
                    if self._is_similar_description(description, q_fee.lower()):
                        is_questionable = True
                        break
                
                # Check if fee amount exceeds standard maximums
                if 'administrative' in description and amount > standards.get('admin_fee_max', float('inf')):
                    is_questionable = True
                elif 'regulatory' in description and amount > standards.get('regulatory_fee_max', float('inf')):
                    is_questionable = True
                elif 'equipment' in description and amount > standards.get('equipment_rental_max', float('inf')):
                    is_questionable = True
            
            if is_fee:
                analyzed_items.append({
                    'description': item['description'],
                    'amount': amount,
                    'is_fee': True,
                    'fee_type': fee_type,
                    'is_questionable': is_questionable,
                    'confidence': confidence,
                    'reason': self._generate_reason(description, amount, is_questionable, bill_type, provider)
                })
        
        return analyzed_items
    
    def _detect_fees_in_text(self, text, bill_type, provider):
        """
        Detect fees in the full text when line items might not be clearly extracted.
        
        Args:
            text (str): Full text of the document.
            bill_type (str): Type of bill.
            provider (str): Service provider name.
            
        Returns:
            list: Detected fees from text.
        """
        detected_fees = []
        text = text.lower()
        
        # Combine all patterns
        all_patterns = self.fee_patterns.get('general', []) + self.fee_patterns.get(bill_type, [])
        
        for pattern in all_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                fee_description = match.group(0)
                
                # Look for amount near the fee description
                amount_match = re.search(r'\$?(\d+\.\d{2})', text[match.end():match.end()+100])
                amount = float(amount_match.group(1)) if amount_match else 0
                
                if amount > 0:
                    # Check if this fee is questionable
                    is_questionable = self._is_questionable_fee(fee_description, amount, bill_type, provider)
                    
                    # Only add if we found an amount and it's not a duplicate
                    if not any(fee['description'].lower() == fee_description.lower() for fee in detected_fees):
                        detected_fees.append({
                            'description': fee_description,
                            'amount': amount,
                            'is_fee': True,
                            'fee_type': bill_type if bill_type in self.fee_patterns else 'general',
                            'is_questionable': is_questionable,
                            'confidence': 'medium',
                            'reason': self._generate_reason(fee_description, amount, is_questionable, bill_type, provider)
                        })
        
        return detected_fees
    
    def _is_questionable_fee(self, description, amount, bill_type, provider):
        """
        Determine if a fee is questionable based on description, amount, and context.
        
        Args:
            description (str): Fee description.
            amount (float): Fee amount.
            bill_type (str): Type of bill.
            provider (str): Service provider name.
            
        Returns:
            bool: True if the fee is questionable, False otherwise.
        """
        description = description.lower()
        
        # Check provider-specific known questionable fees
        if provider in self.common_fees_by_provider:
            for known_fee in self.common_fees_by_provider[provider]:
                if self._is_similar_description(description, known_fee['name'].lower()) and known_fee.get('is_questionable', False):
                    return True
        
        # Check industry standards
        if bill_type in self.industry_standards:
            standards = self.industry_standards[bill_type]
            questionable_fees = [q_fee.lower() for q_fee in standards.get('questionable_fees', [])]
            
            for q_fee in questionable_fees:
                if self._is_similar_description(description, q_fee):
                    return True
        
        # Check for commonly questionable fee types
        questionable_keywords = [
            'administrative', 'admin', 'regulatory', 'recovery', 'compliance',
            'service', 'maintenance', 'paper', 'billing', 'statement',
            'convenience', 'processing', 'technology', 'infrastructure'
        ]
        
        if any(keyword in description for keyword in questionable_keywords):
            return True
        
        return False
    
    def _is_similar_description(self, desc1, desc2, threshold=0.7):
        """
        Check if two descriptions are similar.
        
        Args:
            desc1 (str): First description.
            desc2 (str): Second description.
            threshold (float): Similarity threshold.
            
        Returns:
            bool: True if descriptions are similar, False otherwise.
        """
        # Simple implementation using word overlap
        words1 = set(desc1.lower().split())
        words2 = set(desc2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union)
        return similarity >= threshold
    
    def _combine_fee_results(self, analyzed_items, text_detected_fees):
        """
        Combine and deduplicate fee results from different detection methods.
        
        Args:
            analyzed_items (list): Fees detected from line items.
            text_detected_fees (list): Fees detected from full text.
            
        Returns:
            list: Combined and deduplicated fee results.
        """
        combined_fees = []
        seen_descriptions = set()
        
        # Add all analyzed items
        for item in analyzed_items:
            combined_fees.append(item)
            seen_descriptions.add(item['description'].lower())
        
        # Add text detected fees if not already present
        for fee in text_detected_fees:
            if fee['description'].lower() not in seen_descriptions:
                combined_fees.append(fee)
                seen_descriptions.add(fee['description'].lower())
        
        return combined_fees
    
    def _generate_reason(self, description, amount, is_questionable, bill_type, provider):
        """
        Generate a reason for why a fee is questionable or not.
        
        Args:
            description (str): Fee description.
            amount (float): Fee amount.
            is_questionable (bool): Whether the fee is questionable.
            bill_type (str): Type of bill.
            provider (str): Service provider name.
            
        Returns:
            str: Reason for the fee classification.
        """
        description = description.lower()
        
        if not is_questionable:
            return "This appears to be a standard fee for this service."
        
        reasons = []
        
        # Check for provider-specific known fees
        if provider in self.common_fees_by_provider:
            for known_fee in self.common_fees_by_provider[provider]:
                if self._is_similar_description(description, known_fee['name'].lower()) and known_fee.get('is_questionable', False):
                    reasons.append(f"This is a known questionable fee commonly added by {provider}.")
                    break
        
        # Check industry standards
        if bill_type in self.industry_standards:
            standards = self.industry_standards[bill_type]
            
            # Check for excessive amounts
            if 'administrative' in description and amount > standards.get('admin_fee_max', float('inf')):
                reasons.append(f"This administrative fee exceeds the typical maximum of ${standards['admin_fee_max']:.2f}.")
            elif 'regulatory' in description and amount > standards.get('regulatory_fee_max', float('inf')):
                reasons.append(f"This regulatory fee exceeds the typical maximum of ${standards['regulatory_fee_max']:.2f}.")
            elif 'equipment' in description and amount > standards.get('equipment_rental_max', float('inf')):
                reasons.append(f"This equipment fee exceeds the typical maximum of ${standards['equipment_rental_max']:.2f}.")
        
        # Check for common questionable fee types
        if 'administrative' in description or 'admin' in description:
            reasons.append("Administrative fees are often used to increase revenue without advertising higher rates.")
        elif 'regulatory' in description or 'compliance' in description:
            reasons.append("Regulatory fees often exceed actual costs of regulatory compliance.")
        elif 'convenience' in description or 'processing' in description:
            reasons.append("Convenience or processing fees are often excessive compared to actual costs.")
        elif 'service' in description:
            reasons.append("Service fees are often vague and may not relate to any specific service.")
        elif 'paper' in description or 'billing' in description:
            reasons.append("Paper billing fees are often considered excessive for the actual cost of sending a bill.")
        
        if not reasons:
            reasons.append("This fee appears to be unnecessary or excessive based on industry standards.")
        
        return " ".join(reasons)
    
    def _generate_summary(self, all_fees, bill_type, provider):
    """
    Generate a summary of the fee analysis.
    
    Args:
        all_fees (list): All detected fees.
        bill_type (str): Type of bill.
        provider (str): Service provider name.
        
    Returns:
        dict: Summary of the fee analysis.
    """
    questionable_fees = [fee for fee in all_fees if fee.get('is_questionable', False)]
    total_questionable = sum(fee['amount'] for fee in questionable_fees if fee.get('amount'))
    
    suggestions = []
    
    if questionable_fees:
        suggestions.append(f"Call {provider} customer service to inquire about the questionable fees identified.")
        suggestions.append("Ask for a detailed explanation of each fee and its purpose.")
        suggestions.append("Specifically request to have unnecessary fees removed from your bill.")
        suggestions.append("If they refuse, consider asking for a supervisor or filing a complaint with the FCC or your state's public utility commission.")
    
    summary = {
        'total_fees_detected': len(all_fees),
        'questionable_fees_count': len(questionable_fees),
        'total_questionable_amount': total_questionable,
        'suggestions': suggestions,
        'provider_info': {
            'name': provider,
            'known_for_questionable_fees': provider in self.common_fees_by_provider and any(fee.get('is_questionable', False) for fee in self.common_fees_by_provider[provider])
        },
        'bill_type': bill_type,
        'top_questionable_fees': self._get_top_questionable_fees(questionable_fees, 3)
    }
    
    return summary

def _get_top_questionable_fees(self, questionable_fees, limit=3):
    """
    Get the top questionable fees by amount.
    
    Args:
        questionable_fees (list): List of questionable fees.
        limit (int): Maximum number of fees to return.
        
    Returns:
        list: Top questionable fees.
    """
    if not questionable_fees:
        return []
    
    # Sort fees by amount in descending order
    sorted_fees = sorted(questionable_fees, key=lambda x: x.get('amount', 0), reverse=True)
    
    # Return the top fees
    return [
        {
            'description': fee['description'],
            'amount': fee['amount'],
            'reason': fee.get('reason', '')
        }
        for fee in sorted_fees[:limit]
    ]
    