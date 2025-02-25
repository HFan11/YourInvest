"""
Main file for a SUQL-powered agent loop
"""

import argparse
import json
import logging
import math
import os
import re
import time
from datetime import datetime
from decimal import Decimal
from typing import List

import requests

from suql.prompt_continuation import llm_generate
from suql.sql_free_text_support.execute_free_text_sql import suql_execute
from suql.utils import input_user, num_tokens_from_string, print_chatbot
os.environ["OPENAI_API_KEY"] = "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"
logger = logging.getLogger(__name__)


class DialogueTurn:
    def __init__(
        self,
        agent_utterance: str = None,
        user_utterance: str = None,
        db_results: str = None,
        temp_target: str = None,
        user_target: str = None,
        time_statement: dict = None,
        cache: dict = {},
        results_for_ned: dict = None,
    ):
        self.agent_utterance = agent_utterance
        self.user_utterance = user_utterance
        self.db_results = db_results
        self.temp_target = temp_target
        self.user_target = user_target
        self.results_for_ned = results_for_ned
        self.cache = cache
        self.time_statement = time_statement

    agent_utterance: str
    user_utterance: str
    db_results: str
    user_target: str
    temp_target: str
    time_statement: dict
    results_for_ned: dict
    cache: dict

    def to_text(self, they="They", you="You"):
        """
        Format:
        You:
        They:
        [You check the database for "find chinese restaurants near palo alto"]
        [Database returns "I see Jing Jing Chinese Gourmet. It is a Chinese restaurant rated 3.5 stars."]
        Restaurant reviews: [
        Review 1: ...
        Summary:
        Review 2: ...
        Summary:
        Review 3: ...
        Summary:
        ]
        """
        ret = ""

        ret += they + ": " + self.user_utterance
        if self.db_results is not None:
            ret += "\n" + '[Database returns "' + self.db_results + '"]'
        if self.agent_utterance is not None:
            ret += "\n" + you + ": " + self.agent_utterance
        return ret


def dialogue_history_to_text(
    history: List[DialogueTurn], they="They", you="You"
) -> str:
    """
    From the agent's point of view, it is 'You:'. The agent starts the conversation.
    """
    ret = ""
    for i in range(len(history)):
        ret += "\n" + history[i].to_text(they=they, you=you)

    if len(history) > 0:
        # remove the extra starting newline
        if ret[0] == "\n":
            ret = ret[1:]

    return ret


# this function extracts only the _id and name fields from the database results, if any
def extract_id_name(results, column_names):
    """
    Custom function for associating stock IDs (_id) with their tickers.
    This function is useful for Named Entity Disambiguation (NED) in dialog settings.

    ### Why is a NED module needed?

    Consider the following dialog:
    User: Tell me about Apple stock.
    Agent: I found multiple results, including AAPL and APPLX. Which one would you like?

    Now, ambiguity arises because there are multiple possible matches for "Apple."
    If we parse the user's query like this:
    ```
    SELECT * FROM stocks WHERE ticker = 'AAPL';
    ```
    Then we may miss the other possible match, such as "APPLX."

    Instead, it is better to associate stocks with their IDs (_id) for disambiguation.
    For instance:
    ```
    SELECT * FROM stocks WHERE _id = 123;
    ```
    where 123 is the ID for the stock "AAPL."

    This function extracts the `_id` and `ticker` association for each result presented
    to the user, which can be used for clarification in the next turn.
    """
    results_for_ned = []
    for result in results:
        temp = dict(
            (column_name, each_result)
            for column_name, each_result in zip(column_names, result)
        )
        if "_id" in temp and "ticker" in temp:  # Check for '_id' and 'ticker' keys
            results_for_ned.append({"_id": temp["_id"], "ticker": temp["ticker"]})  # Map '_id' and 'ticker'
    return results_for_ned


def clean_up_response(results, column_names):
    """
    Custom function to define what to include in the final response prompt for stocks.
    This function should be customized for the stocks database schema.

    This function filters out fields that are not relevant for user responses
    (e.g., IDs) and handles potential issues with numeric fields such as `Decimal`.

    It also truncates overly long responses to fit within the token limit.
    """

    def if_usable_stock_fields(field: str):
        """
        Custom function to define what fields to exclude from the user-visible response.
        """
        NOT_USABLE_FIELDS = [
            # no need to show internal IDs
            "_id",
            # technical fields that users don't interact with directly
            "id",
        ]

        if field in NOT_USABLE_FIELDS:
            return False

        return True

    final_res = []
    for res in results:
        temp = dict(
            (column_name, result)
            for column_name, result in zip(column_names, res)
            if if_usable_stock_fields(column_name)
        )
        # Convert Decimal values to float for numeric fields
        for key in temp:
            if isinstance(temp[key], Decimal):
                temp[key] = float(temp[key])

        # Heuristic to truncate responses if they exceed token limits
        if num_tokens_from_string(json.dumps(final_res + [temp], indent=4)) > 3500:
            break

        final_res.append(temp)
    return final_res


