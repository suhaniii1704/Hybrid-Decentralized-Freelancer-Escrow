# Freelancer Escrow Protocol Specification

**Status:** Phase 0 draft
**Network:** Base Sepolia
**Contract language:** Vyper 0.4.3
**Payment token:** USDC (6 decimals)

## 1. State Machine

### 1.1 Actors

The protocol has four relevant actors:

* **Client** — creates a job and funds milestones. The client can approve submitted work, cancel eligible milestones, and participate in disputes.
* **Freelancer** — performs the milestone work and submits proof. The freelancer can claim eligible payments after the review timeout and participate in disputes.
* **Arbitrator** — submits primary and secondary dispute rulings.
* **Anyone** — may trigger permissionless actions whose only purpose is to finalize an already-determined state, including timeout claims and ruling finalization where the applicable conditions are satisfied.

The contract stores the client, freelancer, and arbitrator addresses as immutable job-level parties.

### 1.2 Milestone States

Each milestone has exactly one of the following states:

| State       | Meaning                                                                     |
| ----------- | --------------------------------------------------------------------------- |
| `PENDING`   | The milestone exists but has not been funded.                               |
| `FUNDED`    | The client has deposited the milestone amount into escrow.                  |
| `SUBMITTED` | The freelancer has submitted proof of work and the review period is active. |
| `DISPUTED`  | A dispute has been raised for the submitted milestone.                      |
| `RELEASED`  | The milestone funds have been released to the freelancer.                   |
| `REFUNDED`  | The milestone funds have been returned to the client.                       |
| `CANCELLED` | The milestone has been cancelled before submission.                         |

A milestone transition is terminal once it reaches `RELEASED`, `REFUNDED`, or `CANCELLED`.

### 1.3 Legal Transitions

The following transitions are legal:

```text
PENDING
   │
   │ fund_milestone()
   ▼
FUNDED
   │
   │ submit_milestone(proof_uri)
   ▼
SUBMITTED
   │
   ├── approve_milestone()
   │          │
   │          ▼
   │      RELEASED
   │
   ├── claim_after_timeout()
   │          │
   │          ▼
   │      RELEASED
   │
   └── raise_dispute(evidence_uri)
              │
              ▼
          DISPUTED
```

Cancellation is available before submission:

```text
PENDING ── cancel_milestone() ──> CANCELLED

FUNDED ── cancel_milestone() ──> CANCELLED
```

A disputed milestone is resolved through the dispute process:

```text
DISPUTED
   │
   │ ruling / final ruling
   ├──────────────────────> RELEASED
   │
   └──────────────────────> REFUNDED
```

The exact ruling, appeal, secondary-review, finalization, and ruling-deadline-fallback transitions are specified in the dispute lifecycle section below.

### 1.4 Transition Rules

#### `PENDING → FUNDED`

The client funds the milestone with the exact milestone amount in USDC.

#### `FUNDED → SUBMITTED`

The freelancer submits proof of work. The proof URI is recorded and the review period begins.

#### `SUBMITTED → RELEASED`

The milestone can be released when:

1. the client explicitly approves it; or
2. the review period expires and the timeout-claim conditions are satisfied.

#### `SUBMITTED → DISPUTED`

Either party may raise a dispute while the milestone is submitted. The initial dispute evidence URI is recorded with the dispute event.

#### `PENDING → CANCELLED`

The client may cancel a milestone that has not been funded.

#### `FUNDED → CANCELLED`

The client may cancel a funded milestone provided the freelancer has not yet submitted the milestone.

The escrowed amount is returned to the client.

#### `DISPUTED → RELEASED`

A final dispute outcome in favor of the freelancer releases the escrowed amount to the freelancer.

#### `DISPUTED → REFUNDED`

A final dispute outcome in favor of the client returns the escrowed amount to the client.

### 1.5 Terminal States

The following states are terminal:

```text
RELEASED
REFUNDED
CANCELLED
```

No function may transition a milestone out of a terminal state.

### 1.6 Illegal Transitions

A function must revert if it is called when its required source state is not active.

Examples include:

* funding a milestone that is not `PENDING`;
* submitting proof for a milestone that is not `FUNDED`;
* approving a milestone that is not `SUBMITTED`;
* claiming a milestone that is not `SUBMITTED`;
* raising a dispute for a milestone that is not `SUBMITTED`;
* cancelling a milestone after proof has been submitted;
* modifying a milestone after it is `RELEASED`, `REFUNDED`, or `CANCELLED`.

The complete function-by-state revert matrix is defined in Section 2.

## 1.7 Dispute Lifecycle

A dispute begins when either party raises a dispute against a `SUBMITTED` milestone.

```text
SUBMITTED
    │
    │ raise_dispute()
    ▼
DISPUTED
    │
    │ submit_ruling()
    ▼
PRIMARY RULING
    │
    ├── confidence >= 70
    │       │
    │       ▼
    │   APPEAL WINDOW
    │       │
    │       ├── appeal_ruling()
    │       │       │
    │       │       ▼
    │       │   SECONDARY REVIEW
    │       │       │
    │       │       ▼
    │       │   FINAL RULING
    │       │
    │       └── no appeal
    │               │
    │               ▼
    │           FINALIZE
    │
    └── confidence < 70
            │
            ▼
       SECONDARY REVIEW
            │
            ▼
        FINAL RULING
            │
            ▼
         FINALIZE
```

Only the losing party may appeal a primary ruling.

A high-confidence primary ruling (`confidence >= 70`) opens the appeal window.

A low-confidence primary ruling (`confidence < 70`) proceeds directly to secondary review.

The exact deadline boundary and finalization conditions are defined in the deadlines section.

### 1.8 Ruling-Deadline Fallback

If the arbitrator does not submit the required ruling before the ruling deadline, the milestone must not remain locked indefinitely.

The protocol provides a ruling-deadline fallback that allows the escrowed amount to be resolved through the specified fallback outcome.

The exact trigger, caller, timing boundary, and fund distribution are a protocol-level design decision and must be agreed upon by all four teammates before the contract implementation is finalized.

### 1.9 Deadline Boundary Convention

All deadline comparisons must use explicitly defined inequalities.

The specification will define separately whether each deadline is satisfied at:

```text
timestamp < deadline
timestamp == deadline
timestamp > deadline
```

Tests must cover:

* one second before the deadline;
* exactly at the deadline;
* one second after the deadline.

No contract implementation may rely on an unstated interpretation of a deadline.

# 2. Function Specification

Each function below defines its caller, required state, effects, and failure conditions. The contract must reject calls that violate these conditions.

## 2.1 Milestone Lifecycle Functions

### `fund_milestone(milestone_index)`

