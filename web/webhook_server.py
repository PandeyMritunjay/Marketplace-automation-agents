from flask import Flask, request, jsonify
import hmac
import hashlib
import base64
import time
from lighthouse.config import settings
from lighthouse.integrations.database import get_agent_db
from lighthouse.models.agent import Dispute, DisputeStatus
from lighthouse.integrations.slack import SlackClient
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
slack_client = SlackClient()


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
        return jsonify({'status': 'error'}), 400
    
    import json
    payload = json.loads(payload_str)
    
    actions = payload.get('actions', [])
    if not actions:
        return jsonify({'status': 'ok'})
    
    action = actions[0]
    action_id = action.get('action_id')
    value = action.get('value')
    
    # Parse dispute_id from value
    try:
        dispute_id = int(value)
    except (ValueError, TypeError):
        logger.error(f"Invalid dispute_id in value: {value}")
        return jsonify({'status': 'error'}), 400
    
    agent_db = get_agent_db()
    
    try:
        dispute = agent_db.query(Dispute).filter(Dispute.id == dispute_id).first()
        if not dispute:
            return jsonify({'error': 'Dispute not found'}), 404
        
        if action_id == 'approve_draft':
            # Approve the draft and send to seller
            dispute.status = DisputeStatus.RESOLVED
            dispute.human_approved = True
            agent_db.commit()
            
            # Send message to Slack confirming approval
            slack_client.send_message(
                channel=settings.slack_channel_disputes,
                text=f"✅ Dispute #{dispute_id} approved and sent to seller."
            )
            
        elif action_id == 'decline_draft':
            # Decline the draft (mark for human review)
            dispute.status = DisputeStatus.UNDER_REVIEW
            dispute.human_edited = True
            agent_db.commit()
            
            slack_client.send_message(
                channel=settings.slack_channel_disputes,
                text=f"📝 Dispute #{dispute_id} declined. Needs manual review."
            )
            
        elif action_id == 'edit_draft':
            # Mark for editing (human will edit via UI)
            dispute.status = DisputeStatus.UNDER_REVIEW
            dispute.human_edited = True
            agent_db.commit()
            
            slack_client.send_message(
                channel=settings.slack_channel_disputes,
                text=f"✏️ Dispute #{dispute_id} marked for editing."
            )
            
        else:
            logger.error(f"Unknown action_id: {action_id}")
            return jsonify({'status': 'error'}), 400
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Error handling interactive component: {e}")
        agent_db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        agent_db.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
