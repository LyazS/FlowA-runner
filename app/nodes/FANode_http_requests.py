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
from .tasknode import FATaskNode
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
from .tasknode import FATaskNode
from app.services.messageMgr import ALL_MESSAGES_MGR


class FANode_http_requests(FATaskNode):
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

            for var_dict in D_VARSINPUT.data.value:
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
            for var_dict in D_VARSINPUT.data.value:
                var = Single_VarInput.model_validate(var_dict)
                InputArgs[var.key] = await self.getVar(var)

            d_config = HttpConfigModel.model_validate(D_CONFIG.data.value)
            d_timeout = HttpTimeoutModel.model_validate(D_TIMEOUT.data.value)
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
            json_data = None
            if d_config.body.type == HttpBodyType.json:
                json_data = json.loads(replace_vars(d_config.body.content1, InputArgs))

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
                    json=json_data,
                ) as response:
                    response_data = response
                    content_type = response.headers.get("Content-Type", "").lower()

                    # 判断是否为文本数据
                    is_text_data = (
                        content_type.startswith("text/")
                        or "application/json" in content_type
                        or "application/xml" in content_type
                        or "application/javascript" in content_type
                        or "application/ld+json" in content_type
                        or "application/x-yaml" in content_type
                        or "application/xhtml+xml" in content_type
                        or "application/rss+xml" in content_type
                        or "application/atom+xml" in content_type
                    )

                    if is_text_data:
                        # 处理文本数据
                        charset = "utf-8"  # 默认使用 UTF-8
                        if "charset=" in content_type:
                            charset = content_type.split("charset=")[-1].strip()
                        response_data = await response.text(
                            encoding=charset, errors="replace"
                        )
                    else:
                        # 处理二进制数据
                        binary_data = await response.read()
                        base64_data = base64.b64encode(binary_data).decode("utf-8")
                        response_data = base64_data

                    node_results.byId["DR_STATUS"].data.value = response.status
                    node_results.byId["DR_HEADER"].data.value = [
                        (k, v) for k, v in response.headers.items()
                    ]
                    node_results.byId["DR_COOKIE"].data.value = [
                        (k, v) for k, v in response.cookies.items()
                    ]
                    node_results.byId["DR_CONTENTTYPE"].data.value = content_type
                    node_results.byId["DR_RESPONSE"].data.value = response_data

                    self.setAllOutputStatus(FANodeStatus.Success)
                    return [
                        FANodeUpdateData(
                            type=FANodeUpdateType.overwrite,
                            path=["results", "byId", "DR_STATUS", "data"],
                            data=response.status,
                        ),
                        FANodeUpdateData(
                            type=FANodeUpdateType.overwrite,
                            path=["results", "byId", "DR_HEADER", "data"],
                            data=node_results.byId["DR_HEADER"].data.value,
                        ),
                        FANodeUpdateData(
                            type=FANodeUpdateType.overwrite,
                            path=["results", "byId", "DR_COOKIE", "data"],
                            data=node_results.byId["DR_COOKIE"].data.value,
                        ),
                        FANodeUpdateData(
                            type=FANodeUpdateType.overwrite,
                            path=["results", "byId", "DR_CONTENTTYPE", "data"],
                            data=content_type,
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
