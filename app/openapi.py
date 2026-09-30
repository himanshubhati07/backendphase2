from __future__ import annotations
from flask import Response


def openapi_document() -> dict:
    paths = {"/health":{"get":{"responses":{"200":{"description":"Healthy"}}}},"/openapi.json":{"get":{"responses":{"200":{"description":"OpenAPI document"}}}},"/docs":{"get":{"responses":{"200":{"description":"Swagger UI"}}}}}
    resources = {"members":["get","post"],"trainers":["get","post"],"membership-plans":["post"],"attendance":["get"]}
    for name, methods in resources.items(): paths[f"/api/v1/{name}"]={m:{"security":[{"ApiKeyAuth":[]}],"responses":{"200":{"description":"Success"},"201":{"description":"Created"},"400":{"description":"Invalid input"},"401":{"description":"Missing or invalid API key"}}} for m in methods}
    for path in ["/api/v1/members/{member_id}","/api/v1/trainers/{trainer_id}","/api/v1/memberships/{membership_id}"]:
        paths[path]={m:{"security":[{"ApiKeyAuth":[]}],"parameters":[{"name":path.split("{")[1][:-1],"in":"path","required":True,"schema":{"type":"string","format":"uuid"}}],"responses":{"200":{"description":"Success"},"204":{"description":"Deleted"},"400":{"description":"Invalid input"},"401":{"description":"Unauthorized"},"404":{"description":"Not found"},"409":{"description":"Conflict"}}} for m in ["get","patch","delete"]}
    for path, method in [("/api/v1/members/{member_id}/memberships","post"),("/api/v1/members/{member_id}/attendance/check-in","post"),("/api/v1/members/{member_id}/attendance","get"),("/api/v1/attendance/{attendance_id}/check-out","patch")]: paths[path]={method:{"security":[{"ApiKeyAuth":[]}],"responses":{"200":{"description":"Success"},"201":{"description":"Created"},"400":{"description":"Invalid input"},"401":{"description":"Unauthorized"},"404":{"description":"Not found"},"409":{"description":"Conflict"}}}}
    return {"openapi":"3.0.3","info":{"title":"Gym Management API","version":"1.0.0"},"components":{"securitySchemes":{"ApiKeyAuth":{"type":"apiKey","in":"header","name":"X-API-Key"}},"schemas":{"Error":{"type":"object"},"Pagination":{"type":"object","properties":{"items":{"type":"array","items":{}},"page":{"type":"integer"},"per_page":{"type":"integer"},"total":{"type":"integer"}}}}},"paths":paths}

def docs_html() -> Response:
    return Response('<!doctype html><html><body><div id="swagger-ui"></div><script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script><script>SwaggerUIBundle({url:"/openapi.json",dom_id:"#swagger-ui"})</script></body></html>', mimetype="text/html")
