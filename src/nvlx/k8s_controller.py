"""Render Kubernetes resources for the nvlx 1.6 live operator."""
from __future__ import annotations
import json

def manifests(*, namespace: str="nvlx-system", image: str="ghcr.io/nvlx/controller:1.6.3", replicas: int=2) -> list[dict]:
    if replicas < 2: raise ValueError("production HA requires at least two replicas")
    labels={"app":"nvlx-controller"}
    sa={"apiVersion":"v1","kind":"ServiceAccount","metadata":{"name":"nvlx-controller","namespace":namespace}}
    cr={"apiVersion":"rbac.authorization.k8s.io/v1","kind":"ClusterRole","metadata":{"name":"nvlx-controller"},"rules":[
        {"apiGroups":["nvlx.io"],"resources":["gpufleets"],"verbs":["get","list","watch","patch"]},
        {"apiGroups":["nvlx.io"],"resources":["gpufleets/status"],"verbs":["get","patch","update"]},
        {"apiGroups":["coordination.k8s.io"],"resources":["leases"],"verbs":["get","create","update","patch"]},
        {"apiGroups":["events.k8s.io"],"resources":["events"],"verbs":["create","patch"]},
        {"apiGroups":["nvidia.com"],"resources":["*"],"verbs":["get","list","watch"]},
        {"apiGroups":["resource.nvidia.com"],"resources":["*"],"verbs":["get","list","watch"]},
        {"apiGroups":[""],"resources":["nodes"],"verbs":["get","list","watch"]},
    ]}
    crb={"apiVersion":"rbac.authorization.k8s.io/v1","kind":"ClusterRoleBinding","metadata":{"name":"nvlx-controller"},"subjects":[{"kind":"ServiceAccount","name":"nvlx-controller","namespace":namespace}],"roleRef":{"apiGroup":"rbac.authorization.k8s.io","kind":"ClusterRole","name":"nvlx-controller"}}
    dep={"apiVersion":"apps/v1","kind":"Deployment","metadata":{"name":"nvlx-controller","namespace":namespace},"spec":{"replicas":replicas,"selector":{"matchLabels":labels},"template":{"metadata":{"labels":labels},"spec":{"serviceAccountName":"nvlx-controller","securityContext":{"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"controller","image":image,"args":["--namespace",namespace],"ports":[{"name":"health","containerPort":8080}],"readinessProbe":{"httpGet":{"path":"/readyz","port":"health"},"initialDelaySeconds":3,"periodSeconds":5},"livenessProbe":{"httpGet":{"path":"/livez","port":"health"},"initialDelaySeconds":3,"periodSeconds":10},"securityContext":{"allowPrivilegeEscalation":False,"readOnlyRootFilesystem":True,"runAsNonRoot":True,"capabilities":{"drop":["ALL"]}}}]}}}}
    pdb={"apiVersion":"policy/v1","kind":"PodDisruptionBudget","metadata":{"name":"nvlx-controller","namespace":namespace},"spec":{"minAvailable":1,"selector":{"matchLabels":labels}}}
    netpol={"apiVersion":"networking.k8s.io/v1","kind":"NetworkPolicy","metadata":{"name":"nvlx-controller","namespace":namespace},"spec":{"podSelector":{"matchLabels":labels},"policyTypes":["Ingress"],"ingress":[{"ports":[{"protocol":"TCP","port":8080}]}]}}
    return [sa,cr,crb,dep,pdb,netpol]

def render_json(**kwargs) -> str:
    return "\n".join(json.dumps(x,sort_keys=True) for x in manifests(**kwargs)) + "\n"