def parse_execute_sql(dlgHistory, user_query, prompt_file="prompts/parser_suql.prompt"):
    """
    Call an LLM to predict a SUQL, execute it, and return results for the stocks table.
    """

    # Generate SUQL query using the language model
    generated_suql, generated_sql_time = llm_generate(
        template_file=prompt_file,
        engine="gpt-3.5-turbo-0125",
        stop_tokens=["Agent:"],
        max_tokens=300,
        temperature=0,
        prompt_parameter_values={"dlg": dlgHistory, "query": user_query},
        postprocess=False,
    )
    print("Directly generated SUQL query: {}".format(generated_suql))
    
    # Postprocess the generated SUQL query
    postprocessed_suql = postprocess_suql(generated_suql)

    # Execute the SUQL query against the dynamically determined table
    suql_execute_start_time = time.time()
    final_res, column_names, cache = suql_execute(
        postprocessed_suql,
        table_w_ids = {"etfs": "_id", "stocks": "_id"},
        database="cs224v",
        fts_fields=[("etfs", "ticker"),("stocks", "ticker")],
        embedding_server_address="http://127.0.0.1:8501"
    )
    suql_execute_end_time = time.time()


    # Process results for Named Entity Disambiguation (NED)
    results_for_ned = extract_id_name(final_res, column_names)  # Retaining the name `extract_id_name`
    
    # Clean up the final response for output
    final_res = clean_up_response(final_res, column_names)

    return (
        final_res,
        generated_suql,
        postprocessed_suql,
        generated_sql_time,
        suql_execute_end_time - suql_execute_start_time,
        cache,
        results_for_ned,
    )



def postprocess_suql(suql_query):
    """
    Define your custom functions here to post-process a generated SUQL.
    This function is customized for the `stocks` database.

    In the `stocks` context, we post-process a generated SUQL query with:
    (1) Escape single quotes in the query.
    (2) Ensure all generated queries include a LIMIT clause (default: LIMIT 3).
    (3) Cast `MONEY` fields to `NUMERIC` for numeric operations.
    (4) Handle other fields stored as TEXT appropriately.
    """

    # Escape single quotes for PostgreSQL
    suql_query = suql_query.replace("\\'", "''")

    # Ensure there is a LIMIT clause if not already present
    if "LIMIT" not in suql_query:
        suql_query = re.sub(r";$", " LIMIT 3;", suql_query, flags=re.MULTILINE)

    # Process MONEY fields to allow numeric comparisons
    def process_money_casts(suql_query_):
        """
        Ensure proper casting of MONEY fields like `5_day_return` or others.
        """
        money_fields = [
            "5_day_return",
            "10_day_return",
            "1_month_return",
            "6_month_return",
            "1_year_return",
        ]

        for field in money_fields:
            pattern = rf'({field})\s*(>=|<=|>|<|=)\s*([\d\.]+)'
            suql_query_ = re.sub(pattern, r"CAST(\1 AS NUMERIC) \2 \3", suql_query_)

        return suql_query_

    # Ensure TEXT fields are handled as strings
    def process_text_fields(suql_query_):
        """
        Ensure proper handling of TEXT fields in the query.
        Wraps conditions on TEXT fields in single quotes if not already present.
        """
        text_fields = [
            "5_day_avg_close",
            "5_day_volatility",
            "5_day_avg_volume",
            "10_day_avg_close",
            "10_day_volatility",
            "10_day_avg_volume",
            "1_month_avg_close",
            "1_month_volatility",
            "1_month_avg_volume",
            "6_month_avg_close",
            "6_month_volatility",
            "6_month_avg_volume",
            "1_year_avg_close",
            "1_year_volatility",
            "1_year_avg_volume",
            "rsi",
            "macd",
            "signal_line",
        ]

        for field in text_fields:
            # Match patterns like `field = value` or `field != value` and ensure value is quoted
            pattern = rf'({field})\s*(=|!=)\s*([^\'"\s]+)'
            suql_query_ = re.sub(pattern, r"\1 \2 '\3'", suql_query_)

        return suql_query_

    # Apply processing
    suql_query = process_money_casts(suql_query)
    suql_query = process_text_fields(suql_query)

    return suql_query


