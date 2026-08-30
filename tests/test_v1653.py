import unittest

from nvlx.controller_metrics import (
    MetricSpec,
    _COUNTER_METRICS,
    _METRIC_HELP,
    _METRIC_SPECS,
    _render_metric_values,
    render,
)


class MetricSchemaTests(unittest.TestCase):
    @staticmethod
    def render_body():
        return render(
            leader=True,
            reconcile_total=11,
            reconcile_failures=2,
            pending_approvals=3,
            rollback_required=1,
            controller_ready=True,
            api_reachable=True,
            leadership_fresh=True,
            inventory_fresh=True,
            nvidia_preflight_ready=True,
            checkpoint_writes=5,
            checkpoint_idempotent_acks=6,
            checkpoint_reconciled_commits=7,
            checkpoint_rollbacks=8,
            checkpoint_transaction_mismatches=9,
            checkpoint_failures=10,
            checkpoint_restore_attempts=11,
            checkpoint_restore_successes=10,
            checkpoint_sequence=12,
            checkpoint_epoch=13,
            checkpoint_ready=True,
        )

    def test_rendered_sample_names_exactly_match_schema_order(self):
        body = self.render_body()
        samples = tuple(
            line.split(" ", 1)[0]
            for line in body.splitlines()
            if line and not line.startswith("#")
        )
        self.assertEqual(samples, tuple(_METRIC_SPECS))

    def test_schema_drives_help_type_and_compatibility_views(self):
        body = self.render_body()
        for name, spec in _METRIC_SPECS.items():
            self.assertEqual(_METRIC_HELP[name], spec.help)
            self.assertEqual(name in _COUNTER_METRICS, spec.metric_type == "counter")
            self.assertEqual(body.count(f"# HELP {name} {spec.help}\n"), 1)
            self.assertEqual(body.count(f"# TYPE {name} {spec.metric_type}\n"), 1)

    def test_schema_mapping_is_immutable(self):
        with self.assertRaises(TypeError):
            _METRIC_SPECS["nvlx_test"] = MetricSpec("gauge", "test")

    def test_metric_spec_rejects_invalid_metadata(self):
        with self.assertRaisesRegex(ValueError, "type"):
            MetricSpec("histogram", "invalid")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            MetricSpec("gauge", "")
        with self.assertRaisesRegex(ValueError, "single-line"):
            MetricSpec("counter", "bad\nhelp")

    def test_missing_sample_fails_closed(self):
        vals = {name: 0 for name in _METRIC_SPECS}
        vals.pop("nvlx_nvidia_checkpoint_reconciled_commits_total")
        with self.assertRaisesRegex(RuntimeError, "missing=.*reconciled_commits"):
            _render_metric_values(vals)

    def test_extra_sample_fails_closed(self):
        vals = {name: 0 for name in _METRIC_SPECS}
        vals["nvlx_unregistered_metric"] = 1
        with self.assertRaisesRegex(RuntimeError, "extra=nvlx_unregistered_metric"):
            _render_metric_values(vals)

    def test_sample_order_drift_fails_closed(self):
        vals = {name: 0 for name in reversed(tuple(_METRIC_SPECS))}
        with self.assertRaisesRegex(RuntimeError, "order mismatch"):
            _render_metric_values(vals)

    def test_existing_checkpoint_metric_semantics_remain_unchanged(self):
        body = self.render_body()
        self.assertIn("# TYPE nvlx_nvidia_checkpoint_writes_total counter\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_writes_total 5\n", body)
        self.assertIn(
            "# TYPE nvlx_nvidia_checkpoint_reconciled_commits_total counter\n", body
        )
        self.assertIn("nvlx_nvidia_checkpoint_reconciled_commits_total 7\n", body)
        self.assertIn("# TYPE nvlx_nvidia_checkpoint_sequence gauge\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_sequence 12\n", body)
        self.assertIn("# TYPE nvlx_nvidia_checkpoint_epoch gauge\n", body)
        self.assertIn("nvlx_nvidia_checkpoint_epoch 13\n", body)


if __name__ == "__main__":
    unittest.main()