| Field          | Specification                                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Caller         | Client                                                                                                                   |
| Preconditions  | Job exists; milestone index is valid; milestone is `PENDING`; milestone amount > 0                                       |
| Effect         | Transfers the exact milestone amount of USDC from the client to the escrow contract; changes milestone state to `FUNDED` |
| Token movement | Client → Escrow                                                                                                          |
| Event          | `MilestoneFunded`                                                                                                        |
| Reverts        | Invalid milestone index; caller is not client; milestone is not `PENDING`; token transfer fails                          |

The contract must verify the return value of the USDC transfer operation.

### `submit_milestone(milestone_index, proof_uri)`

| Field          | Specification                                                                                                                 |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Caller         | Freelancer                                                                                                                    |
| Preconditions  | Milestone index is valid; milestone is `FUNDED`; proof URI satisfies the contract's URI requirements                          |
| Effect         | Records the proof URI; changes state to `SUBMITTED`; records the review-period deadline                                       |
| Token movement | None                                                                                                                          |
| Event          | `MilestoneSubmitted`                                                                                                          |
| Reverts        | Invalid milestone index; caller is not freelancer; milestone is not `FUNDED`; invalid proof URI if URI validation is enforced |

### `approve_milestone(milestone_index)`

| Field          | Specification                                                                                                                    |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Caller         | Client                                                                                                                           |
| Preconditions  | Milestone is `SUBMITTED`; review period has not expired according to the specified boundary rules                                |
| Effect         | Changes state to `RELEASED`; transfers the milestone amount to the freelancer                                                    |
| Token movement | Escrow → Freelancer                                                                                                              |
| Event          | `MilestoneApproved` followed by `MilestoneReleased`                                          |
| Reverts        | Invalid milestone index; caller is not client; milestone is not `SUBMITTED`; approval is not permitted after the review deadline |

State must be updated before the token transfer.

### `claim_after_timeout(milestone_index)`

| Field          | Specification                                                                                  |
| -------------- | ---------------------------------------------------------------------------------------------- |
| Caller         | Anyone                                                                                         |
| Preconditions  | Milestone is `SUBMITTED`; review period has expired according to the exact deadline convention |
| Effect         | Changes state to `RELEASED`; transfers the milestone amount to the freelancer                  |
| Token movement | Escrow → Freelancer                                                                            |
| Event          | `MilestoneReleased`                                                                            |
| Reverts        | Invalid milestone index; milestone is not `SUBMITTED`; review period has not expired           |

The function is permissionless so that a silent client cannot permanently block payment.

State must be updated before the token transfer.

### `cancel_milestone(milestone_index)`

| Field          | Specification                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------ |
| Caller         | Client                                                                                           |
| Preconditions  | Milestone is `PENDING` or `FUNDED`; freelancer has not submitted proof                           |
| Effect         | Changes state to `CANCELLED`; if funded, returns the escrowed amount to the client               |
| Token movement | Escrow → Client if milestone is `FUNDED`                                                         |
| Event          | `MilestoneCancelled` and, where applicable, `MilestoneRefunded`                                  |
| Reverts        | Invalid milestone index; caller is not client; milestone is `SUBMITTED`, `DISPUTED`, or terminal |

State must be updated before any token transfer.

## 2.2 Dispute and Evidence Functions

### `raise_dispute(milestone_index, evidence_uri)`

| Field          | Specification                                                                                                               |
| -------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Caller         | Client or Freelancer                                                                                                        |
| Preconditions  | Milestone is `SUBMITTED`; caller is one of the two job parties                                                              |
| Effect         | Changes milestone state to `DISPUTED`; records the dispute initiator and initial evidence reference                         |
| Token movement | None                                                                                                                        |
| Event          | `DisputeRaised` including the actor address                                                                                 |
| Reverts        | Invalid milestone index; caller is neither client nor freelancer; milestone is not `SUBMITTED`; evidence cap/rules violated |

The event actor must be the actual `msg.sender`.

### `submit_evidence(milestone_index, evidence_uri)`

| Field          | Specification                                                                                                  |
| -------------- | -------------------------------------------------------------------------------------------------------------- |
| Caller         | Client or Freelancer                                                                                           |
| Preconditions  | Milestone is `DISPUTED`; caller is one of the two job parties; caller has not exceeded the evidence cap        |
| Effect         | Records the evidence submission according to the event-log evidence design                                     |
| Token movement | None                                                                                                           |
| Event          | `EvidenceSubmitted` including the actor address                                                                |
| Reverts        | Invalid milestone index; caller is neither party; milestone is not `DISPUTED`; per-party evidence cap exceeded |

Evidence content is not stored as full on-chain text. The contract records the evidence reference through events and maintains only the required counts/state.

## 2.3 Ruling Functions

### `submit_ruling(milestone_index, winner, confidence, reasoning_uri)`

| Field          | Specification                                                                                                                                                                    |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Caller         | Arbitrator                                                                                                                                                                       |
| Preconditions  | Milestone is `DISPUTED`; caller is the immutable job arbitrator; no primary ruling has already been submitted; winner is a valid party; confidence is within the permitted range |
| Effect         | Records the primary ruling, confidence and reasoning URI; routes the dispute according to the confidence threshold                                                               |
| Token movement | None                                                                                                                                                                             |
| Event          | `RulingSubmitted`                                                                                                                                                                |
| Reverts        | Invalid milestone index; caller is not arbitrator; milestone is not `DISPUTED`; ruling already submitted; invalid winner; confidence out of range                                |

Confidence routing:

```text
confidence >= 70
    → appeal window opens

confidence < 70
    → secondary review
```

### `appeal_ruling(milestone_index)`

| Field          | Specification                                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Caller         | Losing party only                                                                                                        |
| Preconditions  | A primary ruling exists; ruling is appealable; appeal window is open; caller is the party that lost the primary ruling   |
| Effect         | Records the appeal and moves the dispute into secondary review                                                           |
| Token movement | None                                                                                                                     |
| Event          | `RulingAppealed`                                                                                                         |
| Reverts        | Invalid milestone index; no ruling exists; caller is not losing party; appeal window is closed; appeal already submitted |

A winning party cannot appeal.

### `submit_secondary_ruling(milestone_index, winner, reasoning_uri)`

| Field          | Specification                                                                                                                                  |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Caller         | Arbitrator                                                                                                                                     |
| Preconditions  | Milestone is in secondary review; caller is the immutable arbitrator; secondary ruling has not already been submitted; winner is a valid party |
| Effect         | Records the secondary ruling                                                                                                                   |
| Token movement | None                                                                                                                                           |
| Event          | `SecondaryRulingSubmitted`                                                                                                                     |
| Reverts        | Invalid milestone index; caller is not arbitrator; dispute is not in secondary review; secondary ruling already submitted; invalid winner      |

### `finalize_ruling(milestone_index)`

