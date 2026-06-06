# Lighthouse AI Agents

Three specialized AI agents that automate operations for marketplaces, reducing manual workload for ops teams.

## 🚀 Overview

Lighthouse is a suite of AI agents designed for marketplaces with 600+ sellers and limited ops bandwidth. The system automates dispute resolution, support ticket triage, and operational health monitoring, with human-in-the-loop approval workflows to maintain trust.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Lighthouse System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Dispute    │    │   Support    │    │   Operator   │      │
│  │   Handler    │    │    Lead      │    │              │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │              │
│         └─────────┬─────────┴─────────┬─────────┘              │
│                   │                   │                          │
│            ┌──────▼──────┐    ┌──────▼──────┐                   │
│            │   LLM Layer  │    │   Database  │                   │
│            │  (OpenAI)    │    │  (MySQL)    │                   │
│            └──────┬──────┘    └──────┬──────┘                   │
│                   │                   │                          │
│            ┌──────▼──────┐    ┌──────▼──────┐                   │
│            │ Integrations│    │   Models    │                   │
│            │  Slack/Gmail│    │  SQLAlchemy │                   │
│            └─────────────┘    └─────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 🤖 The Three Agents

# Agent 1: Dispute Handler

## Real-World Data Source
- **Buyer complaints** from marketplace dispute forms, support tickets, or emails
- **Marketplace database** containing order history, seller policies, buyer profiles
- **Seller policy database** with tier-specific rules (TOP vs mid-tier sellers)

## How It Helps
- Reduces dispute resolution time by 50%
- Automates policy application (no manual lookup needed)
- Provides consistent resolution recommendations
- Enables ops team to focus on complex cases only
- Tracks human decisions for trust calibration

## Demo Data Source
- **Sample marketplace database** with test buyers, sellers, orders
- **CLI input** simulating buyer complaint text
- **Pre-configured seller policies** for demo sellers (CeramicsByMaria, etc.)

## What It Analyzes
1. **Complaint text** → Extracts dispute type (non_delivery, damaged, wrong_item, etc.)
2. **Order context** → Order age, amount, seller tier, tracking status
3. **Seller policies** → Tier-specific refund thresholds, response time requirements
4. **Buyer sentiment** → Angry vs neutral vs happy
5. **Time elapsed** → Days since order placed vs policy thresholds

## How It Helps (Technical)
- **LLM extraction**: GPT-3.5-turbo extracts structured data from unstructured complaint text
- **Policy matching**: Applies seller-specific rules automatically
- **Confidence scoring**: HIGH/MEDIUM/LOW based on data completeness and policy match
- **Draft generation**: Creates seller and buyer message drafts automatically
- **Human-in-the-loop**: Slack buttons for Approve/Decline/Edit maintain control

## Execution Code
```bash
python -m lighthouse.main.dispute_handler --complaint "I ordered a vase 12 days ago, never got tracking" --buyer-email "rachel@example.com"
```

## Slack Buttons (Interactive)
- **✅ Approve** → Sends email to seller via Gmail, marks dispute as RESOLVED
- **❌ Decline** → Marks dispute as UNDER_REVIEW for manual handling
- **✏️ Edit** → Marks dispute as UNDER_REVIEW for human to edit draft

---

# Agent 2: Support Lead

## Real-World Data Source
- **Gmail inbox** (support@marketplace.com) with overnight support emails
- **Marketplace database** for sender identification (buyer vs seller vs unknown)
- **Email content** (subject, body, sender email)

## How It Helps
- Reduces morning triage time by 70%
- Prioritizes high-priority issues (legal threats, chargebacks)
- Auto-drafts responses for routine queries (order status, password resets)
- Enables batch approval for low-priority tickets
- Prevents missed emails during overnight hours

## Demo Data Source
- **Gmail API** connected to configured support email
- **Sample unread emails** in Gmail inbox for testing
- **Marketplace database** with test buyer/seller accounts

## What It Analyzes
1. **Sender identity** → Buyer vs Seller vs Unknown (from database lookup)
2. **Email content** → Category (order_status, refund_return, account_password, etc.)
3. **Priority level** → HIGH (legal threats, chargebacks) vs MEDIUM vs LOW
4. **Keyword override** → Safety net for urgent keywords (lawyer, fraud, legal)
5. **Confidence score** → LLM classification confidence (0-1)

## How It Helps (Technical)
- **Gmail API integration**: Fetches unread emails automatically
- **LLM classification**: GPT-3.5-turbo classifies category and priority
- **Keyword override**: Immediate HIGH priority for urgent keywords
- **Duplicate detection**: Skips already-processed emails
- **Draft generation**: Auto-generates responses for appropriate categories
- **Mismatch flagging**: Flags category-sender mismatches in preview
- **Batch approval**: Preview + send all low-priority tickets at once