def compute_next_turn(
    dlgHistory: List[DialogueTurn], user_utterance: str, enable_classifier=False
):
    first_classification_time = 0
    semantic_parser_time = 0
    suql_execution_time = 0
    final_response_time = 0
    cache = {}

    dlgHistory.append(DialogueTurn(user_utterance=user_utterance))

    # determine whether to use database
    if enable_classifier:
        continuation, first_classification_time = llm_generate(
            template_file="prompts/if_db_classification.prompt",
            prompt_parameter_values={"dlg": dlgHistory},
            engine="gpt-3.5-turbo-0125",
            max_tokens=50,
            temperature=0.0,
            stop_tokens=["\n"],
            postprocess=False,
        )

    if not enable_classifier or continuation.startswith("Yes"):
        (
            results,
            first_sql,
            second_sql,
            semantic_parser_time,
            suql_execution_time,
            cache,
            results_for_ned,
        ) = parse_execute_sql(
            dlgHistory, user_utterance, prompt_file="prompts/parser_suql.prompt"
        )
        dlgHistory[-1].db_results = json.dumps(results, indent=4)
        dlgHistory[-1].user_target = first_sql
        dlgHistory[-1].temp_target = second_sql
        dlgHistory[-1].results_for_ned = results_for_ned

        # cut it out if no response returned
        if not results:
            response, final_response_time = llm_generate(
                template_file="prompts/investment_response_no_results.prompt",
                prompt_parameter_values={"dlg": dlgHistory},
                engine="gpt-3.5-turbo-0125",
                max_tokens=400,
                temperature=0.0,
                stop_tokens=[],
                top_p=0.5,
                postprocess=False,
            )

            dlgHistory[-1].agent_utterance = response
            dlgHistory[-1].time_statement = {
                "first_classification": first_classification_time,
                "semantic_parser": semantic_parser_time,
                "suql_execution": suql_execution_time,
                "final_response": final_response_time,
            }
            return dlgHistory

    response, final_response_time = llm_generate(
        template_file="prompts/investment_response_SQL.prompt",
        prompt_parameter_values={"dlg": dlgHistory},
        engine="gpt-3.5-turbo-0125",
        max_tokens=400,
        temperature=0.0,
        stop_tokens=[],
        top_p=0.5,
        postprocess=False,
    )
    dlgHistory[-1].agent_utterance = response

    dlgHistory[-1].time_statement = {
        "first_classification": first_classification_time,
        "semantic_parser": semantic_parser_time,
        "suql_execution": suql_execution_time,
        "final_response": final_response_time,
    }
    dlgHistory[-1].cache = cache

    return dlgHistory


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output_file",
        type=str,
        default="log.log",
        help="Where to write the outputs, pertaining only to CLI testing.",
    )
    parser.add_argument(
        "--quit_commands",
        type=str,
        default=["quit", "q"],
        help="The conversation will continue until this string is typed in, pertaining only to CLI testing.",
    )
    parser.add_argument(
        "--no_logging",
        action="store_true",
        help="Do not output extra information about the intermediate steps.",
    )
    args = parser.parse_args()

    if args.no_logging:
        logging.basicConfig(
            level=logging.CRITICAL, format=" %(name)s : %(levelname)-8s : %(message)s"
        )
    else:
        logging.basicConfig(
            level=logging.INFO, format=" %(name)s : %(levelname)-8s : %(message)s"
        )

    # The dialogue loop. The agent starts the dialogue
    dlgHistory = []
    print_chatbot(dialogue_history_to_text(dlgHistory, they="User", you="Chatbot"))

    try:
        while True:
            user_utterance = input_user()
            if user_utterance in args.quit_commands:
                break

            dlgHistory = compute_next_turn(
                dlgHistory,
                user_utterance,
            )
            print_chatbot("Chatbot: " + dlgHistory[-1].agent_utterance)
            print(dlgHistory[-1].time_statement)

    finally:
        with open(args.output_file, "a") as output_file:
            output_file.write(
                "=====\n"
                + datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                + "\n"
                + dialogue_history_to_text(dlgHistory, they="User", you="Chatbot")
                + "\n"
            )
