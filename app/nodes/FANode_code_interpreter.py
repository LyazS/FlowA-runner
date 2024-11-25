from typing import List, Union
import asyncio
import ast
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.farequest import ValidationError
from .basenode import FABaseNode


class FANode_code_interpreter(FABaseNode):
    def __init__(self, nodeinfo: VFNodeInfo):
        super().__init__(nodeinfo)
        pass

    async def run(self):

        pass

    def init(self, *args, **kwargs):
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
                    for var in item.data:
                        if var["refdata"] not in selfVars:
                            error_msgs.append(f"变量未定义{var['refdata']}")
                        else:
                            CodeInputArgs.add(var["key"])
            for pid in node_results.order:
                item: VFNodeContentData = node_results.byId[pid]
                CodeOutputArgs.append(item.key)
                pass
            for pid in node_payloads.order:
                item: VFNodeContentData = node_payloads.byId[pid]
                if item.type == VFNodeContentDataType.CodePython:
                    if isinstance(item.data, str):
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
                                            raise Exception(
                                                f"输入参数【{in_arg}】未定义"
                                            )
                                        pass
                                    # 检查输出名字是否对上
                                    return_statements = [
                                        n
                                        for n in ast.walk(node)
                                        if isinstance(n, ast.Return)
                                    ]
                                    if len(return_statements) != 1:
                                        raise Exception(f"main函数有且只能返回一个字典")
                                    return_node = return_statements[0]
                                    if isinstance(return_node.value, ast.Dict):
                                        outputs = set(
                                            [key.s for key in return_node.value.keys]
                                        )
                                        for out_arg in CodeOutputArgs:
                                            if out_arg not in outputs:
                                                raise Exception(
                                                    f"输出参数【{out_arg}】未定义"
                                                )
                                            pass
                                    else:
                                        raise Exception(f"main函数返回值必须为字典")
                                    break
                            if not hasMain:
                                raise Exception(f"未找到main函数")
                        except SyntaxError:
                            error_msgs.append(f"Python代码格式错误")
                        except Exception as e:
                            error_msgs.append(str(e))
                    else:
                        error_msgs.append(f"Python代码非str字符格式")
                elif item.type == VFNodeContentDataType.CodeJavaScript:
                    if not isinstance(item.data, str):
                        error_msgs.append(f"JavaScript代码格式错误")
                    pass
            return error_msgs
        except Exception as e:
            error_msgs.append(f"获取内容失败{str(e)}")
            return error_msgs

    def validate(self, selfVars: List[str]) -> ValidationError:
        errors_payloads = self.validateContent(selfVars)
        if len(errors_payloads) > 0:
            return ValidationError(nid=self.id, errors=errors_payloads)
        return None
