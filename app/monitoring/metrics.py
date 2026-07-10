import time

from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
from starlette.routing import BaseRoute

http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "path"],
)


def setup_metrics(app):
    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        path = request.url.path
        if path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        route = request.scope.get("route")
        if route and isinstance(route, BaseRoute):
            path = route.path

        http_requests_total.labels(method=request.method, path=path, status=response.status_code).inc()
        http_request_duration_seconds.labels(method=request.method, path=path).observe(duration)
        return response

    @app.get("/metrics")
    async def metrics():
        return Response(content=generate_latest(), media_type="text/plain")
