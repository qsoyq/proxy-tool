import tempfile
import yagmail
import json
from pydantic import BaseModel, Field


class GmailOauth2File(BaseModel):
    email_address: str
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str


class GmailPushMessage(BaseModel):
    to: str | list[str]
    subject: str
    contents: str | list[str]

    sender: str
    password: str | None = Field(None, description="使用密码登录时需要该值")
    oauth2_file: GmailOauth2File | None = Field(
        None,
        description="使用 oauth2 验证时需要该对象. 见 https://github.com/kootenpv/yagmail?tab=readme-ov-file#oauth2",
    )

    def push(self) -> None:
        yag: yagmail.SMTP | None = None
        if self.password:
            yag = yagmail.SMTP(self.sender, self.password)

        elif self.oauth2_file:
            with tempfile.NamedTemporaryFile("w+") as f:
                f.write(json.dumps(self.oauth2_file.dict()))
                f.seek(0)
                yag = yagmail.SMTP(self.sender, oauth2_file=f.name)

        assert yag

        if isinstance(self.contents, str):
            self.contents = [self.contents]

        if isinstance(self.to, str):
            self.to = [self.to]

        for to in self.to:
            yag.send(to=to, subject=self.subject, contents=self.contents)
