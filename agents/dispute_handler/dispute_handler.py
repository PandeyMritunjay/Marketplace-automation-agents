from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from lighthouse.integrations.database import get_marketplace_db, get_agent_db
from lighthouse.integrations.slack import SlackClient
from lighthouse.integrations.gmail import GmailClient
from lighthouse.services.llm import OpenAIService
from lighthouse.models.marketplace import Order, Seller, Buyer
from lighthouse.models.agent import Dispute, DisputeType, DisputeStatus, ConfidenceLevel, AgentAction, ActionType, AgentType
from lighthouse.config import settings
import logging
import json
import re

logger = logging.getLogger(__name__)


class DisputeHandler:
    def __init__(self):
        self.llm = OpenAIService()
        self.slack = SlackClient()
        self.gmail = GmailClient()
    
    def fetch_and_process_dispute_emails(self, since: Optional[datetime] = None, limit: int = 50) -> Dict:
        """
        Fetch dispute emails from Gmail and process them.
        
        Steps:
        1. Fetch unread emails with dispute-related keywords
        2. Extract buyer email from each email
        3. Process each complaint
        """
        try:
            # Fetch unread emails with dispute keywords
            emails = self.gmail.get_unread_emails(since=since, limit=limit)
            
            dispute_keywords = ['dispute', 'damaged', 'missing order', 'never arrived', 'wrong item', 'not as described']
            dispute_emails = []
            
            for email in emails:
                text = (email.get('subject', '') + ' ' + email.get('body', '')).lower()
                if any(keyword in text for keyword in dispute_keywords):
                    dispute_emails.append(email)
            
            logger.info(f"Found {len(dispute_emails)} dispute-related emails out of {len(emails)} total")
            
            processed = []
            for email in dispute_emails:
                buyer_email = self._extract_email(email['from'])
                complaint_text = email['body']
                
                result = self.process_complaint(complaint_text, buyer_email)
                
                if result:
                    processed.append(result)
                    # Mark email as read
                    self.gmail.mark_as_read(email['id'])
            
            return {
                'total_emails': len(emails),
                'dispute_emails': len(dispute_emails),
                'processed': len(processed),
                'results': processed
            }
            
        except Exception as e:
            logger.error(f"Error fetching and processing dispute emails: {e}")
            return {'total_emails': 0, 'dispute_emails': 0, 'processed': 0, 'results': []}
    
    def _extract_email(self, from_header: str) -> str:
        """Extract email address from From header."""
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1)
        return from_header
    
    def process_complaint(self, complaint_text: str, buyer_email: str) -> Optional[Dict]:
        """
        Process a buyer complaint end-to-end.
        
        Steps:
        1. Extract structured data from complaint
        2. Identify buyer and order
        3. Gather context (order, seller, policies)
        4. Match policy and determine confidence
        5. Generate resolution drafts
        6. Send to Slack for human review
        """
        marketplace_db = get_marketplace_db()
        agent_db = get_agent_db()
        
        try:
            # Step 1: Extract structured data
            extracted = self._extract_complaint_data(complaint_text)
            logger.info(f"Extracted complaint data: {extracted}")
            
            # Step 2: Identify buyer
            buyer = marketplace_db.query(Buyer).filter(
                Buyer.email == buyer_email
            ).first()
            
            if not buyer:
                logger.warning(f"Buyer not found: {buyer_email}, cannot create dispute record without buyer_id")
                return {
                    'error': 'Buyer not found in database',
                    'buyer_email': buyer_email,
                    'recommendation': 'Add buyer to marketplace database first',
                    'confidence': 'low'
                }
            
            # Step 3: Get order (assume most recent order for now)
            order = marketplace_db.query(Order).filter(
                Order.buyer_id == buyer.id
            ).order_by(Order.created_at.desc()).first()
            
            if not order:
                logger.warning(f"No order found for buyer: {buyer_email}, cannot create dispute record without order_id")
                return {
                    'error': 'No order found for buyer',
                    'buyer_email': buyer_email,
                    'buyer_id': buyer.id,
                    'recommendation': 'Buyer exists but has no orders in database',
                    'confidence': 'low'
                }
            
            # Get seller
            seller = marketplace_db.query(Seller).filter(
                Seller.id == order.seller_id
            ).first()
            
            # Step 4: Gather context
            context = self._gather_context(order, seller, buyer, marketplace_db)
            
            # Step 5: Policy matching and confidence determination
            policy_result = self._match_policy(extracted, context)
            
            # Step 6: Generate drafts based on confidence
            drafts = self._generate_drafts(extracted, context, policy_result)
            
            # Step 7: Create dispute record
            dispute = Dispute(
                order_id=order.id,
                buyer_id=buyer.id,
                seller_id=seller.id,
                dispute_type=DisputeType(extracted.get('dispute_type', 'other')),
                complaint_text=complaint_text,
                buyer_sentiment=extracted.get('sentiment'),
                requested_resolution=extracted.get('resolution'),
                confidence_level=ConfidenceLevel(policy_result['confidence']),
                policy_match=policy_result['policy'],
                complicating_factors=json.dumps(policy_result['complicating_factors']),
                seller_message_draft=drafts['seller_message'],
                buyer_message_draft=drafts['buyer_message'],
                internal_summary=drafts['internal_summary'],
                status=DisputeStatus.OPEN
            )
            
            agent_db.add(dispute)
            agent_db.commit()
            
            # Step 8: Send to Slack
            slack_ts = self.slack.send_dispute_notification(
                dispute_id=dispute.id,
                dispute_type=extracted.get('dispute_type', 'unknown'),
                amount=order.total,
                buyer_name=buyer.name,
                seller_name=seller.name,
                seller_tier=seller.tier.value,
                recommendation=policy_result['recommendation'],
                confidence=policy_result['confidence'].upper(),
                seller_message_draft=drafts['seller_message'],
                buyer_message_draft=drafts['buyer_message'],
                internal_summary=drafts['internal_summary']
            )
            
            # Log action
            self._log_action(
                agent_db,
                ActionType.DRAFT_CREATED,
                dispute.id,
                f"Created dispute #{dispute.id} with {policy_result['confidence']} confidence"
            )
            
            # Print full JSON output to console
            output_json = {
                'dispute_id': dispute.id,
                'dispute_type': extracted.get('dispute_type', 'unknown'),
                'confidence_level': policy_result['confidence'],
                'policy_match': policy_result['policy'],
                'buyer_sentiment': extracted.get('sentiment'),
                'seller_message_draft': drafts['seller_message'],
                'buyer_message_draft': drafts['buyer_message'],
                'internal_summary': drafts['internal_summary'],
                'recommendation': policy_result['recommendation'],
                'complicating_factors': policy_result['complicating_factors']
            }
            print("\n" + "="*80)
            print("FULL DISPUTE OUTPUT (JSON):")
            print("="*80)
            print(json.dumps(output_json, indent=2))
            print("="*80 + "\n")
            
            return {
                'dispute_id': dispute.id,
                'confidence': policy_result['confidence'],
                'recommendation': policy_result['recommendation'],
                'slack_timestamp': slack_ts
            }
            
        except Exception as e:
            logger.error(f"Error processing complaint: {e}")
            agent_db.rollback()
            return None
        finally:
            marketplace_db.close()
            agent_db.close()
    
    def _extract_complaint_data(self, complaint_text: str) -> Dict:
        """Extract structured data from complaint text using LLM."""
        schema_description = """
        {
            "dispute_type": "one of: non_delivery, item_not_described, damaged_item, wrong_item, late_shipment, other",
            "product": "brief description of product",
            "time_elapsed_days": "number of days since order",
            "sentiment": "one of: angry, neutral, calm, escalating",
            "resolution": "what the buyer is requesting"
        }
        """
        
        extracted = self.llm.extract_structured_data(
            text=complaint_text,
            extraction_prompt="Extract the following information from this buyer complaint:",
            schema_description=schema_description
        )
        
        return extracted
    
    def _gather_context(
        self,
        order: Order,
        seller: Seller,
        buyer: Buyer,
        db: Session
    ) -> Dict:
        """Gather relevant context for the dispute."""
        # Calculate time elapsed
        time_elapsed = (datetime.utcnow() - order.created_at).days
        
        # Get seller dispute history (simplified)
        # In production, query disputes table for this seller
        
        return {
            'order_id': order.id,
            'order_total': order.total,
            'order_status': order.status.value,
            'tracking_number': order.tracking_number,
            'time_elapsed_days': time_elapsed,
            'seller_name': seller.name,
            'seller_tier': seller.tier.value,
            'seller_rating': seller.rating,
            'seller_total_orders': seller.total_orders,
            'seller_gmv': seller.total_gmv,
            'buyer_name': buyer.name,
            'buyer_total_orders': buyer.total_orders
        }
    
    def _match_policy(self, extracted: Dict, context: Dict) -> Dict:
        """Match dispute against policies and determine confidence."""
        confidence = "high"
        complicating_factors = []
        recommendation = "Standard 48hr seller notice → auto-refund"
        
        # Check dollar threshold
        if context['order_total'] > settings.dispute_auto_refund_threshold:
            confidence = "low"
            complicating_factors.append("High-value order")
        
        # Check seller tier
        if context['seller_tier'] == 'top':
            confidence = "low"
            complicating_factors.append("Top-tier seller")
        
        # Check time elapsed
        if context['time_elapsed_days'] < 10:
            confidence = "low"
            complicating_factors.append("Dispute opened early")
        
        # Check if seller has tracking
        if not context['tracking_number']:
            # This is standard case for non-delivery
            pass
        else:
            complicating_factors.append("Tracking number exists")
            confidence = "medium"
        
        # Final confidence determination
        if len(complicating_factors) == 0:
            confidence = "high"
        elif len(complicating_factors) == 1:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            'confidence': confidence,
            'policy': "Buyers can open disputes after 10 days of non-delivery; sellers have 48 hours to respond with proof of shipment",
            'complicating_factors': complicating_factors,
            'recommendation': recommendation if confidence == "high" else "Requires human review"
        }
    
    def _generate_drafts(self, extracted: Dict, context: Dict, policy_result: Dict) -> Dict:
        """Generate message drafts for seller, buyer, and internal summary."""
        
        # Seller message
        seller_message = f"""Hi {context['seller_name']},

A buyer has opened a {extracted.get('dispute_type', 'dispute')} for Order #{context['order_id']} ({extracted.get('product', 'item')}, ${context['order_total']:.2f}).

Our records show no tracking number was uploaded. Per marketplace policy, please provide proof of shipment within 48 hours. If we don't hear back, we'll issue a full refund to the buyer.

Here's a link to upload tracking: [link]

Thanks,
Marketplace Team"""
        
        # Buyer message
        buyer_message = f"""Hi {context['buyer_name']},

Thanks for reaching out. We take {extracted.get('dispute_type', 'this issue')} seriously.

We've contacted the seller and given them 48 hours to provide shipping confirmation. If they can't confirm shipment, you'll receive a full refund. We'll update you either way.

Sorry for the frustration,
Marketplace Team"""
        
        # Internal summary
        internal_summary = f"""Dispute — {extracted.get('dispute_type', 'unknown')}
Buyer: {context['buyer_name']} (orders: {context['buyer_total_orders']})
Seller: {context['seller_name']} ({context['seller_tier']}, {context['seller_rating']}★, orders: {context['seller_total_orders']})
Order: #{context['order_id']}, ${context['order_total']:.2f}, {context['time_elapsed_days']} days old
Recommendation: {policy_result['recommendation']}
Confidence: {policy_result['confidence'].upper()}
Complicating factors: {', '.join(policy_result['complicating_factors']) if policy_result['complicating_factors'] else 'None'}"""
        
        return {
            'seller_message': seller_message,
            'buyer_message': buyer_message,
            'internal_summary': internal_summary
        }
    
    def _log_action(self, db: Session, action_type: ActionType, entity_id: int, description: str):
        """Log an agent action for metrics tracking."""
        action = AgentAction(
            agent_type=AgentType.DISPUTE_HANDLER,
            action_type=action_type,
            entity_type="dispute",
            entity_id=entity_id,
            description=description
        )
        db.add(action)
        db.commit()
    
    def handle_followup(self, dispute_id: int) -> bool:
        """Handle 48-hour follow-up for a dispute."""
        agent_db = get_agent_db()
        marketplace_db = get_marketplace_db()
        
        try:
            dispute = agent_db.query(Dispute).filter(
                Dispute.id == dispute_id
            ).first()
            
            if not dispute:
                logger.error(f"Dispute not found: {dispute_id}")
                return False
            
            # Check if seller responded
            order = marketplace_db.query(Order).filter(
                Order.id == dispute.order_id
            ).first()
            
            if order.tracking_number:
                # Seller provided tracking - notify buyer
                logger.info(f"Seller provided tracking for dispute {dispute_id}")
                dispute.status = DisputeStatus.RESOLVED
                agent_db.commit()
                return True
            else:
                # No response - proceed with refund
                logger.info(f"No seller response for dispute {dispute_id} - proceeding with refund")
                dispute.status = DisputeStatus.REFUNDED
                dispute.refund_amount = order.total
                agent_db.commit()
                
                # Send refund notification to Slack
                self.slack.send_message(
                    settings.slack_channel_disputes,
                    f"💸 Refund issued for Dispute #{dispute_id} - ${order.total:.2f}"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error handling followup: {e}")
            agent_db.rollback()
            return False
        finally:
            agent_db.close()
            marketplace_db.close()
