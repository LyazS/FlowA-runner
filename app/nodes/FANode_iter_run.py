from typing import List, Dict, Optional, Set
import asyncio
import re
from pydantic import BaseModel
import traceback
from loguru import logger
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import (
    VFNodeInfo,
    VFEdgeInfo,
    VFNodeContentDataType,
    VFNodeData,
    VFlowData,
    VFNodeContentData,
)
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
from .basenode import FABaseNode


class FANode_iter_run(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        pass

    async def run(self) -> List[FANodeUpdateData]:
        from app.nodes.basenode import FANodeWaitStatus
        from app.nodes import FANODECOLLECTION

        flowdata: VFlowData = (await ALL_TASKS_MGR.get(self.tid)).flowdata
        child_node_infos: Dict[str, VFNodeInfo] = {}
        child_edge_infos: Dict[str, VFEdgeInfo] = {}
        # 收集所有子节点
        for nodeinfo in flowdata.nodes:
            if nodeinfo.parentNode == self.id:
                child_node_infos[nodeinfo.id] = nodeinfo
            pass
        pass
        for edgeinfo in flowdata.edges:
            if (
                edgeinfo.source in child_node_infos
                and edgeinfo.target in child_node_infos
            ):
                child_edge_infos[edgeinfo.id] = edgeinfo
            pass
        # 收集附属节点
        attach_node_name = set(
            [
                "attached_node_input",
                "attached_node_output",
                "attached_node_next",
                "attached_node_callbackFunc",
                "attached_node_callbackUser",
            ]
        )
        attach_nodeinfo: Dict[str, VFNodeInfo] = {}
        attach_nodes: Dict[str, FABaseNode] = {}
        for child_id, child_info in child_node_infos.items():
            if child_info.data.ntype in attach_node_name:
                attach_nodeinfo[child_info.data.ntype] = child_info
                pass
        for attached_name in attach_nodeinfo.keys():
            if attached_name == "attached_node_next":
                continue
            nodeinfo = attach_nodeinfo[attached_name]
            node: FABaseNode = (FANODECOLLECTION[nodeinfo.data.ntype])(
                self.tid,
                nodeinfo,
            )
            attach_nodes[attached_name] = node
            (await ALL_TASKS_MGR.get(self.tid)).addNode(node.id, node)
            # 提前先启动附属节点
            if attached_name != "attached_node_output":
                asyncio.create_task(node.invoke())
                pass
        pass
        # 开始迭代
        nest_level = self.getNestLevel()
        iter_var_len = 0
        node_payloads = self.data.getContent("payloads")
        for pid in node_payloads.order:
            item: VFNodeContentData = node_payloads.byId[pid]
            if item.key == "iter_var":
                refdata = await self.getRefData(item.data)
                iter_var_len = len(refdata)
                break
        AllChildNodeNames: Set[str] = set()
        for iter_idx in range(iter_var_len):
            # 构建next附属节点
            nodeinfo_next = attach_nodeinfo["attached_node_next"]
            node_next: FABaseNode = (FANODECOLLECTION[nodeinfo_next.data.ntype])(
                self.tid,
                nodeinfo_next,
            )
            new_nid = node_next.id + "".join(
                map(lambda x: "#" + str(x), nest_level + [iter_idx])
            )
            node_next.setNewID(new_nid)
            (await ALL_TASKS_MGR.get(self.tid)).addNode(node_next.id, node_next)
            # 构建其余子节点
            child_nodes: Dict[str, FABaseNode] = {}
            for child_id, child_info in child_node_infos.items():
                if child_info.data.ntype in attach_node_name:
                    continue
                child_node: FABaseNode = (FANODECOLLECTION[child_info.data.ntype])(
                    self.tid,
                    child_info,
                )
                new_nid = child_node.id.split("#", 1)[0] + "".join(
                    map(lambda x: "#" + str(x), nest_level + [iter_idx])
                )
                child_node.setNewID(new_nid)
                (await ALL_TASKS_MGR.get(self.tid)).addNode(new_nid, child_node)
                child_nodes[child_node.id] = child_node
                AllChildNodeNames.add(child_node.id)
            pass
            # 构建节点连接关系
            for edgeinfo in child_edge_infos.values():
                src_node_info = child_node_infos[edgeinfo.source]
                tgt_node_info = child_node_infos[edgeinfo.target]
                if src_node_info.data.ntype == "attached_node_input":
                    src_node = attach_nodes["attached_node_input"]
                    pass
                else:
                    src_nid = edgeinfo.source.split("#", 1)[0] + "".join(
                        map(lambda x: "#" + str(x), nest_level + [iter_idx])
                    )
                    src_node = (await ALL_TASKS_MGR.get(self.tid)).getNode(src_nid)
                if tgt_node_info.data.ntype == "attached_node_output":
                    tgt_node = attach_nodes["attached_node_output"]
                    pass
                elif tgt_node_info.data.ntype == "attached_node_next":
                    tgt_node = node_next
                    pass
                else:
                    tgt_nid = edgeinfo.target.split("#", 1)[0] + "".join(
                        map(lambda x: "#" + str(x), nest_level + [iter_idx])
                    )
                    tgt_node = (await ALL_TASKS_MGR.get(self.tid)).getNode(tgt_nid)
                    pass

                source_handle = edgeinfo.sourceHandle
                target_handle = edgeinfo.targetHandle
                tgt_node.waitEvents.append(src_node.doneEvent)
                tgt_node.waitStatus.append(
                    FANodeWaitStatus(
                        nid=src_node.id,
                        output=source_handle,
                    )
                )
            # 启动子节点
            for nid in child_nodes.keys():
                asyncio.create_task(child_nodes[nid].invoke())
            # 启动next附属节点
            task_next = asyncio.create_task(node_next.invoke())
            await task_next
        pass
        task_output = asyncio.create_task(attach_nodes["attached_node_output"].invoke())
        await task_output
        if attach_nodes["attached_node_output"].runStatus == FANodeStatus.Success:
            node_results = self.data.getContent("results")
            Niter_pattern = r"#(\w+)"
            returnUpdateData = []
            for rid in node_results.order:
                item: VFNodeContentData = node_results.byId[rid]
                item_ref = item.config.ref
                nidNiter, contentname, ctid = item_ref.split("/")
                nid_matches = re.findall(Niter_pattern, nidNiter)
                if len(nest_level) != len(nid_matches) - 1:
                    raise Exception("迭代节点嵌套层数不匹配")
                for level_idx in range(len(nest_level)):
                    nid_matches[level_idx] = nest_level[level_idx]
                    pass
                nid_pattern = (
                    nidNiter.split("#", 1)[0]
                    + "".join(map(lambda x: "#" + str(x), nid_matches[:-1]))
                    + "#"
                )
                nids = [
                    item for item in AllChildNodeNames if item.startswith(nid_pattern)
                ]
                sort_nids = sorted(nids, key=lambda x: int(x.replace(nid_pattern, "")))
                arraydata = []
                for nid in sort_nids:
                    node = (await ALL_TASKS_MGR.get(self.tid)).getNode(nid)
                    ndata = node.data.getContent(contentname).byId[ctid]
                    arraydata.append(ndata.data)
                node_results.byId[rid].data = arraydata
                returnUpdateData.append(
                    FANodeUpdateData(
                        type=FANodeUpdateType.overwrite,
                        path=["results", "byId", rid, "data"],
                        data=arraydata,
                    )
                )
                pass

            self.setAllOutputStatus(FANodeStatus.Success)
            return returnUpdateData
        else:
            raise Exception("迭代节点执行失败")
        pass