| Field          | Specification                                                                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Caller         | Anyone                                                                                                                                                  |
| Preconditions  | A ruling is finalizable: either the applicable appeal window has closed without an appeal, or secondary review has completed                            |
| Effect         | Resolves the milestone according to the final ruling; changes state to `RELEASED` or `REFUNDED`; transfers the escrowed amount to the appropriate party |
| Token movement | Escrow → Freelancer or Client                                                                                                                           |
| Event          | `RulingFinalized` plus the resulting release/refund event                                                                                               |
| Reverts        | Invalid milestone index; no finalizable ruling; appeal window is still open; secondary ruling is incomplete                                             |

State must be updated before the token transfer.

### 2.4 Ruling-Deadline Fallback

### `trigger_ruling_deadline_fallback(milestone_index)`

| Field | Specification |
|---|---|
| Caller | Anyone |
| Preconditions | Milestone is `DISPUTED`; arbitrator has not submitted the required ruling before the ruling deadline |
| Effect | Resolves the dispute using the 50/50 fallback |
| Token movement | 50% of the escrowed amount → Client; 50% → Freelancer |
| Event | `RulingDeadlineFallback` and the resulting resolution event |
| Reverts | Invalid milestone index; milestone is not `DISPUTED`; ruling deadline has not expired; ruling already submitted |

The fallback distribution is:

