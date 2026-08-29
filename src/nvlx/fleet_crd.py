"""Kubernetes-native GPUFleet desired-state and CRD manifest helpers."""
from __future__ import annotations
from dataclasses import dataclass, asdict

FINALIZER="nvlx.io/fleet-protection"

@dataclass(frozen=True)
class FleetSpec:
    driver_version: str
    gpu_operator_version: str
    allocation_mode: str="dra"
    canary_waves: int=3
    def to_dict(self): return asdict(self)

def crd_manifest() -> dict:
    return {
      "apiVersion":"apiextensions.k8s.io/v1","kind":"CustomResourceDefinition",
      "metadata":{"name":"gpufleets.nvlx.io"},
      "spec":{"group":"nvlx.io","scope":"Cluster","names":{"plural":"gpufleets","singular":"gpufleet","kind":"GPUFleet","shortNames":["gpf"]},
      "versions":[{"name":"v1alpha1","served":True,"storage":True,
        "schema":{"openAPIV3Schema":{"type":"object","properties":{"spec":{"type":"object","required":["driverVersion","gpuOperatorVersion"],"properties":{"driverVersion":{"type":"string"},"gpuOperatorVersion":{"type":"string"},"allocationMode":{"type":"string","enum":["dra","device-plugin"]},"canaryWaves":{"type":"integer","minimum":1}}},"status":{"type":"object","x-kubernetes-preserve-unknown-fields":True}}}},
        "subresources":{"status":{}}}]}}

def resource(name: str, spec: FleetSpec) -> dict:
    if spec.allocation_mode not in {"dra","device-plugin"}: raise ValueError("unsupported allocation mode")
    if spec.canary_waves < 1: raise ValueError("canary_waves must be >=1")
    return {"apiVersion":"nvlx.io/v1alpha1","kind":"GPUFleet","metadata":{"name":name,"finalizers":[FINALIZER]},"spec":{"driverVersion":spec.driver_version,"gpuOperatorVersion":spec.gpu_operator_version,"allocationMode":spec.allocation_mode,"canaryWaves":spec.canary_waves}}
