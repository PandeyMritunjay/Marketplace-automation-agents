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

### 1. Dispute Handler
Processes buyer-seller conflicts with policy-aware resolution recommendations.

**Workflow:**
- Ingests complaint text via CLI or email
- Extracts structured data (dispute type, product, timeline, sentiment)
- Queries marketplace database for order/seller context
- Applies seller-specific policies
- Generates resolution recommendation with confidence score
- Sends Slack notification with Approve/Decline/Edit buttons
- Logs human decisions for learning

**Key Features:**
- Policy-aware resolution (seller-specific policies)
- Confidence scoring for trust calibration
- Seller tier awareness (TOP sellers get special handling)
- Human-in-the-loop approval required

### 2. Support Lead
Triages support emails and drafts responses for the ops team.

**Workflow:**
- Fetches unread emails via Gmail API
- Identifies sender (buyer/seller/unknown) from database
- Classifies category and priority using LLM
- Generates draft responses for appropriate cases
- Sends morning briefing to Slack with ticket counts
- Human approves/edits/drafts before sending

**Key Features:**
- Keyword override for high-priority issues (legal, chargeback threats)
- Duplicate email handling
- Sentiment analysis for angry buyers
- Batch processing for overnight triage

### 3. Operator
Proactively monitors operational health and surfaces issues.

**Workflow:**
- Queries marketplace database for operational metrics
- Checks thresholds (payouts pending, unfulfilled orders, inactive sellers)
- Generates alerts with severity levels (CRITICAL/WARNING/INFO)
- Sends daily briefing to Slack
- Suggests specific actions for each alert
- Tracks human actions for learning

**Key Features:**
- Configurable thresholds (environment variables)
- Multi-dimensional health checks
- Seller tier awareness
- Daily automated reporting

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **Database**: MySQL (marketplace + agent_system)
- **LLM**: OpenAI GPT-3.5-turbo (cost-effective, avoids rate limits)
- **Integrations**: 
  - Slack API (notifications, interactive buttons)
  - Gmail API (email ingestion, sending)
- **ORM**: SQL workbench
- **Web Server**: Flask + g-unicorn
- **Deployment**: Render.com

## Project Structure

```
lighthouse/
├── agents/                # Agent implementations
│   ├── dispute_handler/   # Dispute resolution agent
│   ├── support_lead/      # Support triage agent
│   └── operator/          # Operational monitoring agent
├── config/                # Configuration management
│   └── settings.py        # Environment variables
├── integrations/          # External API integrations
│   ├── database/          # Database connection
│   ├── gmail/             # Gmail API client
│   └── slack/             # Slack API client
├── models/                # SQLAlchemy models
│   ├── agent/             # Agent system models
│   │   ├── dispute.py
│   │   ├── support_ticket.py
│   │   ├── operational_alert.py
│   │   └── agent_action.py
│   └── marketplace/       # Marketplace models (read-only)
│       ├── seller.py
│       ├── buyer.py
│       ├── order.py
│       ├── listing.py
│       └── payout.py
├── services/              # Shared services
│   └── llm/               # OpenAI service
├── web/                   # Webhook server for Slack
│   └── webhook_server.py
├── main/                  # Entry points
│   ├── dispute_handler.py
│   ├── support_lead.py
│   └── operator.py
├── requirements_pilot.txt  # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MySQL database
- OpenAI API key
- Slack workspace
- Gmail account

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

## 🎯 Running the Agents

### Dispute Handler
```bash
python -m lighthouse.main.dispute_handler \
  --complaint "I ordered a vase 12 days ago, never got tracking" \
  --buyer-email "rachel@example.com"
```

### Support Lead (Batch Mode)
```bash
python -m lighthouse.main.support_lead --mode batch
```

### Operator (Daily Health Check)
```bash
python -m lighthouse.main.operator
```

### Webhook Server (for Slack buttons)
```bash
python -m lighthouse.web.webhook_server
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

All metrics tracked via `AgentAction` table in database.

## 🚢 Deployment

### Local Development
Run agents locally with webhook server for Slack integration.

### Production (Render.com - Free Tier)
See `HEROKU_DEPLOYMENT.md` for detailed deployment instructions.

**Quick Deploy:**
1. Push code to GitHub
2. Create Render web service
3. Set environment variables
4. Auto-deploys

### Production (AWS)
See `PRODUCTION_DEPLOYMENT.md` for enterprise deployment options.

## 📚 Documentation

- **PILOT_SETUP_GUIDE.md** - Complete setup instructions
- **SLACK_WEBHOOK_SETUP.md** - Slack app configuration
- **PRODUCTION_DEPLOYMENT.md** - Production deployment guide
- **HEROKU_DEPLOYMENT.md** - Render.com deployment guide
- **DEMONSTRATION_GUIDE.md** - Interview demonstration script
- **Lighthouse_AI_Agents_Assignment.md** - Assignment document with methodology

## 🔒 Security

- Environment variables for all credentials
- Signature verification for Slack webhooks (configurable)
- Database connection pooling
- No sensitive data in git
- Human approval required for all critical actions

## 🤝 Contributing

This is a pilot project for demonstration purposes. For production use, consider:
- Adding comprehensive test suite
- Implementing rate limiting
- Adding monitoring and alerting
- Scaling database infrastructure
- Implementing A/B testing for prompts

## 📝 License

Proprietary - Pilot project for demonstration purposes.

## 🎯 Use Cases

**For Marketplaces:**
- Reduce ops team workload by 60-70%
- Improve dispute resolution time by 50%
- Proactively identify operational issues
- Scale support without hiring

**For Interview Demonstration:**
- Shows understanding of AI agent design
- Demonstrates human-in-the-loop workflows
- Illustrates trust calibration mechanisms
- Shows production-ready architecture

## 🔍 Key Design Decisions

1. **Human-in-the-loop**: All critical actions require Slack approval
2. **Trust calibration**: Confidence scores and tier-aware handling
3. **Failure prevention**: Duplicate handling, keyword overrides, context verification
4. **Week 1 scope**: Single workflow per agent, off-the-shelf LLM, no custom UI
5. **Integration friction**: Uses existing APIs (Gmail, Slack, MySQL)

## 📈 Success Metrics

- **Week 1**: Agents deployed and processing real data
- **Week 2**: Draft approval rate >70%, override rate <20%
- **Week 4**: Ops hours saved >10 hours/week, resolution time reduced by 50%
- **Month 2**: Seller churn rate reduced by 40%
