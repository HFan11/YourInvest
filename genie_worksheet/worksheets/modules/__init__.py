import datetime
import json
import os

from worksheets.annotation_utils import get_agent_action_schemas, get_context_schema
from worksheets.environment import GenieContext, GenieRuntime
from worksheets.modules.agent_policy import run_agent_policy
from worksheets.modules.dialogue import CurrentDialogueTurn
from worksheets.modules.response_generator import generate_response
from worksheets.modules.semantic_parser import semantic_parsing

current_dir = os.path.dirname(os.path.realpath(__file__))

__all__ = [
    "AgentPolicy",
    "CurrentDialogueTurn",
    "ResponseGenerator",
    "SemanticParser",
]


async def generate_next_turn(user_utterance: str, bot):
    current_dlg_turn = CurrentDialogueTurn()
    current_dlg_turn.user_utterance = user_utterance

    current_dlg_turn.context = GenieContext()
    current_dlg_turn.global_context = GenieContext()
    await semantic_parsing(current_dlg_turn, bot.dlg_history, bot)

    if current_dlg_turn.user_target is not None:
        run_agent_policy(current_dlg_turn, bot)

    await generate_response(current_dlg_turn, bot.dlg_history, bot)
    bot.dlg_history.append(current_dlg_turn)
