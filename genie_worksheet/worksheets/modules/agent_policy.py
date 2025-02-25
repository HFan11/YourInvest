import inspect
from typing import Dict, Union

from loguru import logger

from worksheets.environment import (
    AgentAct,
    Answer,
    AskAgentAct,
    AskForConfirmationAgentAct,
    GenieContext,
    GenieField,
    GenieRuntime,
    GenieType,
    GenieValue,
    GenieWorksheet,
    any_open_empty_ws,
    count_number_of_vars,
    eval_predicates,
    generate_var_name,
    genie_deepcopy,
    get_genie_fields_from_ws,
    get_variable_name,
    same_field,
    same_worksheet,
)


def diff_between_contexts(context1: Dict, context2: Dict):
    diff = {}
    for key, value in context2.items():
        if key not in context1:
            diff[key] = value
        else:
            if isinstance(value, GenieWorksheet) and isinstance(
                context1[key], GenieWorksheet
            ):
                if not same_worksheet(value, context1[key]):
                    diff[key] = value
            elif isinstance(value, GenieField) and isinstance(
                context1[key], GenieField
            ):
                if not same_field(value, context1[key]):
                    diff[key] = value
            elif value != context1[key]:
                diff[key] = value
    return diff


def discover_objects(
    local_context: GenieContext, answer_objects, ws_objects, type_objects, bot
):
    for obj_name, obj in local_context.context.items():
        if obj in answer_objects or obj in ws_objects or obj in type_objects:
            continue
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, GenieType):
                    if item not in type_objects:
                        type_objects.append(item)
                elif isinstance(item, Answer):
                    if item not in answer_objects:
                        answer_objects.append(item)
                else:
                    if item not in ws_objects:
                        ws_objects.append(item)
        if isinstance(obj, GenieWorksheet):
            if isinstance(obj, Answer):
                if obj not in answer_objects:
                    answer_objects.append(obj)
            elif isinstance(obj, GenieType):
                if obj not in type_objects:
                    type_objects.append(obj)
            else:
                if obj not in ws_objects:
                    ws_objects.append(obj)

    for type_object in type_objects:
        incoming_actions = perform_action_policy_for_ws(type_object, bot, local_context)
        bot.context.agent_acts.extend(incoming_actions)


def run_agent_policy(current_dlg_turn, bot):
    user_target = current_dlg_turn.user_target
    if user_target is None:
        user_target = ""
    user_target_by_line = user_target.split("\n")

    # We need to keep the original global context to be able to compare it with the new one
    # This helps in detecting the objects that have been updated. Useful for executing actions for lets say confirm fields.
    original_global_context = genie_deepcopy(bot.context.context)
    turn_context = GenieContext()

    original_global_context = _code_execution_and_policy_generation(
        user_target_by_line, original_global_context, turn_context, bot
    )

    # Check if any worksheet is available to fill
    if bot.context.agent_acts.can_have_other_acts():
        code_strings = get_available_ws(turn_context, bot)

        if len(code_strings):
            _code_execution_and_policy_generation(
                code_strings, original_global_context, turn_context, bot
            )

        bot.update_from_context(turn_context)
    _update_current_dlg_turn(current_dlg_turn, turn_context, bot)


def get_available_ws(turn_context, bot):
    code_strings = []
    if any_open_empty_ws(turn_context, bot.context):
        return code_strings
    for ws in bot.genie_worksheets:
        if issubclass(ws, GenieType):
            continue
        found_ws = False
        for _, var in turn_context.context.items():
            if isinstance(var, ws):
                found_ws = True
                break

        if not found_ws:
            # There is no instance of ws in the context
            # The ws is not a GenieType
            # The predicate is empty or the predicate is true
            if (
                not any([isinstance(x, ws) for x in bot.context.context.values()])
                and not issubclass(ws, GenieType)
                and (ws.predicate == "" or bot.eval(ws.predicate, turn_context))
            ):
                logger.info("Creating a new instance of " + ws.__name__)
                code_strings.append(
                    generate_var_name(ws.__name__) + " = " + ws.__name__ + "()"
                )

                # Lets just open one worksheet
                break
    return code_strings


def _update_current_dlg_turn(current_dlg_turn, turn_context, bot):
    current_dlg_turn.context.update(genie_deepcopy(turn_context.context))
    current_dlg_turn.global_context.update(genie_deepcopy(bot.context.context))

    if current_dlg_turn.system_action is None:
        current_dlg_turn.system_action = bot.context.agent_acts
    else:
        current_dlg_turn.system_action.extend(bot.context.agent_acts)


def _code_execution_and_policy_generation(
    user_target_by_line, original_global_context, turn_context, bot
):
    for code_line in user_target_by_line:
        if code_line == "":
            continue
        local_context = GenieContext()
        bot.execute(code_line, local_context, sp=True)

        diff_context = diff_between_contexts(
            original_global_context, bot.context.context
        )

        for key, value in diff_context.items():
            if key == "__builtins__":
                continue
            if key not in local_context.context:
                local_context.set(key, value)

        local_context = discover_and_execute_local(local_context, bot)
        bot.update_from_context(local_context)
        original_global_context = genie_deepcopy(bot.context.context)
        turn_context.update(local_context.context)

    if bot.context.agent_acts.can_have_other_acts():
        discover_and_execute_global(bot.context, bot)

    if bot.context.agent_acts.can_have_other_acts():
        discover_and_execute_ordered(bot)

    return original_global_context


