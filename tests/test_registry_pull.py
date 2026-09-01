from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("registry_pull", REPO / "scripts" / "registry_pull.py")
assert SPEC and SPEC.loader
registry_pull = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = registry_pull
SPEC.loader.exec_module(registry_pull)


class RegistryTests(unittest.TestCase):
    def test_host_of(self) -> None:
        self.assertEqual(registry_pull.host_of("https://www.Example.com/path"), "example.com")
        self.assertEqual(registry_pull.host_of("privacy@example.org"), "example.org")
        self.assertEqual(registry_pull.host_of("example.net/path"), "example.net")

    def test_hosts_from_csv_uses_url_columns(self) -> None:
        body = "Company,Website,Notes\nOne,https://one.example/path,ignore.example\nTwo,www.two.example,none\n"
        self.assertEqual(registry_pull.hosts_from_csv(body), {"one.example", "two.example"})

    def test_hosts_in_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="registry-test-") as tmp:
            path = Path(tmp) / "brokers.md"
            path.write_text("| Broker | https://www.example.com/optout |\nmail privacy@other.example\n", encoding="utf-8")
            self.assertEqual(registry_pull.hosts_in_text(path), {"example.com", "other.example"})


if __name__ == "__main__":
    unittest.main()
