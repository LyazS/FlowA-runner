from typing import List
from pydantic import BaseModel
from .vfnode import VFlowData


class VarItem(BaseModel):
    nodeId: str
    nlabel: str
    dpath: List[str]
    dlabel: str
    dkey: str
    dtype: str


class VarSelectOption(BaseModel):
    label: str
    value: str


class ValidationResult(BaseModel):
    isValid: bool
    message: str
    pass


class FARunRequest(BaseModel):
    vflow: VFlowData
    task_uuid: str
    user_uuid: str
    pass
