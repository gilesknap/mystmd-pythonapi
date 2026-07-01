import pytest

from harness import REPO, build_plugin_and_inventory


@pytest.fixture(scope="session", autouse=True)
def _built():
    """Ensure the plugin + build/objects.inv exist before the suite runs.

    Only builds if missing, so concurrent pytest sessions don't race on
    `tsup --clean`. run_all.sh performs the authoritative clean rebuild.
    """
    if not (REPO / "dist" / "index.mjs").exists() or not (REPO / "build" / "objects.inv").exists():
        build_plugin_and_inventory()
    yield
