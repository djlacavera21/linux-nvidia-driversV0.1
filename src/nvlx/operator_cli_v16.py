"""nvlx 1.6 live Kubernetes operator daemon."""
from __future__ import annotations
import argparse, os
from .k8s_api_v16 import KubeClient
from .lease_v16 import LeaseElector
from .runtime_v16 import Runtime
from .http_v16 import HealthServer

def main(argv=None):
    p=argparse.ArgumentParser(prog="nvlx-operator",description="nvlx 1.6 live GPUFleet Kubernetes operator")
    p.add_argument("--server",help="Kubernetes API URL; defaults to in-cluster configuration")
    p.add_argument("--token")
    p.add_argument("--namespace",default=os.environ.get("NVLX_NAMESPACE","nvlx-system"))
    p.add_argument("--identity",default=os.environ.get("POD_NAME") or os.environ.get("HOSTNAME") or "nvlx-controller")
    p.add_argument("--health-host",default="0.0.0.0"); p.add_argument("--health-port",type=int,default=8080)
    p.add_argument("--timeout",type=float,default=10.0); p.add_argument("--once",action="store_true")
    a=p.parse_args(argv)
    client=KubeClient(a.server,token=a.token,timeout=a.timeout) if a.server else KubeClient.in_cluster(timeout=a.timeout)
    elector=LeaseElector(client,a.identity,namespace=a.namespace)
    runtime=Runtime(client,a.identity,namespace=a.namespace,leader_check=elector.ensure_leader)
    server=HealthServer(runtime,a.health_host,a.health_port).start()
    try:
        if a.once:
            runtime.list_and_watch_once(); return 0
        runtime.run_forever(); return 0
    finally: server.close()

if __name__=="__main__": raise SystemExit(main())
