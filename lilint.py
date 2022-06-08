from astroid import nodes
from typing import TYPE_CHECKING

from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter


def _check_for_decorators(node: nodes.Call, msg: str):
    """Check if the node is called by a function that contains the decorators @utils.check_messages and
    @utils.only_required_for_messages
    :param node: Node to be checked. Should be a call to add_message(msg)
    :param msg: Argument used in the function call to add_message
    :return: True if the node is called by a function with the decorators mentioned before, otherwise False
    """
    parent = node.parent
    while parent is not None:
        if isinstance(parent, nodes.FunctionDef):
            decorators = parent.decorators
            for node in decorators.nodes:
                if (
                    isinstance(node, nodes.Call)
                    and node.func.attrname
                    in [
                        "only_required_for_messages",
                        "check_messages",
                    ]
                    and len(node.args) == 1
                    and isinstance(node.args[0], nodes.Const)
                    and node.args[0].value == msg
                ):
                    return True
        parent = parent.parent

    return False


def _check_call(node: nodes.Attribute, msg: str):
    if node.attrname == "add_message":
        arg = node.args[0]
        if isinstance(arg, nodes.Const) and arg == msg:
            return True

    return False


def _check_for_if(node: nodes.Call, msg: str):
    """Check if the node is contained within an if block that calls _is_message_enabled(msg)
    :param node: Node to be checked. Should be a call to add_message(msg)
    :param msg: Argument used in the function call to add_message(msg)
    :return: True if the node is inside and if block that calls _is_message_enabled(msg), otherwise False
    """
    parent = node.parent
    while parent is not None:
        if isinstance(parent, nodes.If):
            if isinstance(parent.test, nodes.Call) and isinstance(parent.test.func, nodes.Attribute):
                if _check_call(parent.test.func, msg):
                    return True
        parent = parent.parent

    return False


class ConditionalCheckerChecker(BaseChecker):
    """This is a simple checker made to fix the following issue:
    https://github.com/OCA/pylint-odoo/issues/372

    All calls to self.add_message must be inside an if condition that checks whether the message is enabled or not or
    inside a function call that uses the decorators @utils.check_messages and @utils.only_required_for_messages
    """

    name = "conditional-checker"
    msgs = {
        "E0427": (
            "Checker runs without validating it is enabled",
            "non-conditional-checker",
            "Checkers must run only if enabled",
        ),
        "W0427": (
            "Can't determine the type of message added",
            "cant-determine-message",
            "Message added is not a constant. Can't statically determine its type",
        ),
    }

    def visit_call(self, node: nodes.Call) -> None:
        func = node.func
        if isinstance(func, nodes.Attribute) and func.attrname == "add_message":
            msg = node.args[0]
            if isinstance(msg, nodes.Const):
                if _check_for_decorators(node, msg.value) or _check_for_if(node, msg.value):
                    return
                else:
                    self.add_message("non-conditional-checker", node=node)
            else:
                self.add_message("cant-determine-message", node=node)


def register(linter: "PyLinter") -> None:
    linter.register_checker(ConditionalCheckerChecker(linter))
