import logging
from typing import Any
from fastapi import Path, APIRouter, Body
from schemas.webhook.railway import RailwayWebhookPayload
from schemas.notifications.bark import BarkPushMessage, BarkPushLevel


router = APIRouter(tags=["Webhook"], prefix="/webhook/railway")

logger = logging.getLogger(__file__)


@router.options("/bark/{token}", summary="Railway")
def railway_webhook_options():
    return "ok"


@router.post("/bark/{token}", summary="Railway")
def railway_webhook(
    token: str = Path(..., description="bark token"),
    payload: RailwayWebhookPayload = Body(...),
):
    logger.info(f"[Webhook] [Railway]{token} {payload}")
    logger.info(f"[Webhook] [Railway] JSON: {payload.json()}")
    data: dict[str, Any] = dict(
        device_key=token,
        title="Railway Webhook",
        body=f"id:{payload.project.id}\nname:{payload.project.name}\nDEPLOY: {payload.type}\ntimestamp: {payload.timestamp}\nenv:{payload.environment.name}",
        level=BarkPushLevel.active,
        group="railway",
    )
    msg = BarkPushMessage(**data)
    resp = msg.push()
    resp.raise_for_status()
    return "ok"
