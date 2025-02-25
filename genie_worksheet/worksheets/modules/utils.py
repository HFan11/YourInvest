import difflib
import io
import tokenize

from termcolor import colored


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def input_user() -> str:
    try:
        user_utterance = input(bcolors.OKCYAN + bcolors.BOLD + "User: ")
        # ignore empty inputs
        while not user_utterance.strip():
            user_utterance = input(bcolors.OKCYAN + bcolors.BOLD + "User: ")
    finally:
        print(bcolors.ENDC)
    return user_utterance


def print_chatbot(s: str):
    print(bcolors.OKGREEN + bcolors.BOLD + "Agent: " + s + bcolors.ENDC)


def print_user(s: str):
    print(bcolors.OKCYAN + bcolors.BOLD + "User: " + s + bcolors.ENDC)


def print_complete_history(dialogue_history):
    for turn in dialogue_history:
        print_user(turn.user_utterance)
        print_chatbot(turn.system_response)


def print_diff(text1, text2):
    # Split the texts into lines to compare them
    text1_lines = text1.strip().splitlines()
    text2_lines = text2.strip().splitlines()

    # Create a Differ object
    differ = difflib.Differ()

    # Calculate the differences between the two texts
    diff = list(differ.compare(text1_lines, text2_lines))

    # Process the diff output to add colors
    for line in diff:
        if line.startswith("+ "):
            # Text in text2 but not in text1
            print(colored(line, "green"))
        elif line.startswith("- "):
            # Text in text1 but not in text2
            print(colored(line, "red"))
        elif line.startswith("? "):
            # Marks the changes in "change" lines with '^'
            print(colored(line, "blue"))
        else:
            # Lines that are the same in both texts
            print(line)


def assert_with_message(actual, expected, code=True):
    if actual != expected:
        if code:
            print_diff(normalize_code(actual), normalize_code(expected))
        else:
            raise AssertionError(f"expected\n{actual}\n to be\n{expected}")


def normalize_code(code: str) -> str:
    """Normalize code by removing comments, whitespace and newlines.
    We also need to normalize quotes and spaces around operators."""

    tokens = tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline)
    normalized_tokens = []
    for token in tokens:
        token_type, token_string, _, _, _ = token
        if token_type == tokenize.COMMENT:
            continue
        if token_type == tokenize.STRING:
            token_string = repr(token_string.replace("'", "").replace('"', ""))
        normalized_tokens.append(token_string)

    return "".join(normalized_tokens).replace("utf-8", "")


if __name__ == "__main__":
    # Test the normalize_code function
    code = """user_info_0 = UserInfo(user_task='Book Restaurant')
restaurant_db_0 = RestaurantDB(location='Palo Alto', query="SELECT *, summary(reviews) FROM restaurants WHERE location = 'Palo Alto' LIMIT 1;")
"""

    print(normalize_code(code))
