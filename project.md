# AI cli

small useful ai cli

shoudl be based on DSPy! (whatever that would look like)

should have a few specifci use-case. a usecase is a first class citizen (maybe the only one?)

use cases should be defined in some code files so an advanced user could change them/add new ones.

a usecase should then be a subcommand.

the regular bin exec should be 'ai'
and subcommand/usecases e.g.

## `ask`

just ask a question and it will answer it, if needed with context. no file editing, just some commands that do not have side effects.

## `task`

get's whatever task, creates a todo (all toolcall, structured output stuff) and follow that through.

---

in general it should use most modern things, structured outputs for the AI stuff. use the newest gpt-5 models (they have different format under the hood so we need a good lib that handles that! It's only a few days old so yuo can't rely on your information)
