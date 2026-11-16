def systemd_properties(result):
    properties = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            name, value = line.split("=", 1)
            properties[name] = value.split()
    return properties


def test_compliance_backend_api_service(server):
    service = server.service("iop-service-compliance-backend-api")
    assert service.is_running
    assert service.is_enabled


def test_compliance_ssg_service(server):
    service = server.service("iop-service-compliance-ssg")
    assert service.is_running
    assert service.is_enabled


def test_compliance_inventory_consumer_service(server):
    service = server.service("iop-service-compliance-inventory-consumer")
    assert service.is_running
    assert service.is_enabled


def test_compliance_goodjob_service(server):
    service = server.service("iop-service-compliance-goodjob")
    assert service.is_running
    assert service.is_enabled


def test_compliance_dbmigrate_quadlet_file(server):
    quadlet_file = server.file("/etc/containers/systemd/iop-service-compliance-dbmigrate.container")
    assert quadlet_file.exists
    assert quadlet_file.is_file
    assert "TimeoutStartSec=30m" in quadlet_file.content_string


def test_compliance_db_migration_check_quadlet_file(server):
    quadlet_file = server.file(
        "/etc/containers/systemd/iop-service-compliance-db-migration-check.container"
    )
    assert quadlet_file.exists
    assert quadlet_file.is_file
    assert "SuccessExitStatus=1" in quadlet_file.content_string
    assert "TimeoutStartSec=30m" in quadlet_file.content_string


def test_compliance_migration_check_dependencies(server):
    result = server.run(
        "systemctl show iop-service-compliance-db-migration-check "
        "--property=After --property=Wants"
    )
    assert result.succeeded
    properties = systemd_properties(result)
    for dependency in ("postgresql.service", "iop-core-kafka.service"):
        assert dependency in properties["After"]
        assert dependency in properties["Wants"]


def test_compliance_api_container(server):
    result = server.run(
        "podman ps --format '{{.Names}}' | grep iop-service-compliance-backend-api"
    )
    assert result.succeeded
    assert "iop-service-compliance-backend-api" in result.stdout


def test_compliance_ssg_container(server):
    result = server.run("podman ps --format '{{.Names}}' | grep iop-service-compliance-ssg")
    assert result.succeeded
    assert "iop-service-compliance-ssg" in result.stdout


def test_compliance_api_quadlet_file(server):
    quadlet_file = server.file(
        "/etc/containers/systemd/iop-service-compliance-backend-api.container"
    )
    assert quadlet_file.exists
    assert quadlet_file.is_file


def test_compliance_api_service_dependencies(server):
    result = server.run(
        "systemctl show iop-service-compliance-backend-api --property=After --property=Wants"
    )
    assert result.succeeded
    properties = systemd_properties(result)
    assert "iop-service-compliance-dbmigrate.service" in properties["After"]
    for dependency in ("postgresql.service", "iop-core-kafka.service"):
        assert dependency in properties["After"]
        assert dependency in properties["Wants"]


def test_compliance_dbmigrate_service_dependencies(server):
    result = server.run(
        "systemctl show iop-service-compliance-dbmigrate --property=After --property=Wants"
    )
    assert result.succeeded
    properties = systemd_properties(result)
    for dependency in ("postgresql.service", "iop-core-kafka.service"):
        assert dependency in properties["After"]
        assert dependency in properties["Wants"]


def test_compliance_inventory_consumer_dependencies(server):
    result = server.run(
        "systemctl show iop-service-compliance-inventory-consumer "
        "--property=After --property=Wants"
    )
    assert result.succeeded
    properties = systemd_properties(result)
    for dependency in ("postgresql.service", "iop-core-kafka.service"):
        assert dependency in properties["After"]
        assert dependency in properties["Wants"]


def test_compliance_goodjob_dependencies(server):
    result = server.run(
        "systemctl show iop-service-compliance-goodjob --property=After --property=Wants"
    )
    assert result.succeeded
    properties = systemd_properties(result)
    for dependency in ("postgresql.service", "iop-core-kafka.service"):
        assert dependency in properties["After"]
        assert dependency in properties["Wants"]


def test_compliance_ssg_import_dependencies(server):
    result = server.run(
        "systemctl show iop-service-compliance-import-ssg --property=After --property=Wants"
    )
    assert result.succeeded
    properties = systemd_properties(result)
    assert "postgresql.service" in properties["After"]
    assert "postgresql.service" in properties["Wants"]
    assert "iop-service-compliance-ssg.service" in properties["After"]


def test_compliance_database_secrets(server):
    result = server.run("podman secret ls --format '{{.Name}}'")
    assert result.succeeded
    assert "iop-service-compliance-database-username" in result.stdout
    assert "iop-service-compliance-database-password" in result.stdout
    assert "iop-service-compliance-database-name" in result.stdout
    assert "iop-service-compliance-database-host" in result.stdout
    assert "iop-service-compliance-database-port" in result.stdout


def test_compliance_secret_key_base_secret(server):
    result = server.run("podman secret ls --format '{{.Name}}'")
    assert result.succeeded
    assert "iop-service-compliance-secret-key-base" in result.stdout


def test_compliance_ssg_playbook_discovery_paths(server):
    for version in ("rhel8", "rhel9", "rhel10"):
        result = server.run(
            "podman exec iop-service-compliance-ssg "
            f"test -d /content/playbooks/{version}/all"
        )
        assert result.succeeded