def discover_and_execute_ordered(bot):
    for var_name in reversed(bot.order_of_actions):
        obj = bot.context.context[var_name]
        if isinstance(obj, Answer):
            continue
        if hasattr(obj, "predicate"):
            if eval_predicates(obj.predicate, obj, bot, bot.context):
                if obj.is_complete(bot, bot.context) and obj.action_performed is True:
                    bot.order_of_actions.remove(var_name)
                    continue
                if bot.context.agent_acts.can_have_other_acts():
                    actions = ask_for_confirmation_policy_for_field(obj, bot.context)
                    if actions:
                        if isinstance(actions, list):
                            bot.context.agent_acts.extend(actions)
                        else:
                            bot.context.agent_acts.append(actions)
                if bot.context.agent_acts.can_have_other_acts():
                    actions = ask_question_policy(obj, bot, bot.context)
                    if actions:
                        if isinstance(actions, list):
                            bot.context.agent_acts.extend(actions)
                        else:
                            bot.context.agent_acts.append(actions)
                if not bot.context.agent_acts.can_have_other_acts():
                    break
            else:
                bot.order_of_actions.remove(var_name)
        else:
            bot.order_of_actions.remove(var_name)


def discover_and_execute_global(context, bot):
    answer_objects = []
    ws_objects = []
    type_objects = []

    discover_objects(context, answer_objects, ws_objects, type_objects, bot)

    object_types = (answer_objects, ws_objects)

    for objects in object_types:
        for obj in objects:
            if obj is None:
                continue
            if isinstance(obj, dict) or not isinstance(obj, GenieWorksheet):
                continue
            if obj.is_complete(bot, context) and obj.action_performed is True:
                continue
            bot.order_of_actions.append(get_variable_name(obj, context))
            # break as soon as anyone returned result
            if bot.context.agent_acts.can_have_other_acts():
                actions = ask_for_confirmation_policy_for_field(obj, context)
                if actions:
                    if isinstance(actions, list):
                        bot.context.agent_acts.extend(actions)
                    else:
                        bot.context.agent_acts.append(actions)
            if bot.context.agent_acts.can_have_other_acts():
                actions = ask_question_policy(obj, bot, context)
                if actions:
                    if isinstance(actions, list):
                        bot.context.agent_acts.extend(actions)
                    else:
                        bot.context.agent_acts.append(actions)

        # NOTE: maybe an order of the forms is needed somehow
        if not bot.context.agent_acts.can_have_other_acts():
            break


def discover_and_execute_local(context, bot):
    answer_objects = []
    ws_objects = []
    type_objects = []

    discover_objects(context, answer_objects, ws_objects, type_objects, bot)

    object_types = (answer_objects, ws_objects)

    # Priority for agent policy:
    # 1. perform actions that don't need to be confirmed / already-confirmed for a **field**, report any results
    # 2. perform actions that don't need to be confirmed / already-confirmed for a **WS**, report any results

    # any aviliable of the above can be done, plus at most one of the following

    # 3. ask for confirmation for any field
    # 4. confirming the worksheet (all slots togther)

    # 5. check which question (field) to ask next
    for db_obj in answer_objects:
        if db_obj.is_complete(bot, context):
            db_obj.execute(bot, context)

    discover_objects(context, answer_objects, ws_objects, type_objects, bot)
    for objects in object_types:
        i = 0
        while i < len(objects):
            obj = objects[i]
            if obj.is_complete(bot, context) and obj.action_performed is True:
                i += 1
                continue
            bot.order_of_actions.append(get_variable_name(obj, context))
            if not isinstance(obj, Answer):
                bot.context.agent_acts.extend(
                    perform_action_policy_for_field(obj, bot, context)
                )
                bot.context.agent_acts.extend(
                    perform_action_policy_for_ws(obj, bot, context)
                )
            discover_objects(context, answer_objects, ws_objects, type_objects, bot)
            i += 1

    return context


def deduplicate_agent_policy(agent_acts):
    acts = []
    for act in agent_acts:
        if act not in acts:
            acts.append(act)

    return acts


def extract_unconfirmed_field_from(unconfirmed_fields):
    for act in unconfirmed_fields:
        field = act.field
        act.value = field.value
        field.value = None


