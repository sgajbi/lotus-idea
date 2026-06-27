from __future__ import annotations

GENERATED_READINESS_ARTIFACTS = (
    (
        "scripts/generate_scheduled_source_ingestion_worker_proof.py",
        "a scheduled source-ingestion worker proof artifact",
    ),
    ("scripts/generate_durable_repository_proof.py", "durable repository proof artifact"),
    ("scripts/generate_runtime_trust_telemetry_proof.py", "runtime telemetry proof artifact"),
    ("scripts/generate_ai_lineage_store_proof.py", "an AI lineage store proof artifact"),
    (
        "scripts/generate_ai_workflow_pack_registration_proof.py",
        "an AI workflow-pack registration proof artifact",
    ),
    (
        "scripts/generate_ai_workflow_pack_runtime_execution_proof.py",
        "an AI workflow-pack runtime execution proof artifact",
    ),
    ("scripts/generate_workbench_read_path_proof.py", "Workbench read-path proof artifact"),
    ("scripts/generate_outbox_broker_proof.py", "outbox broker proof artifact"),
    (
        "scripts/generate_outbox_consumer_runtime_proof.py",
        "an outbox consumer runtime proof artifact",
    ),
    (
        "scripts/generate_outbox_platform_mesh_event_publication_proof.py",
        "an outbox platform mesh event publication proof artifact",
    ),
    ("scripts/generate_advise_proposal_route_proof.py", "an Advise proposal route proof artifact"),
    ("scripts/generate_manage_action_route_proof.py", "a Manage action route proof artifact"),
    ("scripts/generate_report_intake_route_proof.py", "a report intake route proof artifact"),
    ("scripts/generate_report_materialization_proof.py", "a report materialization proof artifact"),
    ("scripts/generate_mesh_policy_proof.py", "mesh policy proof artifact"),
    (
        "scripts/generate_platform_mesh_onboarding_proof.py",
        "a platform mesh onboarding proof artifact",
    ),
    (
        "scripts/generate_gateway_workbench_operational_proof.py",
        "a Gateway/Workbench operational proof artifact",
    ),
    (
        "scripts/generate_gateway_workbench_discovery_proof.py",
        "a Gateway/Workbench discovery proof artifact",
    ),
)

PASSED_READINESS_ARTIFACTS = (
    (
        "--source-ingestion-scheduled-worker-proof",
        "scheduled source-ingestion worker proof artifact",
    ),
    ("--durable-repository-proof", "durable repository proof artifact"),
    ("--runtime-trust-telemetry-proof", "runtime trust telemetry proof artifact"),
    ("--ai-lineage-store-proof", "AI lineage store proof artifact"),
    ("--ai-workflow-pack-registration-proof", "AI workflow-pack registration proof artifact"),
    (
        "--ai-workflow-pack-runtime-execution-proof",
        "AI workflow-pack runtime execution proof artifact",
    ),
    ("--advise-proposal-route-proof", "Advise proposal route proof artifact"),
    ("--manage-action-route-proof", "Manage action route proof artifact"),
    ("--report-intake-route-proof", "report intake route proof artifact"),
    ("--report-materialization-proof", "report materialization proof artifact"),
    ("--mesh-policy-proof", "mesh policy proof artifact"),
    ("--workbench-read-path-proof", "Workbench read-path proof artifact"),
    ("--outbox-broker-proof", "outbox broker proof artifact"),
    ("--outbox-consumer-runtime-proof", "outbox consumer runtime proof artifact"),
    (
        "--outbox-platform-mesh-event-publication-proof",
        "outbox platform mesh event publication proof artifact",
    ),
    ("--platform-mesh-onboarding-proof", "platform mesh onboarding proof artifact"),
    ("--gateway-workbench-operational-proof", "Gateway/Workbench operational proof artifact"),
    ("--gateway-workbench-discovery-proof", "Gateway/Workbench discovery proof artifact"),
)

