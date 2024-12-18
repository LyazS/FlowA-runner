from pydantic import BaseModel
from typing import List, Dict, Union, Optional
from enum import Enum


class Single_CodeInput(BaseModel):
    key: str
    refdata: str
    pass


class VarType(Enum):
    ref = "ref"
    value = "value"
    pass


class Single_VarInput(BaseModel):
    key: str
    type: VarType
    value: str
    pass


class LLMRole(Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    pass


class Single_Prompt(BaseModel):
    role: LLMRole
    content: str
    pass


class ConditionType(Enum):
    AND = "AND"
    OR = "OR"
    pass


class Single_Condition(BaseModel):
    refdata: str
    operator: str
    comparetype: VarType
    value: str
    pass


class Single_ConditionDict(BaseModel):
    outputKey: str
    condType: ConditionType
    conditions: List[Single_Condition]
    pass


class Single_AggregateBranch(BaseModel):
    node: str
    refdata: str
    pass


# ======= 让AI根据上边的内容自动生成就行了，不用手写schema ======
class VFNodeContentDataType(Enum):
    # BaseContentDataType
    String = "String"  # str
    Integer = "Integer"  # int
    Number = "Number"  # float
    Boolean = "Boolean"  # bool
    List = "List"
    Dict = "Dict"  # dict
    # CodeContentDataType
    CodePython = "CodePython"
    CodeJavaScript = "CodeJavaScript"
    # FileContentDataType
    Image = "Image"
    Docx = "Docx"
    PPT = "PPT"
    Txt = "Txt"
    Excel = "Excel"
    Audio = "Audio"
    Zip = "Zip"
    Video = "Video"
    PDF = "PDF"
    # OtherContentDataType
    CodeInput = "CodeInput"
    VarsInput = "VarsInput"
    ConditionDict = "ConditionDict"
    Prompts = "Prompts"
    IterIndex = "IterIndex"
    IterItem = "IterItem"
    AggregateBranch = "AggregateBranch"
    pass


VFNodeContentDataSchema = Optional[
    Union[
        str,
        int,
        float,
        bool,
        dict,
        list,
        List[Single_CodeInput],
        List[Single_VarInput],
        Single_ConditionDict,
        List[Single_Prompt],
        List[str],  # 对于文件类型
    ]
]
