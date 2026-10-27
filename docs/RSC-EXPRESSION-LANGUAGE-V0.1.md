# MIW RSC expression language v0.1

Status: local engineering candidate. Authority effect: `NONE`.

The language is deliberately smaller than Python. It permits identifiers naming
declared axes; string, integer, Boolean and null literals; comparisons (`==`,
`!=`, `<`, `<=`, `>`, `>=`); Boolean `and`, `or`, and unary `not`; and
parentheses. Calls, attributes, indexing, comprehensions, arithmetic, assignment,
imports, and executable names are refused.

Every constraint and preferred-region predicate declares
`expression_language: miw.rsc.expr.v0.1`. Unknown axis references and unsupported
syntax refuse before selection or lowering.
