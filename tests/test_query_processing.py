import sys
import types
import unittest

# Allow tests to run in environments missing optional third-party dependencies.
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.RequestException = Exception
    requests_stub.Session = object
    sys.modules["requests"] = requests_stub

if "bs4" not in sys.modules:
    bs4_stub = types.ModuleType("bs4")

    class _BeautifulSoup:  # pragma: no cover - simple import stub
        def __init__(self, *_args, **_kwargs):
            pass

    bs4_stub.BeautifulSoup = _BeautifulSoup
    sys.modules["bs4"] = bs4_stub

from terraria_wikipilot.models import SearchResult
from terraria_wikipilot.query_service import QueryService, extract_keywords


class DummyClient:
    pass


class QueryProcessingTests(unittest.TestCase):
    def test_extract_keywords_keeps_entity_name_and_action(self) -> None:
        self.assertEqual(
            extract_keywords("how do i summon the eye of cthulu"),
            "summon eye cthulhu",
        )

    def test_select_best_match_prefers_entity_page_over_ids(self) -> None:
        service = QueryService(DummyClient())
        matches = [
            SearchResult(title="Item IDs", pageid=1, snippet="..."),
            SearchResult(title="Eye of Cthulhu", pageid=2, snippet="..."),
        ]
        selected = service._select_best_match("eye cthulhu summon", matches)
        self.assertEqual(selected.title, "Eye of Cthulhu")


if __name__ == "__main__":
    unittest.main()
