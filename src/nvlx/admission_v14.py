"""Admission policy for guarded GPUFleet spec mutation."""
from __future__ import annotations
import json

def render(namespace: str="nvlx-system") -> str:
    policy={"apiVersion":"admissionregistration.k8s.io/v1","kind":"ValidatingAdmissionPolicy","metadata":{"name":"nvlx-gpufleet-guard"},"spec":{"failurePolicy":"Fail","matchConstraints":{"resourceRules":[{"apiGroups":["nvlx.io"],"apiVersions":["v1alpha1"],"operations":["UPDATE","DELETE"],"resources":["gpufleets"]}]},"validations":[{"expression":"request.operation == 'DELETE' || object.spec == oldObject.spec || has(object.metadata.annotations) && object.metadata.annotations['nvlx.io/approved-change'] == 'true'","message":"GPUFleet spec changes require nvlx.io/approved-change=true after controller approval"}]}}
    binding={"apiVersion":"admissionregistration.k8s.io/v1","kind":"ValidatingAdmissionPolicyBinding","metadata":{"name":"nvlx-gpufleet-guard"},"spec":{"policyName":"nvlx-gpufleet-guard","validationActions":["Deny"],"matchResources":{"namespaceSelector":{}}}}
    return json.dumps(policy,sort_keys=True)+"\n---\n"+json.dumps(binding,sort_keys=True)+"\n"
