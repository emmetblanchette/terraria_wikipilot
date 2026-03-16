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
from terraria_wikipilot.query_service import QueryService, normalize_query


class DummyClient:
    def try_direct_page(self, _entity_guess):
        return None

    def search(self, _query):
        return []


class QueryProcessingTests(unittest.TestCase):
    def test_normalize_query(self) -> None:
        info = normalize_query("How do I summon Duke Fishron?")
        self.assertEqual(info["keywords"], ["summon", "duke", "fishron"])
        self.assertEqual(info["entity_guess"], "duke fishron")

    def test_score_prefers_entity_page_over_ids(self) -> None:
        service = QueryService(DummyClient())
        entity = "eye of cthulhu"
        keywords = ["summon", "eye", "cthulhu"]

        entity_score = service._score_result("Eye of Cthulhu", entity, keywords)
        ids_score = service._score_result("Item IDs", entity, keywords)

        self.assertGreater(entity_score, ids_score)

    def test_resolve_uses_ranking(self) -> None:
        class RankedClient:
            def try_direct_page(self, _entity_guess):
                return None

            def search(self, _query):
                return [
                    SearchResult(title="Item IDs", pageid=1, snippet="..."),
                    SearchResult(title="Eye of Cthulhu", pageid=2, snippet="..."),
                ]

        service = QueryService(RankedClient())
        chosen, _ = service.resolve_wiki_page(
            {"original": "how do i summon eye of cthulhu", "keywords": ["summon", "eye", "cthulhu"], "entity_guess": "eye of cthulhu"}
        )
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen.title, "Eye of Cthulhu")


if __name__ == "__main__":
    unittest.main()