def ask_question_policy(
    obj: GenieWorksheet, bot: GenieRuntime, local_context: GenieContext
):
    agent_acts = []
    fields_to_ask = []
    already_checked = []

    # go over all the objects and find the missing slots.
    # (it does not recurse on worksheets)
    def check_slots(obj):
        if len(fields_to_ask) > 0:
            return
        obj_name = get_variable_name(obj, local_context)
        if not any_open_empty_ws(local_context, bot.context):
            if inspect.isclass(obj) and issubclass(obj, GenieWorksheet):
                if eval_predicates(obj.predicate, obj, bot, local_context):
                    obj_name = obj.__name__
                    var_counter = count_number_of_vars(local_context.context)
                    if var_counter > 0:
                        var_name = (
                            generate_var_name(obj_name)
                            + f"_{var_counter.get(generate_var_name(obj_name), 0)}"
                        )
                    else:
                        var_name = generate_var_name(obj_name)
                    bot.execute(var_name + " = " + obj_name + "()", local_context)
                    obj_name = var_name
        for field in get_genie_fields_from_ws(obj):
            # Slottype is checked if the value is not filled.
            if eval_predicates(field.predicate, obj, bot, local_context):
                if hasattr(field.slottype, "__bases__") and (
                    field.slottype.__bases__ == (GenieType,)
                    or field.slottype.__bases__ == (GenieWorksheet,)
                ):
                    if field.value is not None and field.value not in already_checked:
                        already_checked.append(field.value)
                        check_slots(field.value)
                    else:
                        # check_slots(field.slottype)
                        fields_to_ask.append(
                            {"ws": obj, "field": field, "ws_name": obj_name}
                        )
                        return
                if (
                    field.value is None
                    and field not in fields_to_ask
                    and not field.internal
                    and field.ask
                ):
                    fields_to_ask.append(
                        {"ws": obj, "field": field, "ws_name": obj_name}
                    )

                # if the field.value is "NA" then we don't ask for it again. There might be issues with this.
                # For example, if there is a required field and the user doesn't provide the value then the
                # api will fail.
                # TODO: We need to handle this case.
                # elif (
                #     isinstance(field.value, str)
                #     and field.value == "NA"
                #     and not field.optional
                # ):
                #     fields_to_ask.append(
                #         {
                #             "ws": obj,
                #             "field": field,
                #             "ws_name": obj_name,
                #         }
                #     )

    check_slots(obj)

    if len(fields_to_ask) > 0:
        i = 0
        while i < len(fields_to_ask):
            if isinstance(fields_to_ask[i]["ws"], GenieWorksheet) and not isinstance(
                fields_to_ask[i]["ws"], Answer
            ):
                field_to_ask = fields_to_ask[i]
                agent_acts.append(AskAgentAct(**field_to_ask))
                break
            i += 1

    return agent_acts


def ask_for_confirmation_policy_for_field(
    obj: GenieWorksheet, local_context: GenieContext
):
    agent_acts = []
    ask_for_confirmation = []

    def check_for_confirmation(obj):
        for field in get_genie_fields_from_ws(obj):
            if field.value is not None:
                if field.requires_confirmation and not field.confirmed:
                    if isinstance(field.value, GenieType):
                        ask_for_confirmation.append({"ws": obj, "field": field})
                    elif isinstance(field.value, GenieWorksheet):
                        check_for_confirmation(field.value)
                    else:
                        if field_value_has_info(field.value):
                            ask_for_confirmation.append({"ws": obj, "field": field})

    check_for_confirmation(obj)

    if len(ask_for_confirmation) > 0:
        field_to_ask = ask_for_confirmation[0]
        var_name = get_variable_name(field_to_ask["ws"], local_context)
        agent_acts.append(
            AskForConfirmationAgentAct(
                **field_to_ask,
                ws_name=var_name,
                field_name=var_name + "." + field_to_ask["field"].name,
            )
        )

    return agent_acts


def field_value_has_info(value):
    if value is None:
        return False

    if isinstance(value, GenieValue):
        if value.value is None or len(value.value) == 0:
            return False

    return True


def perform_action_policy_for_field(
    obj: GenieWorksheet, bot: GenieRuntime, local_context: GenieContext
):
    agent_acts = []

    def perform_action(obj):
        for field in get_genie_fields_from_ws(obj):
            if field.value is not None:
                if field.requires_confirmation:
                    if field.confirmed:
                        if isinstance(field.value, GenieWorksheet):
                            perform_action(field.value)
                        else:
                            logger.info(
                                f"Peforming action for {field.name}: {field.actions}"
                            )
                            action = field.perform_action(bot, local_context)
                            agent_acts.extend(action)
                else:
                    if isinstance(field.value, GenieWorksheet):
                        perform_action(field.value)
                    else:
                        action = field.perform_action(bot, local_context)
                        agent_acts.extend(action)

    perform_action(obj)

    return agent_acts


def perform_action_policy_for_ws(
    obj: Union[GenieWorksheet], bot: GenieRuntime, local_context: GenieContext
):
    agent_acts = []
    if obj.is_complete(bot, local_context) and obj.action_performed is False:
        if (
            isinstance(obj, GenieWorksheet)
            and hasattr(obj, "backend_api")
            and len(obj.backend_api)
        ):
            obj.execute(bot, local_context)
        logger.info(
            f"Performing Worksheet action for {obj.__class__.__name__}: {obj.actions.action}"
        )
        actions = obj.perform_action(bot, local_context)
        for action in actions:
            if isinstance(action, AgentAct):
                agent_acts.append(action)

    return agent_acts
