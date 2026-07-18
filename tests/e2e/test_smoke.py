from app.main import app
from tests.support.http import managed_test_client


def test_e2e_smoke() -> None:
    client = managed_test_client(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metadata_endpoint() -> None:
    client = managed_test_client(app)
    response = client.get("/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"].startswith("lotus-")
    assert set(payload["build"]) == {
        "gitCommitSha",
        "gitBranch",
        "buildTimestamp",
        "repoUrl",
        "ciRunId",
        "imageBuildId",
        "imageIdentityContractVersion",
        "registryDigestBinding",
        "imageDigest",
        "imageDigestReference",
        "releaseIdentityStatus",
    }
    assert payload["build"]["imageDigest"] is None
    assert payload["build"]["releaseIdentityStatus"] == "local_unpublished"


def test_version_endpoint_matches_metadata_endpoint() -> None:
    client = managed_test_client(app)
    metadata_response = client.get("/metadata")
    version_response = client.get("/version")

    assert version_response.status_code == 200
    assert version_response.json() == metadata_response.json()
