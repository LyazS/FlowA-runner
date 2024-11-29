from pydantic import BaseModel
from typing import List, Dict, Union, Optional
from enum import Enum


class BaseContentDataType(Enum):
    String = "String"  # str
    Integer = "Integer"  # int
    Number = "Number"  # float
    Boolean = "Boolean"  # bool
    Object = "Object"  # dict


class FileContentDataType(Enum):
    # File = "File"
    Image = "Image"
    Docx = "Docx"
    PPT = "PPT"
    Txt = "Txt"
    Excel = "Excel"
    Audio = "Audio"
    Zip = "Zip"
    Video = "Video"
    PDF = "PDF"
    pass


class CodeContentDataType(Enum):
    Python = "Python"
    JavaScript = "JavaScript"
    pass


class OtherContentDataType(Enum):
    CodeInput = "CodeInput"
    LLMInput = "LLMInput"
    ConditionDict = "ConditionDict"
    Prompts = "Prompts"
    IterIndex = "IterIndex"
    pass


class Single_CodeInput(BaseModel):
    key: str
    refdata: str
    pass


class VarType(Enum):
    ref = "ref"
    value = "value"
    pass


class Single_LLMInput(BaseModel):
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
    compareType: VarType
    value: str
    pass


class Single_ConditionDict(BaseModel):
    outputKey: str
    condType: ConditionType
    conditions: List[Single_Condition]
    pass

# ======= 让AI根据上边的内容自动生成就行了，不用手写schema ======
class VFNodeContentDataType(Enum):
    # BaseContentDataType
    String = "String"  # str
    Integer = "Integer"  # int
    Number = "Number"  # float
    Boolean = "Boolean"  # bool
    Object = "Object"  # dict
    # Array BaseContentDataType
    ArrayString = "ArrayString"
    ArrayInteger = "ArrayInteger"
    ArrayNumber = "ArrayNumber"
    ArrayBoolean = "ArrayBoolean"
    ArrayObject = "ArrayObject"
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
    # Array FileContentDataType
    ArrayImage = "ArrayImage"
    ArrayDocx = "ArrayDocx"
    ArrayPPT = "ArrayPPT"
    ArrayTxt = "ArrayTxt"
    ArrayExcel = "ArrayExcel"
    ArrayAudio = "ArrayAudio"
    ArrayZip = "ArrayZip"
    ArrayVideo = "ArrayVideo"
    ArrayPDF = "ArrayPDF"
    # OtherContentDataType
    CodeInput = "CodeInput"
    LLMInput = "LLMInput"
    ConditionDict = "ConditionDict"
    Prompts = "Prompts"
    IterIndex = "IterIndex"
    pass


VFNodeContentDataSchema = Optional[
    Union[
        str,
        int,
        float,
        bool,
        dict,
        List[Single_CodeInput],
        List[Single_LLMInput],
        Single_ConditionDict,
        List[Single_Prompt],
        List[str],  # 对于文件类型
    ]
]
