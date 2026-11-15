import unittest
from backend import contracts

MOOD = {"mood": 3, "fatigue": 3, "stress": 3, "confidence": 0.5}
SYMPTOM = {"codes": ["dizziness"], "onset": "now", "worse_when": "none", "severity": 2, "needs_question": False}


class SchemaCheck(unittest.TestCase):
    def fails(self, kind, obj):
        return contracts.check_schema(obj, contracts.schema(kind))

    def test_scores_outside_the_schema_range_are_rejected(self):
        for field, value in (("mood", 0), ("mood", 6), ("fatigue", 9), ("stress", -1), ("confidence", 1.5), ("confidence", -0.1)):
            with self.subTest(field=field, value=value):
                self.assertTrue(self.fails("mood", dict(MOOD, **{field: value})))
        self.assertTrue(self.fails("symptom", dict(SYMPTOM, severity=7)))

    def test_range_boundaries_are_accepted(self):
        for field, value in (("mood", 1), ("mood", 5), ("confidence", 0), ("confidence", 1)):
            with self.subTest(field=field, value=value):
                self.assertEqual(self.fails("mood", dict(MOOD, **{field: value})), [])

    def test_number_must_be_a_finite_number(self):
        for value in (True, float("nan"), float("inf"), "0.5", None):
            with self.subTest(value=value):
                self.assertTrue(self.fails("mood", dict(MOOD, confidence=value)))

    def test_integer_scores_reject_floats_bools_and_strings(self):
        for value in (3.0, True, "3"):
            with self.subTest(value=value):
                self.assertTrue(self.fails("mood", dict(MOOD, mood=value)))

    def test_values_outside_an_enum_are_rejected(self):
        self.assertTrue(self.fails("symptom", dict(SYMPTOM, codes=["made_up"])))
        self.assertTrue(self.fails("symptom", dict(SYMPTOM, onset="yesterday")))
        self.assertEqual(self.fails("symptom", SYMPTOM), [])

    def test_locations_is_optional_and_holds_only_listed_body_parts(self):
        self.assertEqual(self.fails("symptom", dict(SYMPTOM, locations=[])), [])
        self.assertEqual(self.fails("symptom", dict(SYMPTOM, locations=contracts.enums()["body_location"])), [])
        self.assertTrue(self.fails("symptom", dict(SYMPTOM, locations=["knee"])))
        self.assertTrue(self.fails("symptom", dict(SYMPTOM, locations=["head", "head"])))
        self.assertTrue(self.fails("symptom", dict(SYMPTOM, locations="head")))
