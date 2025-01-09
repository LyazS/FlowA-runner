from typing import List, Union, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
import os
import re
import ast
import copy
import sys
import json
import traceback
import base64
import subprocess
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from enum import Enum
from decimal import Decimal
from app.schemas.fanode import FANodeStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.vfnode_contentdata import Single_VarInput, VarType, LLMModelConfig
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
)
from app.utils.tools import read_yaml
from .tasknode import FATaskNode
from app.services.messageMgr import ALL_MESSAGES_MGR


class LLMModes(BaseModel):
    name: str
    max_input_tokens: Decimal
    max_output_tokens: Decimal
    prompt: Decimal
    complete: Decimal
    rate: Decimal
    capability: List[str]
    pass


NodeConfig = read_yaml(
    os.path.join(
        os.path.dirname(__file__),
        "configs/FANode_LLM_inference.yaml",
    )
)

BASE_URL = NodeConfig["base_url"]
API_KEY = NodeConfig["api_key"]
MODELS = {
    m["name"]: LLMModes(
        name=m["name"],
        max_input_tokens=Decimal(m["max_input_tokens"]),
        max_output_tokens=Decimal(m["max_output_tokens"]),
        prompt=Decimal(m["prompt"]),
        complete=Decimal(m["complete"]),
        rate=Decimal(m["rate"]),
        capability=m["capability"],
    )
    for m in NodeConfig["models"]
}


class FANode_LLM_inference(FATaskNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        self.validateNeededs = [FANodeValidateNeed.Self]
        pass

    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        error_msgs = []
        try:
            selfVars = validateVars[FANodeValidateNeed.Self]
            node_payloads = self.data.getContent("payloads")

            D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
            for var_dict in D_VARSINPUT.data.value:
                var = Single_VarInput.model_validate(var_dict)
                if var.type == VarType.ref and var.value not in selfVars:
                    error_msgs.append(f"变量未定义{var.value}")
            D_MODELCONFIG: VFNodeContentData = node_payloads.byId["D_MODELCONFIG"]
            model_cfg = LLMModelConfig.model_validate(D_MODELCONFIG.data.value)
            if model_cfg.model.value not in MODELS:
                error_msgs.append(f"模型{model_cfg.model.value}不在支持列表中")
        except Exception as e:
            pass
        if len(error_msgs) > 0:
            return ValidationError(nid=self.id, errors=error_msgs)
        return None

    @staticmethod
    def getNodeConfig():
        return MODELS
