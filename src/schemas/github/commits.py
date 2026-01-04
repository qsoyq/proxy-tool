from typing import Any

from pydantic import BaseModel, Field

from schemas.github import AuthorSchema


class ParentSchema(BaseModel):
    sha: str | None = Field(None, examples=['bfe66441fcdebbce6f9e37554ad85077d7d94e7b'])
    url: str | None = Field(
        None,
        examples=['https://api.github.com/repos/qsoyq/proxy-tool/commits/bfe66441fcdebbce6f9e37554ad85077d7d94e7b'],
    )
    html_url: str | None = Field(
        None, examples=['https://github.com/qsoyq/proxy-tool/commit/bfe66441fcdebbce6f9e37554ad85077d7d94e7b']
    )


class CommitTreeSchema(BaseModel):
    sha: str | None = Field(None, examples=['028503be45e8f3588212fe0526af58558abc3dbe'])
    url: str | None = Field(
        None,
        examples=['https://api.github.com/repos/qsoyq/proxy-tool/git/trees/028503be45e8f3588212fe0526af58558abc3dbe'],
    )


class CommitAuthorSchema(BaseModel):
    name: str | None = Field(None, examples=['Motov Yurii'])
    email: str | None = Field(None, examples=['109919500+YuriiMotov@users.noreply.github.com'])
    date: str | None = Field(None, examples=['2025-08-20T09:10:51Z'])


class CommitVerificationSchema(BaseModel):
    verified: bool | None = Field(None, examples=[False])
    reason: str | None = Field(None, examples=['unsigned'])
    signature: Any | None = Field(None, examples=[None])
    payload: Any | None = Field(None, examples=[None])
    verified_at: Any | None = Field(None, examples=[None])


class CommitSchema(BaseModel):
    author: CommitAuthorSchema | None = Field(None)
    committer: CommitAuthorSchema | None = Field(None)
    message: str | None = Field(None, examples=['feat: convert markdown to html in telegram rss'])
    tree: CommitTreeSchema | None = Field(None)
    url: str | None = Field(
        None,
        examples=[
            'https://api.github.com/repos/qsoyq/proxy-tool/git/commits/d64818a9c3281c8e3df3ac887c266497757c945d'
        ],
    )
    comment_count: int = Field(0, examples=[0])


class CommitItemSchema(BaseModel):
    commit: CommitSchema = Field(...)
    author: AuthorSchema | None = Field(None)
    committer: AuthorSchema | None = Field(None)
    parents: list[ParentSchema] = Field([])
    sha: str | None = Field(None, examples=['d64818a9c3281c8e3df3ac887c266497757c945d'])
    node_id: str | None = Field(
        None, examples=['C_kwDOH2CxMdoAKGQ2NDgxOGE5YzMyODFjOGUzZGYzYWM4ODdjMjY2NDk3NzU3Yzk0NWQ']
    )

    url: str | None = Field(
        None,
        examples=['https://api.github.com/repos/qsoyq/proxy-tool/commits/d64818a9c3281c8e3df3ac887c266497757c945d'],
    )
    html_url: str | None = Field(
        None, examples=['https://github.com/qsoyq/proxy-tool/commit/d64818a9c3281c8e3df3ac887c266497757c945d']
    )
    comments_url: str | None = Field(
        None,
        examples=[
            'https://api.github.com/repos/qsoyq/proxy-tool/commits/d64818a9c3281c8e3df3ac887c266497757c945d/comments'
        ],
    )
