import xmltodict
import json
from pydantic import BaseModel, Field
import logging
from fastapi import APIRouter, Body, Query

router = APIRouter(tags=["Utils"], prefix="/convert/xml")

logger = logging.getLogger(__file__)


class XMLConvertRes(BaseModel):
    content: str = Field(..., description="json字符串")


class XMLConvertReq(BaseModel):
    content: str = Field(..., description="xml字符串")


@router.get("/json", response_model=XMLConvertRes, summary="xml2json")
def to_json(content: str = Query(..., description="xml字符串")):
    """将传入的 xml 字符串转成 json字符串并返回"""
    return {"content": json.dumps(xmltodict.parse(content), ensure_ascii=False)}


@router.post("/json", response_model=XMLConvertRes, summary="xml2json")
def to_json_v2(req: XMLConvertReq = Body(...)):
    """将传入的 xml 字符串转成 json字符串并返回"""
    content = req.content
    return {"content": json.dumps(xmltodict.parse(content), ensure_ascii=False)}
