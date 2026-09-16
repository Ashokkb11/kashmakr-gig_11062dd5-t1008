"""
Enterprise Lead Capture System - Core Automation Logic
This module provides the core functions for the Slack-to-Salesforce lead capture workflow.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

# Configure logging for enterprise monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SlackMessage:
    """Represents a structured Slack message from the #leads channel."""
    text: str
    user_id: str
    channel_id: str
    timestamp: str
    thread_ts: Optional[str] = None
    attachments: Optional[List[Dict]] = None
    
    def extract_lead_data(self) -> Dict[str, str]:
        """
        Extract lead information from Slack message text.
        Returns structured data for Salesforce lead creation.
        """
        # Common patterns for lead information in B2B context
        patterns = {
            'company': r'(?:company|org|firm):\s*([^\n]+)',
            'contact_name': r'(?:contact|person):\s*([^\n]+)',
            'email': r'[\w\.-]+@[\w\.-]+\.\w+',
            'phone': r'\+?\d[\d\s\-\(\)]{7}',
            'interest_level': r'(?:interest|priority):\s*(high|medium|low|critical)',
            'product_interest': r'(?:interested in|needs):\s*([^\n]+)'
        }
        
        extracted = {
            'source': 'slack_leads_channel',
            'slack_user_id': self.user_id,
            'original_message': self.text,
            'slack_timestamp': self.timestamp
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                extracted[key] = match.group(1) if match.groups() else match.group(0)
        
        # Default interest level if not specified
        if 'interest_level' not in extracted:
            extracted['interest_level'] = 'medium'
            
        return extracted
    
    def is_valid_lead(self) -> Tuple[bool, Optional[str]]:
        """
        Validate if the message contains sufficient information for lead creation.
        Returns (is_valid, reason_if_invalid)
        """
        if not self.text or len(self.text.strip()) < 10:
            return False, "Message too short or empty"
        
        # Check for at least company or contact information
        company_match = re.search(r'company:\s*([^\n]+)', self.text, re.IGNORECASE)
        contact_match = re.search(r'contact:\s*([^\n]+)', self.text, re.IGNORECASE)
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', self.text)
        
        if not (company_match or contact_match or email_match):
            return False, "Missing company, contact, or email information"
        
        return True, None


class SalesforceLeadCreator:
    """Handles interactions with Salesforce API for lead creation."""
    
    def __init__(self, api_endpoint: str, api_version: str = "v58.0"):
        self.api_endpoint = api_endpoint
        self.api_version = api_version
        self.leads_created = 0
        self.failed_attempts = 0
        
    def format_lead_payload(self, lead_data: Dict[str, str]) -> Dict:
        """
        Format extracted data into Salesforce Lead object structure.
        Reference: Salesforce REST API documentation
        """
        # Map extracted fields to Salesforce Lead fields
        mapping = {
            'company': 'Company',
            'contact_name': 'LastName',  # Using LastName as required field
            'email': 'Email',
            'phone': 'Phone',
            'product_interest': 'ProductInterest__c',  # Custom field example
            'interest_level': 'Rating'  # Using Rating for interest level
        }
        
        payload = {
            "LastName": "Unknown Contact",  # Default required field
            "LeadSource": "Slack #leads Channel",
            "Status": "Open - Not Contacted"
        }
        
        for source_key, salesforce_field in mapping.items():
            if source_key in lead_data:
                payload[salesforce_field] = lead_data[source_key]
        
        # Set FirstName if we have full name
        if 'contact_name' in lead_data:
            name_parts = lead_data['contact_name'].split()
            if len(name_parts) > 1:
                payload['FirstName'] = ' '.join(name_parts[:-1])
                payload['LastName'] = name_parts[-1]
        
        # Add original message as description
        if 'original_message' in lead_data:
            payload['Description'] = f"Slack lead message: {lead_data['original_message'][:255]}..."
        
        return payload
    
    def create_lead(self, lead_data: Dict[str, str]) -> Dict:
        """
        Simulate Salesforce lead creation.
        In production, this would make actual API call to Salesforce.
        """
        try:
            payload = self.format_lead_payload(lead_data)
            
            # Validate required fields
            if not payload.get('LastName'):
                raise ValueError("Missing required field: LastName")
            
            if not payload.get('Company'):
                raise ValueError("Missing required field: Company")
            
            # Simulate API call
            logger.info(f"Creating lead for company: {payload.get('Company')}")
            
            # Mock successful response
            response = {
                "success": True,
                "id": f"00Q{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "errors": [],
                "payload": payload
            }
            
            self.leads_created += 1
            logger.info(f"Lead created successfully. Total: {self.leads_created}")
            
            return response
            
        except Exception as e:
            self.failed_attempts += 1
            logger.error(f"Failed to create lead: {str(e)}")
            return {
                "success": False,
                "id": None,
                "errors": [str(e)],
                "payload": lead_data
            }
    
    def get_metrics(self) -> Dict[str, int]:
        """Return operational metrics for monitoring."""
        return {
            "leads_created": self.leads_created,
            "failed_attempts": self.failed_attempts,
            "success_rate": (
                (self.leads_created / (self.leads_created + self.failed_attempts) * 100)
                if (self.leads_created + self.failed_attempts) > 0 else 0
            )
        }


class LeadCaptureWorkflow:
    """
    Main workflow orchestrator for Slack to Salesforce lead capture.
    This implements the core automation logic described in the specification.
    """
    
    def __init__(self, salesforce_creator: SalesforceLeadCreator):
        self.salesforce_creator = salesforce_creator
        self.processed_messages = 0
        self.valid_leads = 0
        
    def process_slack_message(self, slack_data: Dict) -> Dict[str, any]:
        """
        Process incoming Slack message through the complete workflow.
        
        Args:
            slack_data: Raw Slack event data from webhook
            
        Returns:
            Dictionary with processing results and status
        """
        self.processed_messages += 1
        
        try:
            # Step 1: Parse and validate Slack message
            message = SlackMessage(
                text=slack_data.get('text', ''),
                user_id=slack_data.get('user', ''),
                channel_id=slack_data.get('channel', ''),
                timestamp=slack_data.get('ts', ''),
                thread_ts=slack_data.get('thread_ts')
            )
            
            # Step 2: Validate message contains lead information
            is_valid, reason = message.is_valid_lead()
            if not is_valid:
                logger.warning(f"Invalid lead message: {reason}")
                return {
                    "status": "rejected",
                    "reason": reason,
                    "message_id": message.timestamp,
                    "workflow_step": "validation"
                }
            
            # Step 3: Extract structured lead data
            lead_data = message.extract_lead_data()
            logger.info(f"Extracted lead data for: {lead_data.get('company', 'Unknown')}")
            
            # Step 4: Create Salesforce lead
            salesforce_result = self.salesforce_creator.create_lead(lead_data)
            
            if salesforce_result["success"]:
                self.valid_leads += 1
                return {
                    "status": "success",
                    "lead_id": salesforce_result["id"],
                    "company": lead_data.get('company', 'Unknown'),
                    "workflow_step": "salesforce_creation",
                    "processed_count": self.processed_messages,
                    "valid_leads_count": self.valid_leads
                }
            else:
                return {
                    "status": "failed",
                    "errors": salesforce_result["errors"],
                    "workflow_step": "salesforce_creation",
                    "retry_eligible": True
                }
                
        except Exception as e:
            logger.error(f"Workflow processing error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "workflow_step": "processing",
                "retry_eligible": True
            }
    
    def get_workflow_metrics(self) -> Dict[str, any]:
        """Return comprehensive workflow metrics for monitoring dashboard."""
        sf_metrics = self.salesforce_creator.get_metrics()
        
        return {
            "workflow_metrics": {
                "processed_messages": self.processed_messages,
                "valid_leads_captured": self.valid_leads,
                "conversion_rate": (
                    (self.valid_leads / self.processed_messages * 100)
                    if self.processed_messages > 0 else 0
                )
            },
            "salesforce_metrics": sf_metrics,
            "timestamp": datetime.now().isoformat(),
            "system_status": "operational"
        }


# Utility functions for common operations
def validate_webhook_signature(signature: str, timestamp: str, body: str, secret: str) -> bool:
    """
    Validate Slack webhook signature for security.
    Reference: Slack API documentation for signing secrets
    
    Args:
        signature: Slack provided signature
        timestamp: Request timestamp
        body: Request body
        secret: Signing secret from Slack app config
        
    Returns:
        Boolean indicating if signature is valid
    """
    # This is a simplified version. In production, use proper HMAC validation
    import hashlib
    import hmac
    
    try:
        # Slack's signature format: v0=hash
        if not signature.startswith("v0="):
            return False
            
        basestring = f"v0:{timestamp}:{body}"
        expected = hmac.new(
            secret.encode('utf-8'),
            basestring.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"v0={expected}", signature)
    except Exception:
        return False


def calculate_roi(leads_generated: int, average_deal_value: float = 15000.0) -> Dict[str, float]:
    """
    Calculate ROI metrics for the automation workflow.
    Based on industry averages for B2B SaaS:
    - Average deal value: $15,000 [UNVERIFIED]
    - Conversion rate from lead to opportunity: 20% [UNVERIFIED]
    - Win rate: 25% [UNVERIFIED]
    
    Args:
        leads_generated: Number of leads created
        average_deal_value: Average value of closed deals
        
    Returns:
        Dictionary with ROI calculations
    """
    conversion_to_opp = 0.20  # 20% of leads become opportunities
    win_rate = 0.25  # 25% of opportunities are won
    
    estimated_opportunities = leads_generated * conversion_to_opp
    estimated_wins = estimated_opportunities * win_rate
    estimated_revenue = estimated_wins * average_deal_value
    
    # Implementation cost estimate (based on gig budget)
    implementation_cost = 3000  # Upper bound of budget
    
    if estimated_revenue > 0:
        roi_percentage = ((estimated_revenue - implementation_cost) / implementation_cost) * 100
    else:
        roi_percentage = 0
    
    return {
        "leads_generated": leads_generated,
        "estimated_opportunities": estimated_opportunities,
        "estimated_wins": estimated_wins,
        "estimated_revenue": estimated_revenue,
        "implementation_cost": implementation_cost,
        "roi_percentage": roi_percentage,
        "payback_period_days": (
            (implementation_cost / (estimated_revenue / 365)) 
            if estimated_revenue > 0 else 0
        )
    }


# Main execution function for standalone testing
def main():
    """Main function for testing the workflow locally."""
    print("Enterprise Lead Capture System - Test Execution")
    print("=" * 50)
    
    # Initialize components
    sf_creator = SalesforceLeadCreator(
        api_endpoint="https://company.my.salesforce.com/services/data"
    )
    
    workflow = LeadCaptureWorkflow(sf_creator)
    
    # Test with sample Slack message
    test_message = {
        "text": "New lead from TechCorp Inc. Contact: Jane Smith, email: jane@techcorp.com, phone: +1-555-123-4567. Interested in: Enterprise plan. Priority: high",
        "user": "U12345678",
        "channel": "CLEADS123",
        "ts": "1625097600.123456"
    }
    
    # Process the message
    result = workflow.process_slack_message(test_message)
    
    print(f"Processing Result: {result['status']}")
    if result['status'] == 'success':
        print(f"Lead ID: {result.get('lead_id')}")
        print(f"Company: {result.get('company')}")
    
    # Display metrics
    metrics = workflow.get_workflow_metrics()
    print("\nWorkflow Metrics:")
    print(json.dumps(metrics, indent=2))
    
    # Calculate ROI
    roi_data = calculate_roi(metrics['workflow_metrics']['valid_leads_captured'])
    print("\nROI Analysis:")
    print(json.dumps(roi_data, indent=2))
    
    print("\n" + "=" * 50)
    print("Test execution completed successfully.")


if __name__ == "__main__":
    main()