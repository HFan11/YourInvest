from setuptools import find_packages, setup

# Package metadata
name = "worksheets"
version = "0.1.0"
description = "KITA is a programmable framework for creating task-oriented conversational agents that are designed to handle complex user interactions."
author = "Harshit Joshi"
author_email = "harshitj@stanford.edu"

# Specify the packages to include. You can use `find_packages` to automatically discover them.
packages = find_packages(
    where=".", include=["worksheets*"], exclude=["frontend*", "baselines*"]
)

# with open("README.md", "r") as f:
#     long_description = f.read()

# with open("requirements.txt", "r") as f:
#     install_requires = f.read().splitlines()


# Additional package information
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
]

# Call setup() with package information
setup(
    name=name,
    version=version,
    description=description,
    author=author,
    author_email=author_email,
    packages=packages,
    classifiers=classifiers,
)
