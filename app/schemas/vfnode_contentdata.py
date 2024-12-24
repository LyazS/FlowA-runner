from pydantic import BaseModel
from typing import List, Dict, Union, Optional, Any
from enum import Enum


class VarType(Enum):
    ref = "ref"
    # value = "value"
    String = "String"
    Integer = "Integer"
    Number = "Number"
    Boolean = "Boolean"
    File = "File"
    pass


# class Single_CodeInput(BaseModel):
#     key: str
#     refdata: str
#     pass


class Single_KeyVar(BaseModel):
    key: str
    value: Any
    pass


class Single_VarInput(BaseModel):
    key: str
    type: VarType
    value: Any
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
    value: Any
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


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"
    PATCH = "PATCH"
    pass


class HttpBodyType(Enum):
    none = "none"
    json = "json"
    text = "text"
    x_www_form_urlencoded = "x_www_form_urlencoded"
    form_data = "form_data"
    pass


class HttpBodyModel(BaseModel):
    type: HttpBodyType
    content1: str
    content2: List[Single_KeyVar]
    content3: List[Single_VarInput]
    pass


class HttpConfigModel(BaseModel):
    method: HttpMethod
    url: str
    headers: List[Single_KeyVar]
    body: HttpBodyModel
    cookies: List[Single_KeyVar]
    pass


class HttpTimeoutModel(BaseModel):
    connect: int
    read: int
    write: int
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
    HttpRequestConfig = "HttpRequestConfig"
    HttpTimeoutConfig = "HttpTimeoutConfig"
    pass


VFNodeContentDataSchema = Optional[
    Union[
        str,
        int,
        float,
        bool,
        dict,
        list,
        # List[Single_CodeInput],
        List[Single_VarInput],
        Single_ConditionDict,
        List[Single_Prompt],
        List[str],  # 对于文件类型
        HttpConfigModel,
        HttpTimeoutModel,
    ]
]
