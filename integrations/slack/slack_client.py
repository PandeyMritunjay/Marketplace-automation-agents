from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from lighthouse.config import settings
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self):
        self.client = WebClient(token=settings.slack_bot_token)
    
    def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Optional[str]:
        """Send a message to a Slack channel."""
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
                attachments=attachments
            )
            return response["ts"]  # Timestamp of the message
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {e}")
            return None
    
    def send_dispute_notification(
        self,
        dispute_id: int,
        dispute_type: str,
        amount: float,
        buyer_name: str,
        seller_name: str,
        seller_tier: str,
        recommendation: str,
        confidence: str,
        seller_message_draft: str = "",
        buyer_message_draft: str = "",
        internal_summary: str = ""
    ) -> Optional[str]:
        """Send a dispute notification to the disputes channel."""
        text = f"� New Dispute: Order #{dispute_id} — {dispute_type}\n"
        text += f"Buyer: {buyer_name} | Seller: {seller_name} ({seller_tier})\n"
        text += f"Amount: ${amount:.2f} | Confidence: {confidence}\n"
        text += f"Recommendation: {recommendation}"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"� New Dispute: Order #{dispute_id} — {dispute_type}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Buyer:*\n{buyer_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Seller:*\n{seller_name} ({seller_tier})"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Amount:*\n${amount:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Confidence:*\n{confidence}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recommendation:* {recommendation}"
                }
            }
        ]
        
        # Add seller message draft if available
        if seller_message_draft:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Seller Message Draft:*\n```{seller_message_draft}```"
                }
            })
        
        # Add internal summary if available
        if internal_summary:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Internal Summary:*\n{internal_summary}"
                }
            })
        
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Approve"
                    },
                    "action_id": "approve_draft",
                    "value": str(dispute_id),
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "❌ Decline"
                    },
                    "action_id": "decline_draft",
                    "value": str(dispute_id),
                    "style": "danger"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✏️ Edit"
                    },
                    "action_id": "edit_draft",
                    "value": str(dispute_id)
                }
            ]
        })
        
        return self.send_message(settings.slack_channel_disputes, text, blocks=blocks)
    
    def send_support_briefing(
        self,
        total_tickets: int,
        high_priority: List[Dict],
        medium_priority: List[Dict],
        low_priority: List[Dict]
    ) -> Optional[str]:
        """Send morning support briefing."""
        text = f"☀️ Morning Support Briefing — {total_tickets} new tickets overnight\n\n"
        
        if high_priority:
            text += f"🔴 HIGH PRIORITY ({len(high_priority)})\n"
            for ticket in high_priority:
                text += f"  • {ticket['description']} — {ticket['action']}\n"
        
        if medium_priority:
            text += f"\n🟡 MEDIUM PRIORITY ({len(medium_priority)})\n"
            for ticket in medium_priority:
                text += f"  • {ticket['description']} — {ticket['action']}\n"
        
        if low_priority:
            text += f"\n🟢 LOW PRIORITY ({len(low_priority)})\n"
            text += f"  • {len(low_priority)} tickets — DRAFTS READY\n"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"☀️ Morning Support Briefing — {total_tickets} new tickets"
                }
            }
        ]
        
        if high_priority:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔴 *HIGH PRIORITY ({len(high_priority)})*\n" + 
                            "\n".join([f"• {t['description']} — {t['action']}" for t in high_priority])
                }
            })
        
        if medium_priority:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🟡 *MEDIUM PRIORITY ({len(medium_priority)})*\n" +
                            "\n".join([f"• {t['description']} — {t['action']}" for t in medium_priority])
                }
            })
        
        if low_priority:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🟢 *LOW PRIORITY ({len(low_priority)})*\n• {len(low_priority)} tickets — DRAFTS READY"
                }
            })
        
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 Open Queue"
                    },
                    "action_id": "open_support_queue"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Approve All Low-Priority"
                    },
                    "action_id": "approve_low_priority",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 Review High-Priority"
                    },
                    "action_id": "review_high_priority"
                }
            ]
        })
        
        return self.send_message(settings.slack_channel_support, text, blocks=blocks)
    
    def send_ops_briefing(
        self,
        critical_alerts: List[Dict],
        warning_alerts: List[Dict],
        healthy_metrics: Dict
    ) -> Optional[str]:
        """Send daily operations briefing."""
        text = f"📊 Daily Ops Briefing\n\n"
        
        if critical_alerts:
            text += f"🚨 NEEDS ATTENTION TODAY\n"
            for alert in critical_alerts:
                text += f"  • {alert['title']}\n"
        
        if warning_alerts:
            text += f"\n🟡 SHOULD ADDRESS THIS WEEK\n"
            for alert in warning_alerts:
                text += f"  • {alert['title']}\n"
        
        text += f"\n✅ HEALTHY\n"
        for metric, value in healthy_metrics.items():
            text += f"  • {metric}: {value}\n"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Daily Ops Briefing"
                }
            }
        ]
        
        if critical_alerts:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🚨 *NEEDS ATTENTION TODAY*\n" +
                            "\n".join([f"• {a['title']}" for a in critical_alerts])
                }
            })
        
        if warning_alerts:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🟡 *SHOULD ADDRESS THIS WEEK*\n" +
                            "\n".join([f"• {a['title']}" for a in warning_alerts])
                }
            })
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ *HEALTHY*\n" +
                        "\n".join([f"• {k}: {v}" for k, v in healthy_metrics.items()])
            }
        })
        
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 See Full Details"
                    },
                    "action_id": "see_ops_details"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📧 Send Onboarding Nudges"
                    },
                    "action_id": "send_onboarding_nudges"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 Investigate Payout Issues"
                    },
                    "action_id": "investigate_payouts",
                    "style": "danger"
                }
            ]
        })
        
        return self.send_message(settings.slack_channel_ops, text, blocks=blocks)
    
    def update_message_reaction(
        self,
        channel: str,
        timestamp: str,
        reaction: str
    ) -> bool:
        """Add a reaction to a message (for feedback)."""
        try:
            self.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=reaction
            )
            return True
        except SlackApiError as e:
            logger.error(f"Error adding reaction: {e}")
            return False