```text
50% → Client
50% → Freelancer

## 2.5 Read Views

The contract must provide read-only functions for frontend, adapter, indexer, and testing purposes.

### `milestone_count()`

Returns the total number of milestones in the job.

| Field        | Specification        |
| ------------ | -------------------- |
| Caller       | Anyone               |
| State change | None                 |
| Returns      | Number of milestones |

### `get_milestone(milestone_index)`

Returns the complete milestone struct for the specified milestone.

The returned structure must contain all state required by the frontend and adapter to determine the milestone's current status and relevant deadlines.

At minimum it must represent:

* milestone amount;
* milestone status;
* due date;
* proof URI;
* review deadline;
* dispute/ruling information required by the state machine.

The exact ABI tuple ordering and field types will be finalized before the ABI draft is generated.

### Additional read-only job information

The implementation may expose additional read-only values required by the frontend and adapter, including immutable:

* client address;
* freelancer address;
* arbitrator address;
* review period;
* appeal window;
* specification URI;
* payment token address.

No write function may modify these immutable job-level values.

## 2.6 Factory Job-Creation Interface

Jobs are created through `EscrowFactory`.

### `create_job(freelancer, arbitrator, spec_uri, milestone_amounts, due_dates)`

| Field | Specification |
|---|---|
| Caller | Client (`msg.sender`) |
| Parameters | Freelancer address, arbitrator address, specification URI, milestone amounts, milestone due dates |
| Client | Set to `msg.sender` |
| Payment token | Factory's immutable configured token |
| Review period | Fixed at 7 days |
| Appeal window | Fixed at 7 days |
| Milestones | At least 1 and at most 20 |
| Amounts | Every milestone amount must be greater than zero |
| Due dates | Exactly one due date per milestone |
| Effect | Creates a new `EscrowJob` with the supplied job configuration |
| Event | `JobCreated` |
| Reverts | Invalid array lengths; zero milestone amount; more than 20 milestones; zero address; arbitrator equals client; arbitrator equals freelancer |

The factory must reject an empty milestone list.

The factory must reject a milestone list containing more than 20 milestones.

The `milestone_amounts` and `due_dates` arrays must have equal lengths.

The factory must reject a zero freelancer or arbitrator address.

The factory must reject an arbitrator address equal to the client or freelancer.

The factory's payment token is immutable and is passed to each newly created `EscrowJob`.

The created job stores the client, freelancer, arbitrator, payment token, review period, appeal window, and specification URI as immutable job-level configuration.

The factory must emit `JobCreated` once for every successfully created job.

The `client` value in `JobCreated` must equal the transaction sender (`msg.sender`).

# 3. Events

Events are the contract's on-chain record of state transitions and important dispute actions.

Every event that identifies an actor must include the actor address explicitly in its arguments. The actor is always the actual `msg.sender`; it must never be inferred from user-provided JSON.

The final ABI will use these event definitions as its source.

## 3.1 `JobCreated`

Emitted once when an `EscrowJob` is created by the factory.

```text
JobCreated(
    job,
    client,
    freelancer,
    arbitrator,
    spec_uri
)
```

| Argument     | Type                                         | Indexed | Description                                 |
| ------------ | -------------------------------------------- | ------: | ------------------------------------------- |
| `job`        | address                                      |      No | Address of the newly created escrow job     |
| `client`     | address                                      |     Yes | Client address                              |
| `freelancer` | address                                      |     Yes | Freelancer address                          |
| `arbitrator` | address                                      |     Yes | Arbitrator address                          |
| `spec_uri`   | string                                       |      No | IPFS URI of the immutable job specification |

The factory emits this event when a job is successfully created.

## 3.2 `MilestoneFunded`

Emitted when a milestone changes from `PENDING` to `FUNDED`.

```text
MilestoneFunded(
    milestone_index,
    actor,
    amount
)
```

| Argument          | Type    | Indexed | Description                      |
| ----------------- | ------- | ------: | -------------------------------- |
| `milestone_index` | uint256 |     Yes | Milestone index                  |
| `actor`           | address |     Yes | Client who funded the milestone  |
| `amount`          | uint256 |      No | Amount funded in USDC base units |

`actor` must equal the transaction sender.

## 3.3 `MilestoneSubmitted`

Emitted when a milestone changes from `FUNDED` to `SUBMITTED`.

```text
MilestoneSubmitted(
    milestone_index,
    actor,
    proof_uri
)
```

| Argument          | Type    | Indexed | Description                   |
| ----------------- | ------- | ------: | ----------------------------- |
| `milestone_index` | uint256 |     Yes | Milestone index               |
| `actor`           | address |     Yes | Freelancer submitting proof   |
| `proof_uri`       | string  |      No | URI referencing proof of work |

`actor` must equal the transaction sender.

## 3.4 `MilestoneApproved`

Emitted when the client explicitly approves a submitted milestone.

```text
MilestoneApproved(
    milestone_index,
    actor
)
```

| Argument          | Type    | Indexed | Description                    |
| ----------------- | ------- | ------: | ------------------------------ |
| `milestone_index` | uint256 |     Yes | Milestone index                |
| `actor`           | address |     Yes | Client approving the milestone |

The approval causes the milestone to enter `RELEASED`. `MilestoneApproved` and `MilestoneReleased` are emitted as separate events in that order.

## 3.5 `MilestoneReleased`

Emitted whenever a milestone reaches `RELEASED`.

```text
MilestoneReleased(
    milestone_index,
    actor,
    recipient,
    amount,
    reason
)
```

| Argument          | Type                        | Indexed | Description                        |
| ----------------- | --------------------------- | ------: | ---------------------------------- |
| `milestone_index` | uint256                     |     Yes | Milestone index                    |
| `actor`           | address                     |     Yes | Address that triggered the release |
| `recipient`       | address                     |     Yes | Freelancer receiving the funds     |
| `amount`          | uint256                     |      No | Released amount                    |
| `reason`          | uint8/enum-compatible value |      No | Reason for release                 |

Possible release reasons include:

```text
APPROVED
TIMEOUT
RULING
SECONDARY_RULING
```

The ABI representation of `reason` is `uint8`.

## 3.6 `MilestoneRefunded`

Emitted whenever milestone funds are returned to the client.

```text
MilestoneRefunded(
    milestone_index,
    actor,
    recipient,
    amount,
    reason
)
```

| Argument          | Type                        | Indexed | Description                       |
| ----------------- | --------------------------- | ------: | --------------------------------- |
| `milestone_index` | uint256                     |     Yes | Milestone index                   |
| `actor`           | address                     |     Yes | Address that triggered the refund |
| `recipient`       | address                     |     Yes | Client receiving the funds        |
| `amount`          | uint256                     |      No | Refunded amount                   |
| `reason`          | uint8/enum-compatible value |      No | Reason for refund                 |

## 3.7 `MilestoneCancelled`

Emitted when a milestone changes to `CANCELLED`.

```text
MilestoneCancelled(
    milestone_index,
    actor
)
```

| Argument          | Type    | Indexed | Description                     |
| ----------------- | ------- | ------: | ------------------------------- |
| `milestone_index` | uint256 |     Yes | Milestone index                 |
| `actor`           | address |     Yes | Client cancelling the milestone |

If the milestone was already funded, the cancellation also results in the appropriate refund event.

## 3.8 `DisputeRaised`

Emitted when a `SUBMITTED` milestone changes to `DISPUTED`.

```text
DisputeRaised(
    milestone_index,
    actor,
    evidence_uri
)
```

| Argument          | Type    | Indexed | Description                   |
| ----------------- | ------- | ------: | ----------------------------- |
| `milestone_index` | uint256 |     Yes | Disputed milestone            |
| `actor`           | address |     Yes | Party that raised the dispute |
| `evidence_uri`    | string  |      No | URI of the initial evidence   |

The `actor` field is mandatory because the arbitrator and indexer must identify which on-chain party raised the dispute.

The actor must equal `msg.sender`.

## 3.9 `EvidenceSubmitted`

Emitted whenever a party submits additional evidence for a disputed milestone.

```text
EvidenceSubmitted(
    milestone_index,
    actor,
    evidence_uri
)
```

| Argument          | Type    | Indexed | Description               |
| ----------------- | ------- | ------: | ------------------------- |
| `milestone_index` | uint256 |     Yes | Disputed milestone        |
| `actor`           | address |     Yes | Party submitting evidence |
| `evidence_uri`    | string  |      No | URI of the evidence JSON  |

The actor must equal `msg.sender`.

The contract maintains the required per-party evidence count. Evidence content itself is stored off-chain, with the URI recorded in the event.

## 3.10 `RulingSubmitted`

Emitted when the arbitrator submits the primary ruling.

```text
RulingSubmitted(
    milestone_index,
    actor,
    winner,
    confidence,
    reasoning_uri
)
```

| Argument          | Type    | Indexed | Description                  |
| ----------------- | ------- | ------: | ---------------------------- |
| `milestone_index` | uint256 |     Yes | Disputed milestone           |
| `actor`           | address |     Yes | Arbitrator                   |
| `winner`          | address |     Yes | Client or freelancer         |
| `confidence`      | uint256 |      No | Arbitrator confidence, 0–100 |
| `reasoning_uri`   | string  |      No | URI of the reasoning JSON    |

The contract verifies that `actor == arbitrator`.

## 3.11 `RulingAppealed`

Emitted when the losing party appeals an eligible primary ruling.

```text
RulingAppealed(
    milestone_index,
    actor
)
```

| Argument          | Type    | Indexed | Description                        |
| ----------------- | ------- | ------: | ---------------------------------- |
| `milestone_index` | uint256 |     Yes | Disputed milestone                 |
| `actor`           | address |     Yes | Losing party submitting the appeal |

The contract verifies that the actor is the losing party from the primary ruling.

## 3.12 `SecondaryRulingSubmitted`

Emitted when the arbitrator submits the secondary ruling.

```text
SecondaryRulingSubmitted(
    milestone_index,
    actor,
    winner,
    reasoning_uri
)
```

| Argument          | Type    | Indexed | Description                |
| ----------------- | ------- | ------: | -------------------------- |
| `milestone_index` | uint256 |     Yes | Disputed milestone         |
| `actor`           | address |     Yes | Arbitrator                 |
| `winner`          | address |     Yes | Client or freelancer       |
| `reasoning_uri`   | string  |      No | URI of secondary reasoning |

The contract verifies that `actor == arbitrator`.

## 3.13 `RulingFinalized`

Emitted when the final dispute outcome is applied to the milestone.

```text
RulingFinalized(
    milestone_index,
    actor,
    winner,
    amount
)
```

| Argument          | Type    | Indexed | Description                     |
| ----------------- | ------- | ------: | ------------------------------- |
| `milestone_index` | uint256 |     Yes | Disputed milestone              |
| `actor`           | address |     Yes | Address triggering finalization |
| `winner`          | address |     Yes | Final winning party             |
| `amount`          | uint256 |      No | Amount resolved                 |

`actor` may be any address because finalization is permissionless.

The finalization causes the milestone to become:

```text
winner == freelancer → RELEASED
winner == client     → REFUNDED
```

## 3.14 `RulingDeadlineFallback`

Emitted when the arbitrator fails to submit the required ruling before the ruling deadline and the fallback mechanism is triggered.

```text
RulingDeadlineFallback(
    milestone_index,
    actor,
    client_amount,
    freelancer_amount
)
```

| Argument            | Type    | Indexed | Description                     |
| ------------------- | ------- | ------: | ------------------------------- |
| `milestone_index`   | uint256 |     Yes | Disputed milestone              |
| `actor`             | address |     Yes | Address triggering the fallback |
| `client_amount`     | uint256 |      No | Amount returned to client       |
| `freelancer_amount` | uint256 |      No | Amount released to freelancer   |

The fallback distribution remains subject to the team's pending product decision.

## 3.15 Event Actor Rules

The following rules apply to all events containing an actor:

1. `actor` MUST equal the transaction's `msg.sender`.
2. The actor MUST NOT be taken from evidence JSON.
3. The actor MUST NOT be taken from the job specification JSON.
4. The actor MUST NOT be inferred from the event's other fields.
5. Off-chain services must use the on-chain actor when labeling statements, claims, evidence, and actions.

This is particularly important for `DisputeRaised` and `EvidenceSubmitted`.

## 3.16 Event Ordering

For a normal milestone lifecycle, the expected event sequence is:

```text
JobCreated
    ↓
