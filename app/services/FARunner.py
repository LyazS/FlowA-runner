from typing import Dict, List, TYPE_CHECKING
import asyncio
import aiofiles
from aiofiles import os as aiofiles_os
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import traceback
from loguru import logger
from app.core.config import settings
from app.schemas.vfnode import VFNodeConnectionDataType, VFlowData
from app.schemas.fanode import FARunnerStatus
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
    FAWorkflowNodeResult,
    FAWorkflowResult,
    FAWorkflow,
)
from app.db.session import get_db_ctxmgr
from app.models.fastore import (
    FAWorkflowModel,
    FAWorkflowResultModel,
    FAWorkflowNodeResultModel,
)
from sqlalchemy import select, update, exc, exists, delete
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from app.nodes import FATaskNode


class FARunner:
    def __init__(self, tid: str):
        self.tid = tid
        self.wid = None
        self.oriflowdata = None
        self.flowdata: VFlowData = None
        self.nodes: Dict[str, "FATaskNode"] = {}
        self.status: FARunnerStatus = FARunnerStatus.Pending
        # 时间戳
        self.starttime = None
        self.endtime = None
        pass

    def addNode(self, nid, node: "FATaskNode"):
        self.nodes[nid] = node
        pass

    def getNode(self, nid: str) -> "FATaskNode":
        return self.nodes[nid]

    def buildNodes(self):
        from app.nodes.tasknode import FANodeWaitStatus
        from app.nodes import FANODECOLLECTION

        # 初始化大图节点，即parentNode == None
        for nodeinfo in self.flowdata.nodes:
            if nodeinfo.parentNode == None:
                self.addNode(
                    nodeinfo.id,
                    (FANODECOLLECTION[nodeinfo.data.ntype])(
                        self.tid,
                        nodeinfo,
                    ),
                )
            pass
        # 构建节点连接关系
        for edgeinfo in self.flowdata.edges:
            if edgeinfo.source in self.nodes and edgeinfo.target in self.nodes:
                if (
                    self.getNode(edgeinfo.source).parentNode != None
                    or self.getNode(edgeinfo.target).parentNode != None
                ):
                    continue
                source_handle = edgeinfo.sourceHandle
                target_handle = edgeinfo.targetHandle
                self.getNode(edgeinfo.target).waitEvents.append(
                    self.getNode(edgeinfo.source).doneEvent
                )
                self.getNode(edgeinfo.target).waitStatus.append(
                    FANodeWaitStatus(
                        nid=edgeinfo.source,
                        output=source_handle,
                    )
                )
        pass

    async def run(self, vflow: FAWorkflow):
        self.starttime = datetime.now(ZoneInfo("Asia/Shanghai"))
        self.wid = vflow.wid
        self.oriflowdata = vflow.vflow
        self.flowdata = VFlowData.model_validate(self.oriflowdata)
        self.buildNodes()
        # 启动所有节点
        self.status = FARunnerStatus.Running
        tasks = []
        # 当前只有根节点，所以直接启动即可
        for nid in self.nodes:
            tasks.append(self.nodes[nid].invoke())
        # 等待所有节点完成
        await asyncio.gather(*tasks)
        self.endtime = datetime.now(ZoneInfo("Asia/Shanghai"))
        self.status = FARunnerStatus.Success
        # 保存历史记录
        await self.saveResult()
        ALL_MESSAGES_MGR.put(
            self.tid,
            SSEResponse(
                event=SSEResponseType.flowfinish,
                data=None,
            ),
        )
        pass

    async def saveResult(self) -> FAWorkflow:
        try:
            async with get_db_ctxmgr() as db:
                stmt = select(exists().where(FAWorkflowModel.wid == self.wid))
                db_result = await db.execute(stmt)
                db_exists = db_result.scalar()
                if not db_exists:
                    raise ValidationError("workflow not found")
                theresult = FAWorkflowResultModel(
                    tid=self.tid,
                    usedvflow=self.oriflowdata,
                    status=self.status.value,
                    starttime=self.starttime,
                    endtime=self.endtime,
                    wid=self.wid,
                )
                db.add(theresult)
                for nid in self.nodes.keys():
                    thenode = self.nodes[nid]
                    noderesult = FAWorkflowNodeResultModel(
                        nid=nid,
                        oriid=thenode.oriid,
                        data=thenode.store().model_dump_json(),
                        ntype=thenode.ntype,
                        parentNode=thenode.parentNode,
                        runStatus=thenode.runStatus.value,
                        tid=self.tid,
                    )
                    db.add(noderesult)
                await db.commit()
                logger.info(f"save result to db, wid: {self.wid}")
                pass
        except Exception as e:
            errmsg = traceback.format_exc()
            logger.error(f"save result error: {errmsg}")
            pass

    async def loadResult(self, wid: int, tid: str):
        from app.nodes import FANODECOLLECTION

        try:
            async with get_db_ctxmgr() as db:
                stmt = (
                    select(FAWorkflowResultModel)
                    .filter(FAWorkflowResultModel.wid == wid)
                    .filter(FAWorkflowResultModel.tid == tid)
                    .options(selectinload(FAWorkflowResultModel.noderesults))
                )
                db_result = await db.execute(stmt)
                store = db_result.scalars().first()
                if store is None:
                    raise ValidationError("workflow result not found")
                self.wid = wid
                self.oriflowdata = store.usedvflow
                self.flowdata: VFlowData = VFlowData.model_validate(self.oriflowdata)
                self.status = store.status
                self.starttime = store.starttime
                self.endtime = store.endtime

                nodeinfo_dict = {}
                for nodeinfo in self.flowdata.nodes:
                    nodeinfo_dict[nodeinfo.id] = nodeinfo
                    pass
                for noderesult in store.noderesults:
                    thenode: "FATaskNode" = FANODECOLLECTION[noderesult.ntype](
                        self.tid, nodeinfo_dict[noderesult.oriid]
                    )

                    thenodedata = noderesult.data
                    if isinstance(thenodedata, str):
                        thenodedata = json.loads(thenodedata)
                    thenodedata = FAWorkflowNodeResult(
                        tid=thenodedata["tid"],
                        id=thenodedata["id"],
                        oriid=thenodedata["oriid"],
                        ntype=thenodedata["ntype"],
                        parentNode=thenodedata["parentNode"],
                        runStatus=thenodedata["runStatus"],
                        data=thenodedata["data"],
                    )
                    thenode.restore(thenodedata)
                    self.addNode(noderesult.nid, thenode)
                    pass
                return True
        except Exception as e:
            errmsg = traceback.format_exc()
            logger.error(f"load result error: {errmsg}")
            return False
