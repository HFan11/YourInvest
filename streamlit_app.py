import streamlit as st
from genie_worksheet.worksheets.modules.dialogue import CurrentDialogueTurn
from genie_worksheet.worksheets.modules import generate_next_turn
from genie_worksheet.worksheets.from_spreadsheet import gsheet_to_genie
from investment_api import investment_plan_api as api
import asyncio
import os

# Path and configuration for Genie prompts
genie_current_dir = os.getcwd()
genie_prompt_dir = os.path.join(genie_current_dir, "genie_worksheet/prompts")
gsheet_id_default = "1UgekrVVQTKgJKXbfx9We02g8tDGZIBpeRItRxX2Esu0"
os.environ["OPENAI_API_KEY"] = "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"

# Bot setup details
botname = "Personal Investment Agent"
starting_prompt = "Hello! I’m here to help you create a tailored investment plan. Please share some details, like your investment goals, budget, preferred duration, and risk tolerance, so I can provide recommendations that best fit your needs."
description = "LLM agent that helps the user come up with investment plans."

# Add custom CSS for styling
st.markdown("""
    <style>
        .st-chat-message {
            padding: 10px;
            margin: 5px 0;
        }
        .st-chat-message.human {
            background-color: #e8f5e9;
            border: 1px solid #1b5e20;
            border-radius: 10px;
        }
        .st-chat-message.ai {
            background-color: #e3f2fd;
            border: 1px solid #1e88e5;
            border-radius: 10px;
        }
        .st-spinner {
            color: #1e88e5;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("About")
    st.write("This is your Personal Investment Agent, here to help you with tailored investment plans.")
    st.markdown("#### Features:")
    st.write("- Interactive chat")
    st.write("- Tailored investment advice")
    st.write("- Risk tolerance assessment")
    st.divider()
    st.caption("Powered by OpenAI & Streamlit")

# Initialize the chatbot and session state
if "bot" not in st.session_state:
    st.session_state.bot = gsheet_to_genie(
        bot_name=botname,
        description=description,
        prompt_dir=genie_prompt_dir,
        starting_prompt=starting_prompt,
        args={},
        api=api,
        gsheet_id=gsheet_id_default,
        suql_runner=None,
        suql_prompt_selector=None
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

    # Add starting prompt as the initial message from AI
    st.session_state.messages.append(("", starting_prompt))

# Header and description
st.title("Investment Planning Agent")
st.subheader("Confused about investment? Our agent can help you!")

# Example queries
st.markdown("#### Example Queries:")
col1, col2 = st.columns(2)
with col1:
    if st.button("What are some good investment options for short-term gains?"):
        user_query = "What are some good investment options for short-term gains?"
with col2:
    if st.button("Suggest investments for a $10,000 budget"):
        user_query = "Suggest investments for a $100,000 budget"

# Chat area
for message in st.session_state.messages:
    if message[0]:  # User message
        with st.chat_message("human"):
            st.markdown(f"**You:** {message[0]}")
    if message[1]:  # AI response
        with st.chat_message("ai"):
            st.markdown(f"**Agent:** {message[1]}")

# Handle user input
if user_query := st.chat_input("Type your investment query here..."):
    st.chat_message("human").write(f"{user_query}")

    async def handle_user_query(user_query):
        with st.spinner("Thinking..."):
            # Generate the next turn using the bot instance
            await generate_next_turn(user_query, st.session_state.bot)
            response = st.session_state.bot.dlg_history[-1]

            # Append user query and bot response to chat history
            st.session_state.messages.append((user_query, response.system_response))
            
            # Display the bot response in the app
            st.chat_message("ai").write(f"{response.system_response}")

    # Run async handler for query
    asyncio.run(handle_user_query(user_query))

