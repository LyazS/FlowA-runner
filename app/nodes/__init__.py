from .tasknode import FATaskNode

from .FANode_attached_node_callbackFunc import FANode_attached_node_callbackFunc
from .FANode_attached_node_callbackUser import FANode_attached_node_callbackUser
from .FANode_attached_node_input import FANode_attached_node_input
from .FANode_attached_node_output import FANode_attached_node_output
from .FANode_attached_node_next import FANode_attached_node_next

from .FANode_code_interpreter import FANode_code_interpreter
from .FANode_cond_branch import FANode_cond_branch
from .FANode_iter_run import FANode_iter_run
from .FANode_LLM_inference import FANode_LLM_inference
from .FANode_http_requests import FANode_http_requests
from .FANode_text_input import FANode_text_input
from .FANode_branch_aggregate import FANode_branch_aggregate
from .FANode_retry_run import FANode_retry_run
from .FANode_jinja2_template import FANode_jinja2_template

FANODECOLLECTION = {
    "attached_node_callbackFunc": FANode_attached_node_callbackFunc,
    "attached_node_callbackUser": FANode_attached_node_callbackUser,
    "attached_node_input": FANode_attached_node_input,
    "attached_node_output": FANode_attached_node_output,
    "attached_node_next": FANode_attached_node_next,
    "code_interpreter": FANode_code_interpreter,
    "cond_branch": FANode_cond_branch,
    "iter_run": FANode_iter_run,
    "LLM_inference": FANode_LLM_inference,
    "http_requests": FANode_http_requests,
    "text_input": FANode_text_input,
    "branch_aggregate": FANode_branch_aggregate,
    "jinja2_template": FANode_jinja2_template,
    "retry_run": FANode_retry_run,
}
