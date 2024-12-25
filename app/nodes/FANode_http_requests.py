from typing import List, Union, Dict, Optional, Any
import traceback
import asyncio
import aiohttp
import base64
import aiofiles
import ast
import re
import json
from loguru import logger
from urllib.parse import urlencode
from app.utils.tools import replace_vars
from app.schemas.fanode import FANodeStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import ValidationError
from .basenode import FABaseNode
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.vfnode_contentdata import (
    Single_ConditionDict,
    VarType,
    ConditionType,
    Single_VarInput,
    HttpMethod,
    HttpBodyType,
    HttpBodyModel,
    HttpConfigModel,
    HttpTimeoutModel,
)
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
)
from .basenode import FABaseNode
from app.services.messageMgr import ALL_MESSAGES_MGR


class FANode_http_requests(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        self.validateNeededs = [FANodeValidateNeed.Self]
        pass

    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        selfVars = validateVars[FANodeValidateNeed.Self]
        error_msgs = []
        try:
            node_payloads = self.data.getContent("payloads")
            D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
            D_CONFIG: VFNodeContentData = node_payloads.byId["D_CONFIG"]
            D_TIMEOUT: VFNodeContentData = node_payloads.byId["D_TIMEOUT"]

            for var_dict in D_VARSINPUT.data:
                var = Single_VarInput.model_validate(var_dict)
                if var.type == "ref" and var.value not in selfVars:
                    error_msgs.append(f"变量未定义{var.value}")
        except Exception as e:
            errmsg = traceback.format_exc()
            error_msgs.append(f"获取results内容失败:{errmsg}")
            logger.error(errmsg)
        finally:
            if len(error_msgs) > 0:
                return ValidationError(nid=self.id, errors=error_msgs)
            return None

    async def run(self) -> List[FANodeUpdateData]:
        try:
            node_payloads = self.data.getContent("payloads")
            node_results = self.data.getContent("results")
            D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
            D_CONFIG: VFNodeContentData = node_payloads.byId["D_CONFIG"]
            D_TIMEOUT: VFNodeContentData = node_payloads.byId["D_TIMEOUT"]

            InputArgs = {}
            for var_dict in D_VARSINPUT.data:
                var = Single_VarInput.model_validate(var_dict)
                InputArgs[var.key] = await self.getVar(var)

            d_config = HttpConfigModel.model_validate(D_CONFIG.data)
            d_timeout = HttpTimeoutModel.model_validate(D_TIMEOUT.data)
            # 准备url
            url = replace_vars(d_config.url, InputArgs)
            # 准备headers
            headers = {
                replace_vars(item.key, InputArgs): replace_vars(item.value, InputArgs)
                for item in d_config.headers
            }
            # 准备cookies
            cookies = {
                replace_vars(item.key, InputArgs): replace_vars(item.value, InputArgs)
                for item in d_config.cookies
            }
            # 准备请求体
            data = None
            if d_config.body.type == HttpBodyType.json:
                data = json.loads(replace_vars(d_config.body.content1, InputArgs))

            elif d_config.body.type == HttpBodyType.text:
                data = replace_vars(d_config.body.content1, InputArgs)

            elif d_config.body.type == HttpBodyType.x_www_form_urlencoded:
                data = {
                    replace_vars(item.key, InputArgs): replace_vars(
                        item.value, InputArgs
                    )
                    for item in d_config.body.content2
                }
                data = urlencode(data)

            elif d_config.body.type == HttpBodyType.form_data:
                data = aiohttp.FormData()
                for item in d_config.body.content3:
                    if item.type == VarType.File:
                        # async with aiofiles.open(item["value"], "rb") as f:
                        #     data.add_field(
                        #         item["key"],
                        #         await f.read(),
                        #         filename=item["value"].split("/")[-1],
                        #         content_type="image/jpeg",
                        #     )
                        # 这里暂不支持文件上传，后续考虑添加文件读取节点再来实现
                        pass
                    else:
                        data.add_field(
                            replace_vars(item.key, InputArgs),
                            replace_vars(item.value, InputArgs),
                        )
            # 准备超时
            timeout = aiohttp.ClientTimeout(
                connect=d_timeout.connect,
                sock_read=d_timeout.read,
                sock_connect=d_timeout.connect,
                total=d_timeout.read + d_timeout.connect,  # 总超时时间
            )
            # 发送请求
            async with aiohttp.ClientSession(
                cookies=cookies, timeout=timeout
            ) as session:
                async with session.request(
                    d_config.method.value,
                    url,
                    headers=headers,
                    data=data,
                ) as response:
                    response_data = response
                    content_type = response.headers.get("Content-Type", "").lower()

                    if content_type.startswith("text/") or content_type in [
                        "application/json",
                        "application/xml",
                    ]:
                        # 处理文本数据
                        response_data = await response.text()
                    else:
                        # 处理二进制数据
                        response_data = await response.read()
                        # 转换为base64编码
                        binary_data = base64.b64encode(response_data)
                        response_data = binary_data.decode()
                    node_results.byId["DR_STATUS"] = response.status
                    node_results.byId["DR_HEADER"] = [
                        (k, v) for k, v in response.headers.items()
                    ]
                    node_results.byId["DR_COOKIE"] = [
                        (k, v) for k, v in response.cookies.items()
                    ]
                    node_results.byId["DR_RESPONSE"] = response_data

                    return [
                        FANodeUpdateData(
                            type=FANodeUpdateType.overwrite,
                            path=["results", "byId", "DR_STATUS", "data"],
                            data=response.status,
                        ),
                        FANodeUpdateData(
                            type=FANodeUpdateType.overwrite,
                            path=["results", "byId", "DR_HEADER", "data"],
                            data=node_results.byId["DR_HEADER"],
                        ),
                        FANodeUpdateData(
                            type=FANodeUpdateType.overwrite,
                            path=["results", "byId", "DR_COOKIE", "data"],
                            data=node_results.byId["DR_COOKIE"],
                        ),
                        FANodeUpdateData(
                            type=FANodeUpdateType.overwrite,
                            path=["results", "byId", "DR_RESPONSE", "data"],
                            data=response_data,
                        ),
                    ]
        except Exception as e:
            errmsg = traceback.format_exc()
            raise Exception(f"节点运行失败：{errmsg}")
