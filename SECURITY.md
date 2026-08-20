# Security and collection policy

This repository is intended for lawful market intelligence using public or explicitly authorized data.

The collector must **not**:
- bypass authentication, CAPTCHAs, access controls, or rate limits;
- exploit vulnerabilities or interfere with the auction platform;
- store hidden reserve prices that are not intentionally public;
- store bidder identities from bid-history payloads;
- treat a last observed bid as a confirmed sale without explicit evidence.

Secrets such as `SUPABASE_SERVICE_ROLE_KEY`, Mercado Libre tokens, and dashboard/admin tokens must exist only in server-side secret stores or environment variables and must never be committed.

Security issues should be reported privately to the repository owner rather than disclosed in a public issue.
