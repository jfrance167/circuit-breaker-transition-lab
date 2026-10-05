import copy
from dataclasses import FrozenInstanceError
import itertools
import json
import unittest
from unittest.mock import patch

from breaker_lab import model, model_document, render
from breaker_lab.admission import LabError, check_tree
from breaker_lab.core import Pending, _validate
from tests.support import cases, document, encode, table_oracle


class ModelTests(unittest.TestCase):
    def test_full_frozen_hand_reports(self):
        self.assertEqual(len(cases()), 13)
        for case in cases():
            with self.subTest(name=case["name"]):
                expected = case["expected"]
                if expected["status"] == "error":
                    with self.assertRaises(LabError) as caught:
                        model(encode(case["input"]))
                    self.assertEqual(caught.exception.code, expected["code"])
                else:
                    self.assertEqual(model(encode(case["input"])), expected)
                    self.assertEqual(model_document(case["input"]), expected)

    def test_independent_table_oracle(self):
        # 4 parameter sets x256 serial tails, including invalid ownership/overlap.
        for failure, recovery in itertools.product((1, 2), repeat=2):
            for tail in itertools.product("ASFI", repeat=4):
                actions = [("attempt", 1, 0, None), ("complete", 1, 0, "failure")]
                target = 1
                for index, symbol in enumerate(tail, start=2):
                    if symbol == "A":
                        target = index
                        actions.append(("attempt", target, index, None))
                    else:
                        actions.append(("complete", target, index,
                                        {"S": "success", "F": "failure", "I": "ignored"}[symbol]))
                doc = document(actions, (failure, 2, recovery))
                expected = table_oracle(doc)
                if expected == "trace.invalid":
                    with self.assertRaises(LabError) as caught:
                        model_document(doc)
                    self.assertEqual(caught.exception.code, "trace.invalid")
                else:
                    report = model_document(doc)
                    self.assertEqual([(row["before"], row["after"]) for row in report["rows"]], expected)

    def test_counts_reconcile_and_labels(self):
        for case in cases():
            if case["expected"]["status"] == "error":
                continue
            report = model_document(case["input"])
            count = report["summary"]
            self.assertEqual(count["attempts"], count["admitted"] + count["denied"])
            self.assertEqual(count["admitted"], count["completed"] + count["pending"])
            self.assertEqual(count["admitted"], count["closed_admissions"] + count["probe_admissions"])
            self.assertEqual(count["completed"], sum(count[key] for key in
                ("success_observations", "failure_observations", "ignored_observations")))
            self.assertEqual(count["actions"], len(report["rows"]))
            self.assertEqual((report["effects"], report["actual_service_health"]), ("unmodeled", "unverified"))

    def test_timestamp_and_opening_persistence(self):
        report = model_document(next(case["input"] for case in cases() if case["name"] == "ignored-probe-preserves-progress"))
        for index, row in enumerate(report["rows"]):
            self.assertEqual(row["before"]["last_action_time_ms"],
                             None if index == 0 else report["rows"][index - 1]["time_ms"])
            self.assertEqual(row["after"]["last_action_time_ms"], row["time_ms"])
            if row["after"]["mode"] == "half_open":
                self.assertEqual((row["after"]["opened_at_ms"], row["after"]["eligible_at_ms"]), (1, 11))
        self.assertIsNone(report["final_state"]["opened_at_ms"])

    def test_empty_and_derived_time_beyond_bound(self):
        report = model_document(document(actions=[]))
        self.assertEqual(report["rows"], [])
        self.assertEqual(set(report["summary"].values()), {0})
        self.assertIsNone(report["final_state"]["last_action_time_ms"])
        report = model_document(document([("attempt",1,0,None),("complete",1,3600000,"failure")], (1,60000,3)))
        self.assertEqual(report["final_state"]["eligible_at_ms"], 3660000)

    def test_native_input_no_mutation_or_shared_output(self):
        doc = document()
        original = copy.deepcopy(doc)
        first = model_document(doc)
        second = model_document(doc)
        self.assertEqual(doc, original)
        self.assertEqual(first, second)
        first["final_state"]["pending"]["role"] = "invented"
        self.assertEqual(second["final_state"]["pending"]["role"], "closed")
        admitted = _validate(doc)
        with self.assertRaises(FrozenInstanceError):
            admitted.actions[0].kind = "complete"
        with self.assertRaises(FrozenInstanceError):
            Pending("lab-attempt-0001", "probe", 0).role = "closed"

    def test_late_structure_precedes_earlier_semantic_error(self):
        doc = document([("complete",9,0,"success"),("attempt",1,1,None)])
        doc["actions"][-1]["extra"] = True
        with patch("breaker_lab.core._simulate") as replay:
            with self.assertRaises(LabError) as caught:
                model_document(doc)
            self.assertEqual(caught.exception.code, "schema.invalid")
            replay.assert_not_called()

    def test_semantic_ownership_recompletion_and_ties(self):
        for actions in ([('complete',9,0,'success')],
                        [('attempt',1,0,None),('complete',1,0,'success'),('complete',1,0,'ignored')],
                        [('attempt',1,0,None),('complete',2,0,'failure')],
                        [('attempt',1,0,None),('attempt',2,0,None),('complete',1,0,'failure')]):
            with self.assertRaises(LabError) as caught:
                model_document(document(actions))
            self.assertEqual(caught.exception.code, "trace.invalid")

    def test_schema_unknown_null_extra_and_duplicate_ids(self):
        base = document()
        positions = [(), ("policy",), ("actions",0)]
        for position in positions:
            for mode in ("extra", "missing", "null"):
                doc = copy.deepcopy(base)
                target = doc
                for part in position:
                    target = target[part]
                if mode == "extra":
                    target["extra"] = 1
                elif mode == "missing":
                    del target[next(iter(target))]
                else:
                    target[next(iter(target))] = None
                with self.assertRaises(LabError):
                    model_document(doc)
        for field, value in (("schema_version",2),("profile","unknown"),("source_kind",True),
                             ("breaker_id","lab-breaker-１２３４"),("actions",None)):
            doc = copy.deepcopy(base)
            doc[field] = value
            with self.assertRaises(LabError):
                model_document(doc)
        for key in ("kind","outcome"):
            doc = document([("attempt",1,0,None),("complete",1,1,"success")])
            doc["actions"][-1][key] = []
            with self.assertRaises(LabError):
                model_document(doc)
        for duplicate in ("action_id", "attempt_id"):
            doc = document([("attempt",1,0,None),("attempt",2,1,None)])
            doc["actions"][-1][duplicate] = doc["actions"][0][duplicate]
            with self.assertRaises(LabError) as caught:
                model_document(doc)
            self.assertEqual(caught.exception.code, "schema.invalid")

    def test_integer_policy_time_boundaries(self):
        for field, upper in (("failure_threshold",5),("cooldown_ms",60000),("success_threshold",3)):
            for value in (True,0,-1,upper+1,None,"1",1.0):
                doc = document()
                doc["policy"][field] = value
                with self.assertRaises(LabError):
                    model_document(doc)
            for value in (1,upper):
                doc = document()
                doc["policy"][field] = value
                self.assertEqual(model_document(doc)["status"], "modeled")
        for value in (True,-1,3600001,None,"1",0.0):
            doc = document()
            doc["actions"][0]["time_ms"] = value
            with self.assertRaises(LabError):
                model_document(doc)
        with self.assertRaises(LabError):
            model_document(document([("attempt",1,1,None),("complete",1,0,"success")]))

    def test_maximum_actions_and_cardinality(self):
        actions = [(kind,index,3600000,outcome) for index in range(64)
                   for kind,outcome in (("attempt",None),("complete","ignored"))]
        doc = document(actions, (5,60000,3))
        report = model_document(doc)
        self.assertEqual(report["summary"]["actions"], 128)
        self.assertEqual(report["summary"]["completed"], 64)
        self.assertLess(len(encode(doc)), 65536)
        self.assertLess(len(render(report).encode()), 262144)
        for actions in ([("attempt",i,0,None) for i in range(65)],
                        [("complete",1,0,"ignored") for i in range(65)],
                        [("attempt",i,0,None) for i in range(129)]):
            with self.assertRaises(LabError) as caught:
                model_document(document(actions))
            self.assertEqual(caught.exception.code, "input.limit")

    def test_native_cycles_aliases_and_exact_types_no_hooks(self):
        cycle = []
        cycle.append(cycle)
        for value in (cycle, {"cycle":cycle}):
            with self.assertRaises(LabError) as caught:
                model_document(value)
            self.assertEqual(caught.exception.code, "input.invalid_json")
        shared = [0]
        check_tree([shared,shared])
        class Evil(dict):
            def items(self):
                raise AssertionError("custom hook ran")
        class EvilInt(int):
            def __str__(self):
                raise AssertionError("custom hook ran")
        for value in (Evil(), EvilInt(1), object(), {1:0}, (1,), b"{}"):
            with self.assertRaises(LabError) as caught:
                model_document(value)
            self.assertEqual(caught.exception.code, "input.invalid_json")

    def test_native_node_depth_number_and_byte_gates(self):
        value = [[0]*31 for _ in range(128)]
        value[-1].pop()
        check_tree(value)  # 4096 visits exactly, depth2, no keys.
        value[-1].append(0)
        with self.assertRaises(LabError) as caught:
            check_tree(value)
        self.assertEqual(caught.exception.code, "input.limit")
        nested = 0
        for _ in range(8):
            nested = [nested]
        check_tree(nested)
        with self.assertRaises(LabError):
            check_tree([nested])
        check_tree(9999999999999999)
        for number in (10**16, -(10**15), 1<<10000, float('nan'), 1.0):
            with self.assertRaises(LabError) as caught:
                check_tree(number)
            self.assertEqual(caught.exception.code, "input.number")
        with self.assertRaises(LabError) as caught:
            model_document({str(i):'x'*128 for i in range(500)})
        self.assertEqual(caught.exception.code, "input.limit")

    def test_defensive_render_guard_and_bytes_api(self):
        with self.assertRaises(LabError) as caught:
            render({"injected": "x"*262144})
        self.assertEqual(caught.exception.code, "output.error")
        with self.assertRaises(LabError):
            model(bytearray(encode(document())))
        self.assertEqual(json.loads(render(model(encode(document()))))["status"], "modeled")


if __name__ == "__main__":
    unittest.main()