MilestoneFunded
    ↓
MilestoneSubmitted
    ↓
MilestoneApproved
    ↓
MilestoneReleased
```

For a timeout release:

```text
JobCreated
    ↓
MilestoneFunded
    ↓
MilestoneSubmitted
    ↓
MilestoneReleased
```

For a dispute:

```text
JobCreated
    ↓
MilestoneFunded
    ↓
MilestoneSubmitted
    ↓
DisputeRaised
    ↓
EvidenceSubmitted*
    ↓
RulingSubmitted
    ↓
RulingAppealed*
    ↓
SecondaryRulingSubmitted*
    ↓
RulingFinalized
    ↓
MilestoneReleased / MilestoneRefunded
```

`*` indicates an optional event depending on the dispute path.

The indexer must preserve the transaction/log ordering when constructing the event timeline.


# 4. Bounds and JSON Formats

## 4.1 Protocol Bounds

The following bounds apply to the protocol.

| Parameter                          | Requirement                          |
| ---------------------------------- | ------------------------------------ |
| Maximum milestones per job         | 20                                   |
| Minimum milestone amount           | Greater than 0                       |
| Confidence range                   | 0–100                                |
| High-confidence threshold          | 70                                   |
| Review period                      | 7 days                               |
| Appeal window                      | 7 days                               |
| Evidence per party per milestone   | 3 per party                          |
| Job client address                 | Non-zero                             |
| Freelancer address                 | Non-zero                             |
| Arbitrator address                 | Non-zero                             |
| Arbitrator/client relationship     | Arbitrator must not equal client     |
| Arbitrator/freelancer relationship | Arbitrator must not equal freelancer |
| Milestone index                    | Must be less than milestone count    |

### 4.1.1 Maximum Milestones

A job may contain at most **20 milestones**.

Job creation must revert if the supplied milestone list contains more than 20 milestones.

### 4.1.2 Amounts

Every milestone amount must be greater than zero.

```text
amount > 0
```

Zero-value milestones are invalid.

The contract uses USDC's six-decimal base units for token amounts.

### 4.1.3 Confidence

Arbitrator confidence is represented as an integer from 0 through 100 inclusive.

```text
0 <= confidence <= 100
```

Routing is:

```text
confidence >= 70 → appeal window
confidence < 70  → secondary review
```

The threshold is therefore inclusive at 70.

### 4.1.4 Review Period

The review period is fixed at **7 days**.

The review deadline is calculated from the timestamp at which the milestone
enters `SUBMITTED`.

### 4.1.5 Appeal Window

The appeal window is fixed at **7 days**.

The appeal window begins when an appealable primary ruling is submitted.

### 4.1.6 Addresses

The following addresses must not be the zero address:

* client;
* freelancer;
* arbitrator;
* payment token;
* factory-created job where applicable.

The factory must reject:

```text
arbitrator == client
arbitrator == freelancer
```
### 4.1.7 Evidence Cap

Each party may submit a maximum of **3 evidence submissions per milestone**.

The contract tracks the number of evidence submissions by party and rejects
additional submissions once that party has reached the cap.

Evidence content itself is not stored in contract storage. Evidence references
are emitted through events.

## 4.1.8 URI Representation

Contract URI fields use the Solidity/Vyper ABI `string` type.

This applies to `spec_uri`, `proof_uri`, `evidence_uri`, and `reasoning_uri`.

# 4.2 Job Specification JSON

The job specification is stored off-chain, pinned to IPFS, and referenced by the immutable `spec_uri`.

The required top-level format is:

```json
{
  "title": "Website redesign",
  "description": "Redesign the company website.",
  "milestones": [
    {
      "title": "Design",
      "description": "Create the initial website design.",
      "amount": 10000000,
      "dueDate": "2026-10-01T00:00:00Z",
      "acceptanceCriteria": "Approved responsive design delivered."
    }
  ]
}
```

## 4.2.1 Job Specification Fields

### `title`

Required string describing the project.

### `description`

Required string containing the project description.

### `milestones`

Required array containing one or more milestone objects.

The array must contain no more than 20 milestones.

### Milestone `title`

Required string identifying the milestone.

### Milestone `description`

Required string describing the milestone work.

### Milestone `amount`

Required positive integer representing the milestone amount in USDC base units.

USDC uses six decimal places.

### Milestone `dueDate`

Required date/time value identifying the milestone's target due date.

The canonical serialized representation is an ISO-8601 UTC timestamp.

### Milestone `acceptanceCriteria`

Required string defining the criteria used to determine whether the submitted work satisfies the milestone.

The acceptance criteria are used by the arbitrator when evaluating a dispute.

---

# 4.3 Evidence JSON

Evidence is stored off-chain and referenced from the contract through an IPFS URI.

The canonical evidence structure is:

```json
{
  "statement": "The requested feature was completed and submitted before the deadline.",
  "attachments": [
    {
      "name": "proof.png",
      "uri": "ipfs://example",
      "mimeType": "image/png"
    }
  ]
}
```

## 4.3.1 Evidence Fields

### `statement`

Required string containing the party's claim or explanation.

The statement is untrusted user-provided content.

### `attachments`

Array of zero or more attachment objects.

### Attachment `name`

Required string containing the attachment's display name.

### Attachment `uri`

Required URI identifying the stored attachment.

### Attachment `mimeType`

Required MIME type describing the attachment.

Only supported MIME types should be accepted by the off-chain backend/arbitrator pipeline.

The contract itself records the evidence URI and evidence count rather than parsing the JSON content.

---

# 4.4 JSON Integrity Rules

The smart contract does not trust JSON contents as authorization data.

In particular:

* a JSON `statement` cannot establish who submitted evidence;
* an address appearing inside JSON cannot override `msg.sender`;
* evidence JSON cannot change milestone state;
* job-spec JSON cannot change client, freelancer, arbitrator, periods, or payment token;
* the immutable on-chain job configuration remains authoritative.

The arbitrator must label statements according to the on-chain sender of the corresponding evidence event.

---

# 4.5 Immutable Job Configuration

The following values are fixed when the job is created:

* client;
* freelancer;
* arbitrator;
* payment token;
* review period;
* appeal window;
* `spec_uri`.

No owner, administrator, or upgrade function may modify these values after job creation.

# 5. Design Decisions and Invariants

## 5.1 Loser-Only Appeal

Only the losing party of a primary ruling may appeal.

The winning party cannot appeal a ruling in its favor.

### Rationale

Allowing the winner to appeal would only delay the resolution and payout of a dispute without providing a protocol-level benefit.

### Rule

```text id="m5n3g2"
primary ruling exists
        +
caller == losing party
        +
