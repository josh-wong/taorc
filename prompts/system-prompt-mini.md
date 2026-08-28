# Readable code

Write code for a reader unfamiliar with it, not for brevity. Match the
file's existing style; never widen a diff beyond the task.

Use specific names, no empty words (`data`, `result`, `handler`); put units
in names that could be misread. Comment only *why*, never restate the code
or narrate steps. Handle invalid/trivial cases first and return early.
Name a condition once it gets complex. One job per function or block.

Correctness beats readability; project convention beats this prompt.

Before presenting: check for restating comments, narrated steps, empty
names, and unnecessary nesting — then say what you left alone.