REQUIRED_READINESS_WIRING = (
    ("--source-ingestion-manifest", "pass the source-ingestion manifest"),
    ("LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT", "pass the default AI lineage proof"),
    ("LOTUS_IDEA_AI_LINEAGE_STORE_PROOF", "support optional AI lineage proof wiring"),
    (
        "LOTUS_AI_ROOT",
        "support default lotus-ai root wiring for AI workflow-pack registration proof generation",
    ),
    (
        "LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT",
        "pass the default AI workflow-pack registration proof output into readiness generation",
    ),
    ("LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF", "support optional AI pack proof"),
    (
        "LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT",
        "pass the default AI workflow-pack runtime execution proof output into readiness generation",
    ),
    ("LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF", "support AI runtime proof"),
    ("LOTUS_ADVISE_ROOT", "support default lotus-advise root wiring"),
    ("LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT", "pass default Advise proof"),
    ("LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF", "support optional Advise proof"),
    ("LOTUS_MANAGE_ROOT", "support default lotus-manage root wiring"),
    ("LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT", "pass default Manage proof"),
    ("LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF", "support optional Manage proof"),
    (
        "LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT",
        "pass the default report intake route proof output into readiness generation",
    ),
    ("LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF_OUTPUT", "pass default materialization proof"),
    ("LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF", "support optional materialization proof"),
    ("LOTUS_IDEA_MESH_POLICY_PROOF_OUTPUT", "pass default mesh policy proof"),
    ("LOTUS_IDEA_MESH_POLICY_PROOF", "support optional mesh policy proof"),
    (
        "LOTUS_PLATFORM_ROOT",
        "support default platform root wiring for platform mesh onboarding proof generation",
    ),
    (
        "LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT",
        "pass the default platform mesh onboarding proof output into readiness generation",
    ),
    ("LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF", "support optional onboarding proof"),
    (
        "LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF_OUTPUT",
        "pass the default Gateway/Workbench operational proof output into readiness generation",
    ),
    (
        "LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF",
        "support optional Gateway/Workbench operational proof wiring",
    ),
    (
        "LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF_OUTPUT",
        "pass the default Gateway/Workbench discovery proof output into readiness generation",
    ),
    (
        "LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF",
        "support optional Gateway/Workbench discovery proof wiring",
    ),
    ("LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF_OUTPUT", "pass default outbox proof"),
    ("LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF", "support optional outbox proof"),
    (
        "LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_OUTPUT",
        "pass default outbox platform mesh event publication proof",
    ),
    (
        "LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF",
        "support optional outbox platform mesh event publication proof",
    ),
    (
        "--allow-missing-evidence",
        "keep cross-repo proof generation CI-stable when sibling evidence is absent",
    ),
    (
        "--source-ingestion-live-proof",
        "support optional live source-ingestion proof artifact wiring",
    ),
    (
        "LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF",
        "support optional Risk concentration live proof artifact wiring",
    ),
    (
        "--risk-concentration-live-proof",
        "pass optional Risk concentration live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF",
        "support optional Performance underperformance live proof artifact wiring",
    ),
    (
        "--performance-underperformance-live-proof",
        "pass optional Performance underperformance live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF",
        "support optional Core benchmark assignment live proof artifact wiring",
    ),
    (
        "--core-benchmark-assignment-live-proof",
        "pass optional Core benchmark assignment live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF",
        "support optional Risk drawdown live proof artifact wiring",
    ),
    (
        "--risk-drawdown-live-proof",
        "pass optional Risk drawdown live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF",
        "support optional Manage mandate live proof artifact wiring",
    ),
    (
        "--manage-mandate-live-proof",
        "pass optional Manage mandate live proof artifact into readiness generation",
    ),
    (
        "LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF",
        "support optional Advise missing suitability live proof artifact wiring",
    ),
    (
        "--missing-suitability-live-proof",
        "pass optional Advise missing suitability live proof artifact into readiness generation",
    ),
    ("--core-query-base-url", "support optional Core query-service URL wiring"),
    (
        "--core-query-control-plane-base-url",
        "support optional Core query-control-plane URL wiring",
    ),
    (
        "IMPLEMENTATION_PROOF_OUTPUT",
        "support optional implementation proof output artifact wiring",
    ),
)