appeal window is open
        ↓
appeal permitted
```

Any other caller must be rejected.

---

## 5.2 Confidence-Based Routing

The primary arbitrator ruling contains an integer confidence value from 0 through 100.

The protocol uses a threshold of **70**.

```text id="bny8vz"
confidence >= 70
    → appeal window opens

confidence < 70
    → secondary review
```

The value `70` belongs to the high-confidence branch.

Confidence is not itself a guarantee of correctness. It is a routing value supplied by the arbitrator.

---

## 5.3 Secondary Review

A low-confidence primary ruling proceeds directly to secondary review.

A high-confidence ruling enters an appeal window.

If the losing party appeals within that window, the dispute proceeds to secondary review.

The secondary ruling produces the final winner.

The secondary ruling does not create another appeal window.

---

## 5.4 Arbitrator Ruling Deadline

A dispute must not remain permanently locked because the arbitrator fails to act.

The protocol therefore includes a ruling deadline.

If the arbitrator has not submitted the required ruling before the deadline, any address may trigger the ruling-deadline fallback.

### Pending Team Decision

The current proposed fallback is:

```text id="jkv6qp"
50% → Client
50% → Freelancer
```

The exact implementation must be approved by all four teammates before the contract is finalized.

The ruling deadline duration is not yet fixed in this specification and must be defined before ABI freeze and contract implementation.

The fallback must not be callable before the ruling deadline.

Once the fallback resolves the escrow, the dispute cannot later be ruled or finalized by the arbitrator.

---

## 5.5 Evidence Storage

Evidence content is stored off-chain.

The contract does not store complete evidence JSON or attachments in storage.

Instead:

* evidence JSON is pinned to IPFS;
* the resulting URI is submitted to the contract;
* the contract emits an `EvidenceSubmitted` event;
* the event includes the on-chain actor;
* the contract maintains the required per-party evidence count.

The same model applies to the initial evidence attached to `DisputeRaised`: the initial evidence counts as one evidence submission for the party that raised the dispute.

### Evidence Cap

Each party has a maximum number of evidence submissions per milestone.

The numerical cap is fixed at **3 evidence submissions per party per milestone**.

The cap exists to prevent unbounded evidence growth and excessive arbitrator input.

---

## 5.6 Deadline Boundaries

All deadlines use explicit timestamp comparisons.

The protocol distinguishes:

```text id="sg7o3n"
timestamp < deadline
timestamp == deadline
timestamp > deadline
```

For timeout-based actions, the specification uses the following convention:

```text id="n5e9m1"
timestamp >= deadline
    → deadline has expired
