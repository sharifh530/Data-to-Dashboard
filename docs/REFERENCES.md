# Technical references

Primary documentation consulted on 2026-09-16. Recheck APIs and compatibility while implementing; no specific library versions are pinned by these documents.

- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts): persistent pauses, stable identifiers, and replay/idempotency behavior.
- [gVisor security model](https://gvisor.dev/docs/architecture_guide/security/): runtime boundary and limits of host exposure reduction.
- [MDN iframe reference](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe): sandbox flags and separate-origin concerns.
- [scikit-learn common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html): training/test separation and preprocessing pipelines. Search also returned the [versioned 1.5 guidance](https://scikit-learn.org/1.5/common_pitfalls.html); this is not a recommendation to pin that version.

Numeric limits, product choices, and release targets in this repository are project design proposals, not claims from these sources. Add source links to later ADRs when relying on platform-specific behavior.
