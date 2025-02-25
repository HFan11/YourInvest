import json
import re

from loguru import logger

from worksheets.environment import Answer, GenieType, GenieWorksheet, find_list_variable


def handle_genie_type(key, value, context, response_generator):
    schema = ""
    if isinstance(value, GenieType):
        return
    if key.startswith("__"):  # To prevent __answer_result from shown in the schema
        return
    if isinstance(value, Answer):
        if value.query.value is not None and response_generator:
            schema += (
                key
                + " = answer("
                + repr(value.nl_query)
                + ", sql="
                + repr(value.query.value)
                + ")\n"
            )
        else:
            schema += key + " = answer(" + repr(value.nl_query) + ")\n"

        if value.result:
            if hasattr(value.result, "value"):
                res = value.result.value
            else:
                res = value.result
            if isinstance(res, list):
                parent_var_name = None
                indices = []

                result_strings = []
                for val in res:
                    if isinstance(val, GenieType):
                        var_name, idx = find_list_variable(val, context)
                        if var_name is None and idx is None:
                            result_strings.append(val)
                        else:
                            if (
                                parent_var_name is not None
                                and parent_var_name != var_name
                            ):
                                logger.error(
                                    "Cannot handle multiple list variables in the same answer"
                                )
                            parent_var_name = var_name  # Ignoring any potential multiple list variables

                            indices.append(idx)
                    else:
                        result_strings.append(val)

                if parent_var_name:
                    indices_str = []
                    for idx in indices:
                        indices_str.append(f"{parent_var_name}[{idx}]")

                    result_strings = "[" + ", ".join(indices_str) + "]"

            else:
                result_strings = (
                    res.schema_without_type(context)
                    if isinstance(res, GenieWorksheet)
                    else res
                )
            schema += key + ".result = " + str(result_strings) + "\n"
        else:
            schema += key + ".result = None\n"
    elif isinstance(value, GenieWorksheet):
        if value.__class__.__name__ == "MoreFieldInfo":
            return
        schema += key + " = " + str(value.schema_without_type(context)) + "\n"
        if hasattr(value, "result"):
            if value.result:
                schema += key + ".result = " + str(value.result.value) + "\n"

    return schema


def get_context_schema(context, response_generator=False):
    schema = ""

    for key, value in context.context.items():
        if isinstance(value, list):
            bad_list = False
            for val in value:
                if not isinstance(val, GenieType):
                    bad_list = True
                    break

            if not bad_list:
                schema += key + " = " + str(value) + "\n"
        else:
            new_schema = handle_genie_type(key, value, context, response_generator)
            if new_schema:
                schema += new_schema

    return schema.replace("\\", "")


def get_agent_action_schemas(agent_acts, *args, **kwargs):
    agent_acts_schema = []
    if agent_acts:
        for act in agent_acts:
            agent_acts_schema.append(str(act))

    return agent_acts_schema


def prepare_context_input(bot, dlg_history, current_dlg_turn):
    if len(dlg_history):
        state_schema = get_context_schema(bot.context)
        agent_acts = json.dumps(
            get_agent_action_schemas(dlg_history[-1].system_action, bot.context),
            indent=2,
        )
        agent_utterance = dlg_history[-1].system_response
    else:
        state_schema = None
        agent_acts = None
        agent_utterance = None

    return state_schema, agent_acts, agent_utterance


def prepare_semantic_parser_input(bot, dlg_history, current_dlg_turn):
    state_schema, agent_acts, agent_utterance = prepare_context_input(
        bot, dlg_history, current_dlg_turn
    )

    available_worksheets = [
        ws.get_semantic_parser_schema() for ws in bot.genie_worksheets
    ]
    available_worksheets_text = "\n".join(available_worksheets)

    available_dbs = [db.get_semantic_parser_schema() for db in bot.genie_db_models]
    available_dbs_text = "\n".join(available_dbs)
    return (
        state_schema,
        agent_acts,
        agent_utterance,
        available_worksheets_text,
        available_dbs_text,
    )
