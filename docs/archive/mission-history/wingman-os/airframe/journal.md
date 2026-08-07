<!-- wingman-archive-metadata
{
  "schema_version": 1,
  "classification": "historical_noncanonical",
  "canonical_replacement": "docs/missions/wingman-os/airframe/mission.md",
  "archived_from": "docs/missions/wingman-os/airframe/journal.md"
}
-->

> [!WARNING]
> **HISTORICAL / NONCANONICAL MISSION EVIDENCE.** The sole canonical
> mission record is [`docs/missions/wingman-os/airframe/mission.md`](../../../../missions/wingman-os/airframe/mission.md).
> Every lifecycle, approval, commit, publication, and next-gate claim in
> the preserved body below is time-bound historical evidence and is not
> authoritative current status.

# Mission 027 — Wingman Defines the Boundary

**Call Sign:** Airframe  
**Product:** Wingman OS  
**Status:** Complete  
**Date:** July 31, 2026

**Implementation commit:** `e1570b0c0d759933eaa0d2d0b48839051337d441`

**Commit subject:** `Establish product-neutral Wingman Airframe`

---

## Objective

Establish enforceable ownership and dependency boundaries among Wingman Core, the Shared Product Framework, Atlas, and Product Configuration without changing the physical Ledger.

Mission 027 began with a broader ambition: convert the Ledger to a product-neutral version-4 schema and build the authorization, locking, backup, restoration, readiness, and recovery machinery needed to perform that conversion safely.

Independent review exposed a more important architectural truth:

> Logical ownership and physical storage transition are separate missions with different risk profiles.

Airframe was therefore deliberately de-scoped. The completed mission retains the existing version-3 Ledger schema as a deprecated legacy-storage implementation while moving academic meaning out of generic Core and Shared APIs.

The mission had to preserve:

* Upload and reprocessing behavior.
* Retrieval, Chat, Briefing, and Library behavior.
* CLI, terminal, and Streamlit behavior.
* Existing import, function, and patch surfaces.
* The original 141-test behavioral baseline.
* Every live Ledger, WAL, SHM, registry, embedding, source, and content file.

The governing architectural principle became:

> Product meaning enters through composition and configuration. Core and Shared mechanisms remain product-neutral, even while a private adapter translates to legacy product-shaped storage.

---

## Deliverables

### 1. Machine-Readable Ownership Manifest

Added a compact Airframe manifest that declares:

* The modules owned by Core, Shared Product Framework, Atlas, and Product Configuration.
* The permitted dependency direction between those layers.
* The limited set of modules allowed to consume active product configuration.
* External dependency allowances.
* Explicit transitional exceptions required by the current flat module layout.

The manifest is intentionally reviewable data rather than a new runtime framework. It gives architecture tests and human reviewers one shared statement of ownership.

### 2. Product-Neutral Knowledge Ingestion

Extracted the generic ingestion mechanism into Core.

Core now owns:

* File loading and normalization.
* Chunking.
* Content hashing.
* Embedding orchestration.
* Persistence orchestration.
* Generic metadata transport.

Atlas retains the academic enrichment policy and supplies it as a callback at the composition boundary.

The historical `document_ingestion` module remains as a compatibility facade. Existing callers, imports, CLI behavior, and patch points continue to work while the implementation underneath follows the new ownership direction.

### 3. Product-Neutral Retrieval

Separated retrieval execution from Atlas query interpretation.

Core now executes a supplied retrieval plan. It does not decide what academic vocabulary means or infer Atlas-specific filters.

Atlas remains responsible for:

* Interpreting a user query.
* Applying academic meaning.
* Constructing the plan given to Core.
* Composing the generic retrieval result into Atlas behavior.

The existing retrieval entry point remains available through a compatibility wrapper.

### 4. Shared Conversation Context

Moved reusable conversation-context extraction into the Shared Product Framework.

The shared mechanism can identify generic conversational context without importing Atlas academic policy. Atlas composes it into the existing Wingman service and re-exports the supported names so repository callers do not break.

### 5. Minimal Product Configuration

Added a deliberately small product-configuration boundary.

Configuration supplies:

* Product identity.
* The product-owned program field.
* The product-owned academic-year field.

These values remain opaque to Core and Shared code. Atlas gives them meaning.

The configuration object is consumed only at approved composition roots. It is not a service locator, plugin framework, or premature implementation of Mission 028.

### 6. Minimal Product Contract

Added only the product-neutral contract needed by Airframe:

