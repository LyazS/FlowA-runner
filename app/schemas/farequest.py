from typing import List, Optional, Any, Union
import json
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


class FANodeUpdateType(Enum):
    overwrite = "overwrite"
    append = "append"
    remove = "remove"
    pass


class FANodeUpdateData(BaseModel):
    type: FANodeUpdateType
    path: Optional[List[str]] = None
    data: Optional[Any] = None
    pass


class SSEResponseType(Enum):
    updatenode = "updatenode"
    batchupdatenode = "batchupdatenode"
    internalerror = "internalerror"
    flowfinish = "flowfinish"
    pass


class SSEResponseData(BaseModel):
    nid: str
    oriid: str
    data: List[FANodeUpdateData]
    pass


class SSEResponse(BaseModel):
    event: SSEResponseType
    data: Union[SSEResponseData, List[SSEResponseData], None] = None
    pass

    def toSSEResponse(self):
        data = None
        if isinstance(self.data, SSEResponseData):
            data = self.data.model_dump_json()
        elif isinstance(self.data, list):
            model_datas = [json.loads(d.model_dump_json()) for d in self.data]
            data = json.dumps(model_datas)
        return {
            "event": self.event.value,
            "data": data,
        }
