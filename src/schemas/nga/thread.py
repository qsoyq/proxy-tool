from enum import Enum
from pydantic import BaseModel, Field


class ForumSectionIndex(BaseModel):
    fid: int = Field(description="版面id 或当前子板面的父版面 id")
    name: str
    stid: int | None = Field(None, description="部分分区子板面的id")
    info: str | None = Field(None)
    icon: str | None = Field(None, description="分区对应的logo")


class GetForumSectionsRes(BaseModel):
    sections: list[ForumSectionIndex] = Field([])


class NGASmile(BaseModel):
    name: str = Field(..., description="名称代码", examples=["[s:ac:哭笑]"])
    url: str = Field(
        ..., description="表情对应的图片链接", examples=["https://img4.nga.178.com/ngabbs/post/smile/ac15.png"]
    )
    tag: str = Field(
        ..., description="html a标签", examples=["""<img src="https://img4.nga.178.com/ngabbs/post/smile/ac15.png">"""]
    )


class GetNGASmiles(BaseModel):
    data: list[NGASmile]


class OrderByEnum(str, Enum):
    lastpostdesc = "lastpostdesc"
    postdatedesc = "postdatedesc"


class Thread(BaseModel):
    tid: int
    fid: int
    fname: str | None = Field(None, description="fid 对应的分区名称")
    icon: str | None = Field(None, description="主题对应的分区logo")
    subject: str
    postdate: int
    lastpost: int
    lastpostStr: str | None = Field(None)
    postdateStr: str | None = Field(None)
    url: str | None = Field(None, description="帖子网页链接")
    ios_app_scheme_url: str | None = Field(None)
    ios_open_scheme_url: str | None = Field(None, description="通过 http 重定向打开 app")


class Threads(BaseModel):
    threads: list[Thread]


class ThreadsGroup(BaseModel):
    fid: int | None = None
    favor: int | None = None
    threads: list[Thread]


class GetThreadsV2Res(BaseModel):
    data: list[ThreadsGroup]
