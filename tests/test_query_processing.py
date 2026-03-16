import unittest

from terraria_wikipilot.query_pipeline import QueryPipeline, normalize_query
from terraria_wikipilot.query_service import QueryService


class FakeIndex:
    def search(self, _query, k=5):
        return [
            {
                "title": "Duke Fishron",
                "section": "Summoning",
                "text": "Use a Truffle Worm as bait. Fish in the Ocean biome. Requires Hardmode.",
            },
            {
                "title": "Duke Fishron",
                "section": "Behavior",
                "text": "Duke Fishron has multiple phases.",
            },
        ][:k]


class QueryProcessingTests(unittest.TestCase):
    def test_normalize_query_reorders_for_entity_then_action(self) -> None:
        self.assertEqual(normalize_query("how do i summon duke fishron"), "duke fishron summon")

    def test_pipeline_answer_uses_preferred_section(self) -> None:
        pipeline = QueryPipeline(index=FakeIndex())
        answer = pipeline.answer("how do i summon duke fishron")
        self.assertIsNotNone(answer)
        self.assertEqual(answer.title, "Duke Fishron")
        self.assertEqual(answer.section, "Summoning")

    def test_query_service_wraps_pipeline_output(self) -> None:
        service = QueryService(query_pipeline=QueryPipeline(index=FakeIndex()))
        response = service.ask("how do i summon duke fishron")
        self.assertIsNotNone(response.page)
        self.assertEqual(response.page.title, "Duke Fishron")


if __name__ == "__main__":
    unittest.main()
