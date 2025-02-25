from dataclasses import dataclass
from typing import List

from worksheets.environment import GenieContext


@dataclass
class CurrentDialogueTurn:
    user_utterance: str = None
    user_target_sp: str = None
    user_target: str = None
    system_response: str = None
    system_target: str = None
    system_action: List[str] = None
    user_is_asking_question: bool = False
    context: GenieContext = None
    global_context: GenieContext = None
    user_target_suql: str = None
