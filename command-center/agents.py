from pydantic import BaseModel
import random
import time

class Agent(BaseModel):
    id: int
    name: str
    description: str
    division: str
    division_id: int
    status: str
    uptime: float
    tasks_completed: int
    throughput: str
    is_revenue_engine: bool = False


DIVISIONS = {
    1: {"name": "Intelligence & Orchestration", "icon": "brain", "color": "#667eea", "agent_count": 12},
    2: {"name": "Legal & Governance", "icon": "scale-balanced", "color": "#f6ad55", "agent_count": 16},
    3: {"name": "Real Estate & Construction", "icon": "building", "color": "#48bb78", "agent_count": 22},
    4: {"name": "DeFi & Treasury", "icon": "coins", "color": "#ed64a6", "agent_count": 18},
    5: {"name": "Voice / Avatar / UX", "icon": "microphone", "color": "#9f7aea", "agent_count": 20},
    6: {"name": "Infrastructure / Security / Data", "icon": "shield-halved", "color": "#4fd1c5", "agent_count": 24},
}

REVENUE_ENGINE_IDS = {49, 29, 30, 64, 63}

_AGENTS_RAW = [
    # Division 1: Intelligence & Orchestration (12)
    (1, "IQCoreModule", "AI reasoning scoring, feedback loops, SBT logging"),
    (2, "CUDAOrchestrator", "GPU task execution (15B+ ops/sec)"),
    (3, "AI Council Control", "Coordinates all 112 agents"),
    (4, "TaskRouter.ai", "Routes jobs to correct agent clusters"),
    (5, "LangGraphExecutor", "Multi-step reasoning workflows"),
    (6, "TemporalFlowAgent", "Job scheduling + retries"),
    (7, "MemoryVault.ai", "Long-term memory (IPFS + DB sync)"),
    (8, "ContextWindowAgent", "Real-time decision context"),
    (9, "SignalProcessor.ai", "Event ingestion (webhooks, voice, UI)"),
    (10, "DecisionEngine.ai", "Final execution authority logic"),
    (11, "MultiAgentSync", "Keeps agents consistent across nodes"),
    (12, "AutonomousLearningLoop", "Improves system performance continuously"),
    # Division 2: Legal & Governance (16)
    (13, "NPCAgreementAgent", "Contract automation (AIA/HIC compliant)"),
    (14, "ZoningCourtAgent", "AI dispute resolution (Chainlink VRF judges)"),
    (15, "SnapshotGovernanceAgent", "DAO voting execution"),
    (16, "AragonControlAgent", "Role-based DAO permissions"),
    (17, "AuditBeaconAgent", "Audit trails (Certik / Trail of Bits)"),
    (18, "ComplianceEngine.ai", "Reg D, KYC, AML enforcement"),
    (19, "zkKYTMonitor", "Transaction compliance"),
    (20, "IdentityValidator", "zkSBT identity verification"),
    (21, "PolicyEnforcementAgent", "Applies governance rules"),
    (22, "LegalDocParser", "Reads contracts + permits"),
    (23, "RiskAssessmentAgent", "Legal + financial risk scoring"),
    (24, "DisputeResolutionSubAgent", "Handles edge-case conflicts"),
    (25, "DAOProposalGenerator", "Creates governance proposals"),
    (26, "VotingAnalyticsAgent", "Tracks DAO participation"),
    (27, "ComplianceReporter", "Generates regulatory reports"),
    (28, "EthicsGuard.ai", "Ensures governance integrity"),
    # Division 3: Real Estate & Construction (22)
    (29, "GCagent.ai", "Full job orchestration (Master GC Agent)"),
    (30, "PermitStream.ai", "Permit automation + zoning validation"),
    (31, "RealEstateNFTAgent", "Property tokenization"),
    (32, "ZoningValidationAgent", "GIS + zoning compliance"),
    (33, "ProjectEstimator.ai", "Cost + material estimates"),
    (34, "SchedulePlanner", "Gantt + timeline execution"),
    (35, "SubcontractorRouter", "Assigns trades"),
    (36, "InspectionCoordinator", "Schedules inspections"),
    (37, "MaterialProcurementAgent", "Orders + logistics"),
    (38, "SiteMonitorAgent", "Field updates (photos, logs)"),
    (39, "ChangeOrderAgent", "AWO Engine - Change orders to revenue"),
    (40, "InvoiceGenerator", "Billing automation"),
    (41, "PaymentTracker", "Tracks incoming payments"),
    (42, "CloseoutManager", "Final QA + turnover"),
    (43, "QualityControlAgent", "Build quality validation"),
    (44, "SafetyComplianceAgent", "OSHA + safety tracking"),
    (45, "EnergyEfficiencyAgent", "Code + performance compliance"),
    (46, "BIMIntegrationAgent", "Model coordination"),
    (47, "ClientPortalAgent", "Client communication"),
    (48, "CrewMobileAgent", "Field crew interface"),
    (49, "LeadIntakeAgent", "Converts leads to jobs (CRITICAL)"),
    (50, "RevenueProtectionAgent", "Margin + risk monitoring"),
    # Division 4: DeFi & Treasury (18)
    (51, "NPETFManager", "Tokenized ETF engine"),
    (52, "TreasuryBotV3", "Yield optimization (Curve, Aave)"),
    (53, "FiatRouterAgent", "Stripe to USDC routing"),
    (54, "LiquidityManager", "AMM + pools"),
    (55, "NBPTTokenManager", "Token supply + burns"),
    (56, "StakingEngine", "Contractor + investor staking"),
    (57, "YieldRouter", "DeFi allocation logic"),
    (58, "BondStreamAgent", "NFT bonds + yield"),
    (59, "OracleSyncAgent", "Chainlink feeds"),
    (60, "PriceFeedMonitor", "Market data"),
    (61, "RiskHedgeAgent", "Downside protection"),
    (62, "PortfolioBalancer", "Treasury allocation"),
    (63, "RevenueAggregator", "Consolidates income streams"),
    (64, "PaymentGatewayAgent", "Stripe / PayPal / crypto"),
    (65, "EscrowManager", "Project escrow logic"),
    (66, "BurnMechanismAgent", "Token deflation"),
    (67, "ComplianceFinanceAgent", "Regulated financial flows"),
    (68, "InvestorReportingAgent", "Reports + dashboards"),
    # Division 5: Voice / Avatar / UX (20)
    (69, "AvatarGPUAgent", "60fps rendering"),
    (70, "NeMoVoiceAgent", "Voice synthesis"),
    (71, "EmotionEngine", "Emotional intelligence"),
    (72, "LipSyncAgent", "Multilingual sync (21 languages)"),
    (73, "GestureEngine", "Body movement"),
    (74, "VoiceCommandAgent", "Voice-triggered actions"),
    (75, "CallRouterAgent", "Phone routing"),
    (76, "VoiceAnalyticsAgent", "Call insights"),
    (77, "VideoStreamAgent", "Live streaming"),
    (78, "AMAHostAgent", "Investor events"),
    (79, "TTSController", "Voice playback"),
    (80, "SpeechToTextAgent", "Transcription"),
    (81, "VoiceSecurityAgent", "Voice authentication"),
    (82, "AvatarInteractionAgent", "User conversations"),
    (83, "MultilingualAgent", "Language switching"),
    (84, "VoiceCRMIntegrator", "Push data to CRM"),
    (85, "LeadVoiceIntake", "Converts calls to jobs"),
    (86, "VoiceNotificationAgent", "Alerts + updates"),
    (87, "VideoExplainerAgent", "Client walkthroughs"),
    (88, "EmotionFeedbackLoop", "Improves user experience"),
    # Division 6: Infrastructure / Security / Data (24)
    (89, "IPFSStorageAgent", "File storage"),
    (90, "ArweaveAnchorAgent", "Permanent records"),
    (91, "DatabaseSyncAgent", "Postgres / Redis"),
    (92, "CacheManager", "Performance layer"),
    (93, "APIGatewayAgent", "External integrations"),
    (94, "WebhookIngestAgent", "Stripe / Slack / events"),
    (95, "OpenClawSecurityAgent", "Webhook validation"),
    (96, "EncryptionAgent", "AES-256 security"),
    (97, "AccessControlAgent", "Permissions"),
    (98, "DDoSShieldAgent", "Network protection"),
    (99, "NodeBalancer", "Load distribution"),
    (100, "TelemetryAgent", "Metrics + logs"),
    (101, "ErrorRecoveryAgent", "Failover systems"),
    (102, "CICDAgent", "Deployment automation"),
    (103, "ContainerOrchestrator", "Docker/K8s"),
    (104, "CloudSyncAgent", "AWS / GCP / Vultr"),
    (105, "EdgeComputeAgent", "Low latency execution"),
    (106, "GPUOptimizer", "CUDA tuning"),
    (107, "DataPipelineAgent", "ETL workflows"),
    (108, "AnalyticsEngine", "Insights"),
    (109, "AuditLogAgent", "Compliance logs"),
    (110, "BackupAgent", "Redundancy"),
    (111, "FailoverAgent", "Disaster recovery"),
    (112, "SystemHealthAgent", "Overall monitoring"),
]

