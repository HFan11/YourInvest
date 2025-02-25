from jinja2 import Template
from langchain_openai import ChatOpenAI
import datetime
import os
import json
import re

# Config the prompts directory for the investment plan API
api_prompt_dir = os.path.join(os.getcwd(), "investment_api/prompt")

def create_portfolio_draft(
    customer_name,
    age,
    income,
    occupation,
    budget_usd,
    time_horizon_weeks,
    risk_level,
    asset_preference,
    liquidity,
    model_name="gpt-4o",
    llm_params=None
):
    if llm_params is None:
        llm_params = {}

    # Load the prompt from the prompt directory
    prompt_file_path = os.path.join(api_prompt_dir, "draft_investment_plan.prompt")
    with open(prompt_file_path, "r") as prompt_file:
        prompt_template = prompt_file.read()

    # Prepare template inputs with 'not provided' only for debug visibility
    prompt_inputs = {
        "customer_name": customer_name or "not provided",
        "age": age or "not provided",
        "income": income or "not provided",
        "occupation": occupation or "not provided",
        "budget_usd": budget_usd or "not provided",
        "time_horizon_weeks": time_horizon_weeks or "not provided",
        "risk_level": risk_level or "not provided",
        "asset_preference": asset_preference or "not provided",
        "liquidity": liquidity or "not provided",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "day": datetime.datetime.now().strftime("%A")
    }

    # Use Jinja2 for better placeholder handling
    template = Template(prompt_template)
    prompt = template.render(**prompt_inputs)

    # Check for unreplaced placeholders
    unreplaced_placeholders = re.findall(r"\{\{(.*?)\}\}", prompt)
    if unreplaced_placeholders:
        print(f"Warning: The following placeholders were not replaced: {unreplaced_placeholders}")

    # Instantiate the ChatOpenAI model
    llm = ChatOpenAI(
        model=model_name,
        api_key=os.environ["OPENAI_API_KEY"],
        **llm_params
    )

    # Generate the response using the prompt
    response = llm(prompt)

    response_text = response.content

    # Parse the response to a human-readable format
    try:
        parsed_response = json.dumps(json.loads(response_text), indent=4) if response_text.startswith('{') else response_text
    except json.JSONDecodeError as e:
        print("Error parsing JSON response. Raw response:")
        print(response_text)
        raise ValueError(f"JSON decoding error: {e}")

    print("Draft plan:\n" + parsed_response)

    return parsed_response



def create_detailed_portfolio(
    draft_portfolio,
    detailed_plan,
    model_name="gpt-4o",
    llm_params=None
):
    if llm_params is None:
        llm_params = {}

    # Load the prompt from the prompt directory
    prompt_file_path = os.path.join(api_prompt_dir, "detailed_investment_plan.prompt")
    with open(prompt_file_path, "r") as prompt_file:
        prompt_template = prompt_file.read()

    # Prepare template inputs with 'not provided' only for debug visibility
    def get_detail(plan, category, index, default="not provided"):
        return plan.get(category, [None] * (index + 1))[index] if category in plan and len(plan[category]) > index else default

    prompt_inputs = {
        "draft_plan": draft_portfolio or "not provided",
        "stock_detail": get_detail(detailed_plan, "Stocks", 1),
        "stock_criteria": get_detail(detailed_plan, "Stocks", 0),
        "etf_detail": get_detail(detailed_plan, "ETFs", 1),
        "etf_criteria": get_detail(detailed_plan, "ETFs", 0),
        "indices_detail": get_detail(detailed_plan, "Stock Indices", 1),
        "indices_criteria": get_detail(detailed_plan, "Stock Indices", 0),
        "bonds_detail": get_detail(detailed_plan, "US Bonds", 1),
        "bonds_criteria": get_detail(detailed_plan, "US Bonds", 0),
        "crypto_detail": get_detail(detailed_plan, "Crypto", 1),
        "crypto_criteria": get_detail(detailed_plan, "Crypto", 0),
    }

    # Use Jinja2 for better placeholder handling
    template = Template(prompt_template)
    prompt = template.render(**prompt_inputs)

    # Check for unreplaced placeholders
    unreplaced_placeholders = re.findall(r"\{\{(.*?)\}\}", prompt)
    if unreplaced_placeholders:
        print(f"Warning: The following placeholders were not replaced: {unreplaced_placeholders}")

    # Instantiate the ChatOpenAI model
    llm = ChatOpenAI(
        model=model_name,
        api_key=os.environ["OPENAI_API_KEY"],
        **llm_params
    )

    # Generate the response using the prompt
    response = llm(prompt)

    return response


def process_stocks(criteria):
    print("Processing Stocks with criteria:")
    for key, value in criteria.items():
        print(f"  {key}: {value}")
    return "Recommended stocks are: GOOG, AMAZN, INTU and DAL"