* Small immutable data structures for product-facing composition.
* Generic source metadata.
* Collision validation for reserved source-metadata fields.

The contract does not define future agent infrastructure, broad plugin behavior, or speculative product extension points.

### 7. Generic Metadata Flow

Reworked ingestion and registry paths so generic layers pass product metadata without interpreting it.

The intake service accepts opaque product metadata while preserving deprecated compatibility arguments for existing callers.

The source registry transports generic metadata without owning the meaning of `program` or `academic_year`.

Library and interface paths preserve this metadata through existing user flows.

### 8. Private Version-3 Legacy-Storage Adapter

Kept the physical Ledger at schema version 3.

A narrowly scoped private adapter in the Ledger source repository translates between:

* Product-neutral metadata exposed to the application.
* The legacy `program` and `academic_year` physical columns.

Its read rules are:

* A present metadata key is authoritative, including an explicit `null`.
* A missing metadata key may fall back to a non-null legacy column.
* Conflicting legacy-column values do not overwrite explicit metadata.
* Unrelated nested dictionaries and lists are preserved exactly.
* Reads do not mutate the stored or caller-owned metadata object.

Its write rules are:

* Generic metadata is persisted as metadata.
* Recognized legacy keys are mirrored into the version-3 physical columns.
* Partial registration merges preserve untouched metadata.
* Complete registry replacement replaces the complete snapshot and removes omitted sources.
* Reprocessing preserves product metadata.
* Persistence remains compatible with Ledger schema versions 1 through 3.

This adapter is an anti-corruption boundary, not a claim that the physical schema is product-neutral.

### 9. Atlas Composition

Atlas remains the product layer and owns academic interpretation.

Atlas composes:

* Product configuration.
* Academic query interpretation.
* Concept enrichment.
* Product metadata.
* Core ingestion and retrieval.
* Shared conversation context.

Core and Shared receive values and callbacks; they do not import Atlas policy to discover what those values mean.

### 10. Compatibility Surfaces

Preserved supported repository behavior while moving implementation ownership.

Compatibility facades retain:

* Historical module imports.
* Public functions used by the application and tests.
* Existing CLI entry points.
* Existing monkeypatch and test seams.
* Streamlit, terminal, and service composition.

The wrappers are transitional seams. They allow architectural extraction without forcing an unrelated repository-wide import migration into Airframe.

### 11. Bounded Architecture Review Automation

Added static architecture tests that inspect ordinary Python structure without pretending to provide runtime security.

The tests verify:

* Declared layer ownership and dependency direction.
* Product-configuration consumer boundaries.
* Forbidden academic vocabulary in new Core and Shared code.
* Direct imports, aliases, and relative imports.
* Simple constructed static strings.
* Direct dynamic imports through `__import__()` and `importlib.import_module()`.
* Exact semantic identities for documented transitional exceptions.
* Duplicate permitted exceptions through multiset comparison.
* Agreement among the manifest, source layout, and Airframe documentation.

The evaluator understands bounded static forms:

* String constants.
* String addition.
* Static joined strings and f-string fragments.

It deliberately does not execute variables, calls, arbitrary expressions, or runtime-formatted values.

These tests are architecture review automation. They raise the cost of ordinary accidental boundary violations; they are not a sandbox or adversarial runtime enforcement system.

### 12. Behavioral and Integration Coverage

Added focused tests for the new seams:

* Airframe composition.
* Architecture boundaries.
* Version-3 adapter behavior.
* Real ingestion and reprocessing.

The adapter tests cover:

* Column-only legacy records.
* Metadata-only records.
* Agreeing and conflicting values.
* Null and missing values.
* Partial updates.
* Complete snapshot replacement and source removal.
* Nested JSON preservation.
* Read immutability.
* Schema-version compatibility.

The integration tests exercise real XLSX ingestion and reprocessing, including preservation of program, academic year, and nested product metadata.

No permissive production mock was needed to prove those paths.

### 13. Explicit Ledger Transition Deferral

Removed Migration 4 and all infrastructure that existed only to authorize or protect that transition.

Airframe does not include:

* A physical version-4 schema conversion.
* Migration authorization tokens.
* Global readiness gates.
* A new application locking platform.
* Exclusive maintenance-window behavior.
* Backup or restoration production systems.
* Live-migration commands.
* Crash-recovery orchestration.

Those requirements belong to a dedicated Ledger Transition mission after Assurance v1 and its Crew Chief prerequisites.

Approval of the Airframe code commit does not authorize a future Ledger migration.

