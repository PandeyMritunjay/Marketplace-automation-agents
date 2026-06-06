from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from lighthouse.integrations.database import get_marketplace_db, get_agent_db
from lighthouse.integrations.slack import SlackClient
from lighthouse.integrations.gmail import GmailClient
from lighthouse.services.llm import OpenAIService
from lighthouse.models.marketplace import Seller, Buyer
from lighthouse.models.agent import (
    SupportTicket, SenderType, TicketCategory, TicketPriority, 
    TicketStatus, AgentAction, ActionType, AgentType
)
from lighthouse.config import settings
import logging
import re

logger = logging.getLogger(__name__)


class SupportLead:
    def __init__(self):
        self.llm = OpenAIService()
        self.slack = SlackClient()
        self.gmail = GmailClient()
    
    def process_overnight_batch(self, limit: int = 10) -> Dict:
        """
        Process overnight support emails and send morning briefing.

        Steps:
        1. Fetch unread emails from Gmail
        2. Classify each email (sender, intent, priority)
        3. Generate drafts for appropriate tickets
        4. Send morning briefing to Slack
        """
        agent_db = get_agent_db()
        marketplace_db = get_marketplace_db()

        try:
            # Step 1: Fetch unread emails (reduced limit for faster testing)
            emails = self.gmail.get_unread_emails(limit=limit)
            logger.info(f"Fetched {len(emails)} unread emails")
            
            if not emails:
                return {"total": 0, "high": 0, "medium": 0, "low": 0}
            
            # Step 2-3: Process each email
            high_priority = []
            medium_priority = []
            low_priority = []
            
            for email in emails:
                try:
                    result = self._process_email(email, marketplace_db, agent_db)
                    
                    # Skip if email was already processed (result is None)
                    if result is None:
                        continue
                    
                    if result['priority'] == TicketPriority.HIGH:
                        high_priority.append(result)
                    elif result['priority'] == TicketPriority.MEDIUM:
                        medium_priority.append(result)
                    else:
                        low_priority.append(result)
                except Exception as e:
                    logger.error(f"Error processing email {email.get('id', 'unknown')}: {e}")
                    continue
            
            # Step 4: Send morning briefing
            self.slack.send_support_briefing(
                total_tickets=len(emails),
                high_priority=[{
                    'description': f"{t['sender_type']} — {t['category']}",
                    'action': 'DRAFT READY' if t['draft'] else 'CONTEXT READY'
                } for t in high_priority],
                medium_priority=[{
                    'description': f"{t['category']}",
                    'action': 'DRAFT READY' if t['draft'] else 'CONTEXT READY'
                } for t in medium_priority],
                low_priority=[{
                    'description': 'various',
                    'action': 'DRAFT READY'
                } for _ in low_priority]
            )
            
            return {
                "total": len(emails),
                "high": len(high_priority),
                "medium": len(medium_priority),
                "low": len(low_priority)
            }
            
        except Exception as e:
            logger.error(f"Error processing overnight batch: {e}")
            return {"total": 0, "high": 0, "medium": 0, "low": 0}
        finally:
            agent_db.close()
            marketplace_db.close()
    
    def _process_email(
        self,
        email: Dict,
        marketplace_db: Session,
        agent_db: Session
    ) -> Dict:
        """Process a single support email."""
        
        # Extract sender email
        sender_email = self._extract_email(email['from'])
        
        # Identify sender type
        sender_type, sender_id = self._identify_sender(sender_email, marketplace_db)
        
        # Keyword override check (safety net)
        if self._has_high_priority_keywords(email['body'] + email['subject']):
            priority = TicketPriority.HIGH
            category = TicketCategory.COMPLAINT_ESCALATION
            confidence = 1.0
        else:
            # LLM classification
            classification = self._classify_email(email['body'], email['subject'], sender_type)
            category = TicketCategory(classification['category'])
            priority = TicketPriority(classification['priority'])
            confidence = classification['confidence']
        
        # Generate draft if appropriate
        draft = None
        if confidence > 0.8 and priority != TicketPriority.HIGH:
            draft = self._generate_draft(email, category, sender_type)
        
        # Check if email already processed
        existing = agent_db.query(SupportTicket).filter(
            SupportTicket.source_email_id == email['id']
        ).first()
        
        if existing:
            logger.info(f"Email {email['id']} already processed, skipping")
            return None
        
        # Create support ticket record
        ticket = SupportTicket(
            source_email_id=email['id'],
            sender_type=sender_type,
            sender_id=sender_id,
            sender_email=sender_email,
            raw_text=email['body'],
            category=category,
            priority=priority,
            classification_confidence=confidence,
            status=TicketStatus.DRAFTED if draft else TicketStatus.NEW,
            agent_draft=draft
        )
        
        agent_db.add(ticket)
        agent_db.commit()
        
        # Log action
        self._log_action(
            agent_db,
            ActionType.CLASSIFICATION,
            ticket.id,
            f"Classified as {category.value} with {confidence:.2f} confidence"
        )
        
        return {
            'ticket_id': ticket.id,
            'sender_type': sender_type.value,
            'category': category.value,
            'priority': priority.value,
            'draft': draft
        }
    
    def _extract_email(self, from_header: str) -> str:
        """Extract email address from From header."""
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1)
        return from_header
    
    def _identify_sender(self, email: str, db: Session) -> tuple[SenderType, Optional[int]]:
        """Identify if sender is a buyer, seller, or unknown."""
        seller = db.query(Seller).filter(Seller.email == email).first()
        if seller:
            return SenderType.SELLER, seller.id
        
        buyer = db.query(Buyer).filter(Buyer.email == email).first()
        if buyer:
            return SenderType.BUYER, buyer.id
        
        return SenderType.UNKNOWN, None
    
    def _has_high_priority_keywords(self, text: str) -> bool:
        """Check for high-priority keywords that override classification."""
        text_lower = text.lower()
        for keyword in settings.support_keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def _classify_email(
        self,
        body: str,
        subject: str,
        sender_type: SenderType
    ) -> Dict:
        """Classify email intent and priority using LLM."""

        categories = [
            "order_status",
            "refund_return",
            "account_password",
            "seller_onboarding",
            "payout_payment",
            "product_listing",
            "complaint_escalation",
            "other"
        ]

        schema_description = """
        {
            "category": "one of: order_status, refund_return, account_password, seller_onboarding, payout_payment, product_listing, complaint_escalation, other",
            "priority": "one of: high, medium, low",
            "confidence": "float between 0 and 1"
        }
        """

        # Truncate body to avoid context length errors
        max_body_length = 4000  # characters
        truncated = False
        if len(body) > max_body_length:
            body = body[:max_body_length] + "... [truncated]"
            truncated = True

        prompt = f"""Classify this support email.

Sender type: {sender_type.value}
Subject: {subject}
Body: {body}
{'(Note: Email body was truncated due to length)' if truncated else ''}

Available categories: {', '.join(categories)}

Priority guidelines:
- HIGH: payout issues, account suspensions, threats (chargebacks, legal), top-tier sellers
- MEDIUM: return requests, listing issues, onboarding questions
- LOW: order status, password resets, general questions"""

        result = self.llm.extract_structured_data(
            text=body,
            extraction_prompt=prompt,
            schema_description=schema_description
        )

        return result
    
    def _generate_draft(
        self,
        email: Dict,
        category: TicketCategory,
        sender_type: SenderType
    ) -> Optional[str]:
        """Generate a draft response for the email."""
        
        # Only generate drafts for certain categories
        draftable_categories = [
            TicketCategory.ORDER_STATUS,
            TicketCategory.ACCOUNT_PASSWORD,
            TicketCategory.SELLER_ONBOARDING
        ]
        
        if category not in draftable_categories:
            return None
        
        # Generate draft based on category
        if category == TicketCategory.ORDER_STATUS:
            draft = f"""Hi,

Thanks for checking on your order status. I've looked into this for you and [order status details].

Let me know if you have any other questions!

Best,
Marketplace Team"""
        
        elif category == TicketCategory.ACCOUNT_PASSWORD:
            draft = f"""Hi,

I can help you with your account access. Here's a link to reset your password: [reset link]

If you're still having trouble, let me know and I'll look into it further.

Best,
Marketplace Team"""
        
        elif category == TicketCategory.SELLER_ONBOARDING:
            draft = f"""Hi,

Welcome to the marketplace! I'm happy to help you get started with onboarding.

Here are the next steps:
1. Complete your profile
2. Add your payout information
3. List your first item

Let me know if you have any questions along the way!

Best,
Marketplace Team"""
        
        else:
            draft = None
        
        return draft
    
    def _log_action(self, db: Session, action_type: ActionType, entity_id: int, description: str):
        """Log an agent action for metrics tracking."""
        action = AgentAction(
            agent_type=AgentType.SUPPORT_LEAD,
            action_type=action_type,
            entity_type="support_ticket",
            entity_id=entity_id,
            description=description
        )
        db.add(action)
        db.commit()
    
    def _test_single_email(self, body: str, from_email: str, subject: str) -> Dict:
        """Test classification on a single email (for CLI testing)."""
        from lighthouse.integrations.database import get_marketplace_db, get_agent_db
        
        marketplace_db = get_marketplace_db()
        agent_db = get_agent_db()
        
        try:
            # Identify sender type
            sender_type, sender_id = self._identify_sender(from_email, marketplace_db)
            
            # Keyword override check
            if self._has_high_priority_keywords(body + subject):
                priority = TicketPriority.HIGH
                category = TicketCategory.COMPLAINT_ESCALATION
                confidence = 1.0
            else:
                # LLM classification
                classification = self._classify_email(body, subject, sender_type)
                category = TicketCategory(classification['category'])
                priority = TicketPriority(classification['priority'])
                confidence = classification['confidence']
            
            # Generate draft if appropriate
            draft = None
            if confidence > 0.8 and priority != TicketPriority.HIGH:
                draft = self._generate_draft({'body': body, 'subject': subject}, category, sender_type)
            
            return {
                'sender_type': sender_type.value,
                'sender_id': sender_id,
                'category': category.value,
                'priority': priority.value,
                'classification_confidence': confidence,
                'agent_draft': draft,
                'reasoning': f"Email classified as {category.value} with {priority.value} priority based on content analysis"
            }
            
        finally:
            marketplace_db.close()
            agent_db.close()
    
    def approve_batch_low_priority(self) -> Dict:
        """Show preview of low-priority tickets with mismatch flagging before sending."""
        agent_db = get_agent_db()
        
        try:
            tickets = agent_db.query(SupportTicket).filter(
                SupportTicket.priority == TicketPriority.LOW,
                SupportTicket.status == TicketStatus.DRAFTED,
                SupportTicket.sender_type == SenderType.BUYER  # Only buyers for batch approve
            ).all()
            
            # Build preview with mismatch flagging
            preview = []
            for ticket in tickets:
                if ticket.agent_draft:
                    # Check for category-sender type mismatch
                    mismatch = False
                    if ticket.sender_type == SenderType.SELLER and ticket.category in [TicketCategory.ORDER_STATUS, TicketCategory.ACCOUNT_PASSWORD]:
                        mismatch = True
                    elif ticket.sender_type == SenderType.BUYER and ticket.category in [TicketCategory.SELLER_ONBOARDING, TicketCategory.PAYOUT_PAYMENT]:
                        mismatch = True
                    
                    preview.append({
                        'ticket_id': ticket.id,
                        'sender_email': ticket.sender_email,
                        'sender_type': ticket.sender_type.value,
                        'category': ticket.category.value,
                        'mismatch_flag': '⚠️' if mismatch else '',
                        'draft_preview': ticket.agent_draft[:100] + '...' if len(ticket.agent_draft) > 100 else ticket.agent_draft
                    })
            
            # Send preview to Slack
            if preview:
                self.slack.send_message(
                    channel=settings.slack_channel_support,
                    text=f"📋 Approve All Low-Priority Preview ({len(preview)} tickets)\n\n" +
                          "\n".join([f"{p['mismatch_flag']} {p['sender_email']} — {p['category']}" for p in preview])
                )
            
            return {
                'total_tickets': len(preview),
                'preview': preview,
                'ready_to_send': len([p for p in preview if not p['mismatch_flag']])
            }
            
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            return {'total_tickets': 0, 'preview': [], 'ready_to_send': 0}
        finally:
            agent_db.close()
    
    def confirm_and_send_batch(self) -> int:
        """Confirm and send all low-priority drafted tickets via Gmail."""
        agent_db = get_agent_db()
        
        try:
            tickets = agent_db.query(SupportTicket).filter(
                SupportTicket.priority == TicketPriority.LOW,
                SupportTicket.status == TicketStatus.DRAFTED,
                SupportTicket.sender_type == SenderType.BUYER  # Only buyers for batch approve
            ).all()
            
            count = 0
            for ticket in tickets:
                if ticket.agent_draft and ticket.sender_email:
                    # Send the email via Gmail
                    self.gmail.send_email(
                        to=ticket.sender_email,
                        subject=f"Re: Your support inquiry",
                        body=ticket.agent_draft
                    )
                    ticket.status = TicketStatus.SENT
                    count += 1
            
            agent_db.commit()
            logger.info(f"Approved and sent {count} low-priority tickets via Gmail")
            return count
            
        except Exception as e:
            logger.error(f"Error approving batch: {e}")
            agent_db.rollback()
            return 0
        finally:
            agent_db.close()