_DIVISION_RANGES = {
    1: (1, 12), 2: (13, 28), 3: (29, 50),
    4: (51, 68), 5: (69, 88), 6: (89, 112),
}

_seed_state = {}


def _agent_metrics(agent_id: int) -> dict:
    rng = random.Random(agent_id * 1000 + int(time.time() // 30))
    status_roll = rng.random()
    if agent_id in REVENUE_ENGINE_IDS:
        status = "online"
        uptime = round(rng.uniform(99.90, 99.99), 2)
    elif status_roll < 0.88:
        status = "online"
        uptime = round(rng.uniform(97.0, 99.99), 2)
    elif status_roll < 0.96:
        status = "idle"
        uptime = round(rng.uniform(95.0, 99.5), 2)
    else:
        status = "maintenance"
        uptime = round(rng.uniform(90.0, 96.0), 2)
    tasks = rng.randint(800, 50000)
    throughput = f"{rng.randint(50, 9999)}/s"
    return {"status": status, "uptime": uptime, "tasks_completed": tasks, "throughput": throughput}


def _get_division_id(agent_id: int) -> int:
    for div_id, (lo, hi) in _DIVISION_RANGES.items():
        if lo <= agent_id <= hi:
            return div_id
    return 1


def get_all_agents() -> list[Agent]:
    agents = []
    for aid, name, desc in _AGENTS_RAW:
        div_id = _get_division_id(aid)
        metrics = _agent_metrics(aid)
        agents.append(Agent(
            id=aid,
            name=name,
            description=desc,
            division=DIVISIONS[div_id]["name"],
            division_id=div_id,
            is_revenue_engine=aid in REVENUE_ENGINE_IDS,
            **metrics,
        ))
    return agents


def get_system_metrics() -> dict:
    agents = get_all_agents()
    online = sum(1 for a in agents if a.status == "online")
    idle = sum(1 for a in agents if a.status == "idle")
    maintenance = sum(1 for a in agents if a.status == "maintenance")
    avg_uptime = round(sum(a.uptime for a in agents) / len(agents), 2)
    total_tasks = sum(a.tasks_completed for a in agents)
    return {
        "total_agents": 112,
        "online": online,
        "idle": idle,
        "maintenance": maintenance,
        "avg_uptime": avg_uptime,
        "total_tasks_completed": total_tasks,
        "tvl": "$289.6M",
        "throughput": "1.69M tasks/sec",
        "tokenized_properties": 847,
        "active_projects": 23,
        "permits_tracked": 156,
    }
