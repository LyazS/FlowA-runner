from typing import List, Optional, Any
from pydantic import BaseModel
from enum import Enum


class FANodeStatus(Enum):
    Default = "Default"
    Pending = "Pending"
    Running = "Running"
    Success = "Success"
    Canceled = "Canceled"
    Error = "Error"
    pass


class FARunnerStatus(Enum):
    Pending = "Pending"
    Running = "Running"
    Success = "Success"
    Canceled = "Canceled"
    Error = "Error"
    pass


class FANodeWaitType(Enum):
    AND = "AND"
    OR = "OR"
    pass


class FANodeValidateNeed(Enum):
    Self = "Self"
    Attach = "Attach"
    InputNodes = "InputNodes"
    InputNodesWVars = "InputNodesWVars"
    pass
