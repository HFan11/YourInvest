# Define the input string
data = """
internal; primary str restaurant_id 
internal str name 
internal List[str] cuisines 
internal Enum price 
        cheap
        moderate
        expensive
        luxury
internal float rating 
internal int num_reviews 
internal str address 
internal List[str] popular_dishes 
internal str phone_number 
internal str location 
internal List[str] opening_hours 
internal str summary 
"""

# Split the input into lines
lines = data.strip().split("\n")

# Define the SQL components
sql_lines = []
primary_keys = []

for line in lines:
    # Normalize spaces and split line into parts
    parts = " ".join(line.split()).split(" ")

    # Determine if the column is a primary key
    is_primary = "primary" in parts
    if is_primary:
        parts.remove("primary")

    # Extract internal type (remove if not needed)
    if "internal" in parts:
        parts.remove("internal")

    # Extract the type and column name
    col_type = parts[0]
    col_name = parts[-1]

    # Map the abstract type to SQL types
    if col_type == "str":
        sql_type = "VARCHAR(255)"
    elif col_type == "int":
        sql_type = "INT"
    elif col_type == "float":
        sql_type = "FLOAT"
    elif col_type.startswith("List"):
        sql_type = "TEXT"  # or use a proper relation if using PostgreSQL arrays, etc.
    elif col_type == "Enum":
        sql_type = "ENUM('cheap', 'moderate', 'expensive', 'luxury')"
    else:
        sql_type = "VARCHAR(255)"  # default

    # Create SQL line
    sql_line = f"{col_name} {sql_type}"
    if is_primary:
        primary_keys.append(col_name)
    sql_lines.append(sql_line)

# Create the full CREATE TABLE statement
table_name = "Restaurants"
primary_key_stmt = ", ".join(primary_keys)
sql_statement = "CREATE TABLE %s (\n    " % table_name
sql_statement += ",\n    ".join(sql_lines)
if primary_keys:
    sql_statement += ",\n    PRIMARY KEY (%s)" % primary_key_stmt
sql_statement += "\n);"


print(sql_statement)
