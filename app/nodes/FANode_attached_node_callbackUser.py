from typing import List, Union, Dict, TYPE_CHECKING
import asyncio
from app.schemas.fanode import FARunStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import ValidationError
from .tasknode import FATaskNode

if TYPE_CHECKING:
    from app.services.FARunner import FARunner


class FANode_attached_node_callbackUser(FATaskNode):
    def __init__(self, wid: str, nodeinfo: VFNodeInfo, runner: "FARunner"):
        super().__init__(wid, nodeinfo, runner)
        pass