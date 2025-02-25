import re
from functools import partial

import tiktoken


def callable_name(any_callable):
    if isinstance(any_callable, partial):
        return any_callable.func.__name__

    try:
        return any_callable.__name__
    except AttributeError:
        return str(any_callable)


def deep_compare_lists(list1, list2):
    try:
        # First, try the simple Counter method for hashable elements.
        from collections import Counter

        return Counter(list1) == Counter(list2)
    except TypeError:
        # If elements are unhashable, fall back to a method that sorts them.
        # This requires all elements to be comparable.
        try:
            return sorted(list1) == sorted(list2)
        except TypeError:
            # Final fallback: Convert inner structures to tuples if they are lists
            def to_tuple(x):
                if isinstance(x, list):
                    return tuple(to_tuple(e) for e in x)
                return x

            return sorted(map(to_tuple, list1)) == sorted(map(to_tuple, list2))


def generate_var_name(name):
    name = camel_to_snake(name)
    name = name.lower()

    return name


def camel_to_snake(name):
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def extract_code_block_from_output(output: str, lang="python"):
    code = output.split("```")
    if len(code) > 1:
        res = code[1]
        if res.startswith(lang):
            res = res[len(lang) :]
        return res
    else:
        return output


def num_tokens_from_string(string: str, model: str = "gpt-3.5-turbo") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens
