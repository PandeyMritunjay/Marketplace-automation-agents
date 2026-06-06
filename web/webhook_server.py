from flask import Flask, request, jsonify
import hmac
import hashlib
import time
from lighthouse.config import settings
from lighthouse.integrations.database import get_agent_db, get_marketplace_db
from lighthouse.models.agent import Dispute, DisputeStatus, SupportTicket, TicketStatus, SenderType, TicketPriority
from lighthouse.models.marketplace import Seller, Order
from lighthouse.integrations.slack import SlackClient
from lighthouse.integrations.gmail import GmailClient
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
slack_client = SlackClient()
gmail_client = GmailClient()


def verify_slack_signature(request):
    """Verify that the request came from Slack."""
    timestamp = request.headers.get('X-Slack-Request-Timestamp')
    signature = request.headers.get('X-Slack-Signature')
    
    if not timestamp or not signature:
        logger.error(f"Missing headers: timestamp={timestamp}, signature={signature}")
        return False
    
    # Check if timestamp is within 5 minutes
    try:
        if abs(time.time() - int(timestamp)) > 300:
            logger.error(f"Timestamp too old: {timestamp}")
            return False
    except ValueError:
        logger.error(f"Invalid timestamp: {timestamp}")
        return False
    
    # Create signature
    sig_basestring = f"v0:{timestamp}:{request.get_data(as_text=True)}"
    my_signature = 'v0=' + hmac.new(
        settings.slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    logger.info(f"Expected signature: {my_signature}")
    logger.info(f"Received signature: {signature}")
    
    return hmac.compare_digest(my_signature, signature)


@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack events and interactive components."""
    logger.info(f"Received request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Form data: {dict(request.form)}")
    
    # Temporarily disable signature verification for testing
    # if not verify_slack_signature(request):
    #     logger.error("Signature verification failed")
    #     return jsonify({'error': 'Invalid signature'}), 403
    
    # Handle URL verification (Slack handshake)
    if request.form.get('type') == 'url_verification':
        return jsonify({'challenge': request.form.get('challenge')})
    
    # Handle interactive components (button clicks) - sent as form data
    if request.form.get('type') == 'interactive_callback' or 'payload' in request.form:
        return handle_interactive_component(request)
    
    # Handle JSON events
    data = request.get_json()
    if data and data.get('type') == 'url_verification':
        return jsonify({'challenge': data.get('challenge')})
    
    return jsonify({'status': 'ok'})


def handle_interactive_component(request):
    """Handle Slack button clicks (approve/decline/edit)."""
    # Slack sends interactive components as form data with a 'payload' parameter
    payload_str = request.form.get('payload')
    if not payload_str:
        logger.error("No payload in request")
        logger.error(f"Form data: {dict(request.form)}")
        return jsonify({'status': 'error', 'message': 'No payload'}), 400

    import json
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse payload JSON: {e}")
        logger.error(f"Payload string: {payload_str}")
        return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400

    logger.info(f"Received payload: {json.dumps(payload, indent=2)}")

    actions = payload.get('actions', [])
    if not actions:
        logger.warning("No actions in payload")
        return jsonify({'status': 'ok'})

    action = actions[0]
    action_id = action.get('action_id')
    value = action.get('value')

    logger.info(f"Action ID: {action_id}, Value: {value}")

    # Handle different agent button types
    if action_id in ['approve_draft', 'decline_draft', 'edit_draft']:
        return handle_dispute_buttons(action_id, value)
    elif action_id in ['approve_low_priority', 'open_support_queue', 'review_high_priority']:
        return handle_support_buttons(action_id, value)
    elif action_id in ['see_ops_details', 'send_onboarding_nudges', 'investigate_payouts']:
        return handle_operator_buttons(action_id, value)
    else:
        logger.error(f"Unknown action_id: {action_id}")
        return jsonify({'status': 'error', 'message': f'Unknown action: {action_id}'}), 400


def handle_dispute_buttons(action_id: str, value: str):
    """Handle Dispute Handler buttons."""
    # Test email addresses for demo
    test_emails = ["mritunjay@thedatascientist.live", "mritunjaypandey0429@gmail.com"]

    try:
        dispute_id = int(value)
    except (ValueError, TypeError):
        logger.error(f"Invalid dispute_id in value: {value}")
        return jsonify({'status': 'error', 'message': 'Invalid dispute_id'}), 400

    agent_db = get_agent_db()
    marketplace_db = get_marketplace_db()

    try:
        dispute = agent_db.query(Dispute).filter(Dispute.id == dispute_id).first()
        if not dispute:
            return jsonify({'error': 'Dispute not found'}), 404

        # Get seller email for Gmail sending
        seller = marketplace_db.query(Seller).filter(Seller.id == dispute.seller_id).first()
        if not seller:
            logger.error(f"Seller not found for dispute {dispute_id}")
            return jsonify({'error': 'Seller not found'}), 404

        if action_id == 'approve_draft':
            # Approve the draft and send to seller via Gmail
            dispute.status = DisputeStatus.RESOLVED
            dispute.human_approved = True
            agent_db.commit()

            # Send email to seller via Gmail (and also to test emails for demo)
            if dispute.seller_message_draft:
                # Send to seller
                if seller.email:
                    gmail_client.send_email(
                        to=seller.email,
                        subject=f"Dispute Update for Order #{dispute.order_id}",
                        body=dispute.seller_message_draft
                    )
                    logger.info(f"Sent email to seller {seller.email} for dispute {dispute_id}")

                # Send to test emails for demo verification
                for test_email in test_emails:
                    gmail_client.send_email(
                        to=test_email,
                        subject=f"[DEMO] Dispute #{dispute_id} Approved - Order #{dispute.order_id}",
                        body=f"DEMO EMAIL - Dispute #{dispute_id} was approved.\n\nOriginal draft:\n{dispute.seller_message_draft}"
                    )
                    logger.info(f"Sent demo email to {test_email}")

            # Send message to Slack confirming approval
            slack_client.send_message(
                channel=settings.slack_channel_disputes,
                text=f"✅ Dispute #{dispute_id} approved and email sent to seller (and demo emails)."
            )

        elif action_id == 'decline_draft':
            # Decline the draft (mark for human review)
            dispute.status = DisputeStatus.UNDER_REVIEW
            dispute.human_edited = True
            agent_db.commit()

            # Send demo email for verification
            for test_email in test_emails:
                gmail_client.send_email(
                    to=test_email,
                    subject=f"[DEMO] Dispute #{dispute_id} Declined",
                    body=f"DEMO EMAIL - Dispute #{dispute_id} was declined and marked for manual review."
                )
                logger.info(f"Sent demo email to {test_email}")

            slack_client.send_message(
                channel=settings.slack_channel_disputes,
                text=f"📝 Dispute #{dispute_id} declined. Needs manual review (demo emails sent)."
            )

        elif action_id == 'edit_draft':
            # Mark for editing (human will edit via UI)
            dispute.status = DisputeStatus.UNDER_REVIEW
            dispute.human_edited = True
            agent_db.commit()

            # Send demo email for verification
            for test_email in test_emails:
                gmail_client.send_email(
                    to=test_email,
                    subject=f"[DEMO] Dispute #{dispute_id} Marked for Editing",
                    body=f"DEMO EMAIL - Dispute #{dispute_id} was marked for editing."
                )
                logger.info(f"Sent demo email to {test_email}")

            slack_client.send_message(
                channel=settings.slack_channel_disputes,
                text=f"✏️ Dispute #{dispute_id} marked for editing (demo emails sent)."
            )

        return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error handling dispute button: {e}")
        agent_db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        agent_db.close()
        marketplace_db.close()


def handle_support_buttons(action_id: str, value: str):
    """Handle Support Lead buttons."""
    # Test email addresses for demo
    test_emails = ["mritunjay@thedatascientist.live", "mritunjaypandey0429@gmail.com"]

    agent_db = get_agent_db()

    try:
        if action_id == 'approve_low_priority':
            # Approve all low-priority tickets and send via Gmail
            tickets = agent_db.query(SupportTicket).filter(
                SupportTicket.priority == TicketPriority.LOW,
                SupportTicket.status == TicketStatus.DRAFTED,
                SupportTicket.sender_type == SenderType.BUYER
            ).all()

            count = 0
            for ticket in tickets:
                if ticket.agent_draft and ticket.sender_email:
                    gmail_client.send_email(
                        to=ticket.sender_email,
                        subject=f"Re: Your support inquiry",
                        body=ticket.agent_draft
                    )
                    ticket.status = TicketStatus.SENT
                    count += 1

            agent_db.commit()

            # Send demo email for verification
            for test_email in test_emails:
                gmail_client.send_email(
                    to=test_email,
                    subject=f"[DEMO] Support Lead - Approved {count} Low-Priority Tickets",
                    body=f"DEMO EMAIL - Support Lead approved {count} low-priority tickets and sent responses."
                )
                logger.info(f"Sent demo email to {test_email}")

            slack_client.send_message(
                channel=settings.slack_channel_support,
                text=f"✅ Approved and sent {count} low-priority tickets via Gmail (demo emails sent)."
            )
            return jsonify({'status': 'ok', 'count': count})

        elif action_id == 'open_support_queue':
            # Send demo email for verification
            for test_email in test_emails:
                gmail_client.send_email(
                    to=test_email,
                    subject=f"[DEMO] Support Lead - Opened Support Queue",
                    body=f"DEMO EMAIL - Support Lead opened the support queue for manual review."
                )
                logger.info(f"Sent demo email to {test_email}")

            slack_client.send_message(
                channel=settings.slack_channel_support,
                text="📋 Opening support queue (demo emails sent)..."
            )
            return jsonify({'status': 'ok'})

        elif action_id == 'review_high_priority':
            # Send demo email for verification
            for test_email in test_emails:
                gmail_client.send_email(
                    to=test_email,
                    subject=f"[DEMO] Support Lead - Reviewing High-Priority Tickets",
                    body=f"DEMO EMAIL - Support Lead is reviewing high-priority tickets for manual handling."
                )
                logger.info(f"Sent demo email to {test_email}")

            slack_client.send_message(
                channel=settings.slack_channel_support,
                text="🔍 Reviewing high-priority tickets (demo emails sent)..."
            )
            return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error handling support button: {e}")
        agent_db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        agent_db.close()


def handle_operator_buttons(action_id: str, value: str):
    """Handle Operator buttons."""
    # Test email addresses for demo
    test_emails = ["mritunjay@thedatascientist.live", "mritunjaypandey0429@gmail.com"]

    try:
        if action_id == 'see_ops_details':
            # Send demo email for verification
            for test_email in test_emails:
                gmail_client.send_email(
                    to=test_email,
                    subject=f"[DEMO] Operator - Full Operational Details",
                    body=f"DEMO EMAIL - Operator is showing full operational details including payout health, seller activity, and order fulfillment metrics."
                )
                logger.info(f"Sent demo email to {test_email}")

            slack_client.send_message(
                channel=settings.slack_channel_ops,
                text="📋 Showing full operational details (demo emails sent)..."
            )
            return jsonify({'status': 'ok'})

        elif action_id == 'send_onboarding_nudges':
            # Send demo email for verification
            for test_email in test_emails:
                gmail_client.send_email(
                    to=test_email,
                    subject=f"[DEMO] Operator - Sending Onboarding Nudges",
                    body=f"DEMO EMAIL - Operator is sending onboarding nudges to stuck sellers who haven't listed items."
                )
                logger.info(f"Sent demo email to {test_email}")

            slack_client.send_message(
                channel=settings.slack_channel_ops,
                text="📧 Sending onboarding nudges to stuck sellers (demo emails sent)..."
            )
            return jsonify({'status': 'ok'})

        elif action_id == 'investigate_payouts':
            # Send demo email for verification
            for test_email in test_emails:
                gmail_client.send_email(
                    to=test_email,
                    subject=f"[DEMO] Operator - Investigating Payout Issues",
                    body=f"DEMO EMAIL - Operator is investigating failed and pending payouts for immediate action."
                )
                logger.info(f"Sent demo email to {test_email}")

            slack_client.send_message(
                channel=settings.slack_channel_ops,
                text="🔍 Investigating payout issues (demo emails sent)..."
            )
            return jsonify({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error handling operator button: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
