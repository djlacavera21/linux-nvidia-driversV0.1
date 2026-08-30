"""Small stdlib Kubernetes API transport for nvlx 1.6."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from urllib import request, error, parse
import json, os, ssl

@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: dict | list | None
    resource_version: str | None = None

class ApiError(RuntimeError):
    def __init__(self, status: int, reason: str):
        super().__init__(f"Kubernetes API {status}: {reason[:240]}")
        self.status=status
        self.reason=reason[:240]

class KubeClient:
    def __init__(self, base_url: str, *, token: str | None=None, ca_file: str | None=None, timeout: float=10.0):
        if not base_url.startswith(("https://","http://")): raise ValueError("base_url must be http(s)")
        if timeout <= 0: raise ValueError("timeout must be positive")
        self.base_url=base_url.rstrip("/")
        self.token=token.strip() if token else None
        self.timeout=timeout
        self.context=ssl.create_default_context(cafile=ca_file) if self.base_url.startswith("https://") else None

    @classmethod
    def in_cluster(cls, *, timeout: float=10.0):
        host=os.environ.get("KUBERNETES_SERVICE_HOST")
        port=os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS","443")
        if not host: raise RuntimeError("KUBERNETES_SERVICE_HOST is not set")
        root=Path("/var/run/secrets/kubernetes.io/serviceaccount")
        token=(root/"token").read_text(encoding="utf-8").strip()
        return cls(f"https://{host}:{port}",token=token,ca_file=str(root/"ca.crt"),timeout=timeout)

    def _req(self, method: str, path: str, body=None, *, content_type="application/json"):
        data=None if body is None else json.dumps(body,separators=(",",":"),sort_keys=True).encode()
        headers={"Accept":"application/json"}
        if data is not None: headers["Content-Type"]=content_type
        if self.token: headers["Authorization"]="Bearer "+self.token
        return request.Request(self.base_url+path,data=data,headers=headers,method=method)

    def request_json(self, method: str, path: str, body=None, *, content_type="application/json") -> ApiResponse:
        try:
            with request.urlopen(self._req(method,path,body,content_type=content_type),timeout=self.timeout,context=self.context) as r:
                raw=r.read()
                parsed=json.loads(raw.decode()) if raw else None
                rv=parsed.get("metadata",{}).get("resourceVersion") if isinstance(parsed,dict) else None
                return ApiResponse(r.status,parsed,rv)
        except error.HTTPError as e:
            raw=e.read().decode("utf-8","replace")
            try:
                parsed=json.loads(raw); reason=parsed.get("message") or parsed.get("reason") or e.reason
            except Exception: reason=e.reason
            raise ApiError(e.code,str(reason)) from None
        except error.URLError as e:
            raise ApiError(0,str(getattr(e,"reason","connection failed"))) from None

    def watch_lines(self, path: str):
        """Yield decoded Kubernetes watch events from a newline JSON stream."""
        try:
            with request.urlopen(self._req("GET",path),timeout=self.timeout,context=self.context) as r:
                for raw in r:
                    line=raw.strip()
                    if line: yield json.loads(line.decode("utf-8"))
        except error.HTTPError as e:
            raise ApiError(e.code,str(e.reason)) from None
        except error.URLError as e:
            raise ApiError(0,str(getattr(e,"reason","connection failed"))) from None

    def list_fleets(self) -> ApiResponse:
        return self.request_json("GET","/apis/nvlx.io/v1alpha1/gpufleets")

    def get_fleet(self, name: str) -> ApiResponse:
        return self.request_json("GET","/apis/nvlx.io/v1alpha1/gpufleets/"+parse.quote(name,safe=""))

    def patch_status(self, name: str, resource_version: str, status: dict) -> ApiResponse:
        body={"metadata":{"resourceVersion":resource_version},"status":status}
        return self.request_json("PATCH","/apis/nvlx.io/v1alpha1/gpufleets/"+parse.quote(name,safe="")+"/status",body,content_type="application/merge-patch+json")

    def patch_finalizers(self, name: str, resource_version: str, finalizers: list[str]) -> ApiResponse:
        body={"metadata":{"resourceVersion":resource_version,"finalizers":finalizers}}
        return self.request_json("PATCH","/apis/nvlx.io/v1alpha1/gpufleets/"+parse.quote(name,safe=""),body,content_type="application/merge-patch+json")

    def create_event(self, namespace: str, event: dict) -> ApiResponse:
        return self.request_json("POST","/apis/events.k8s.io/v1/namespaces/"+parse.quote(namespace,safe="")+"/events",event)

    def watch_path(self, resource_version: str) -> str:
        q=parse.urlencode({"watch":"true","allowWatchBookmarks":"true","resourceVersion":resource_version})
        return "/apis/nvlx.io/v1alpha1/gpufleets?"+q
