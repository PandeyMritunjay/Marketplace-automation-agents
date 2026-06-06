from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from lighthouse.integrations.database import get_marketplace_db, get_agent_db
from lighthouse.integrations.slack import SlackClient
from lighthouse.services.llm import OpenAIService
from lighthouse.models.marketplace import Seller, Order, Payout, Listing, SellerStatus
from lighthouse.models.agent import (
    OperationalAlert, AlertType, AlertSeverity, AlertStatus,
    AgentAction, ActionType, AgentType
)
from lighthouse.config import settings
import logging
import json
import time
import threading

logger = logging.getLogger(__name__)


class Operator:
    def __init__(self):
        self.llm = OpenAIService()
        self.slack = SlackClient()
        self._scheduler_thread = None
        self._stop_event = threading.Event()
    
    def start_scheduler(self):
        """Start the scheduler to run daily health check at 8am."""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            logger.warning("Scheduler already running")
            return
        
        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info("Scheduler started - will run daily health check at 8am")
    
    def stop_scheduler(self):
        """Stop the scheduler."""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._stop_event.set()
            self._scheduler_thread.join(timeout=5)
            logger.info("Scheduler stopped")
    
    def _scheduler_loop(self):
        """Scheduler loop that runs health check at 8am daily."""
        while not self._stop_event.is_set():
            now = datetime.now()
            target_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
            
            # If it's already past 8am today, schedule for tomorrow
            if now >= target_time:
                target_time += timedelta(days=1)
            
            # Calculate seconds until next run
            seconds_until_run = (target_time - now).total_seconds()
            logger.info(f"Next health check scheduled for {target_time} (in {seconds_until_run:.0f} seconds)")
            
            # Wait until target time or stop event
            if self._stop_event.wait(timeout=seconds_until_run):
                break  # Stop event was set
            
            # Run health check
            logger.info("Running scheduled daily health check")
            try:
                self.run_daily_health_check()
            except Exception as e:
                logger.error(f"Error in scheduled health check: {e}")
    
    def run_daily_health_check(self) -> Dict:
        """
        Run overnight operational health check and send daily briefing.
        
        Steps:
        1. Check payout health
        2. Check seller activity (churn signals)
        3. Check order fulfillment
        4. Generate briefing and send to Slack
        """
        marketplace_db = get_marketplace_db()
        agent_db = get_agent_db()
        
        try:
            alerts = []
            
            # Step 1: Payout health
            payout_alerts = self._check_payout_health(marketplace_db)
            alerts.extend(payout_alerts)
            
            # Step 2: Seller activity
            activity_alerts = self._check_seller_activity(marketplace_db)
            alerts.extend(activity_alerts)
            
            # Step 3: Order fulfillment
            fulfillment_alerts = self._check_order_fulfillment(marketplace_db)
            alerts.extend(fulfillment_alerts)
            
            # Save alerts to database
            for alert_data in alerts:
                alert = OperationalAlert(
                    alert_type=AlertType(alert_data['type']),
                    severity=AlertSeverity(alert_data['severity']),
                    status=AlertStatus.OPEN,
                    seller_id=alert_data.get('seller_id'),
                    order_id=alert_data.get('order_id'),
                    payout_id=alert_data.get('payout_id'),
                    listing_id=alert_data.get('listing_id'),
                    title=alert_data['title'],
                    description=alert_data['description'],
                    metric_value=alert_data.get('metric_value'),
                    threshold=alert_data.get('threshold'),
                    suggested_action=alert_data.get('suggested_action'),
                    draft_communication=alert_data.get('draft_communication')
                )
                agent_db.add(alert)
            
            agent_db.commit()
            
            # Step 4: Generate healthy metrics
            healthy_metrics = self._get_healthy_metrics(marketplace_db)
            
            # Step 5: Send briefing
            critical = [a for a in alerts if a['severity'] == 'critical']
            warnings = [a for a in alerts if a['severity'] == 'warning']
            
            self.slack.send_ops_briefing(
                critical_alerts=critical,
                warning_alerts=warnings,
                healthy_metrics=healthy_metrics
            )
            
            # Format output to match documentation
            formatted_alerts = self._format_alerts_for_output(alerts)
            
            # Print full JSON output to console
            print("\n" + "="*80)
            print("OPERATOR OUTPUT (JSON):")
            print("="*80)
            print(json.dumps({"alerts": formatted_alerts}, indent=2))
            print("="*80 + "\n")
            
            return {
                "total_alerts": len(alerts),
                "critical": len(critical),
                "warnings": len(warnings),
                "alerts": formatted_alerts
            }
            
        except Exception as e:
            # Send error alert to Slack on database failure
            logger.error(f"Database error in health check: {e}")
            self.slack.send_message(
                channel=settings.slack_channel_ops,
                text=f"⚠️ DATABASE ERROR: Health check failed - {str(e)}"
            )
            agent_db.rollback()
            return {"total_alerts": 0, "critical": 0, "warnings": 0, "error": str(e)}
        finally:
            marketplace_db.close()
            agent_db.close()
    
    def _format_alerts_for_output(self, alerts: List[Dict]) -> List[Dict]:
        """Format alerts to match documentation output structure."""
        # Group alerts by type
        grouped = {}
        for alert in alerts:
            alert_type = alert['type']
            if alert_type not in grouped:
                grouped[alert_type] = {
                    'alert_type': alert_type,
                    'severity': alert['severity'],
                    'count': 0,
                    'sellers_affected': [],
                    'suggested_action': alert.get('suggested_action', ''),
                    'draft_communication': alert.get('draft_communication', '')
                }
            grouped[alert_type]['count'] += 1
            
            # Add seller if available
            if 'seller_id' in alert:
                # Get seller email from database if needed
                # For now, just use the title to extract seller name
                title = alert.get('title', '')
                if ' — ' in title:
                    seller_name = title.split(' — ')[0]
                    grouped[alert_type]['sellers_affected'].append(seller_name)
            
            # Add total_amount for payout alerts
            if alert_type == 'payout_pending' and 'metric_value' in alert:
                if 'total_amount' not in grouped[alert_type]:
                    grouped[alert_type]['total_amount'] = 0
                # Extract amount from title or use metric
                if '$' in alert.get('title', ''):
                    try:
                        amount_str = alert['title'].split('$')[1].split(')')[0]
                        grouped[alert_type]['total_amount'] += float(amount_str)
                    except:
                        pass
            
            # Add top_tier_sellers for inactive alerts
            if alert_type == 'seller_inactive':
                if 'top_tier_sellers' not in grouped[alert_type]:
                    grouped[alert_type]['top_tier_sellers'] = 0
                # Check if seller is top tier (would need DB lookup, using placeholder)
                # For now, just increment if count > 0
                if alert.get('metric_value', 0) > 0:
                    grouped[alert_type]['top_tier_sellers'] += 1
        
        return list(grouped.values())
    
    def _check_payout_health(self, db: Session) -> List[Dict]:
        """Check for payout issues."""
        alerts = []
        
        # Payouts pending > threshold days
        threshold_date = datetime.utcnow() - timedelta(days=settings.operator_payout_pending_days)
        
        pending_payouts = db.query(Payout, Seller).join(
            Seller, Payout.seller_id == Seller.id
        ).filter(
            Payout.status == 'pending',
            Payout.initiated_at < threshold_date
        ).all()
        
        for payout, seller in pending_payouts:
            alerts.append({
                'type': 'payout_pending',
                'severity': 'critical',
                'seller_id': seller.id,
                'payout_id': payout.id,
                'title': f"{seller.name} — Payout pending {settings.operator_payout_pending_days}+ days (${payout.amount:.2f})",
                'description': f"Payout of ${payout.amount:.2f} initiated on {payout.initiated_at.strftime('%Y-%m-%d')} has not completed",
                'metric_value': (datetime.utcnow() - payout.initiated_at).days,
                'threshold': settings.operator_payout_pending_days,
                'suggested_action': 'Contact seller to verify payout information',
                'draft_communication': self._generate_payout_nudge(seller.name, payout.amount)
            })
        
        # Failed payouts
        failed_payouts = db.query(Payout, Seller).join(
            Seller, Payout.seller_id == Seller.id
        ).filter(
            Payout.status == 'failed'
        ).all()
        
        for payout, seller in failed_payouts:
            alerts.append({
                'type': 'payout_failed',
                'severity': 'critical',
                'seller_id': seller.id,
                'payout_id': payout.id,
                'title': f"{seller.name} — Payout failed (${payout.amount:.2f})",
                'description': f"Payout of ${payout.amount:.2f} failed: {payout.error_message or 'Unknown error'}",
                'suggested_action': 'Investigate bank details and retry',
                'draft_communication': self._generate_payout_failed_email(seller.name, payout.amount, payout.error_message)
            })
        
        return alerts
    
    def _check_seller_activity(self, db: Session) -> List[Dict]:
        """Check for inactive sellers (churn signals)."""
        alerts = []
        
        threshold_date = datetime.utcnow() - timedelta(days=settings.operator_inactive_days)
        
        inactive_sellers = db.query(Seller).filter(
            Seller.status == SellerStatus.active,
            Seller.last_login < threshold_date
        ).all()
        
        for seller in inactive_sellers:
            # Only alert for sellers with meaningful activity
            if seller.total_orders > 10:
                alerts.append({
                    'type': 'seller_inactive',
                    'severity': 'warning',
                    'seller_id': seller.id,
                    'title': f"{seller.name} — Inactive for {settings.operator_inactive_days}+ days",
                    'description': f"Last login: {seller.last_login.strftime('%Y-%m-%d') if seller.last_login else 'Never'}. {seller.total_orders} lifetime orders, ${seller.total_gmv:.2f} GMV",
                    'metric_value': (datetime.utcnow() - seller.last_login).days if seller.last_login else 999,
                    'threshold': settings.operator_inactive_days,
                    'suggested_action': 'Send re-engagement email'
                })
        
        return alerts
    
    def _check_order_fulfillment(self, db: Session) -> List[Dict]:
        """Check for unfulfilled orders."""
        alerts = []
        
        threshold_date = datetime.utcnow() - timedelta(days=settings.operator_unfulfilled_days)
        
        unfulfilled_orders = db.query(Order, Seller).join(
            Seller, Order.seller_id == Seller.id
        ).filter(
            Order.status == 'paid',
            Order.created_at < threshold_date
        ).all()
        
        # Group by seller
        seller_order_counts = {}
        for order, seller in unfulfilled_orders:
            if seller.id not in seller_order_counts:
                seller_order_counts[seller.id] = {'seller': seller, 'count': 0, 'total': 0}
            seller_order_counts[seller.id]['count'] += 1
            seller_order_counts[seller.id]['total'] += order.total
        
        for seller_id, data in seller_order_counts.items():
            seller = data['seller']
            alerts.append({
                'type': 'unfulfilled_order',
                'severity': 'critical',
                'seller_id': seller.id,
                'title': f"{seller.name} — {data['count']} orders unfulfilled {settings.operator_unfulfilled_days}+ days (${data['total']:.2f})",
                'description': f"{data['count']} orders marked paid but not shipped. Total value: ${data['total']:.2f}",
                'metric_value': data['count'],
                'threshold': 3,  # Alert if 3+ orders
                'suggested_action': 'Contact seller about order fulfillment'
            })
        
        return alerts
    
    def _get_healthy_metrics(self, db: Session) -> Dict:
        """Get healthy operational metrics for the briefing."""
        active_sellers = db.query(func.count(Seller.id)).filter(
            Seller.status == SellerStatus.active
        ).scalar()
        
        avg_fulfillment = db.query(
            func.avg(func.datediff(Order.shipped_at, Order.created_at))
        ).filter(
            Order.shipped_at.isnot(None),
            Order.created_at > datetime.utcnow() - timedelta(days=30)
        ).scalar()
        
        if avg_fulfillment:
            avg_fulfillment_days = round(avg_fulfillment, 1)
        else:
            avg_fulfillment_days = 0
        
        new_signups = db.query(func.count(Seller.id)).filter(
            Seller.signup_date > datetime.utcnow() - timedelta(days=7)
        ).scalar()
        
        return {
            "Active seller count": active_sellers,
            "Average fulfillment time": f"{avg_fulfillment_days} days",
            "New sign-ups this week": new_signups,
            "Payment processor alerts": "None"
        }
    
    def _generate_payout_nudge(self, seller_name: str, amount: float) -> str:
        """Generate payout nudge email."""
        return f"""Hi {seller_name},

We noticed your latest payout of ${amount:.2f} hasn't completed yet — it's been pending for a while.

Could you log in and double-check your payout information? Here's a direct link: [link]

We want to make sure you get paid ASAP. Let us know if you need help.

Best,
Marketplace Team"""
    
    def _generate_payout_failed_email(self, seller_name: str, amount: float, error: str) -> str:
        """Generate payout failed email."""
        return f"""Hi {seller_name},

We tried to process your payout of ${amount:.2f} but it failed with this error: {error or 'Invalid bank details'}

This usually means there's an issue with your bank information on file. Could you log in and update your payout details? Here's a direct link: [link]

We'll retry the payout once you've updated your information.

Best,
Marketplace Team"""
    
    def _log_action(self, db: Session, action_type: ActionType, entity_id: int, description: str):
        """Log an agent action for metrics tracking."""
        action = AgentAction(
            agent_type=AgentType.OPERATOR,
            action_type=action_type,
            entity_type="operational_alert",
            entity_id=entity_id,
            description=description
        )
        db.add(action)
        db.commit()
