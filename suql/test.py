import os 
os.environ["OPENAI_API_KEY"] = "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"



from suql import suql_execute
# e.g. suql = "SELECT * FROM restaurants WHERE answer(reviews, 'is this a family-friendly restaurant?') = 'Yes' AND rating = 4 LIMIT 3;"
suql = "Your favorite SUQL"

# e.g. table_w_ids = {"restaurants": "_id"}
table_w_ids = "mapping between table name -> unique ID column name"

# e.g. database = "restaurants"
database = "your postgres database name"

suql_execute(suql, table_w_ids, database)
print(suql_execute(suql, table_w_ids, database))