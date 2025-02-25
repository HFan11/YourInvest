import streamlit as st
import asyncio
import logging
from agent import compute_next_turn, DialogueTurn

# Initial setup
st.title("MyInvestPath: Your own Investment Planning Assistant")
st.subheader("Confuse about investment? Get tailored investment advice based on your preferences!")
st.sidebar.title("About")
st.sidebar.write("This is an interactive investment advisor assistant powered by SUQL and LLMs.")
st.sidebar.caption("Powered by OpenAI, Genieworksheet, and SUQL")

st.markdown("#### Example Queries:")
col1, col2 = st.columns(2)
with col1:
    if st.button("What are some good investment options for short-term gains?"):
        user_query = "What are some good investment options for short-term gains?"
with col2:
    if st.button("Suggest investments for a $10,000 budget"):
        user_query = "Suggest investments for a $100,000 budget"

# Initialize state for dialogue history
if "dlgHistory" not in st.session_state:
    st.session_state.dlgHistory = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the chat messages
for message in st.session_state.messages:
    if message[0]:  # User message
        with st.chat_message("human"):
            st.markdown(f"**You:** {message[0]}")
    if message[1]:  # Chatbot response
        with st.chat_message("ai"):
            st.markdown(f"**Chatbot:** {message[1]}")

# Handle user input
if user_query := st.chat_input("Type your investment query here..."):
    # Display user input in chat
    st.chat_message("human").write(user_query)

    # Append the user input to dlgHistory
    st.session_state.dlgHistory.append(DialogueTurn(user_utterance=user_query))

    # Handle the query asynchronously
    async def handle_query():
        with st.spinner("Processing your request..."):
            # Call `compute_next_turn` to process the query
            dlgHistory = compute_next_turn(st.session_state.dlgHistory, user_query)

            # Update the dialog history in Streamlit state
            st.session_state.dlgHistory = dlgHistory

            # Get the chatbot response (agent_utterance) from the latest turn
            chatbot_response = dlgHistory[-1].agent_utterance

            # Append the latest dialog turn to the messages
            st.session_state.messages.append((user_query, chatbot_response))

            # Display the chatbot's response
            st.chat_message("ai").write(chatbot_response)

            # Log timing details for debugging
            logging.info(dlgHistory[-1].time_statement)

    # Run the async function to process the query
    asyncio.run(handle_query())



