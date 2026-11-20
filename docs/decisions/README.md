# Architecture Decisions

This directory contains short Architecture Decision Records (ADRs) only when a decision needs durable context beyond the approved specifications.

Create an ADR only when:

- a new architecture decision is required;
- an approved architecture decision must change;
- meaningful alternatives were considered;
- the rationale will matter to future maintainers.

Do not create ADRs for ordinary implementation choices, local refactors, naming, routine library usage already implied by the architecture, or decisions already fully captured in an approved specification.

An ADR must not silently override the Product Specification or Technical Architecture. Changes to approved V1 architecture require explicit human approval.

## Contents and usage

Currently this README is the only tracked file in this directory; there are no
standalone ADRs or required ADR templates. Start with the
[Product Specification](../specs/SourcePilot-Product-Specification-v0.2.md),
[Technical Architecture](../specs/SourcePilot-Technical-Architecture-v0.2.md) and
[Implementation Plan](../specs/SourcePilot-Implementation-Plan-v0.2.md), in that
authority order, before proposing a decision.

Use the [development workflow](../development/WORKFLOW.md) to plan and obtain
approval for an architecture change. An ADR should capture the decision, relevant
alternatives, rationale and consequences when durable context is needed. This
directory has no executable setup step; use [local development](../local-development.md)
to run the application and [repository instructions](../../AGENTS.md) for scope
and approval boundaries.
