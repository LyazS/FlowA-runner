from typing import List
from pydantic import BaseModel
from enum import Enum
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


class FARunRequest(BaseModel):
    vflow: VFlowData
    task_uuid: str
    user_uuid: str
    pass


class ValidationError(BaseModel):
    nid: str
    errors: List[str]  # 可能存在多条错误信息。如果isValid为True，则messages应该为空。
    pass


class FARunResponse(BaseModel):
    task_uuid: str
    user_uuid: str
    validation_errors: List[ValidationError]
    pass
