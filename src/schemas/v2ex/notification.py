from pydantic import BaseModel, Field


class Notification(BaseModel):
    id: int
    member_id: int = Field(..., description="通知发起方")
    for_member_id: int = Field(..., description="通知接收方")
    text: str = Field(
        ...,
        description="通知描述",
        examples=[
            '<a href="/member/xxxxx" target="_blank"><strong>xxxxx</strong></a> 在回复 <a href="/t/xxxxx#reply10" class="topic-link">iPhone 17 Pro 和 Pro Max 杀后台严重吗</a> 时提到了你'
        ],
    )
    payload: str
    payload_rendered: str
    created: int