### 14. Documentation and Verification

Updated the repository architecture documentation to describe:

* Current logical ownership.
* Dependency direction.
* Atlas composition.
* The private legacy adapter.
* Transitional compatibility surfaces.
* The bounded nature of architecture tests.
* The explicit deferral of physical Ledger conversion.

Final verification established:

* 141 original tests remained byte-for-byte unchanged and passed.
* 26 additive tests passed.
* The complete 167-test suite passed.
* Source compilation passed.
* Review-time `git diff --check` returned no output. This journal was then an
  untracked file and therefore outside that command's scope. The final
  commit's `git show --check` reports only the intentional Markdown
  hard-line-break spaces on metadata lines 3–5 of this journal.
* The working tree remained unstaged and uncommitted during review. After
  approval, the completed implementation was committed as
  `e1570b0c0d759933eaa0d2d0b48839051337d441` (`Establish product-neutral
  Wingman Airframe`).
* No real model credential or network model call was used.
* No live migration, restoration, or live-data write occurred.

---

## Engineering Concepts

### 1. Logical Architecture vs. Physical Storage

A logical boundary answers:

> Which layer owns this concept and may depend on which other layer?

A physical transition answers:

> How do durable records move safely from one representation to another?

The first can be established while retaining a legacy schema. The second requires operational guarantees that cannot be manufactured merely by adding more code to the first mission.

Separating them reduced both implementation scope and migration risk.

### 2. Dependency Inversion

Core provides mechanisms. Atlas supplies policy.

Instead of Core importing academic logic, Atlas passes:

* Enrichment callbacks.
* Retrieval plans.
* Product metadata.
* Product configuration.

This reverses the dependency without requiring a broad framework.

### 3. Composition Roots

Product meaning should enter the system at a small number of visible locations.

The main application and Streamlit entry point are approved configuration consumers. They assemble Core, Shared, Atlas, and configuration behavior.

Restricting composition makes ownership easier to review and accidental product coupling easier to detect.

### 4. Anti-Corruption Layer

The version-3 adapter prevents the legacy physical schema from defining the new public application model.

Outside the repository boundary, callers see generic metadata.

Inside the boundary, the adapter mirrors selected keys into legacy columns for compatibility.

This isolates technical debt without denying that it exists.

### 5. Compatibility Facade

A compatibility facade preserves a supported public surface while forwarding behavior to a new owner.

This pattern made it possible to:

* Move implementation without breaking callers.
* Preserve CLI and application entry points.
* Keep patch surfaces stable.
* Avoid a mass import rewrite.

The facade must remain thin. If it begins owning new policy, it stops being a compatibility seam and becomes duplicated architecture.

### 6. Opaque Metadata

Generic code may transport a value without interpreting it.

Core can persist `program` and `academic_year` as metadata while remaining product-neutral if:

* It does not attach academic semantics to those keys.
* It does not branch on their meaning.
* Atlas declares and supplies them.
* The only physical-column knowledge stays inside the private adapter.

Opacity is an ownership rule, not a claim that values have no meaning anywhere.

### 7. Semantic Static Checks

Line numbers and formatting hashes make architecture exceptions fragile for the wrong reasons.

Airframe identifies transitional exceptions by semantic identity:

* Exact module.
* Exact consuming function or immutable statement.
* Normalized vocabulary or legacy-column identity.

This allows harmless formatting and line movement while rejecting:

* Movement to an unauthorized owner.
* Identity changes.
* Duplicated exceptions.
* Ordinary alias and relative-import bypasses.

### 8. Deliberate De-Scoping

De-scoping is not merely deleting features. It is re-stating the mission around the smallest coherent outcome.

Airframe retained code that established architectural ownership and removed code whose only purpose was to make Migration 4 possible.

The criterion was not how much effort had already been spent. It was whether each abstraction still reduced risk in the revised mission.

---

## Key Lessons

### 1. Architecture Can Advance Before Storage Changes

The public model does not have to wait for the physical schema to become ideal.

A private translation boundary can establish the desired ownership now while preserving durable compatibility.

### 2. Destructive Transitions Deserve Their Own Mission

Migration authorization, multiprocess locking, immutable backups, crash-safe restoration, and rollback operations are not supporting details.

Together they form a transition system with its own threat model, tests, operational procedures, and approval gates.

Combining them with a logical refactor made both outcomes harder to verify.

### 3. Legacy Details Must Stay Private

Retaining version-3 storage is safe only if new Core and Shared APIs do not normalize the legacy academic columns into permanent public concepts.

