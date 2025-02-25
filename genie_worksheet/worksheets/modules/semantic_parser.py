import datetime
import os
import re
from typing import List

from loguru import logger

from worksheets.annotation_utils import prepare_semantic_parser_input
from worksheets.environment import (
    Answer,
    GenieRuntime,
    count_number_of_vars,
    get_genie_fields_from_ws,
)
from worksheets.llm.basic import llm_generate
from worksheets.modules import CurrentDialogueTurn
from worksheets.modules.rewriter import rewrite_code_to_extract_funcs
from worksheets.utils import extract_code_block_from_output

current_dir = os.path.dirname(__file__)
# Think of the semantic parsing as three-address code generation
# from a high-level language (the natural language) to a low-level language (the code)
# Three address code has three operands
# the assignment instruction has atmost one operator on the right side
# the compiler must generate a temporary variable to hold the result of the instruction
# there can be fewer than three operands in the instruction


async def semantic_parsing(current_dlg_turn, dlg_history, bot):
    bot.context.reset_aget_acts()
    user_target, suql_target = await _nl_to_code(current_dlg_turn, dlg_history, bot)
    current_dlg_turn.user_target_sp = user_target
    current_dlg_turn.user_target_suql = "\n".join(suql_target)
    genie_user_target = _rewrite_code(user_target, bot)
    current_dlg_turn.user_target = genie_user_target


def _rewrite_code(user_target, bot):
    # Use LLM to extract the function calls to variables

    # Use the AST to extract the function calls to variables
    valid_worksheets = [func.__name__ for func in bot.genie_worksheets]
    valid_dbs = [func.__name__ for func in bot.genie_db_models]

    valid_worksheets.append("Answer")
    valid_worksheets.append("MoreFieldInfo")

    var_counter = count_number_of_vars(bot.context.context)

    try:
        rewritten_user_target = rewrite_code_to_extract_funcs(
            user_target,
            valid_worksheets,
            valid_dbs,
            var_counter,
        )
    except SyntaxError as e:
        logger.info(f"SyntaxError: {e}")
        rewritten_user_target = None

    return rewritten_user_target


async def _nl_to_code(current_dlg_turn, dlg_history, bot, **kwargs):
    (
        state_schema,
        agent_acts,
        agent_utterance,
        available_worksheets_text,
        available_dbs_text,
    ) = prepare_semantic_parser_input(bot, dlg_history, current_dlg_turn)

    user_target = await user_utterance_to_user_target(
        bot,
        dlg_history,
        current_dlg_turn,
        state_schema,
        agent_acts,
        agent_utterance,
        available_worksheets_text,
        available_dbs_text,
    )

    # refined_user_target = refine_user_target(
    #     user_target,
    #     bot,
    #     dlg_history,
    #     state_schema,
    #     agent_acts,
    #     agent_utterance,
    #     current_dlg_turn.user_utterance,
    # )

    # user_target = refined_user_target

    # extract `answer("query")` where query is a string from user_target

    answer_queries, pattern_type = extract_answer(user_target)
    suql_queries = []
    for answer_query in answer_queries:
        from sql_metadata import Parser
        from suql.sql_free_text_support.execute_free_text_sql import (
            _check_required_params,
        )

        use_spinach = True if bot.name == "Course Enrollment Assistant" else False
        suql_query = await suql_sp(
            dlg_history, answer_query[1:-1], bot, spinach=use_spinach
        )

        if suql_query is None:
            logger.error(f"SUQL parsing failed for {answer_query}")
            suql_query = ""

        suql_query = suql_query.replace("\*", "*")

        if "SELECT" in suql_query:
            tables = Parser(suql_query).tables

            table_req_params = {}
            for table in tables:
                req_params, table_class = get_required_params_in_table(table, bot)
                table_req_params[table] = req_params

            req_filled, unfilled_params = _check_required_params(
                suql_query, table_req_params
            )
        else:
            tables = []
            unfilled_params = {}

        suql_queries.append(suql_query)

        # hardcoded for resturants; we can use the primary key here later.
        if len(unfilled_params) > 0:
            if "restaurants" in tables:
                _, id_filled = _check_required_params(
                    suql_query, {"restaurants": ["id"]}
                )
                if id_filled != {}:
                    _, id_filled = _check_required_params(
                        suql_query, {"restaurants": ["_id"]}
                    )
                    if id_filled == {}:
                        unfilled_params = {}

        if pattern_type == "func":
            answer_str = f"Answer({repr(suql_query)}, {unfilled_params}, {tables}, {repr(answer_query[1:-1])})"

            user_target = user_target.replace(f"answer({answer_query})", answer_str)
        else:
            # We need Answer(query, unfilled_params, tables, query_str)
            answer_var = re.search(r"answer_(\d+)", user_target).group(0)
            answer_str = f"{answer_var}.result = []\n"
            answer_str = f"{answer_var}.update(query={repr(suql_query)}, unfilled_params={unfilled_params}, tables={tables}, query_str={repr(answer_query[1:-1])})"
            user_target = user_target.replace(
                f"{answer_var}.query = {answer_query}", answer_str
            )
    return user_target.strip(), suql_queries


