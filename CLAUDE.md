# Task
The idea is called promptview. This is for management and versioning of prompts. We will describe what the problem is and how to approach the solution.

## Problem
* People are working on agentic AI and almost all applications have large prompts which become very hard to manage and have and overview of.
* There are prompt versioning methods given in langfuse and / or langsmith but it is hard to integrate them and look for changes in the same.

## Proposed Solution
* Make a pip installable library.
* That can explore any codebase and find all the prompts and version it with an init command.
* Make it like git (so that developers do not have to learn new commands).
* Make it compatible with langfuse and langsmith prompt versioning (default none is linked).
* Make a UI where each prompt can be viewed as a graph where each node is a high level entity without a lot of text.
* Users can add or delete a node and based on that the prompt can be refined.
* This should be project specific you need init stuff locally.

Use UV