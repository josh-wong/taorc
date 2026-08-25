# Language map

Load this file when the language is Go, Rust, Java, or C#. It records where a
catalog rule lands differently than its general statement suggests.

The rules themselves do not change by language. What changes is the idiom that
satisfies them, and a rule applied through the wrong language's idiom produces
code that is technically compliant and obviously foreign — which costs a reader
more than the rule saved.

Precedence entry 2 governs every entry below: where a project's convention
differs from what this file says, the project wins.

## Where the idiom differs

Each cell is the form that satisfies the rule in that language, not a different
rule. Where the last column pairs two forms with a slash, Java comes first and
C# second — the two agree less often than sharing a column suggests, and the
rows below are the ones where they part company.

| Rule  | Python                        | TypeScript / JavaScript    | Go                                   | Rust                            | Java / C#                              |
| ----- | ----------------------------- | -------------------------- | ------------------------------------ | ------------------------------- | -------------------------------------- |
| `N7`  | `snake_case`, `UPPER` consts  | `camelCase`, `PascalCase`  | `MixedCaps`; case sets export        | `snake_case`, `CamelCase` types | `camelCase` / `PascalCase` methods     |
| `N10` | `is_`/`has_` prefix           | `is`/`has`/`should` prefix | often a bare adjective: `ok`         | `is_`/`has_`, or bare adjective | `is`/`has`; C# also `Can`              |
| `E4`  | `if items:`                   | `if (items.length)`        | `if len(items) > 0` is idiom         | `if !items.is_empty()`          | `items.isEmpty()` / `items.Count == 0` |
| `V4`  | no binding-level `const`      | `const` by default         | `const` only for compile-time values | `let` is immutable by default   | `final` / `readonly`                   |
| `F5`  | guard clause + `raise`        | guard clause + `throw`     | `if err != nil { return ... }`       | `?` operator                    | guard clause + `throw`                 |
| `C14` | docstring, first line summary | JSDoc `/** ... */`         | `// FuncName ...` godoc form         | `///` rustdoc, `# Examples`     | Javadoc / XML doc comments             |

Two of those pairings are worth stating outright, because sharing a column
hides them. C# names methods `PascalCase` where Java names them `camelCase`.
And C# collections have no `isEmpty()` at all: `List<T>` and arrays expose
`Count`, LINQ offers `Any()`, and the types that do carry the concept spell it
`IsEmpty`, a property rather than a method.

## Go

**`N10` and bare adjectives.** Go frequently names booleans without a prefix —
`ok`, `found`, `done`. This is idiomatic and satisfies the rule's intent, which
is that the reader can tell what `true` means. Do not rewrite `ok` to `isOk`.

**`E4` and emptiness.** `len(x) > 0` is the idiom, not a violation. Go has no
truthiness, so the comparison is the direct statement of the condition, which is
exactly what `E4` asks for.

**`F5` and error returns.** The early-return guard is already the language's
central pattern. Where the general rule says "handle the special case and return
immediately", Go says `if err != nil { return nil, err }`, and a function that
nests its happy path inside `if err == nil` is fighting the language.

**`N5` and short names.** Go's convention scales name length to scope more
aggressively than most languages — single-letter receivers, `i`, `b` for a
builder. That is `N5` applied consistently, not a violation of `N1`.

**`N7` and export.** Capitalization is not a style choice; it decides
visibility. A rename that changes the first letter changes the API, which makes
`X3` a hard rule here rather than a cautious one.

## Rust

**`V4` is the default.** `let` bindings are immutable unless declared `mut`, so
the rule mostly enforces itself. What it asks for in Rust is narrower: do not
reach for `mut` before checking whether a different formulation avoids it.

**`F5` and `?`.** The `?` operator is the guard clause, compressed. It satisfies
`F5` and `F6` at once, and expanding it into an explicit `match` for the sake of
visible control flow makes the code longer and less idiomatic.

**`N10` and `is_`.** Rust's convention is `is_`/`has_` for predicates, and bare
adjectives for fields. Both read as questions at the use site.

**`C14` and doc tests.** Rustdoc examples compile and run, which makes `C15`
(show the corner case with a worked example) unusually valuable here: the
example cannot drift out of date without the build noticing.

## C# and Java

**`N8` versus ceremony.** Both languages carry naming conventions that look
verbose against `N8` — `AbstractSessionFactoryBean`, `IReadOnlyCollection`. The
rule asks you not to add words that carry no information; it does not ask you to
strip conventions a reader relies on to know what kind of thing they are looking
at. C#'s `I` prefix for interfaces is information.

**`V4` and `final` / `readonly`.** Available and underused. Applying them is the
direct expression of `V4`, but they are also the sort of change that touches
many lines for no behavior difference — so `X1` applies: do it in its own
commit, not inside a diff about something else.

**`N15` and property conventions.** C# properties are expected to be cheap. A
property that performs I/O or an expensive computation violates `N15` more
sharply than an equivalently named method would, because the call site does not
even look like a call.

**`C14` and XML doc comments.** The structured form makes it easy to write a
comment that restates the signature — one `<param>` per parameter, each naming
the parameter again. That is `C1` in a structured wrapper. Fill in the tags that
carry information and leave the rest out.

## Python and TypeScript

These two are the catalog's default idiom, so this file records only the traps.

**Python `E4` and truthiness.** `if items:` is idiomatic, and it is also where
`E4`'s correctness exception bites hardest: `0`, `""`, `[]`, and `None` are all
falsy, so the change from `if x is not None:` to `if x:` is not equivalence-
preserving. Precedence entry 1 governs.

**Python `N7` and the leading underscore.** A single underscore is a convention
about intent, not a compiler-enforced boundary, but it is the signal `S7` and
`X3` rely on to tell module-private from exported. Treat a name without one as
exported unless the module defines `__all__`.

**TypeScript `V4` and `const`.** `const` prevents rebinding, not mutation. A
`const` array whose contents change still costs the reader what `V4` is trying
to save; use `readonly` types where the intent is that the value does not
change.

**TypeScript `N3` and branded types.** Where a unit is easy to get wrong, a
branded or nominal type makes the misuse a compile error rather than a naming
convention. That is stronger than what `N3` asks for and worth reaching for at
API boundaries.
