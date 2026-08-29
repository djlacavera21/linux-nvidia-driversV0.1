"""Prometheus alert-rule generation for NVIDIA fleet health."""
from __future__ import annotations

def prometheus_rule_group()->str:
    return '''groups:
- name: nvlx-gpu-fleet
  rules:
  - alert: NvlxGpuNodeUnhealthy
    expr: nvlx_health_ok == 0
    for: 5m
    labels: { severity: critical }
    annotations: { summary: "NVIDIA GPU node health failed" }
  - alert: NvlxGpuXidError
    expr: increase(nvlx_gpu_xid_errors_total[10m]) > 0
    labels: { severity: critical }
    annotations: { summary: "NVIDIA Xid error detected" }
  - alert: NvlxGpuUncorrectedEcc
    expr: nvlx_gpu_ecc_uncorrected_volatile > 0
    for: 2m
    labels: { severity: critical }
    annotations: { summary: "Uncorrected GPU ECC error detected" }
  - alert: NvlxNvSwitchFault
    expr: nvlx_nvswitch_fault > 0
    for: 2m
    labels: { severity: critical }
    annotations: { summary: "NVSwitch fault detected" }
  - alert: NvlxDriverTransactionPending
    expr: nvlx_transaction_pending > 0
    for: 20m
    labels: { severity: warning }
    annotations: { summary: "NVIDIA driver transaction remains pending" }
'''
