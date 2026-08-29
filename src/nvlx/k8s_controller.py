"""Render minimal Kubernetes resources for nvlx-controller."""
from __future__ import annotations
import json

def manifests(*, namespace: str="nvlx-system", image: str="ghcr.io/nvlx/controller:1.1.0", replicas: int=2) -> list[dict]:
    if replicas < 2: raise ValueError("production HA requires at least two replicas")
    sa={"apiVersion":"v1","kind":"ServiceAccount","metadata":{"name":"nvlx-controller","namespace":namespace}}
    role={"apiVersion":"rbac.authorization.k8s.io/v1","kind":"Role","metadata":{"name":"nvlx-controller","namespace":namespace},"rules":[
        {"apiGroups":["coordination.k8s.io"],"resources":["leases"],"verbs":["get","list","watch","create","update","patch"]},
        {"apiGroups":[""],"resources":["configmaps"],"verbs":["get","list","watch"]},
    ]}
    rb={"apiVersion":"rbac.authorization.k8s.io/v1","kind":"RoleBinding","metadata":{"name":"nvlx-controller","namespace":namespace},"subjects":[{"kind":"ServiceAccount","name":"nvlx-controller","namespace":namespace}],"roleRef":{"apiGroup":"rbac.authorization.k8s.io","kind":"Role","name":"nvlx-controller"}}
    dep={"apiVersion":"apps/v1","kind":"Deployment","metadata":{"name":"nvlx-controller","namespace":namespace},"spec":{"replicas":replicas,"selector":{"matchLabels":{"app":"nvlx-controller"}},"template":{"metadata":{"labels":{"app":"nvlx-controller"}},"spec":{"serviceAccountName":"nvlx-controller","containers":[{"name":"controller","image":image,"args":["runtime-tick","--observed-generation","0","--desired-generation","0"],"readinessProbe":{"exec":{"command":["nvlx-controller","metrics"]},"initialDelaySeconds":5,"periodSeconds":10}}]}}}}
    return [sa,role,rb,dep]

def render_json(**kwargs) -> str:
    return "\n".join(json.dumps(x,sort_keys=True) for x in manifests(**kwargs)) + "\n"
