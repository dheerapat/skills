# Plan: [Epic Name]
**Status:** [Planning / In Progress / Blocked / Complete]

---

## Epic
> "As a [type of user or internal role], I want to [perform an action], so that [I get a specific value/benefit]."

**Description**
[Provide a detailed explanation of the epic, background context, and why this work is important right now. This could be a business feature, a system migration, or an internal infrastructure improvement.]

**Goal**
[State the specific, measurable outcome or business objective this epic aims to achieve.]

**Definition of Done (Epic Level)**
- [ ] [e.g., All user stories meet their individual acceptance criteria]
- [ ] [e.g., End-to-end tests are passing in CI/CD pipeline]
- [ ] [e.g., API documentation and architecture decision records (ADRs) are updated]

**Out of Scope**
- [e.g., Integration with third-party API X - deferred to next quarter]
- [e.g., Rewriting the legacy authentication module - tracked in separate Epic Y]

---

## Story 1: [End-User Facing Feature]
> "As an [end-user persona], I want to [perform a specific action], so that [I achieve a specific result]."

**Description**
[Add any technical context, design links (e.g., Figma), or edge cases the developer needs to know.]

**Tasks**
- [ ] [e.g., Create database migration for the new user preferences table]
- [ ] [e.g., Build the frontend UI component for the settings modal]
- [ ] [e.g., Write unit tests for the user input validation logic]

**Acceptance Criteria**
- [ ] [Given [the user is on the settings page], When [they toggle the notification switch], Then [the preference is saved and a success toast is shown]]
- [ ] [e.g., Error message is displayed if the database fails to save]
- [ ] [e.g., Data persists accurately after a page refresh]

---

## Story 2: [Technical / API Contract]
> "As a [frontend developer], I want the [endpoint name] API to return a standardized JSON error format, so that [I can reliably parse and display error messages in the UI without guessing the schema]."

**Description**
[Add technical specifications, contract details, or schema definitions. E.g., Currently, the API returns HTML error pages on 500s, which breaks the frontend error boundary.]

**Tasks**
- [ ] [e.g., Update the global exception handler in the backend to catch all 4xx and 5xx errors]
- [ ] [e.g., Create a standardized `ApiError` DTO with `code`, `message`, and `details` fields]
- [ ] [e.g., Write contract tests to ensure the error schema is strictly followed on all endpoints]

**Acceptance Criteria**
- [ ] [Given [the API encounters a validation error], When [the request is sent], Then [a 400 status is returned with a JSON body matching the agreed schema]]
- [ ] [e.g., Internal server exceptions return a 500 status with a generic message, hiding stack traces from the client]
- [ ] [e.g., The response `Content-Type` header is strictly set to `application/json` for all error responses]

---

## Story 3: [Internal Architecture / Domain Logic]
> "As a [backend engineer], I want the [domain service name] to publish an event to the [message queue name] when a [business entity] is updated, so that [downstream bounded contexts can react asynchronously without tight coupling to my database]."

**Description**
[Add context about the domain model, the message broker being used (e.g., Kafka, RabbitMQ), and the required event schema. E.g., This is purely an internal domain change; no API endpoints will be modified.]

**Tasks**
- [ ] [e.g., Define the `[Entity]UpdatedEvent` schema and add it to the shared events package]
- [ ] [e.g., Implement the message publisher interface within the `[DomainService]` using the outbox pattern]
- [ ] [e.g., Write an integration test to verify the message is correctly placed onto the broker topic upon transaction commit]
- [ ] [e.g., Configure dead-letter queue (DLQ) routing for failed message deliveries]

**Acceptance Criteria**
- [ ] [Given [a valid update to the business entity occurs], When [the database transaction successfully commits], Then [an event containing the updated payload is published to the specified topic]]
- [ ] [e.g., The message publishing happens asynchronously and does not block the main business transaction response time beyond acceptable thresholds]
- [ ] [e.g., If the message broker is unreachable, the event is stored in the outbox table for automated retry, preventing data loss]