The adapter is valuable because its scope is narrow, explicit, and replaceable.

### 4. Explicit Null Is Data

When metadata explicitly contains `null`, the adapter must not silently replace it with a value from a legacy column.

Presence and truthiness are different. Compatibility code must preserve that distinction.

### 5. Partial and Complete Writes Are Different Operations

A partial source registration should merge and preserve untouched metadata.

A complete source-registry save should replace the snapshot and remove omitted records.

Conflating these operations creates silent stale-data or data-loss bugs.

### 6. Configuration Supplies Meaning

Core should not infer which fields are academically significant.

Product configuration declares product-owned fields, and Atlas interprets them. This keeps the mechanism reusable without erasing product behavior.

### 7. Compatibility Is a First-Class Constraint

Architectural cleanliness that breaks real upload, reprocessing, retrieval, CLI, or UI behavior is not a successful refactor.

Thin wrappers allowed the dependency direction to improve while the supported surface remained stable.

### 8. Architecture Tests Need Honest Limits

Static tests can catch common violations and ownership drift.

They cannot prove that arbitrary runtime behavior is safe. Making that limitation explicit produces a smaller and more trustworthy test system than escalating toward pseudo-security.

### 9. Existing Tests Are Part of the Contract

Keeping all original tests byte-identical made the baseline meaningful.

New tests could then prove the new architectural seams without rewriting history to make the refactor appear compatible.

### 10. Exercise Real Seams

The highest-value integration tests used real XLSX upload and reprocessing paths.

This proved that product metadata survived the boundary changes in the behavior users actually depend on.

### 11. Sunk Cost Is Not Architecture

Code written for the original Migration 4 scope was removed when the mission changed.

Useful transition requirements were retained as future design knowledge, but unsafe or unnecessary production machinery did not remain merely because it had taken effort to build.

### 12. Approval Must Be Precisely Scoped

Approval of a product-neutral Airframe commit means the logical boundary is ready to enter source control.

It does not authorize:

* A live Migration 4.
* A maintenance window.
* A Ledger backup or restore.
* A schema cutover.
* Use of a live authorization mechanism.

Those actions require a future dry run and separate CEO authorization.

---

## Interview Takeaway

If asked how to make a product-specific system more modular without risking durable data:

> I separate logical ownership from physical migration. I move reusable mechanisms into product-neutral layers, keep product policy at the composition boundary, and hide the old schema behind a narrow anti-corruption adapter. I preserve public behavior through thin compatibility facades, prove the storage edge cases and real ingestion path, and use bounded static checks to catch ordinary architecture drift. I defer the destructive transition until locking, backup, restoration, concurrency, dry-run, and approval requirements can be treated as a dedicated operational system.

The important point is not that the legacy schema disappears immediately.

The important point is that new architecture no longer spreads its assumptions.

---

## Architectural Decision

### Decision

Mission 027 establishes logical Airframe boundaries while intentionally retaining Ledger schema version 3 as deprecated legacy storage.

### Why

The logical refactor is independently valuable and testable.

The physical transition requires a larger safety system:

* Exact-transition authorization.
* Cooperative and exclusive locking.
* Multiprocess initialization control.
* WAL-safe backup identity.
* Crash-safe restoration.
* Schema and migration-history readiness.
* Semantic and byte-preservation checks.
* Dry-run and rollback procedures.
* Separate executive approval.

Implementing those concerns inside Airframe expanded the mission far beyond the ownership problem and introduced more risk than it removed.

### Alternatives Rejected

#### Perform Migration 4 in Airframe

Rejected because the required operational safety and authorization system was not mature enough to justify a destructive shared-truth transition.

#### Leave Academic Meaning in Core

Rejected because it would preserve the coupling Airframe exists to remove.

#### Expose Legacy Columns as the New Public Contract

Rejected because it would make temporary storage details permanent architecture.

#### Build a General Plugin Framework

Rejected because Mission 027 needs explicit composition, not speculative Mission 028 infrastructure.

#### Remove All Compatibility Wrappers Immediately

Rejected because it would expand the mission into a broad caller migration and create avoidable behavioral risk.

#### Treat Architecture Tests as Runtime Security

Rejected because source review automation cannot safely execute or reason about arbitrary Python behavior.

### Tradeoffs Accepted

* The physical schema remains product-shaped.
* Metadata and legacy columns can temporarily contain conflicting values.
* The adapter must maintain explicit precedence rules.
* Transitional wrappers and manifest exceptions remain.
* Static checks cover bounded ordinary forms rather than every possible dynamic construction.
* Full transition safety and concurrency hardening remain future work.

