from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parents[1]
if "ryd" in sys.modules:
    ryd = sys.modules["ryd"]
else:
    SPEC = importlib.util.spec_from_file_location("ryd", REPO / "scripts" / "ryd.py")
    ryd = importlib.util.module_from_spec(SPEC)
    sys.modules[SPEC.name] = ryd
    SPEC.loader.exec_module(ryd)

IDENTS = [
    {"kind": "name", "value": "Jane Doe", "scan": 1},
    {"kind": "city", "value": "Springfield", "scan": 1},
    {"kind": "phone", "value": "555-555-0100", "scan": 1},
    {"kind": "keep_host", "value": "janedoe.example", "scan": 1},
]


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class SerpApiTests(unittest.TestCase):
    def test_no_key_is_noop(self):
        opener = mock.Mock()
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ryd.serpapi_enabled(True))
            self.assertEqual(ryd.serpapi_check(IDENTS, ["google"], opener=opener), [])
        opener.assert_not_called()

    def test_default_off_without_opt_in(self):
        with mock.patch.dict(os.environ, {"SERPAPI_API_KEY": "k"}, clear=True):
            self.assertFalse(ryd.serpapi_enabled(False))
            self.assertTrue(ryd.serpapi_enabled(True))
        with mock.patch.dict(os.environ, {"SERPAPI_API_KEY": "k", "RYD_SERP_PROVIDER": "serpapi"}, clear=True):
            self.assertTrue(ryd.serpapi_enabled(False))

    def test_mocked_multi_engine(self):
        seen = []

        def opener(req, timeout=0):
            qs = parse_qs(urlparse(req.full_url).query)
            seen.append(qs)
            body = {"organic_results": [
                {"link": "https://people.example/jane-doe", "title": "Jane Doe", "snippet": "555-0100"},
                {"link": "https://janedoe.example/about", "title": "keep", "snippet": ""},
                {"link": "javascript:alert(1)", "title": "bad"},
            ]}
            return FakeResp(json.dumps(body).encode())

        rows = ryd.serpapi_check(IDENTS, ["google", "yahoo"], api_key="k", opener=opener)
        self.assertEqual({r["engine"] for r in rows}, {"google", "yahoo"})
        self.assertTrue(all(r["url"] == "https://people.example/jane-doe" for r in rows))
        self.assertTrue(any("p" in q and q["engine"] == ["yahoo"] for q in seen))
        self.assertFalse(any("site:" in (q.get("q") or q.get("p"))[0] for q in seen))
        self.assertEqual(ryd.serpapi_engines("Google, bing ,"), ["google", "bing"])


if __name__ == "__main__":
    unittest.main()