```

Therefore:

* one second before the deadline → action is rejected;
* exactly at the deadline → action is permitted;
* one second after the deadline → action is permitted.

The same explicit convention must be applied independently to:

* review timeout;
* appeal window;
* ruling deadline.

Tests must cover all three boundary positions.

---

## 5.7 Immutable Configuration

The following values cannot change after job creation:

* client;
* freelancer;
* arbitrator;
* payment token;
* review period;
* appeal window;
* specification URI.

There is no owner function that can modify them.

There are no upgrade functions.

---

## 5.8 Arbitrator Restrictions

The factory must reject a job where:

```text id="t2h6vf"
arbitrator == client
```

or:

```text id="wz6h0p"
arbitrator == freelancer
```

The arbitrator must also be a non-zero address.

This prevents a job party from simultaneously controlling the arbitrator role.

---

## 5.9 USDC Transfer Safety

Every operation that moves USDC must:

1. validate the required conditions;
2. update the milestone state before making the external token call;
3. perform the token transfer;
4. verify the token's returned success value;
5. revert if the transfer fails.

Token-moving functions must use the contract's reentrancy protection.

A failed transfer must leave the entire transaction reverted.

---

# 5.10 Escrow Balance Invariant

At every valid observable contract state:

```text id="m7kq0b"
contract USDC balance
=
sum(FUNDED milestone amounts)
+
sum(SUBMITTED milestone amounts)
+
sum(DISPUTED milestone amounts)
```

Terminal milestones do not contribute to the escrow balance:

```text id="t4f2w8"
RELEASED    → 0
REFUNDED    → 0
CANCELLED   → 0
```

The invariant must hold after every scenario and after every successful state transition.

### Example

If three milestones are:

```text id="r4t6e1"
Milestone 0 → FUNDED     → 100 USDC
Milestone 1 → SUBMITTED  → 200 USDC
Milestone 2 → RELEASED   → 300 USDC
```

then:

```text id="7s8z1j"
Escrow balance = 100 + 200 = 300 USDC
```

The released milestone contributes nothing to the escrow balance.

---

# 5.11 Multi-Milestone Independence

Each milestone has an independent lifecycle.

An action affecting milestone `i` must not accidentally modify the state, amount, deadline, proof, evidence, or dispute state of another milestone `j`.

For any valid:

```text id="0x5t3n"
i != j
```

operations on milestone `i` must preserve the state of milestone `j`, except for job-level accounting that is explicitly derived from all milestones.

---

# 5.12 One-Time Transitions

Each milestone transition may occur only once.

Examples:

* a funded milestone cannot be funded again;
* a submitted milestone cannot be submitted again;
* a dispute cannot be raised twice for the same submitted milestone;
* a primary ruling cannot be submitted twice;
* an appeal cannot be submitted twice;
* a secondary ruling cannot be submitted twice;
* a finalized dispute cannot be finalized again.

Repeated calls must revert.

---

# 5.13 Permissionless Finalization

Actions whose purpose is only to finalize an already-determined outcome may be permissionless.

This includes:

* `claim_after_timeout`;
* `finalize_ruling`;
* ruling-deadline fallback.

Permissionless execution prevents a party or arbitrator from permanently blocking an outcome after the required conditions have already been satisfied.

---

# 5.14 No Unbounded Contract Loops

Contract functions must not depend on loops whose execution grows without a fixed protocol bound.

The maximum of 20 milestones provides a fixed upper bound for milestone-related operations.

Evidence submission does not require iterating over all previous evidence because evidence is represented by event logs and per-party counters.

---

# 5.15 Zero-Address Safety

The contract must reject zero addresses for:

* client;
* freelancer;
* arbitrator;
* payment token;
* factory-created job addresses where applicable.

A valid party address must be a non-zero address.

---

# 5.16 Supported Payment Token

The escrow supports the configured USDC-like payment token only.

The factory stores the token address as an immutable factory-level value.

Fee-on-transfer tokens are outside the supported protocol model.

The contract assumes that a successful transfer of `amount` transfers exactly `amount` token units.

The `BadToken` test contract is used to verify failure handling when token transfers return failure or attempt a callback.


# 6. Scenarios

Each scenario is expressed using Given/When/Then notation.

These scenarios are the shared behavioral test list for:

* `pytest` + Titanoboa;
* A's `MockAdapter`;
* D's live Base Sepolia scenario runner.

The implementation must not introduce behavior that is not represented by the specification.

## 6.1 Core Escrow Scenarios

### SC-01 — Create a valid job

**Given**

* a valid client address;
* a valid freelancer address;
* a valid arbitrator address;
* valid milestone amounts;
* a valid specification URI;
* the protocol-fixed 7-day review period and 7-day appeal window.

**When**

* the factory creates the job.

**Then**

* a new escrow job is created;
* the client, freelancer, arbitrator, token, 7-day review period, and 7-day appeal window are fixed;
* `JobCreated` is emitted;
* the event contains the job address, client, freelancer, arbitrator and `spec_uri`.

---

### SC-02 — Reject more than 20 milestones

**Given**

* a job specification containing more than 20 milestones.

**When**

* the factory attempts to create the job.

**Then**

* the transaction reverts;
* no job is created.

---

### SC-03 — Reject zero milestone amount

**Given**

* a milestone with amount `0`.

**When**

* the job is created.

**Then**

* the transaction reverts.

---

### SC-04 — Fund a milestone

**Given**

* a milestone is `PENDING`;
* the caller is the client;
* the client has sufficient USDC and has approved the escrow.

**When**

* `fund_milestone()` is called.

**Then**

* the milestone becomes `FUNDED`;
* the exact milestone amount enters escrow;
* `MilestoneFunded` is emitted;
* the escrow balance invariant holds.

---

### SC-05 — Reject funding by a non-client

**Given**

* a `PENDING` milestone;
* caller is freelancer, arbitrator, or stranger.

**When**

* `fund_milestone()` is called.

**Then**

* the transaction reverts;
* the milestone remains `PENDING`.

---

### SC-06 — Submit proof

**Given**

* a milestone is `FUNDED`;
* caller is the freelancer.

**When**

* `submit_milestone(proof_uri)` is called.

**Then**

* the milestone becomes `SUBMITTED`;
* the proof URI is recorded;
* the review deadline is established;
* `MilestoneSubmitted` is emitted.

---

### SC-07 — Approve submitted work

**Given**

* a milestone is `SUBMITTED`;
* the client is permitted to approve it.

**When**

* `approve_milestone()` is called.

**Then**

* the milestone becomes `RELEASED`;
* the milestone amount is transferred to the freelancer;
* the appropriate release event is emitted;
* the escrow balance invariant holds.

---

### SC-08 — Claim after review timeout

**Given**

* a milestone is `SUBMITTED`;
* the review deadline has expired.

**When**

* any address calls `claim_after_timeout()`.

**Then**

* the milestone becomes `RELEASED`;
* the milestone amount is transferred to the freelancer;
* the release event identifies the triggering actor;
* the escrow balance invariant holds.

---

### SC-09 — Reject timeout claim before deadline

**Given**

* a milestone is `SUBMITTED`;
* the review deadline has not expired.

**When**

* any address calls `claim_after_timeout()`.

**Then**

* the transaction reverts;
* the milestone remains `SUBMITTED`.

---

### SC-10 — Cancel unfunded milestone

**Given**

* a milestone is `PENDING`;
* caller is the client.

**When**

* `cancel_milestone()` is called.

**Then**

* the milestone becomes `CANCELLED`;
* `MilestoneCancelled` is emitted;
* no token transfer occurs.

---

### SC-11 — Cancel funded milestone before submission

**Given**

* a milestone is `FUNDED`;
* freelancer has not submitted proof;
* caller is the client.

**When**

* `cancel_milestone()` is called.

**Then**

* the milestone becomes `CANCELLED`;
* the escrowed amount is returned to the client;
* the appropriate cancellation/refund events are emitted;
* the escrow balance invariant holds.

---

### SC-12 — Reject cancellation after submission

**Given**

* a milestone is `SUBMITTED`.

**When**

* the client calls `cancel_milestone()`.

**Then**

* the transaction reverts;
* the milestone remains `SUBMITTED`.

---

# 6.2 Dispute Scenarios

### SC-13 — Raise a dispute

**Given**

* a milestone is `SUBMITTED`;
* caller is the client or freelancer.

**When**

* `raise_dispute(evidence_uri)` is called.

**Then**

* the milestone becomes `DISPUTED`;
* the dispute actor is recorded by the event;
* `DisputeRaised` is emitted;
* the evidence URI is included in the event.

---

### SC-14 — Reject dispute from stranger

**Given**

* a milestone is `SUBMITTED`;
* caller is neither client nor freelancer.

**When**

* `raise_dispute()` is called.

**Then**

* the transaction reverts;
* the milestone remains `SUBMITTED`.

---

### SC-15 — Submit additional evidence

**Given**

* a milestone is `DISPUTED`;
* caller is one of the job parties;
* the caller has not reached the evidence cap.

**When**

* `submit_evidence(evidence_uri)` is called.

**Then**

* the evidence submission is accepted;
* the party's evidence count increases;
* `EvidenceSubmitted` is emitted;
* the event actor equals the transaction sender.

---

### SC-16 — Reject evidence after cap

**Given**

* a milestone is `DISPUTED`;
* the caller has reached the per-party evidence cap.

**When**

* `submit_evidence()` is called again.

**Then**

* the transaction reverts;
* the evidence count does not increase.

---

# 6.3 Primary Ruling Scenarios

### SC-17 — High-confidence ruling

**Given**

* a milestone is `DISPUTED`;
* caller is the arbitrator;
* confidence is `70` or greater.

**When**

* `submit_ruling()` is called.

**Then**

* the primary ruling is recorded;
* `RulingSubmitted` is emitted;
* an appeal window opens;
* the losing party may appeal during that window.

---

### SC-18 — Low-confidence ruling

**Given**

* a milestone is `DISPUTED`;
* caller is the arbitrator;
* confidence is below `70`.

**When**

* `submit_ruling()` is called.

**Then**

* the primary ruling is recorded;
* `RulingSubmitted` is emitted;
* the dispute proceeds directly to secondary review;
* no primary appeal window is opened.

---

### SC-19 — Confidence exactly 70

**Given**

* a valid disputed milestone;
* arbitrator submits confidence `70`.

**When**

* `submit_ruling()` is called.

**Then**

* the ruling follows the high-confidence path;
* the appeal window opens.

---

### SC-20 — Reject ruling from non-arbitrator

**Given**

* a milestone is `DISPUTED`;
* caller is not the immutable arbitrator.

**When**

* `submit_ruling()` is called.

**Then**

* the transaction reverts;
* no ruling is recorded.

---

# 6.4 Appeal Scenarios

### SC-21 — Losing party appeals

**Given**

* a high-confidence primary ruling exists;
* the appeal window is open;
* caller is the losing party.

**When**

* `appeal_ruling()` is called.

**Then**

* the appeal is recorded;
* `RulingAppealed` is emitted;
* secondary review begins.

---

### SC-22 — Winner cannot appeal

**Given**

* a primary ruling exists;
* caller is the winning party.

**When**

* `appeal_ruling()` is called.

**Then**

* the transaction reverts.

---

### SC-23 — Appeal after window

**Given**

* a primary ruling is appealable;
* the appeal deadline has expired.

**When**

* the losing party calls `appeal_ruling()`.

**Then**

* the transaction reverts.

---

# 6.5 Secondary Review Scenarios

### SC-24 — Submit secondary ruling

**Given**

* the dispute is in secondary review;
* caller is the arbitrator.

**When**

* `submit_secondary_ruling()` is called.

**Then**

* the secondary ruling is recorded;
* `SecondaryRulingSubmitted` is emitted;
* the secondary ruling becomes the final dispute outcome.

---

### SC-25 — Reject secondary ruling from non-arbitrator

**Given**

* the dispute is in secondary review;
* caller is not the arbitrator.

**When**

* `submit_secondary_ruling()` is called.

**Then**

* the transaction reverts.

---

# 6.6 Finalization Scenarios

### SC-26 — Finalize unappealed ruling

**Given**

* a high-confidence primary ruling exists;
* no appeal was submitted;
* the appeal window has expired.

**When**

* any address calls `finalize_ruling()`.

**Then**

* the ruling is finalized;
* the milestone becomes `RELEASED` if the freelancer won or `REFUNDED` if the client won;
* the appropriate token transfer occurs;
* `RulingFinalized` is emitted.

---

### SC-27 — Cannot finalize while appeal window is open

**Given**

* a high-confidence primary ruling exists;
* the appeal window is still open.

**When**

* any address calls `finalize_ruling()`.

**Then**

* the transaction reverts.

---

### SC-28 — Finalize after secondary ruling

**Given**

* a secondary ruling has been submitted.

**When**

* `finalize_ruling()` is called when finalization is permitted.

**Then**

* the secondary outcome is applied;
* the milestone becomes `RELEASED` or `REFUNDED`;
* the appropriate token transfer occurs;
* `RulingFinalized` is emitted.

---

# 6.7 Ruling-Deadline Fallback Scenarios

### SC-29 — Trigger fallback after arbitrator deadline

**Given**

* a milestone is `DISPUTED`;
* no required ruling has been submitted;
* the ruling deadline has expired.

**When**

* any address triggers the fallback.

**Then**

* the fallback executes according to the team-approved rule;
* the dispute cannot later receive a normal ruling;
* the appropriate fallback event is emitted.

---

### SC-30 — Reject fallback before deadline

**Given**

* the ruling deadline has not expired.

**When**

* any address triggers the fallback.

**Then**

* the transaction reverts.

---

# 6.8 Deadline Boundary Scenarios

Every deadline must be tested at all three boundary positions.

### SC-31 — One second before review deadline

**Given**

* a milestone is `SUBMITTED`;
* current time is one second before the review deadline.

**When**

* `claim_after_timeout()` is called.

**Then**

* the transaction reverts.

### SC-32 — Exactly at review deadline

**Given**

* a milestone is `SUBMITTED`;
* current time equals the review deadline.

**When**

* `claim_after_timeout()` is called.

**Then**

* the timeout claim succeeds.

### SC-33 — One second after review deadline

**Given**

* a milestone is `SUBMITTED`;
* current time is one second after the review deadline.

**When**

* `claim_after_timeout()` is called.

**Then**

* the timeout claim succeeds.

The same three-point boundary test must be applied to the appeal window and ruling deadline.

---

# 6.9 Multi-Milestone Scenarios

### SC-34 — Milestones operate independently

**Given**

* a job contains multiple milestones.

**When**

* one milestone is funded, submitted, disputed, released, refunded, or cancelled.

**Then**

* other milestones retain their existing states and amounts.

---

### SC-35 — Independent payout accounting

**Given**

* multiple milestones have different states and amounts.

**When**

* one milestone reaches a terminal state.

**Then**

* only that milestone's escrowed amount leaves the contract;
* the remaining escrow balance equals the sum of the non-terminal funded amounts.

---

# 6.10 Security and Hardening Scenarios

### SC-36 — Failed token transfer

**Given**

* the configured token returns failure from a transfer operation.

**When**

* a token-moving contract function is executed.

**Then**

* the transaction reverts;
* milestone state remains unchanged;
* funds remain accounted for correctly.

---

### SC-37 — Callback reentrancy attempt

**Given**

* a malicious token attempts to call back into the escrow contract during a token transfer.

**When**

* the escrow performs a token transfer.

**Then**

* reentrancy protection prevents the callback from changing escrow state;
* the transaction fails safely or completes without allowing an invalid state transition.

---

### SC-38 — Zero-address rejection

**Given**

* a job creation parameter contains a zero address.

**When**

* the factory attempts to create the job.

**Then**

* the transaction reverts.

---

### SC-39 — Arbitrator conflicts with a party

**Given**

* the proposed arbitrator equals the client or freelancer.

**When**

* the factory attempts to create the job.

**Then**

* the transaction reverts.

---

# 6.11 Invariant Scenario

### SC-40 — Escrow balance invariant

**Given**

* a job with one or more milestones.

**When**

* any successful state transition occurs.

**Then**

```text id="jv0p9h"
contract USDC balance
=
sum(FUNDED amounts)
+
sum(SUBMITTED amounts)
+
sum(DISPUTED amounts)
```

The invariant must hold after:

* funding;
* submission;
* cancellation;
* approval;
* timeout release;
* dispute creation;
* evidence submission;
* ruling;
* appeal;
* secondary ruling;
* finalization;
* fallback.

---

# 6.12 Read-View Scenarios

### SC-41 — Read milestone count

**Given**

* a job contains N milestones.

**When**

* `milestone_count()` is called.

**Then**

* it returns N.

---

### SC-42 — Read complete milestone

**Given**

* a valid milestone index.

**When**

* `get_milestone(index)` is called.

**Then**

* the complete milestone struct is returned;
* its values match the current on-chain state.

---

# 6.13 Existing Test Suite Integration

The original project contains 41 dispute and escrow test cases.

Those existing cases must be incorporated into this scenario list without changing their intended behavioral coverage.

Each existing test should map to one or more `SC-*` identifiers.

Additional scenarios introduced by the Phase 0 specification include:

* evidence handling;
* factory creation;
* zero-address validation;
* arbitrator conflict validation;
* token-transfer failure;
* callback/reentrancy hardening;
* escrow balance invariant;
* ruling-deadline fallback;
* exact deadline boundaries;
* read-view behavior.

The final scenario list must identify all existing 41 cases and all newly introduced cases before the ABI is frozen.
