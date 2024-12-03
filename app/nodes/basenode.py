from typing import List, Dict, Optional
import asyncio
from pydantic import BaseModel
import traceback
from loguru import logger
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeData
from app.schemas.vfnode import VFNodeInfo, VFNodeContentDataType
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
)
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR


class FANodeWaitStatus(BaseModel):
    nid: str
    output: str
    pass


class NodeCancelException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class FABaseNode:
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        self.tid = tid
        self.id = nodeinfo.id
        self.data: VFNodeData = nodeinfo.data
        self.ntype: str = nodeinfo.data.ntype
        self.parentNode = nodeinfo.parentNode

        self.doneEvent = asyncio.Event()
        # 其他节点的doneEvent会存在该节点的waitEvents列表里
        self.waitEvents: List[asyncio.Event] = []
        self.waitType = FANodeWaitType.AND

        # 其他节点的输出handle的状态
        self.waitStatus: List[FANodeWaitStatus] = []
        # 该节点的输出handle的状态
        self.outputStatus: Dict[str, FANodeStatus] = {
            oname: FANodeStatus.Pending
            for oname in self.data.connections.outputs.keys()
        }
        # 该节点的运行状态
        self.runStatus = FANodeStatus.Pending
        pass

    async def invoke(self):
        logger.debug(f"invoke {self.data.label} {self.id}")
        await asyncio.gather(*(event.wait() for event in self.waitEvents))
        logger.debug(f"wait done {self.data.label} {self.id}")
        try:
            if len(self.waitStatus) > 0:
                # 如果是AND，要求不能出现任何error或cancel状态
                waitFunc = all if self.waitType == FANodeWaitType.AND else any
                preNodeSuccess = []
                for thiswstatus in self.waitStatus:
                    thenode = (await ALL_TASKS_MGR.get(self.tid)).getNode(
                        thiswstatus.nid
                    )
                    thisowstatus = thenode.outputStatus[thiswstatus.output]
                    wstatus = not (
                        thisowstatus == FANodeStatus.Error
                        or thisowstatus == FANodeStatus.Canceled
                    )
                    preNodeSuccess.append(wstatus)

                canRunNode = waitFunc(preNodeSuccess)
                # 前置节点出错或取消，本节点取消运行
                if not canRunNode:
                    raise NodeCancelException("前置节点出错或取消，本节点取消运行")
                logger.debug(f"can run {self.data.label} {self.id}")
            self.setAllOutputStatus(FANodeStatus.Running)
            self.putNodeStatus(FANodeStatus.Running)

            # 前置节点全部成功，本节点开始运行
            updateDatas = await self.run()
            # 运行成功
            logger.debug(f"run success {self.data.label} {self.id}")
            # self.setAllOutputStatus(FANodeStatus.Success)
            # 各个输出handle的成功需要由子类函数来设置
            self.putNodeStatus(FANodeStatus.Success)
            nodeUpdateDatas = []
            if updateDatas:
                nodeUpdateDatas.extend(updateDatas)
                pass
            ALL_MESSAGES_MGR.put(
                self.tid,
                SSEResponse(
                    event=SSEResponseType.updatenode,
                    data=SSEResponseData(
                        nid=self.id,
                        data=nodeUpdateDatas,
                    ),
                ),
            )
            pass
        except NodeCancelException as e:
            logger.debug(f"node cancel {self.data.label} {self.id} {e.message}")
            self.setAllOutputStatus(FANodeStatus.Canceled)
            self.putNodeStatus(FANodeStatus.Canceled)
            pass
        except Exception as e:
            error_message = traceback.format_exc()
            logger.debug(f"node error {self.data.label} {error_message} {self.id}")
            self.setAllOutputStatus(FANodeStatus.Error)
            self.putNodeStatus(FANodeStatus.Error)
        finally:
            self.doneEvent.set()
        pass

    def setAllOutputStatus(self, status: FANodeStatus):
        for oname in self.outputStatus:
            self.outputStatus[oname] = status
        pass

    def setOutputStatus(self, oname: str, status: FANodeStatus):
        self.outputStatus[oname] = status
        pass

    def putNodeStatus(self, status: FANodeStatus):
        self.runStatus = status
        ALL_MESSAGES_MGR.put(
            self.tid,
            SSEResponse(
                event=SSEResponseType.updatenode,
                data=SSEResponseData(
                    nid=self.id,
                    data=[
                        FANodeUpdateData(
                            type=FANodeUpdateType.overwrite,
                            path=["state", "status"],
                            data=status,
                        )
                    ],
                ),
            ),
        )
        pass

    async def getRefData(self, refdata: str):
        mayiter = refdata.split("#")
        if len(mayiter) > 1:
            pass
        nid, contentname, ctid = mayiter[0].split("/")
        thenode = (await ALL_TASKS_MGR.get(self.tid)).getNode(nid)
        content = thenode.data.getContent(contentname).byId[ctid]
        rtype = content.type
        rdata = None
        if rtype == VFNodeContentDataType.IterIndex:
            pass
        else:
            rdata = content.data
        pass
        return rdata

    # 需要子类实现的函数 ===============================================================
    async def run(self) -> List[FANodeUpdateData]:
        self.setAllOutputStatus(FANodeStatus.Success)
        pass

    def getCurData(self) -> Optional[List[FANodeUpdateData]]:
        return [
            FANodeUpdateData(
                type=FANodeUpdateType.overwrite,
                path=["state", "status"],
                data=self.runStatus,
            )
        ]

    def validate(self, validateVars: Dict[str, List[str]]) -> Optional[ValidationError]:
        return None