def get_required_params_in_table(table, bot: GenieRuntime):
    required_params = []
    table_class = None
    for db in bot.genie_db_models:
        if db.__name__ == table:
            table_class = db
            for field in get_genie_fields_from_ws(db):
                if not field.optional:
                    required_params.append(field.name)

    return required_params, table_class


def extract_answer(text):
    pattern_type = "func"
    # Regex pattern to find answer() with a string argument inside, handling both single and double quotes
    pattern = r'answer\((?:("[^"]*")|(\'[^\']*\'))\)'

    matches = re.findall(pattern, text)

    # Each match is a tuple with the string in either the first or the second position, depending on the quote type
    # We extract non-None values from these tuples and return them as a list
    queries = [match[0] or match[1] for match in matches]
    if len(queries) == 0:
        pattern = r'answer_\d+\.query = (?:("[^"]*")|(\'[^\']*\'))'
        matches = re.findall(pattern, text)
        queries = [match[0] or match[1] for match in matches]
        pattern_type = "attr"

    return queries, pattern_type


async def user_utterance_to_user_target(
    bot: GenieRuntime,
    dlg_history: list[CurrentDialogueTurn],
    current_dlg_turn: CurrentDialogueTurn,
    state_schema: str | None,
    agent_acts: str | None,
    agent_utterance: str | None,
    available_worksheets_text: str,
    available_dbs_text: str,
):
    if state_schema == "" or state_schema is None:
        prompt_file = "semantic_parser_stateless.prompt"
    else:
        prompt_file = "semantic_parser_stateful.prompt"

    prompt_inputs = {
        "user_utterance": current_dlg_turn.user_utterance,
        "dlg_history": dlg_history,
        "bot": bot,
        "available_worksheets_text": available_worksheets_text,
        "available_dbs_text": available_dbs_text,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "day": datetime.datetime.now().strftime("%A"),
        "date_tmr": (datetime.datetime.now() + datetime.timedelta(days=1)).strftime(
            "%Y-%m-%d"
        ),
        "yesterday_date": (
            datetime.datetime.now() - datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d"),
        "state": state_schema,
        "agent_actions": agent_acts if agent_acts else "None",
        "agent_utterance": agent_utterance,
        "description": bot.description,
        "apis": bot.genie_worksheets
    }

    parsed_output = await llm_generate(
        prompt_file,
        prompt_inputs=prompt_inputs,
        prompt_dir=bot.prompt_dir,
        model_name="azure/gpt-4o",
        temperature=0.0,
    )

    user_target = extract_code_block_from_output(parsed_output, lang="python")

    return user_target


def refine_user_target(
    user_target,
    bot,
    dlg_history,
    state_schema,
    agent_acts,
    agent_utterance,
    user_utterance,
):
    prompt_file = "semantic_parser_refine.prompt"

    prompt_inputs = {
        "user_target": user_target,
        "dlg_history": dlg_history,
        "bot": bot,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "day": datetime.datetime.now().strftime("%A"),
        "date_tmr": (datetime.datetime.now() + datetime.timedelta(days=1)).strftime(
            "%Y-%m-%d"
        ),
        "yesterday_date": (
            datetime.datetime.now() - datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d"),
        "state": state_schema,
        "agent_actions": agent_acts if agent_acts else "None",
        "agent_utterance": agent_utterance,
        "description": bot.description,
        "user_utterance": user_utterance,
    }

    parsed_output = llm_generate(
        prompt_file,
        prompt_inputs=prompt_inputs,
        prompt_dir=bot.prompt_dir,
        model_name="azure/gpt-4o-mini",
        temperature=0.0,
    )

    refined_user_target = extract_code_block_from_output(parsed_output, lang="python")

    return refined_user_target


async def suql_sp(
    dlg_history: List[CurrentDialogueTurn],
    query: str,
    bot: GenieRuntime,
    db_results: List[str] | None = None,
    spinach: bool = False,
):
    """
    A SUQL conversational semantic parser, with a pre-set prompt file.
    The function convets the List[CurrentDialogueTurn] to the expected format
    in SUQL (suql.agent.DialogueTurn) and calls the prompt file.

    # Parameters:

    `dlg_history` (List[CurrentDialogueTurn]): a list of past dialog turns.

    `query` (str): the current query to be parsed.

    # Returns:

    `parsed_output` (str): a parsed SUQL output
    """

    if spinach:
        return await spinach_sp(dlg_history, query, bot, db_results)
    else:
        from suql.agent import DialogueTurn

        suql_dlg_history = []
        for i, turn in enumerate(dlg_history):
            user_target = turn.user_target_suql
            agent_utterance = turn.system_response
            user_utterance = turn.user_utterance

            if db_results is None:
                db_result = [
                    obj.result
                    for obj in turn.context.context.values()
                    if isinstance(obj, Answer)
                    and obj.query.value == turn.user_target_suql
                ]
            else:
                db_result = db_results[i]

            suql_dlg_history.append(
                DialogueTurn(
                    user_utterance=user_utterance,
                    db_results=db_result,
                    user_target=user_target,
                    agent_utterance=agent_utterance,
                )
            )

        if bot.suql_prompt_selector:
            prompt_file = await bot.suql_prompt_selector(query)
        else:
            prompt_file = "suql_parser.prompt"

        parsed_output = await llm_generate(
            prompt_file,
            prompt_inputs={
                "dlg": suql_dlg_history,
                "query": query,
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "day": datetime.datetime.now().strftime("%A"),
                "day_tmr": (
                    datetime.datetime.now() + datetime.timedelta(days=1)
                ).strftime("%A"),
            },
            prompt_dir=bot.prompt_dir,
            model_name="azure/gpt-4o",
            temperature=0.0,
        )

        return extract_code_block_from_output(parsed_output, lang="sql")


async def spinach_sp(
    dlg_history: List[CurrentDialogueTurn],
    query: str,
    bot: GenieRuntime,
    db_results: List[str] | None = None,
):
    from suql.agent import DialogueTurn

    from knowledge_agent.agents.course_assistant.main import CourseAssistantAgent

    suql_dlg_history = []
    for i, turn in enumerate(dlg_history):
        user_target = turn.user_target_suql
        agent_utterance = turn.system_response
        user_utterance = turn.user_utterance

        if db_results is None:
            db_result = [
                obj.result
                for obj in turn.context.context.values()
                if isinstance(obj, Answer) and obj.query.value == turn.user_target_suql
            ]
        else:
            db_result = db_results[i]

        suql_dlg_history.append(
            DialogueTurn(
                user_utterance=user_utterance,
                db_results=db_result,
                user_target=user_target,
                agent_utterance=agent_utterance,
            )
        )

    agent = CourseAssistantAgent(engine="gpt-4o")
    agent.initialize(
        examples_file=os.path.join(
            current_dir,
            "..",
            "..",
            "knowledge_agent",
            "agents",
            "course_assistant",
            "examples.txt",
        ),
        instructions_file=os.path.join(
            current_dir,
            "..",
            "..",
            "knowledge_agent",
            "agents",
            "course_assistant",
            "instructions.txt",
        ),
        tables_schema_file=os.path.join(
            current_dir,
            "..",
            "..",
            "knowledge_agent",
            "agents",
            "course_assistant",
            "table_schema.txt",
        ),
    )
    agent.conversation_history = suql_dlg_history

    output = await agent.anext_turn(query)

    # TODO: KeyError: 'final_sql'
    # happens when the action_counter limit is met without a final SQL being generated
    try:
        final_output = output[0]["final_sql"].sql
    except Exception as e:
        final_output = None
    return final_output
