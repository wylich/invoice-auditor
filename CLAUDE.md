# Agent instructions:

The most important thing in this repo is simplicity.
If my request requires design decisions, always ask many follow-up questions to clarify.
Always challenge what I propose, if you don't think it's the most appropriate way.


## Coding preferences
* Prefer Pydantic over dataclasses
* Always require absolute file paths
* Use absolute import paths
* Use pathlib for paths
* You will never under any circumstances expose the contents of .env files

Use uv package manager to run things.