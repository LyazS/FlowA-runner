from typing import List, Optional
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
    uid: str
    pass


class ValidationError(BaseModel):
    nid: str
    errors: List[str]  # 可能存在多条错误信息。如果isValid为True，则messages应该为空。
    pass


class FARunResponse(BaseModel):
    success: bool
    tid: Optional[str] = None
    validation_errors: Optional[List[ValidationError]] = None
    pass
