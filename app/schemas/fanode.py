from typing import List, Optional
from pydantic import BaseModel
from enum import Enum


class FANodeStatus(Enum):
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
