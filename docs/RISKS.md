# Assumptions, open questions, and risks

These choices need resolution during implementation; they do not block writing docs or provider-independent scaffolding.

| Question | Working assumption | Resolve by |
| --- | --- | --- |
| Audience/deployment | Authenticated portfolio MVP, then small hosted pilot | Before production auth/deployment |
| LLM provider/model/budget | Adapter with fake provider for development; no paid default selected | Before live-agent integration |
| Hosting/runtime | Linux service deployment with independently enforced execution isolation | B01 |
| Authentication provider | Managed OIDC-compatible provider, selected later | B04 |
| Dataset domain/privacy | Synthetic/public non-sensitive data for demonstration | Before accepting external users |
| Branding/design | Working name Data-to-Dashboard; accessible neutral analytics UI | B12 |
| Delivery date/team | No deadline or staffing assumptions | When estimates are requested |

## Risk register

| Risk | Impact | Mitigation / trigger |
| --- | --- | --- |
| Sandbox escape or weak hosting controls | Critical | B01/public-release gates; fail closed if enforcement cannot be proven |
| Generated React exfiltration or CPU freeze | Critical/high | Minimal iframe capability, restricted CSP/data, browser tests, outer fallback; reduce supported syntax if necessary |
| Misleading cleaning/model claims | High | Provenance, train-only preprocessing, metric references, conservative defaults |
| Private content sent to provider/logs | High | Minimal masked context, disclosure, log inspection, provider review |
| LLM variance and invalid output | High | Typed validation, bounded repairs, fixed test provider, fallback modes |
| Queue replay/cancellation race | High | Leases, generations, publication transactions, fault injection |
| Costs/latency exceed useful limits | Medium/high | Token/time caps, per-user quotas, benchmark before limit increases |
| Large categorical expansions or parser abuse | High | Decoded/feature/resource caps and isolated parsing |
| Scope expands before core is reliable | Medium | MVP exclusions and dependency-ordered milestones |
| Dependency/runtime drift | Medium | Exact lockfiles/images, compatibility checks, controlled upgrades |

An open question is not an implemented capability. Record resolution in ADRs and memory, and update affected requirements instead of letting contradictory defaults accumulate.
