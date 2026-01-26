from pydantic import BaseModel, Field


class RailwayProjectField(BaseModel):
    id: str = Field(..., examples=["d99868df-a1a8-441d-bd1b-b7adc9a41872"])
    name: str = Field(..., examples=["name"])
    description: str = Field(..., examples=[""])
    createdAt: str = Field(..., examples=["2023-04-18T16:32:08.172Z"])


class RailwayEnvironmentField(BaseModel):
    id: str = Field(..., examples=["d38dab2e-5fad-408c-a2e5-71a980003170"])
    name: str = Field(..., examples=["production"])


class RailwayDeploymentCreatorField(BaseModel):
    id: str = Field(..., examples=["d99868df-a1a8-441d-bd1b-b7adc9a41872"])
    name: str = Field(..., examples=["name"])
    avatar: str = Field(..., examples=["https://avatars.githubusercontent.com/u/9385015?v=4"])


class RailwayDeploymentField(BaseModel):
    id: str = Field(..., examples=[""])
    creator: RailwayDeploymentCreatorField
    meta: dict = Field(..., examples=[{}])


class RailwayWebhookPayload(BaseModel):
    type: str = Field(..., examples=["DEPLOY"])
    timestamp: str = Field(..., examples=["2024-12-13T17:29:30.012Z"])
    project: RailwayProjectField
    environment: RailwayEnvironmentField
    deployment: RailwayDeploymentField
