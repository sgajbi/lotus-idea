from __future__ import annotations

GENERATED_READINESS_ARTIFACTS = (
    (
        "scripts.source_ingestion_scheduler.generate_source_contract",
        "a scheduled source-ingestion worker source-contract artifact",
    ),
    (
        "scripts/persistence/generate_durable_repository_proof.py",
        "durable repository proof artifact",
    ),
    (
        "scripts/runtime_trust_telemetry/generate_test_execution_contract.py",
        "runtime telemetry test-execution artifact",
    ),
    ("scripts/generate_ai_lineage_store_proof.py", "an AI lineage store proof artifact"),
    (
        "scripts/ai_workflow_pack_registration/generate_source_contract_proof.py",
        "an AI workflow-pack registration source-contract proof artifact",
    ),
    (
        "scripts/generate_ai_workflow_pack_runtime_execution_proof.py",
        "an AI workflow-pack runtime execution proof artifact",
    ),
    (
        "scripts/workbench/generate_read_path_source_contract.py",
        "Workbench read-path source-contract proof artifact",
    ),
    (
        "scripts/outbox/broker/generate_source_contract_proof.py",
        "outbox broker source-contract proof artifact",
    ),
    (
        "scripts/outbox/generate_consumer_contract_proof.py",
        "an outbox consumer contract proof artifact",
    ),
    (
        "scripts/outbox/platform_mesh/generate_source_contract_proof.py",
        "an outbox platform-mesh event source-contract proof artifact",
    ),
    (
        "scripts/downstream_realization/generate_advise_route_source_contract.py",
        "an Advise route source-contract artifact",
    ),
    (
        "scripts/downstream_realization/generate_manage_route_source_contract.py",
        "a Manage route source-contract artifact",
    ),
    (
        "scripts/downstream_realization/generate_manage_intake_runtime_execution.py",
        "a Manage intake runtime-execution proof artifact",
    ),
    (
        "scripts/report/generate_intake_route_source_contract.py",
        "a Report intake-route source-contract proof artifact",
    ),
    (
        "scripts/report/generate_materialization_source_contract.py",
        "a report materialization source-contract artifact",
    ),
    (
        "scripts/report/generate_materialization_runtime_execution.py",
        "a Report materialization runtime-execution proof artifact",
    ),
    (
        "scripts/data_mesh/generate_mesh_policy_source_contract.py",
        "mesh policy source-contract artifact",
    ),
    (
        "scripts/data_mesh/generate_platform_catalog_source_contract.py",
        "a platform catalog source contract artifact",
    ),
    (
        "scripts/workbench/generate_contract_proof.py",
        "a Gateway/Workbench contract proof artifact",
    ),
    (
        "scripts/workbench/generate_discovery_contract_proof.py",
        "a Gateway/Workbench discovery contract proof artifact",
    ),
    (
        "scripts/advise_source_product_evidence/generate_source_contract.py",
        "a mandate/restriction source-product proof artifact",
    ),
)

PASSED_READINESS_ARTIFACTS = (
    (
        "--source-ingestion-scheduled-worker-source-contract",
        "scheduled source-ingestion worker source-contract artifact",
    ),
    ("--durable-repository-proof", "durable repository proof artifact"),
    ("--runtime-trust-telemetry-test-execution", "runtime trust telemetry test execution artifact"),
    ("--ai-lineage-store-proof", "AI lineage store proof artifact"),
    (
        "--ai-workflow-pack-registration-proof",
        "AI workflow-pack registration source-contract proof artifact",
    ),
    (
        "--ai-workflow-pack-runtime-execution-proof",
        "AI workflow-pack runtime execution proof artifact",
    ),
    (
        "--advise-proposal-route-source-contract-proof",
        "Advise route source-contract artifact",
    ),
    (
        "--manage-action-route-source-contract-proof",
        "Manage route source-contract artifact",
    ),
    (
        "--manage-intake-runtime-execution-proof",
        "Manage intake runtime-execution proof artifact",
    ),
    (
        "--report-intake-route-source-contract-proof",
        "Report intake-route source-contract proof artifact",
    ),
    (
        "--report-materialization-source-contract-proof",
        "report materialization source contract artifact",
    ),
    (
        "--report-materialization-runtime-execution-proof",
        "Report materialization runtime-execution proof artifact",
    ),
    ("--mesh-policy-source-contract-proof", "mesh policy source-contract artifact"),
    (
        "--workbench-read-path-source-contract-proof",
        "Workbench read-path source-contract proof artifact",
    ),
    (
        "--outbox-broker-source-contract-proof",
        "outbox broker source-contract proof artifact",
    ),
    ("--outbox-consumer-contract-proof", "outbox consumer contract proof artifact"),
    (
        "--outbox-platform-mesh-event-source-contract-proof",
        "outbox platform-mesh event source-contract proof artifact",
    ),
    ("--platform-catalog-source-contract-proof", "platform catalog source contract artifact"),
    ("--gateway-workbench-contract-proof", "Gateway/Workbench contract proof artifact"),
    (
        "--gateway-workbench-discovery-contract-proof",
        "Gateway/Workbench discovery contract proof artifact",
    ),
    (
        "--mandate-restriction-source-product-proof",
        "Mandate/restriction source-product proof artifact",
    ),
)
