from genie_worksheet.worksheets.annotation_utils import get_agent_action_schemas, get_context_schema
from genie_worksheet.worksheets.modules.dialogue import CurrentDialogueTurn
from genie_worksheet.worksheets.modules import utils as chat_utils
from genie_worksheet.worksheets.modules import generate_next_turn
from genie_worksheet.worksheets.from_spreadsheet import gsheet_to_genie
from investment_api import investment_plan_api as api
import asyncio
import json
import os



# Determines the path where Genie prompts are saved
genie_current_dir = os.getcwd()
genie_prompt_dir = os.path.join(genie_current_dir, "genie_worksheet/prompts")

# ID of the google sheet here
gsheet_id_default = "1UgekrVVQTKgJKXbfx9We02g8tDGZIBpeRItRxX2Esu0"

# The api key
os.environ["OPENAI_API_KEY"] = "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"

# Helper function that is used for logging.
def convert_to_json(dialogue: list[CurrentDialogueTurn]):
    json_dialogue = []
    for turn in dialogue:
        json_turn = {
            "user": turn.user_utterance,
            "bot": turn.system_response,
            "turn_context": get_context_schema(turn.context),
            "global_context": get_context_schema(turn.global_context),
            "system_action": get_agent_action_schemas(turn.system_action),
            "user_target_sp": turn.user_target_sp,
            "user_target": turn.user_target,
            "user_target_suql": turn.user_target_suql,
        }
        json_dialogue.append(json_turn)
    return json_dialogue


async def main():
    botname = "Personal Investment Agent"
    starting_prompt = "Hello! I’m here to help you create a tailored investment plan. Please share some details, like your investment goals, budget, preferred duration, and risk tolerance, so I can provide recommendations that best fit your needs."
    description = "LLM agent that helps the user come up with investment plan."


    bot = gsheet_to_genie(
        bot_name=botname,
        description=description,
        prompt_dir=genie_prompt_dir,
        starting_prompt=starting_prompt,
        args = {},
        api=api,
        gsheet_id=gsheet_id_default,
        suql_runner=None,
        suql_prompt_selector=None
    )

    quit_commands = ["quit()", "exit()"]
    save_file_name = "log_file.json" # output path of the log for the conversation


    try:
        while True:
            if len(bot.dlg_history) == 0:
                chat_utils.print_chatbot(bot.starting_prompt)
            user_utterance = None
            if user_utterance is None:
                user_utterance = chat_utils.input_user()
            if user_utterance.lower().strip() in quit_commands:
                break

            await generate_next_turn(user_utterance, bot)
            chat_utils.print_complete_history(bot.dlg_history)
    except Exception as e:
        print(e)

        import traceback

        traceback.print_exc()
    finally:
        with open(save_file_name, "w") as f:
            json.dump(convert_to_json(bot.dlg_history), f, indent=4)


# Use asyncio.run to properly run the async function
if __name__ == "__main__":
    asyncio.run(main())