### Final Rule

> Airframe defines who owns meaning. Ledger Transition will define how durable shared truth changes.

---

## Goose's Notes

Mission 027 was a lesson in knowing when a technically ambitious plan has crossed a mission boundary.

The first implementation tried to solve logical architecture and destructive storage conversion together. That produced a large diff and a migration-safety platform involving authorization, locking, backup, restoration, readiness, and postflight validation.

Independent review did exactly what independent review should do: it challenged the operational assumptions, not just the happy path.

The right response was not to keep hardening an oversized mission indefinitely. It was to separate the decisions.

Airframe returned to its core purpose:

* Define ownership.
* Reverse the dependency direction.
* Keep product meaning in Atlas.
* Preserve current behavior.
* Hide legacy storage behind a private adapter.
* Document the debt honestly.

The completed working tree described during review contained 25 Mission 027
files:

* 18 production files.
* 4 additive test files.
* 3 documentation files.

The subsequent approved implementation commit contains 26 files. Git records
the same 18 production files and 4 additive test files, plus 4 documentation
files because `README.md` is also part of the final commit.

The final suite contains:

* 141 unchanged baseline tests.
* 26 additive Airframe tests.
* 167 passing tests in total.

The most important number is not the line count. It is zero:

* Zero live migrations.
* Zero live-data writes.
* Zero real credential use.
* Zero network model calls.
* Zero authorization implied for the future Ledger transition.

Airframe is smaller because its promise is sharper.

---

## Mission Debrief

### What We Built

Mission 027 established the logical skeleton of Wingman OS:

* Core owns reusable mechanisms.
* Shared owns cross-product utilities.
* Atlas owns academic policy and meaning.
* Product Configuration supplies declared product values.
* Composition roots connect those layers.
* A private adapter contains version-3 storage debt.
* Compatibility facades protect supported behavior.
* Static review tests guard ordinary dependency drift.

### Biggest Lesson

Do not confuse architectural progress with immediate physical purity.

The system became meaningfully more product-neutral without touching the live schema.

### Architecture Impact

Before Airframe:

* Generic mechanisms and Atlas policy were interleaved.
* Academic fields leaked through Core-facing source models.
* Ownership direction was implicit.
* Physical storage shape influenced public concepts.

After Airframe:

* Ownership is declared and tested.
* Core ingestion and retrieval accept supplied policy.
* Shared context logic is reusable.
* Atlas composes academic behavior.
* Product configuration has a narrow entry point.
* Generic metadata crosses public boundaries.
* Legacy columns are confined to a private repository adapter.

### Validated Airframe Tests

The final verification covered:

* Original regression behavior.
* Layer ownership and import direction.
* Configuration consumption.
* Academic-vocabulary boundaries.
* Alias and relative-import cases.
* Bounded dynamic-string construction.
* Compatibility exports and patch surfaces.
* Version-3 read precedence.
* Explicit-null behavior.
* Partial and complete registry writes.
* Nested metadata preservation.
* Real XLSX upload and reprocessing.
* CLI ingestion.
* Application composition.
* Compilation and diff hygiene.

### Accepted Limitations

Airframe does not:

* Convert existing version-3 databases.
* Resolve every historical metadata conflict.
* Add a global readiness gate.
* Introduce a cross-process locking platform.
* Provide backup or restoration operations.
* Prove arbitrary dynamic Python imports safe.
* Replace the current flat module layout with final package boundaries.
* Implement future product or agent contracts.

These limitations are explicit and intentional.

### Next Mission Boundaries

Mission 028 may build on the Airframe through stable product contracts and package-level hardpoints, but should not smuggle the physical Ledger transition back into ordinary product work.

A future Ledger Transition mission must independently address:

* Exact-target migration authorization.
* Cooperative and exclusive application locking.
* Concurrent and multiprocess initialization.
* WAL- and SHM-safe quiescence.
* Immutable backup identity and checksums.
* Crash-safe restoration that preserves the failed database.
* Schema and migration-history readiness.
* Semantic and byte-preservation guarantees.
* Disposable dry runs.
* Tested rollback procedures.
* Assurance v1 and Crew Chief prerequisites.
* A separate CEO approval gate for live execution.

Until those requirements are satisfied:

> The Airframe code is committed. The live Ledger may not be migrated, and
> Mission 027 does not authorize a future Ledger migration.
