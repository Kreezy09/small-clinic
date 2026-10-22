# AI Reflection

### 1. What did you use AI for across the four sections?

* **Section 1 (System Design):**
  * Brainstormed domain edge cases in clinic scheduling, such as handling time zone boundaries (converting `Africa/Nairobi` local clinic day boundaries to UTC ranges) and preserving existing bookings when slot lengths change.
  * Formatted the initial Mermaid ER diagram syntax for documentation.

* **Section 2 (API Implementation):**
  * Scaffolded initial Django REST Framework boilerplate (serializers, viewset actions, and route registration).
  * Generated parameterized test skeletons for boundary conditions (e.g. off-grid times, bookings during tea breaks, past dates, and lead-time edge cases).
  * Served as an architectural sounding board to explore PostgreSQL concurrency behaviors and constraint handling.

* **Section 3 (Deployment & CI/CD):**
  * Drafted the Azure Bicep resource syntax for Azure Container Apps and Azure Database for PostgreSQL Flexible Server (including parameter wiring and secret references).
  * Assisted in templating the multi-stage GitHub Actions CI/CD workflow and resolving pin-to-SHA best practices for third-party actions.

---

### 2. Give one example where an AI suggestion improved your work. What did you prompt it with?

* **Prompt:**
  > *"We are designing a booking system for a small clinic with 5 doctors using Django REST Framework and PostgreSQL. Each doctor has weekly recurring working hours (e.g. Mon–Fri 08:00–13:00 and 14:00–17:00, with breaks in between) and operates in fixed-length slots (initially 30 minutes, but individual doctors might need 15 or 20-minute slots in the future). Patients need an endpoint to view all free slots for a given doctor on a specific date.*
  >
  > *I am evaluating two data modeling approaches for availability:*
  > *1. A pre-generated `slots` table populated by a background worker or recurring cron job with `(doctor_id, start_at, end_at, is_booked)` rows.*
  > *2. Storing only the doctors' recurring working hours blocks and computing free slots dynamically at query time by stepping through the working-hours intervals and subtracting active appointments.*
  >
  > *How should we structure this schema and availability calculation in PostgreSQL and Django so that:*
  > *- Doctors can change their slot duration or working hours without leaving orphaned or stale slot records.*
  > *- Availability queries for a specific day remain fast (<10ms).*
  > *- We avoid unnecessary background cron jobs or synchronization logic.*
  > *What are the architectural trade-offs of both approaches, and which one provides the cleanest growth path?"*

* **How it improved the work:**
  * The response thoroughly broke down the hidden operational costs of the pre-generated `slots` table: managing background cron jobs, handling time-zone daylight shifts, database table bloat over time, and the painful synchronization logic needed when a doctor modifies their working hours or slot length (which leaves orphaned or stale future slot records).
  * It showed that for a clinic with 5 doctors (each with at most 16–20 slots per day), computing slots on the fly—generating intervals in Python by stepping through `doctor_working_hours` and dropping those overlapping active appointments—takes less than 2 milliseconds.
  * This suggestion simplified the architecture significantly: it eliminated the need for a `slots` table, cron workers, and cache invalidation, while making slot duration changes and break patterns work instantly without schema migrations.

---

### 3. Give one example where AI output was wrong or incomplete and how you caught it.

* **The Issue:**
  * When adding the `UniqueConstraint` to the `Appointment` model, the AI suggested that duplicate concurrent bookings would bubble up directly to `save_slot()` as database integrity errors to be caught and returned as `409 Conflict`.
  * The AI overlooked that Django REST Framework's `ModelSerializer` automatically inspects model `UniqueConstraint`s and injects a default `UniqueTogetherValidator` during serializer validation.

* **How it was caught:**
  * Running the test suite against a real PostgreSQL instance immediately failed `test_rejects_taken_slot` with `400 Bad Request` instead of the expected `409 Conflict`. The serializer was rejecting the duplicate before the model's `save()` method or domain exception handlers were ever invoked.

* **The Fix:**
  * Setting `validators = ()` explicitly on `AppointmentSerializer.Meta` disabled DRF's auto-generated validator, allowing domain logic and database constraints to return the required `409 SlotUnavailableError` responses.

---

### 4. Name two decisions you made without AI. Why did you trust your own judgment there?

#### Decision 1: Storing working hours as one row per weekday block rather than grouped weekday ranges/arrays
* **Why:** Entering Monday–Friday hours weekday by weekday feels slightly repetitive in the admin interface, and an AI often suggests combining them into a single row with an array of days (e.g. `weekdays = [1, 2, 3, 4, 5]`) to reduce admin input.
* **Why I trusted my own judgment:** Relational database schemas should optimize for data integrity, query speed, and indexing rather than admin form ergonomics. One row per weekday block allows indexed B-tree lookups (`iso_weekday = day.isoweekday()`) and makes single-day schedule adjustments (e.g. leaving early on Friday) trivial without splitting multi-day records. Form convenience belongs in the admin UI layer, not in database normalization compromises.

#### Decision 2: Replacing raw SQL advisory locks with declarative B-tree UniqueConstraints
* **Why:** Reviewing the code generated for concurrency showed raw SQL queries (`SELECT pg_advisory_xact_lock(hashtextextended(...))`) that serialized the entire doctor and patient row across all dates and times.
* **Why I trusted my own judgment:** Having raw SQL strings in an otherwise clean Python/Django codebase is an anti-pattern when standard database constraints can do the job better. Furthermore, serializing the whole doctor meant someone booking Dr. Ada for next week blocked someone booking Dr. Ada for three months from now. I insisted on replacing this with declarative B-tree `UniqueConstraint`s on `(doctor, start_at)` and `(patient, start_at)` ahead of the GiST `ExclusionConstraint`s. This achieved slot-level concurrency, removed all raw SQL, and kept the solution 100% in pure Python and Django models.
