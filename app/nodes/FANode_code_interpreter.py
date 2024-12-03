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
from enum import Enum
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.vfnode_contentdata import Single_CodeInput
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
)
from app.utils.tools import read_yaml
from .basenode import FABaseNode
from app.services.messageMgr import ALL_MESSAGES_MGR


class EvalType(str, Enum):
    Python = "Python"
    SnekBox = "SnekBox"
    pass


class CodeOutput(BaseModel):
    success: bool
    output: Union[Dict, str] = None
    error: str = None
    pass


NodeConfig = read_yaml(
    os.path.join(
        os.path.dirname(__file__),
        "configs/FANode_code_interpreter.yaml",
    )
)

CODE_TEMPLATE_FUNCTION = NodeConfig["codetemplate_func"]
CODE_TEMPLATE_INPUT = NodeConfig["codetemplate_input"]
CODE_TEMPLATE_OUTPUT_RE = NodeConfig["codetemplate_output_re"]
CODE_TEMPLATE = NodeConfig["codetemplate"]

EVALTYPE = EvalType(NodeConfig["evaltype"])
SNEKBOXURL = NodeConfig.get("snekboxUrl", "")


async def SimplePythonRun(code, evaltype: EvalType, snekboxUrl: str = ""):
    if evaltype == EvalType.Python:
        python_executable = sys.executable

        # Use asyncio.create_subprocess_exec for async subprocess handling
        process = await asyncio.create_subprocess_exec(
            python_executable,
            "-Xfrozen_modules=off",
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for the process to complete and capture output
        stdout_b, stderr_b = await process.communicate()
        stdout = stdout_b.decode("utf-8").replace("\r", "")
        stderr = stderr_b.decode("utf-8").replace("\r", "")
        if len(stdout) <= 0:
            raise Exception("代码格式问题:\n", stderr)

        output_result = re.findall(CODE_TEMPLATE_OUTPUT_RE, stdout, re.S)

        if len(output_result) > 0:
            output_type, res = output_result[-1].strip().split("\n", 1)
            if "@CODEOUTPUT-BASE64" in output_type:
                json_string = base64.b64decode(res).decode("utf-8")
                res_json = json.loads(json_string)
                return CodeOutput(success=True, output=res_json)
            elif "@CODEOUTPUT-ERROR" in output_type:
                return CodeOutput(success=False, error=res)
            else:
                return CodeOutput(success=False, error="代码执行失败，请检查代码输出")

    elif evaltype == EvalType.SnekBox:
        pass
    else:
        raise Exception(f"不支持的执行类型{evaltype}")


class FANode_code_interpreter(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        pass

    def validateContent(self, selfVars: List[str]) -> List[str]:
        error_msgs = []
        try:
            # 首先要检查输入
            # 收集输出名字
            # 然后检查代码需求的输入是否在输入data里边
            # 然后检查输出data是否在输出data里边
            CodeInputArgs = set()
            CodeOutputArgs = []
            node_payloads = self.data.getContent("payloads")
            node_results = self.data.getContent("results")
            for pid in node_payloads.order:
                item: VFNodeContentData = node_payloads.byId[pid]
                if item.type == VFNodeContentDataType.CodeInput:
                    idata: List[Single_CodeInput] = item.data
                    for var in idata:
                        if var.refdata not in selfVars:
                            error_msgs.append(f"变量未定义{var.refdata}")
                        else:
                            CodeInputArgs.add(var.key)
            for pid in node_results.order:
                item: VFNodeContentData = node_results.byId[pid]
                CodeOutputArgs.append(item.key)
                pass
            for pid in node_payloads.order:
                item: VFNodeContentData = node_payloads.byId[pid]
                if item.type == VFNodeContentDataType.CodePython:
                    if not isinstance(item.data, str):
                        raise Exception(f"Python代码格式错误")
                    try:
                        tree = ast.parse(item.data)
                        hasMain = False
                        for node in ast.walk(tree):
                            if (
                                isinstance(node, ast.FunctionDef)
                                and node.name == "main"
                            ):
                                hasMain = True
                                # 检查输入名字是否对上
                                input_params = [arg.arg for arg in node.args.args]
                                for in_arg in input_params:
                                    if in_arg not in CodeInputArgs:
                                        raise Exception(f"缺少输入参数【{in_arg}】")
                                    pass
                                # 检查输出名字是否对上
                                return_statements = [
                                    n
                                    for n in ast.walk(node)
                                    if isinstance(n, ast.Return)
                                ]
                                for return_node in return_statements:
                                    if isinstance(return_node.value, ast.Dict):
                                        outputs = set(
                                            [key.s for key in return_node.value.keys]
                                        )
                                        for out_arg in CodeOutputArgs:
                                            if out_arg not in outputs:
                                                raise Exception(
                                                    f"返回值缺少输出参数【{out_arg}】"
                                                )
                                            pass
                                    else:
                                        raise Exception(f"main函数返回值必须为字典")
                                    pass
                                break
                        if not hasMain:
                            raise Exception(f"未找到main函数")
                    except SyntaxError:
                        error_msgs.append(f"Python代码格式错误")
                    except Exception as e:
                        error_msgs.append(str(e))
                elif item.type == VFNodeContentDataType.CodeJavaScript:
                    if not isinstance(item.data, str):
                        error_msgs.append(f"JavaScript代码格式错误")
                    pass
            return error_msgs
        except Exception as e:
            errmsg = traceback.format_exc()
            error_msgs.append(f"获取内容失败{str(errmsg)}")
            return error_msgs

    def validate(self, validateVars: Dict[str, List[str]]) -> Optional[ValidationError]:
        selfVars = validateVars["self"]
        errors_payloads = self.validateContent(selfVars)
        if len(errors_payloads) > 0:
            return ValidationError(nid=self.id, errors=errors_payloads)
        return None

    async def run(self) -> List[FANodeUpdateData]:
        CodeInputArgs = {}
        node_payloads = self.data.getContent("payloads")
        node_results = self.data.getContent("results")
        CodeStr: str = ""
        for pid in node_payloads.order:
            item: VFNodeContentData = node_payloads.byId[pid]
            if item.type == VFNodeContentDataType.CodeInput:
                idata: List[Single_CodeInput] = item.data
                for var in idata:
                    CodeInputArgs[var.key] = await self.getRefData(var.refdata)
            elif item.type == VFNodeContentDataType.CodePython:
                CodeStr = item.data
        # 开始执行代码
        code_in_args = json.dumps(CodeInputArgs, ensure_ascii=False)
        code_in_args_b64 = base64.b64encode(code_in_args.encode("utf-8")).decode(
            "utf-8"
        )
        code_run: str = copy.deepcopy(CODE_TEMPLATE)
        code_run = code_run.replace(CODE_TEMPLATE_FUNCTION, CodeStr).replace(
            CODE_TEMPLATE_INPUT, code_in_args_b64
        )
        # 需要返回输出结果
        codeResult = await SimplePythonRun(code_run, EVALTYPE, SNEKBOXURL)
        if codeResult.success:
            returnUpdateData = []
            for rid in node_results.order:
                item: VFNodeContentData = node_results.byId[rid]
                if item.key not in codeResult.output:
                    raise Exception(f"实际返回结果缺少输出参数【{rid}】")
                returnUpdateData.append(
                    FANodeUpdateData(
                        type=FANodeUpdateType.overwrite,
                        path=["results", "byId", rid, "data"],
                        data=codeResult.output[item.key],
                    )
                )
                # 更新内部数据
                self.data.results.byId[rid].data = codeResult.output[item.key]
            # 返回之前先设置好输出handle状态
            self.setAllOutputStatus(FANodeStatus.Success)
            return returnUpdateData
        else:
            raise Exception(f"执行代码失败：{codeResult.error}")

    def getCurData(self) -> Optional[List[FANodeUpdateData]]:
        return [
            FANodeUpdateData(
                type=FANodeUpdateType.overwrite,
                path=["state", "status"],
                data=self.runStatus,
            )
        ] + [
            FANodeUpdateData(
                type=FANodeUpdateType.overwrite,
                path=["results", "byId", rid, "data"],
                data=self.data.results.byId[rid].data,
            )
            for rid in self.data.results.order
        ]