## Execution Code
```bash
python -c "from lighthouse.agents.support_lead.support_lead import SupportLead; lead = SupportLead(); lead.process_overnight_batch(limit=5)"
```

## Slack Buttons (Interactive)
- **📋 Open Queue** → Opens support queue for manual review
- **✅ Approve All Low-Priority** → Shows preview with mismatch flags, sends all approved emails via Gmail
- **🔍 Review High-Priority** → Opens high-priority tickets for manual handling

---

# Agent 3: Operator

## Real-World Data Source
- **Marketplace database** with operational metrics
- **Payout data** (pending, failed, amounts, dates)
- **Order data** (fulfillment status, shipment dates)
- **Seller data** (activity, login history, tier, GMV)

## How It Helps
- Proactively identifies operational issues before they become crises
- Reduces manual health check time from hours to minutes
- Surface seller churn signals early
- Tracks payout failures for immediate action
- Provides daily briefing for ops team

## Demo Data Source
- **Sample marketplace database** with test sellers, orders, payouts
- **Simulated operational data** for demo purposes
- **Configurable thresholds** for alert generation

## What It Analyzes
1. **Payout health** → Payouts pending >7 days, failed payouts
2. **Seller activity** → Inactive sellers (no login >14 days)
3. **Order fulfillment** → Unfulfilled orders >5 days
4. **Seller tier** → TOP vs mid-tier for prioritization
5. **Threshold violations** → Configurable limits per metric

## How It Helps (Technical)
- **Database queries**: Automated health checks on operational tables
- **Threshold monitoring**: Configurable limits for each metric
- **Severity classification** → CRITICAL (needs immediate attention) vs WARNING (address this week)
- **Alert generation** → Creates operational alert records with suggested actions
- **Draft communications** → Auto-generates seller outreach emails
- **Daily scheduling** → Runs automatically at 8am daily
- **Error alerts** → Notifies Slack on database failures

## Execution Code
```bash
python -m lighthouse.main.operator
```

## Slack Buttons (Interactive)
- **📋 See Full Details** → Shows detailed alert information
- **📧 Send Onboarding Nudges** → Sends onboarding emails to stuck sellers
- **🔍 Investigate Payout Issues** → Opens payout investigation dashboard

---

# Webhook Server (Required for Slack Buttons)

## Purpose
Enables Slack interactive buttons to work by receiving button click events and processing them.

## Execution Code
```bash
python -m lighthouse.web.webhook_server
```

## Setup for Local Testing
```bash
# Expose localhost via ngrok
ngrok http 5000


# Demo Flow for Recruiters

1. **Start webhook server** (keeps running in background)
2. **Run Dispute Handler** → Show Slack notification with buttons
3. **Click Approve button** → Show Gmail email sent
4. **Run Support Lead** → Show morning briefing in Slack
5. **Click Approve All** → Show preview + batch email sending
6. **Run Operator** → Show daily health check briefing
7. **Explain human-in-the-loop** → All critical actions require approval

---

# Key Technical Features Demonstrated

1. **LLM Integration** → OpenAI GPT-3.5-turbo for data extraction and classification
2. **Human-in-the-loop** → Slack buttons maintain control while automating
3. **Trust calibration** → Confidence scores and tier-aware handling
4. **Database integration** → SQLAlchemy ORM for marketplace and agent databases
5. **External APIs** → Gmail API (email ingestion/sending), Slack API (notifications/buttons)
6. **Error handling** → Graceful failures with Slack alerts
7. **Scheduling** → Automated daily runs for Operator
8. **Edge case handling** → Proper error responses for missing data


### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/lighthouse-agents.git
cd lighthouse-agents
```

2. **Install dependencies**
```bash
pip install -r requirements_pilot.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Setup databases**
```bash
# Create MySQL databases
mysql -u root -p
CREATE DATABASE marketplace;
CREATE DATABASE agent_system;
```

5. **Load sample data**
```bash
python -c "from lighthouse.integrations.database import init_marketplace_db; init_marketplace_db()"
python -c "from lighthouse.integrations.database import init_agent_db; init_agent_db()"
```

6. **Setup Gmail API**
```bash
# Follow PILOT_SETUP_GUIDE.md for Gmail setup
python -m lighthouse.integrations.gmail.authenticate
```

7. **Setup Slack**
```bash
# Follow SLACK_WEBHOOK_SETUP.md for Slack setup
```

## 📊 Metrics & Trust

### Leading Metrics
- Agent draft approval rate
- Time-to-first-response reduction
- Alert detection rate

### Lagging Metrics
- Dispute resolution time
- Ops team hours saved per week
- Seller churn rate

### Trust Metrics
- Override rate (human rejections)
- Escalation rate over time
- Human approval rate
- **Week 4**: Ops hours saved >10 hours/week, resolution time reduced by 50%
- **Month 2**: Seller churn rate reduced by 40%
