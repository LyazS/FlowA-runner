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

if TYPE_CHECKING:
    from app.nodes import FABaseNode


class FARunner:
    def __init__(self, tid: str):
        self.tid = tid
        self.name = tid
        self.oriflowdata = None
        self.flowdata: VFlowData = None
        self.nodes: Dict[str, "FABaseNode"] = {}
        self.status: FARunnerStatus = FARunnerStatus.Pending
        # 时间戳
        self.starttime = None
        self.endtime = None
        pass

    def setName(self, name: str):
        self.name = name
        pass

    def addNode(self, nid, node: "FABaseNode"):
        self.nodes[nid] = node
        pass

    def getNode(self, nid: str) -> "FABaseNode":
        return self.nodes[nid]

    def buildNodes(self):
        from app.nodes.basenode import FANodeWaitStatus
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

    async def run(self, oriflowdata):
        self.starttime = datetime.now(ZoneInfo("Asia/Shanghai"))
        self.oriflowdata = oriflowdata
        self.flowdata = VFlowData.model_validate(self.oriflowdata)
        # self.name = self.flowdata.name
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
        await self.saveHistory()
        ALL_MESSAGES_MGR.put(
            self.tid,
            SSEResponse(
                event=SSEResponseType.flowfinish,
                data=None,
            ),
        )
        pass

    async def saveHistory(self) -> FAWorkflow:
        vflowData: List[FAWorkflowNodeResult] = []
        for nid in self.nodes:
            vflowData.append(self.nodes[nid].store())
        vflowStore = FAWorkflow(
            name=self.name,
            vflow=self.oriflowdata,
            result=FAWorkflowResult(
                tid=self.tid,
                noderesult=vflowData,
                status=self.status,
                starttime=self.starttime,
                endtime=self.endtime,
            ),
            isCached=True,
        )
        savePath = os.path.join(settings.HISTORY_FOLDER, f"{self.tid}.json")
        async with aiofiles.open(savePath, mode="w", encoding="utf-8") as f:
            await f.write(vflowStore.model_dump_json(indent=4))
        logger.info(f"save history to {savePath}")
        pass

    async def loadHistory(self, store: FAWorkflow):
        from app.nodes import FANODECOLLECTION

        try:
            self.name = store.name
            self.oriflowdata = store.vflow
            self.flowdata: VFlowData = VFlowData.model_validate(self.oriflowdata)
            self.status = store.result.status
            self.starttime = store.result.starttime
            self.endtime = store.result.endtime

            nodeinfo_dict = {}
            for nodeinfo in self.flowdata.nodes:
                nodeinfo_dict[nodeinfo.id] = nodeinfo
                pass
            for noderesult in store.result.noderesult:
                thenode: "FABaseNode" = FANODECOLLECTION[noderesult.ntype](
                    self.tid, nodeinfo_dict[noderesult.oriid]
                )
                thenode.restore(noderesult)
                self.addNode(noderesult.id, thenode)
                pass
            return True
            pass
        except Exception as e:
            errmsg = traceback.format_exc()
            logger.error(f"load history error: {errmsg}")
            return False