def process_etfs(criteria):
    print("Processing ETFs with criteria:")
    for key, value in criteria.items():
        print(f"  {key}: {value}")
    return "The good ETF candidates are: AIA.US, BOTZ.US"

def process_stock_indices(criteria):
    print("Processing Stock Indices with criteria:")
    for key, value in criteria.items():
        print(f"  {key}: {value}")
    return "The good Stock Indices candidates are: SPA, QQQ"

def process_us_bonds(criteria):
    print("Processing US Bonds with criteria:")
    for key, value in criteria.items():
        print(f"  {key}: {value}")
    return "Recommended bonds are: Treasury Bond 3 month"

def process_crypto(criteria):
    print("Processing Crypto with criteria:")
    for key, value in criteria.items():
        print(f"  {key}: {value}")
    return ""


def plan_investment(
    customer_name,
    age,
    income,
    occupation,
    budget_usd,
    time_horizon_weeks,
    risk_level,
    asset_preference,
    liquidity,
    model_name="gpt-4o",
    llm_params=None
):

    # Define the investment types and their corresponding processing functions
    investment_types = ["Stocks", "ETFs", "Stock Indices", "US Bonds", "Crypto"]
    processing_functions = {
        "Stocks": process_stocks,
        "ETFs": process_etfs,
        "Stock Indices": process_stock_indices,
        "US Bonds": process_us_bonds,
        "Crypto": process_crypto
    }

    # Generate the draft portfolio
    draft_portfolio = create_portfolio_draft(
        customer_name,
        age,
        income,
        occupation,
        budget_usd,
        time_horizon_weeks,
        risk_level,
        asset_preference,
        liquidity,
        model_name=model_name,
        llm_params=llm_params
    )

    # Remove backticks if they are present in the response
    draft_portfolio = draft_portfolio.strip("```json\n").strip("```")

    print("Draft plan is:", draft_portfolio)

    # Parse the JSON string into a Python dictionary
    try:
        draft_portfolio_dict = json.loads(draft_portfolio)
    except json.JSONDecodeError as e:
        print("Error decoding JSON response.")
        print(f"Raw JSON response: {draft_portfolio}")
        return None

    detailed_plan = {}

    for investment_type, details in draft_portfolio_dict.items():
        if investment_type in investment_types:
            # Extract criteria, excluding 'reason'
            criteria = {key: value for key, value in details.items() if key != "reason"}
            
            # Get the corresponding function based on the investment type
            process_function = processing_functions.get(investment_type)
            
            if process_function:
                result = process_function(criteria)  # Call the function with criteria as argument
                detailed_plan[investment_type] = (criteria, result)
            else:
                print(f"No processing function defined for {investment_type}")

    detailed_portfolio = create_detailed_portfolio(
        draft_portfolio,
        detailed_plan,
        model_name=model_name,
        llm_params=llm_params
    )


    return detailed_portfolio


def update_investment(
    customer_name,
    age,
    income,
    occupation,
    budget_usd,
    time_horizon_weeks,
    risk_level,
    asset_preference,
    liquidity,
    draft_plan,
    change_to_apply,
    model_name="gpt-4o",
    llm_params=None
):
    print("The update requirement is:", change_to_apply)

    if draft_plan is None or change_to_apply is None:
        print("Error, draft plan or change to apply is None, return plan with no changes.")
        return draft_plan        

    if llm_params is None:
        llm_params = {}

    # Load the prompt from the prompt directory
    prompt_file_path = os.path.join(api_prompt_dir, "update_investment_plan.prompt")
    with open(prompt_file_path, "r") as prompt_file:
        prompt_template = prompt_file.read()

    # Prepare template inputs with 'not provided' only for debug visibility
    prompt_inputs = {
        "customer_name": customer_name or "not provided",
        "age": age or "not provided",
        "income": income or "not provided",
        "occupation": occupation or "not provided",
        "budget_usd": budget_usd or "not provided",
        "time_horizon_weeks": time_horizon_weeks or "not provided",
        "risk_level": risk_level or "not provided",
        "asset_preference": asset_preference or "not provided",
        "liquidity": liquidity or "not provided",
        "old_plan": draft_plan,
        "new_requirement": change_to_apply,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "day": datetime.datetime.now().strftime("%A"),
    }

    # Use Jinja2 for better placeholder handling
    template = Template(prompt_template)
    prompt = template.render(**prompt_inputs)

    # Check for unreplaced placeholders
    unreplaced_placeholders = re.findall(r"\{\{(.*?)\}\}", prompt)
    if unreplaced_placeholders:
        print(f"Warning: The following placeholders were not replaced: {unreplaced_placeholders}")

    # Instantiate the ChatOpenAI model
    llm = ChatOpenAI(
        model=model_name,
        api_key=os.environ["OPENAI_API_KEY"],
        **llm_params
    )

    # Generate the response using the prompt
    response = llm(prompt)

    return response