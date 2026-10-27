# Invariant-evidence space semantic checks

The Python validator complements the JSON Schemas. It enforces:

- defaults are inside their typed domains;
- identifiers and references are unique and closed-world;
- every expression uses the versioned, bounded language;
- preferred-region defaults satisfy the region and every hard constraint;
- the default selection policy is declared and fallback is explicit;
- only lockable axes may be locked;
- immediate/frame-boundary application is forbidden for simulation, world-generation, and persistence-schema effects;
- adaptive frame mutation affecting simulation determinism is refused;
- lowering target capability references resolve through the capability dictionary;
- absent capability declarations are `UNDECLARED`, not `UNSUPPORTED`;
- `MEASURED` declarations bind host, adapter version, and evidence root;
- fallback and experimental declarations carry their status-algebra data;
- revision records bind predecessor and trigger-evidence roots.

Structural validity is not correctness, admission, or evidence that a realizer
actually provides a declared capability.
