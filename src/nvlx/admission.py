"""Generate admission-policy guardrails for GPU fleet changes."""
from __future__ import annotations
import json

def policy()->dict:
    return {"apiVersion":"admissionregistration.k8s.io/v1","kind":"ValidatingAdmissionPolicy","metadata":{"name":"nvlx-gpu-safety"},"spec":{"failurePolicy":"Fail","matchConstraints":{"resourceRules":[{"apiGroups":[""],"apiVersions":["v1"],"operations":["UPDATE"],"resources":["nodes"]}]},"validations":[{"expression":"!(has(object.metadata.labels) && object.metadata.labels.exists(k, k == 'nvlx.io/quarantined') && object.metadata.labels['nvlx.io/quarantined'] == 'true') || oldObject.metadata.labels['nvlx.io/quarantined'] == 'true'","message":"quarantined GPU nodes require the explicit nvlx unquarantine workflow"}]}}

def render()->str: return json.dumps(policy(),indent=2,sort_keys=True)+"\n"
