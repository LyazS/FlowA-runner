from pydantic import BaseModel
from typing import List, Dict, Union, Optional
from enum import Enum


class BaseContentDataType(Enum):
    String = "String"  # str
    Integer = "Integer"  # int
    Number = "Number"  # float
    Boolean = "Boolean"  # bool
    Object = "Object"  # dict
    Prompt = "Prompt"  #


class FileContentDataType(Enum):
    File = "File"
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


class NonArrayContentDataType(Enum):
    CodeInput = "CodeInput"
    CodePython = "CodePython"
    CodeJavaScript = "CodeJavaScript"
    ConditionDict = "ConditionDict"
    IterIndex = "IterIndex"
    LLMInput = "LLMInput"


def generate_array_enum(prefix, base_type_enum):
    """Generate array enums based on base types."""
    return {prefix + member.name: prefix + member.value for member in base_type_enum}


VFNodeContentDataType: Enum = Enum(
    "VFNodeContentDataType",
    {
        **{member.name: member.value for member in BaseContentDataType},
        **{member.name: member.value for member in NonArrayContentDataType},
        **{member.name: member.value for member in FileContentDataType},
        **generate_array_enum("Array", BaseContentDataType),
    },
)


VFNodeContentData_String = str
VFNodeContentData_Integer = int
VFNodeContentData_Float = float
VFNodeContentData_Boolean = bool
VFNodeContentData_Object = dict

VFNodeContentData_File = str
VFNodeContentData_Image = str
VFNodeContentData_Docx = str
VFNodeContentData_PPT = str
VFNodeContentData_Txt = str
VFNodeContentData_Excel = str
VFNodeContentData_Audio = str
VFNodeContentData_Zip = str
VFNodeContentData_Video = str
VFNodeContentData_PDF = str


class Single_CodeInput(BaseModel):
    key: str
    refdata: str
    pass


VFNodeContentData_CodeInput = List[Single_CodeInput]


class VarType(Enum):
    ref = "ref"
    value = "value"
    pass


class Single_LLMInput(BaseModel):
    key: str
    type: VarType
    value: str
    pass


VFNodeContentData_LLMInput = List[Single_LLMInput]


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


VFNodeContentDataSchema = Union[None]
