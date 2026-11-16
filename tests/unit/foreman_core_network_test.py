import sys
from importlib import import_module
from pathlib import Path

import yaml
from jinja2 import Environment

REPOSITORY_ROOT = Path(__file__).parents[2]
COLLECTIONS_ROOT = REPOSITORY_ROOT / "build/collections/foremanctl"


def _render_foreman_network_options(ipv4_available):
    tasks_path = REPOSITORY_ROOT / "src/roles/foreman_core_network/tasks/main.yaml"
    tasks = yaml.safe_load(tasks_path.read_text())
    create_network = next(task for task in tasks if task.get("name") == "Create foreman-core-network")
    options_template = create_network["containers.podman.podman_network"]["opt"]
    rendered_options = Environment().from_string(options_template).render(
        foreman_core_network_ipv4_available=ipv4_available
    )
    return yaml.safe_load(rendered_options)


def _podman_network_options_differ(requested, inspected):
    # setup-environment builds this collection before the test suite runs.
    if str(COLLECTIONS_ROOT) not in sys.path:
        sys.path.insert(0, str(COLLECTIONS_ROOT))
    podman_network = import_module(
        "ansible_collections.containers.podman.plugins.modules.podman_network"
    )

    class Module:
        params = {"opt": requested}

    diff = podman_network.PodmanNetworkDiff(Module(), {"options": inspected}, "4.0.0")
    return diff.diffparam_opt()


def test_foreman_network_omits_default_no_default_route_option():
    requested = _render_foreman_network_options(ipv4_available=True)
    # Negative control: the installed collection treats explicit false as
    # drift when inspect omits Podman's default option.
    assert _podman_network_options_differ(
        {"no_default_route": "false"},
        inspected={},
    )
    assert requested == {}
    # Existing networks omit Podman's default false option; this is the
    # idempotency comparison that previously triggered network recreation.
    assert not _podman_network_options_differ(requested, inspected={})


def test_foreman_network_disables_default_route_without_host_ipv4():
    requested = _render_foreman_network_options(ipv4_available=False)
    assert requested == {"no_default_route": "true"}
    assert not _podman_network_options_differ(
        requested,
        inspected={"no_default_route": "true"},
    )
