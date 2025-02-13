from typing import List, Optional, Any, Union
import json
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
from .vfnode import VFlowData, VFNodeData
from .fanode import FARunnerStatus, FANodeStatus


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


class ValidationError(BaseModel):
    nid: str
    errors: List[str]  # 可能存在多条错误信息。如果isValid为True，则messages应该为空。
    pass


# class FARunResponse(BaseModel):
#     success: bool
#     tid: Optional[str] = None
#     validation_errors: Optional[List[ValidationError]] = None
#     pass


class FANodeUpdateType(Enum):
    overwrite = "overwrite"
    append = "append"
    remove = "remove"
    dontcare = "dontcare"
    pass


class FANodeUpdateData(BaseModel):
    type: FANodeUpdateType
    path: Optional[List[Union[str, int]]] = None
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
            model_datas = []
            for d in self.data:
                d_json = d.model_dump_json()
                model_datas.append(json.loads(d_json))
            # model_datas = [json.loads(d.model_dump_json()) for d in self.data]
            data = json.dumps(model_datas)
        return {
            "event": self.event.value,
            "data": data,
        }

    pass


class FAWorkflowNodeResult(BaseModel):
    tid: str
    id: str
    oriid: str
    data: VFNodeData
    ntype: str
    parentNode: Optional[str]
    runStatus: FANodeStatus
    pass


class FAWorkflowResult(BaseModel):
    tid: str
    usedvflow: Optional[dict]
    noderesult: Optional[List[FAWorkflowNodeResult]]
    status: FARunnerStatus
    starttime: datetime
    endtime: datetime
    pass


class FAWorkflow(BaseModel):
    wid: Optional[str] = None
    name: Optional[str] = None
    vflow: Optional[dict] = None
    pass


class FAWorkflowCreateType(Enum):
    new = "new"
    upload = "upload"
    release = "release"
    pass


class FAWorkflowCreateRequest(BaseModel):
    type: FAWorkflowCreateType
    wid: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    vflow: Optional[dict] = None
    pass


class FAWorkflowLocation(Enum):
    name = "name"
    vflow = "vflow"
    release = "release"
    allReleases = "allReleases"
    pass


class FAWorkflowUpdateRequset(BaseModel):
    wid: str
    location: FAWorkflowLocation
    data: Optional[Any] = None


class FAWorkflowReadRequest(BaseModel):
    wid: str
    locations: List[FAWorkflowLocation]
    rwid: Optional[str] = None
    pass


class FAWorkflowInfo(BaseModel):
    wid: str
    name: str
    lastModified: Optional[datetime]
    pass


class FAReleaseWorkflowInfo(BaseModel):
    rwid: str
    releaseTime: datetime
    name: str
    description: str
    pass


class FAWorkflowNodeRequest(BaseModel):
    wid: str
    tid: str
    nid: str
    request: dict
    pass


class FAWorkflowOperationResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    pass


class FAProgressNodeType(Enum):
    ALL_TASK_NODE = "ALL_TASK_NODE"
    SELECTED = "SELECTED"
    pass


class FAProgressRequest(BaseModel):
    tid: str
    node_type: FAProgressNodeType
    selected_nids: Optional[List[str]] = None
    pass
