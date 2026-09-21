# Coding Standards

These are stable repository-wide principles. Tool-specific commands and formatter, linter, or type-checker configuration are added only when those tools are approved and introduced.

## General

- Prefer simple, explicit code.
- Avoid speculative abstractions, dead code, and premature framework layers.
- Keep modules focused and use clear names.
- Use explicit types at important boundaries.
- Do not perform unrelated refactors during an implementation unit.

## Python / FastAPI

- Use type hints for public and application-facing functions.
- Use Pydantic for API and structured AI contracts where appropriate.
- Keep route handlers thin.
- Let the application layer coordinate use cases.
- Keep deterministic business behavior in the domain layer.
- Do not let persistence concerns leak into domain logic.
- Domain logic must not call LLMs.
- Handle errors explicitly.
- Use pytest for backend tests.

## TypeScript / Next.js

- Use TypeScript strictness and avoid `any` unless justified.
- Keep components focused.
- Do not duplicate backend business rules in frontend code.
- Use a shared API-access layer once introduced.
- Choose client and server boundaries intentionally.
- Avoid unnecessary state-management libraries.

## Tests

- Test behavior rather than implementation details.
- Add unit tests for deterministic domain logic.
- Add integration or API tests for API boundaries.
- Cover meaningful user workflows with browser tests.
- Add contract tests and evals when AI capabilities are introduced.
- Add regression tests for meaningful bug fixes.

## Dependencies

- Every dependency must solve a current implementation-unit requirement.
- Do not add dependencies for trivial helpers.
- Do not introduce future-scope infrastructure.

## Security and configuration

- Never commit credentials or secrets.
- Treat user uploads and external data as untrusted.
- Validate boundary input.
- Do not log secrets or sensitive raw values.
- Put environment-specific configuration in environment configuration, not hardcoded constants.

## Change discipline

- Work on the current implementation unit only.
- Do not add opportunistic future-unit work.
- Do not incidentally edit source-of-truth specifications.
- Do not perform large cleanup or refactoring unless the active unit requires it.
