"""Small stdlib Kubernetes API transport for nvlx 1.6.x."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from urllib import request, error, parse
import json, os, socket, ssl

@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: dict | list | None
    resource_version: str | None = None

class ApiError(RuntimeError):
    def __init__(self, status: int, reason: str):
        clean=str(reason or "request failed").replace("\n"," ").replace("\r"," ")[:240]
        super().__init__(f"Kubernetes API {status}: {clean}")
        self.status=status
        self.reason=clean

class KubeClient:
    def __init__(self, base_url: str, *, token: str | None=None, ca_file: str | None=None, timeout: float=10.0, watch_timeout: float=35.0, watch_timeout_seconds: int=30):
        if not base_url.startswith(("https://","http://")): raise ValueError("base_url must be http(s)")
        if isinstance(timeout,bool) or timeout <= 0: raise ValueError("timeout must be positive")
        if isinstance(watch_timeout,bool) or watch_timeout <= 0: raise ValueError("watch_timeout must be positive")
        if isinstance(watch_timeout_seconds,bool) or not isinstance(watch_timeout_seconds,int) or watch_timeout_seconds < 5:
            raise ValueError("watch_timeout_seconds must be an integer >= 5")
        if watch_timeout <= watch_timeout_seconds:
            raise ValueError("watch_timeout must exceed watch_timeout_seconds")
        self.base_url=base_url.rstrip("/")
        self.token=token.strip() if token else None
        self.timeout=float(timeout)
        self.watch_timeout=float(watch_timeout)
        self.watch_timeout_seconds=watch_timeout_seconds
        self.context=ssl.create_default_context(cafile=ca_file) if self.base_url.startswith("https://") else None

    @classmethod
    def in_cluster(cls, *, timeout: float=10.0, watch_timeout: float=35.0, watch_timeout_seconds: int=30):
        host=os.environ.get("KUBERNETES_SERVICE_HOST")
        port=os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS","443")
        if not host: raise RuntimeError("KUBERNETES_SERVICE_HOST is not set")
        root=Path("/var/run/secrets/kubernetes.io/serviceaccount")
        token=(root/"token").read_text(encoding="utf-8").strip()
        if not token: raise RuntimeError("service account token is empty")
        return cls(f"https://{host}:{port}",token=token,ca_file=str(root/"ca.crt"),timeout=timeout,watch_timeout=watch_timeout,watch_timeout_seconds=watch_timeout_seconds)

    def _req(self, method: str, path: str, body=None, *, content_type="application/json"):
        if not path.startswith("/"): raise ValueError("Kubernetes API path must be absolute")
        data=None if body is None else json.dumps(body,separators=(",",":"),sort_keys=True).encode()
        headers={"Accept":"application/json"}
        if data is not None: headers["Content-Type"]=content_type
        if self.token: headers["Authorization"]="Bearer "+self.token
        return request.Request(self.base_url+path,data=data,headers=headers,method=method)

    def _api_error(self, status: int, reason) -> ApiError:
        clean=str(reason or "request failed")
        if self.token:
            clean=clean.replace("Bearer "+self.token,"Bearer <redacted>")
            clean=clean.replace(self.token,"<redacted>")
        return ApiError(status,clean)

    @staticmethod
    def _decode_json(raw: bytes):
        if not raw: return None
        try: return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError,json.JSONDecodeError):
            raise ApiError(0,"Kubernetes API returned malformed JSON") from None

    def request_json(self, method: str, path: str, body=None, *, content_type="application/json") -> ApiResponse:
        try:
            with request.urlopen(self._req(method,path,body,content_type=content_type),timeout=self.timeout,context=self.context) as r:
                parsed=self._decode_json(r.read())
                rv=parsed.get("metadata",{}).get("resourceVersion") if isinstance(parsed,dict) else None
                return ApiResponse(r.status,parsed,rv)
        except error.HTTPError as e:
            raw=e.read().decode("utf-8","replace")
            try:
                parsed=json.loads(raw)
                reason=(parsed.get("message") or parsed.get("reason") or e.reason) if isinstance(parsed,dict) else e.reason
            except Exception: reason=e.reason
            raise self._api_error(e.code,reason) from None
        except (error.URLError,socket.timeout,TimeoutError) as e:
            if isinstance(e,(socket.timeout,TimeoutError)):
                reason="request timed out"
            else:
                reason=getattr(e,"reason",None) or "connection failed"
            raise self._api_error(0,reason) from None

    def watch_lines(self, path: str):
        """Yield decoded Kubernetes watch events; malformed lines are ignored safely."""
        try:
            with request.urlopen(self._req("GET",path),timeout=self.watch_timeout,context=self.context) as r:
                for raw in r:
                    line=raw.strip()
                    if not line: continue
                    try: value=json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError,json.JSONDecodeError): continue
                    if isinstance(value,dict): yield value
        except error.HTTPError as e:
            raw=e.read().decode("utf-8","replace")
            try:
                parsed=json.loads(raw)
                reason=(parsed.get("message") or parsed.get("reason") or e.reason) if isinstance(parsed,dict) else e.reason
            except Exception: reason=e.reason
            raise self._api_error(e.code,reason) from None
        except (error.URLError,socket.timeout,TimeoutError) as e:
            if isinstance(e,(socket.timeout,TimeoutError)):
                reason="watch timed out"
            else:
                reason=getattr(e,"reason",None) or "connection failed"
            raise self._api_error(0,reason) from None

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
        q=parse.urlencode({"watch":"true","allowWatchBookmarks":"true","resourceVersion":resource_version,"timeoutSeconds":self.watch_timeout_seconds})
        return "/apis/nvlx.io/v1alpha1/gpufleets?"+q
