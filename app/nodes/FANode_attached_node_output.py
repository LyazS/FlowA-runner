from typing import List, Union, Dict, TYPE_CHECKING
import asyncio
from loguru import logger
from app.schemas.fanode import FARunStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import ValidationError, FANodeUpdateData
from .tasknode import FATaskNode

if TYPE_CHECKING:
    from app.services.FARunner import FARunner


class FANode_attached_node_output(FATaskNode):
    def __init__(self, wid: str, nodeinfo: VFNodeInfo, runner: "FARunner"):
        super().__init__(wid, nodeinfo, runner)
        pass

    async def run(self) -> List[FANodeUpdateData]:
        self.setAllOutputStatus(FARunStatus.Success)
        logger.info(f"Node {self.id} run success")
        pass
