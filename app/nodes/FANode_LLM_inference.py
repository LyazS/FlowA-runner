from typing import List, Union, Dict, Any, Optional, cast
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
from loguru import logger
import openai
from openai import AsyncOpenAI, NotGiven
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from enum import Enum
from decimal import Decimal
from app.utils.tools import replace_vars
from app.schemas.fanode import FANodeStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import (
    VFNodeInfo,
    VFNodeContentData,
    VFNodeContentDataType,
)
from app.schemas.vfnode_contentdata import (
    Single_VarInput,
    VarType,
    LLMModelConfig,
    Single_LLMModelConfig_type,
    Single_LLMModelConfig,
    Single_Prompt,
)
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
AsyncOAIClient = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)


class FANode_LLM_inference(FATaskNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        self.validateNeededs = [FANodeValidateNeed.Self]
        pass

    def validateConfigVar(self, s_config: Single_LLMModelConfig, selfVars):
        if s_config.type == Single_LLMModelConfig_type.REF:
            if s_config.value not in selfVars:
                return False
        return True

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
            if not self.validateConfigVar(model_cfg.model, selfVars):
                error_msgs.append(f"模型配置变量{model_cfg.model.value}未定义")
            if not self.validateConfigVar(model_cfg.max_tokens, selfVars):
                error_msgs.append(f"模型配置变量{model_cfg.max_tokens.value}未定义")
            if not self.validateConfigVar(model_cfg.temperature, selfVars):
                error_msgs.append(f"模型配置变量{model_cfg.temperature.value}未定义")
            if not self.validateConfigVar(model_cfg.top_p, selfVars):
                error_msgs.append(f"模型配置变量{model_cfg.top_p.value}未定义")
            if not self.validateConfigVar(model_cfg.frequency_penalty, selfVars):
                error_msgs.append(
                    f"模型配置变量{model_cfg.frequency_penalty.value}未定义"
                )
            if not self.validateConfigVar(model_cfg.response_format, selfVars):
                error_msgs.append(
                    f"模型配置变量{model_cfg.response_format.value}未定义"
                )

        except Exception as e:
            pass
        if len(error_msgs) > 0:
            return ValidationError(nid=self.id, errors=error_msgs)
        return None

    async def getConfigVar(self, s_config: Single_LLMModelConfig):
        if s_config.type == Single_LLMModelConfig_type.REF:
            return await self.getVar(
                Single_VarInput(
                    key="",
                    type=VarType.ref,
                    value=s_config.value,
                )
            )
            pass
        elif s_config.type == Single_LLMModelConfig_type.VALUE:
            return s_config.value
        elif s_config.type == Single_LLMModelConfig_type.NULL:
            return NotGiven
        return NotGiven

    async def run(self) -> List[FANodeUpdateData]:
        try:
            node_payloads = self.data.getContent("payloads")
            node_results = self.data.getContent("results")
            D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
            D_MODELCONFIG: VFNodeContentData = node_payloads.byId["D_MODELCONFIG"]
            D_PROMPTS: VFNodeContentData = node_payloads.byId["D_PROMPTS"]
            D_ANSWER: VFNodeContentData = node_results.byId["D_ANSWER"]
            D_MODEL: VFNodeContentData = node_results.byId["D_MODEL"]
            D_IN_TOKEN: VFNodeContentData = node_results.byId["D_IN_TOKEN"]
            D_OUT_TOKEN: VFNodeContentData = node_results.byId["D_OUT_TOKEN"]
            D_STOP_REASON: VFNodeContentData = node_results.byId["D_STOP_REASON"]
            InputArgs = {}
            for var_dict in D_VARSINPUT.data.value:
                var = Single_VarInput.model_validate(var_dict)
                InputArgs[var.key] = await self.getVar(var)
            model_cfg = LLMModelConfig.model_validate(D_MODELCONFIG.data.value)
            completions_params = {
                "model": await self.getConfigVar(model_cfg.model),
                "stream": model_cfg.stream,
                "max_tokens": await self.getConfigVar(model_cfg.max_tokens),
                "temperature": await self.getConfigVar(model_cfg.temperature),
                "top_p": await self.getConfigVar(model_cfg.top_p),
                # "top_k": await self.getConfigVar(model_cfg.top_k),
                "frequency_penalty": await self.getConfigVar(
                    model_cfg.frequency_penalty
                ),
            }
            if model_cfg.stream:
                completions_params["stream_options"] = {"include_usage": True}
                pass
            if await self.getConfigVar(model_cfg.response_format) == "json":
                completions_params["response_format"] = {"type": "json_object"}
            # messages
            messages = []
            for prompt in D_PROMPTS.data.value:
                prompt_obj = Single_Prompt.model_validate(prompt)
                prompt_obj.content = replace_vars(prompt_obj.content, InputArgs)
                messages.append(json.loads(prompt_obj.model_dump_json()))
                pass
            completions_params["messages"] = messages
            completions_params = {
                k: v for k, v in completions_params.items() if v is not NotGiven
            }
            chat_completion: ChatCompletion = await AsyncOAIClient.with_options(
                max_retries=10
            ).chat.completions.create(**completions_params)
            D_ANSWER.data.value = ""
            if model_cfg.stream:
                async for chunk in chat_completion:
                    chunk = cast(ChatCompletionChunk, chunk)
                    if len(chunk.choices) > 0:
                        content = chunk.choices[0].delta.content
                        D_ANSWER.data.value += content
                        D_STOP_REASON.data.value = chunk.choices[0].finish_reason
                        pass
                    if chunk.usage is not None:
                        D_IN_TOKEN.data.value = chunk.usage.prompt_tokens
                        D_OUT_TOKEN.data.value = chunk.usage.completion_tokens
                        pass
            else:
                D_ANSWER.data.value = chat_completion.choices[0].message.content
                D_IN_TOKEN.data.value = chat_completion.usage.prompt_tokens
                D_OUT_TOKEN.data.value = chat_completion.usage.completion_tokens
                D_STOP_REASON.data.value = chat_completion.choices[0].finish_reason
                pass
            D_MODEL.data.value = completions_params["model"]
            logger.info(
                f"补全Tokens：{D_IN_TOKEN.data.value} + {D_OUT_TOKEN.data.value}"
            )
            self.setAllOutputStatus(FANodeStatus.Success)
        except openai.APIConnectionError as e:
            logger.error("The server could not be reached")
            logger.error(e.__cause__)  # an underlying Exception, likely raised within httpx.
            errmsg = traceback.format_exc()
            raise Exception(f"LLM节点运行失败：{errmsg}")
        except openai.RateLimitError as e:
            logger.error("A 429 status code was received; we should back off a bit.")
            errmsg = traceback.format_exc()
            raise Exception(f"LLM节点运行失败：{errmsg}")
        except openai.APIStatusError as e:
            logger.error("Another non-200-range status code was received")
            logger.error(e.status_code)
            logger.error(e.response)
            errmsg = traceback.format_exc()
            raise Exception(f"LLM节点运行失败：{errmsg}")
        except Exception as e:
            errmsg = traceback.format_exc()
            raise Exception(f"LLM节点运行失败：{errmsg}")
        pass

    @staticmethod
    def getNodeConfig():
        return MODELS
