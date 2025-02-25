import json
import re

from flask import Flask, request

from suql.faiss_embedding import compute_top_similarity_documents
from suql.utils import num_tokens_from_string

app = Flask(__name__)

# # Default top number of results to send to LLM answer function
# # if given a list of strings
# k = 5

# # Max number of input tokens for the `summary` function
# max_input_token = 3800

# # Default LLM engine for `answer` and `summary` functions
# engine = "gpt-3.5-turbo-0613"


def _answer(
    source,
    query,
    type_prompt=None,
    k=5,
    max_input_token=10000,
    engine="gpt-3.5-turbo-0125"
):
    """
    Answer function for stock data. Queries the stock database and retrieves relevant responses
    using an LLM based on the input source and query.
    """
    from suql.prompt_continuation import llm_generate

    if not source:
        return {"result": "no information"}

    text_res = []
    if isinstance(source, list):
        documents = compute_top_similarity_documents(
            source, query, top=k
        )
        for i in documents:
            if num_tokens_from_string("\n".join(text_res + [i])) < max_input_token:
                text_res.append(i)
            else:
                break
    else:
        text_res = [source]

    # Handle specific type prompts (e.g., format expectations for numeric or date fields)
    type_prompt = ""
    if type_prompt:
        if type_prompt == "numeric":
            type_prompt = " Output the result as a numeric value."
        elif type_prompt == "date":
            type_prompt = " Output the result in date format, e.g., 2023-11-20."

    continuation, _ = llm_generate(
        "prompts/answer_qa.prompt",
        {
            "data": text_res,
            "question": query,
            "type_prompt": type_prompt,
        },
        engine=engine,
        max_tokens=1000,
        temperature=0.0,
        stop_tokens=[],
        postprocess=False,
    )
    return {"result": continuation}


def start_free_text_fncs_server(
    host="127.0.0.1", port=8500, k=5, max_input_token=3800, engine="gpt-4o-mini"
):
    """
    Set up a free text functions server for the stock database.

    Args:
        host (str, optional): The host running this server. Defaults to "127.0.0.1" (localhost).
        port (int, optional): The port running this server. Defaults to 8500.
        k (int, optional): Default top number of results to send to LLM answer function
            if given a list of strings. Defaults to 5.
        max_input_token (int, optional): Max number of input tokens for the `summary` function.
            Defaults to 3800.
        engine (str, optional): Default LLM engine for `answer` and `summary` functions.
            Defaults to "gpt-3.5-turbo-0613".
    """

    @app.route("/answer", methods=["POST"])
    def answer():
        """
        LLM-based answer function, set up as a server for the stock database to call.

        Expected input params in request.get_json():

        - data["text"] (str or List[str]): text to query upon.
        - data["question"] (str): question to answer.

        If data["text"] is a list of strings, computes embedding to find top `k`
        documents to send to the LLM for answering (Default set to 5);
        Includes those in the LLM prompt until `max_input_token` is reached.

        Returns:
        {
            "result" (str): answer function result.
        }
        """
        from suql.prompt_continuation import llm_generate

        data = request.get_json()

        if "text" not in data or "question" not in data:
            return None

        return _answer(
            data["text"],
            data["question"],
            type_prompt=data.get("type_prompt"),
            k=k,
            max_input_token=max_input_token,
            engine=engine,
        )

    @app.route("/summary", methods=["POST"])
    def summary():
        """
        LLM-based summary function for stock data. The function retrieves a summary
        of input text or data.

        Expected input params in request.get_json():

        - data["text"] : text to summarize.

        Returns:
        {
            "result" (str): summary function result.
        }
        """
        from suql.prompt_continuation import llm_generate

        data = request.get_json()

        if "text" not in data:
            return None

        if not data["text"]:
            return {"result": "no information"}

        text_res = []
        if isinstance(data["text"], list):
            for i in data["text"]:
                if num_tokens_from_string("\n".join(text_res + [i])) < max_input_token:
                    text_res.append(i)
                else:
                    break
        else:
            text_res = [data["text"]]

        continuation, _ = llm_generate(
            "prompts/answer_qa.prompt",
            {"data": text_res, "question": "What is the summary of this data?"},
            engine=engine,
            max_tokens=200,
            temperature=0.0,
            stop_tokens=["\n"],
            postprocess=False,
        )

        res = {"result": continuation}
        return res

    # Start Flask server
    app.run(host=host, port=port)


if __name__ == "__main__":
    start_free_text_fncs_server(
        host="127.0.0.1",
        port=8500,
    )
