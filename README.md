# Investment Conversational Virtual Agent with Deep Learning

## Introduction
This project aims to create a conversational virtual agent that provides personalized investment recommendations. By integrating Large Language Models (LLMs), structured data retrieval (via SUQL), offline embedding, and a free-text server, our system offers tailored, user-centric financial guidance. Users can input their financial profile—age, risk tolerance, investment timeline, and budget—and the agent returns a diversified portfolio aligned with their objectives.

## Methodology
Our approach involves several key steps to ensure both the depth and relevance of recommendations:

1. **User Information Collection:**  
   Genie Worksheet guides the conversation to collect essential user details (age, budget, risk tolerance, etc.). This information seeds the generation of a preliminary investment plan.

2. **Offline Data Preparation:**  
   We acquire historical market data and incorporate FinQA-based Q&A content. Using FAISS embeddings for similarity search and a free-text server for flexible content retrieval, we ensure that the agent has access to both structured and unstructured financial insights.

3. **Advanced Search and Filtering (SUQL):**  
   The SUQL method enables structured querying of the embedded dataset. By translating user requirements and preferences into optimized queries, the system filters and narrows down asset options efficiently.

4. **Reasoning via Parser Prompt:**  
   We combine mathematical reasoning (calculating expected returns, volatility, and other financial metrics) with LLM reasoning (qualitative evaluation, risk assessment, and user-centric insight) to refine the initial plan.

5. **Final Plan Generation and Refinement:**  
   A final prompt integrates both quantitative and qualitative results, producing a well-rounded investment plan. The system supports iterative refinements—if the user wishes to adjust goals or risk parameters, the plan can be updated accordingly.

## Installation and Setup
Follow the steps below to run the application on your machine:

1. **Install Dependencies:**
   *Ensure you have Python 3.9+ installed.

   ```bash
   pip install -r requirements.txt
   ```
2. **Set up PostgreSQL 17:**
   Install PostgreSQL 17 on your machine. For instructions, refer to the PostgreSQL documentation.

   Configure Language Input for Python 3:
   ```bash
   CREATE EXTENSION plpython3u;
   ```

   Then, copy all functions in custom function.sql in the Query Tool.

3. **Prepare the Data and Populate the Database:**
   
   Download the investment data section that you are intereted in from https://stooq.com/.
   Then, navigate to the data_script directory and use the script to pre-process the data and calculate various fanicial metrics.
   Finally, load the provided data into your PostgreSQL database.
   Ensure that the database credentials in your code are correctly set to connect to the PostgreSQL instance you’ve created.


4. **Run FAISS Embedding and Free-Text Servers:**

   ```bash
   python faiss_embedding.py
   python free_text_server.py
   ```
These commands will run local servers that handle embedding queries and free-text processing.

5. **Install Genie Worksheet package:**
   ```bash
   cd  genie_worksheet
   pip install -e .
   ```

6. **Launch the Streamlit App:**
 
   In a separate terminal, activate your environment and run:

   ```bash
   streamlit run streamlit_app.py --server.port 8505
   ```

7. **Optionally, run the following command if any packege is reporting errors:**
   ```bash
   pip install pydantic
   pip install orjson
   pip install jiter
   pip install regex
   pip install termcolor 
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   ```

The Streamlit application will start locally, and to make sure the port is different from faiss_embedding and free_text_server.



