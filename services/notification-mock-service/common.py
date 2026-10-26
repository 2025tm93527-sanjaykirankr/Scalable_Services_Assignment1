import json
import logging
import os
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("service")

def request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or str(uuid.uuid4())

def log_event(event: str, request_id_value: str, **fields):
    logger.info(json.dumps({"event": event, "request_id": request_id_value, **fields}, default=str))

def error_response(status: int, code: str, message: str, rid: str):
    return JSONResponse(status_code=status, content={"error": {
        "code": code, "message": message, "request_id": rid
    }})
