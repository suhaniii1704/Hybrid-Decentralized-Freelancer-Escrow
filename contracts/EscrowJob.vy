#pragma version 0.4.3

"""
@title Decentralized Freelancer Escrow Job
@notice Directly deployed escrow contract for one freelance job.
@dev
    - No factory
    - No separate evidence subsystem
    - No ruling-deadline fallback
    - Single proof_uri / evidence_uri
    - Core milestone lifecycle
    - Dispute and ruling lifecycle
"""


# ============================================================
# CONSTANTS
# ============================================================

MAX_MILESTONES: constant(uint256) = 20

PENDING: constant(uint8) = 0
FUNDED: constant(uint8) = 1
SUBMITTED: constant(uint8) = 2
DISPUTED: constant(uint8) = 3
RELEASED: constant(uint8) = 4
REFUNDED: constant(uint8) = 5
CANCELLED: constant(uint8) = 6

REASON_APPROVED: constant(uint8) = 1
REASON_TIMEOUT: constant(uint8) = 2
REASON_CLIENT_CANCELLED: constant(uint8) = 3


# ============================================================
# INTERFACES
# ============================================================

interface IERC20:

    def transfer(
        to: address,
        amount: uint256
    ) -> bool: nonpayable

    def transferFrom(
        from_: address,
        to: address,
        amount: uint256
    ) -> bool: nonpayable


# ============================================================
# IMMUTABLE JOB CONFIGURATION
# ============================================================

client: public(immutable(address))
freelancer: public(immutable(address))
arbitrator: public(immutable(address))
token: public(immutable(address))

review_period: public(immutable(uint256))
appeal_window: public(immutable(uint256))

spec_uri: public(immutable(String[2048]))


# ============================================================
# MILESTONE DATA
# ============================================================

struct Milestone:
    amount: uint256
    status: uint8
    due_date: uint256

    proof_uri: String[2048]

    review_deadline: uint256

    dispute_raised_by: address
    evidence_uri: String[2048]

    ruling_winner: address
    ruling_confidence: uint8
    ruling_uri: String[2048]

    appeal_deadline: uint256

    secondary_ruling_winner: address


milestones: DynArray[Milestone, MAX_MILESTONES]


# ============================================================
# EVENTS
# ============================================================

event MilestoneFunded:
    milestone_index: indexed(uint256)
    actor: indexed(address)
    amount: uint256

event MilestoneSubmitted:
    milestone_index: indexed(uint256)
    actor: indexed(address)
    proof_uri: String[2048]
    review_deadline: uint256

event MilestoneApproved:
    milestone_index: indexed(uint256)
    actor: indexed(address)

event MilestoneReleased:
    milestone_index: indexed(uint256)
    actor: indexed(address)
    amount: uint256
    reason: uint8

event MilestoneRefunded:
    milestone_index: indexed(uint256)
    actor: indexed(address)
    amount: uint256
    reason: uint8

event MilestoneCancelled:
    milestone_index: indexed(uint256)
    actor: indexed(address)

event DisputeRaised:
    milestone_index: indexed(uint256)
    actor: indexed(address)
    evidence_uri: String[2048]

event RulingSubmitted:
    milestone_index: indexed(uint256)
    actor: indexed(address)
    winner: address
    confidence: uint8
    reasoning_uri: String[2048]
    appeal_deadline: uint256

event RulingAppealed:
    milestone_index: indexed(uint256)
    actor: indexed(address)

event SecondaryRulingSubmitted:
    milestone_index: indexed(uint256)
    actor: indexed(address)
    winner: address
    reasoning_uri: String[2048]

event RulingFinalized:
    milestone_index: indexed(uint256)
    actor: indexed(address)
    winner: address


# ============================================================
# CONSTRUCTOR
# ============================================================

@deploy
def __init__(
    _client: address,
    _freelancer: address,
    _arbitrator: address,
    _token: address,
    _review_period: uint256,
    _appeal_window: uint256,
    _spec_uri: String[2048],
    _milestone_amounts: DynArray[uint256, MAX_MILESTONES],
    _milestone_due_dates: DynArray[uint256, MAX_MILESTONES]
):
    assert _client != empty(address), "Invalid client"
    assert _freelancer != empty(address), "Invalid freelancer"
    assert _arbitrator != empty(address), "Invalid arbitrator"
    assert _token != empty(address), "Invalid token"

    assert _client != _freelancer, "Client and freelancer must differ"

    assert _review_period > 0, "Review period must be positive"
    assert _appeal_window > 0, "Appeal window must be positive"

    assert len(_milestone_amounts) > 0, "No milestones"
    assert len(_milestone_amounts) <= MAX_MILESTONES, "Too many milestones"
    assert len(_milestone_amounts) == len(_milestone_due_dates), "Length mismatch"

    client = _client
    freelancer = _freelancer
    arbitrator = _arbitrator
    token = _token

    review_period = _review_period
    appeal_window = _appeal_window

    spec_uri = _spec_uri

    for i: uint256 in range(MAX_MILESTONES):

        if i >= len(_milestone_amounts):
            break

        assert _milestone_amounts[i] > 0, "Milestone amount must be positive"

        self.milestones.append(
            Milestone(
                amount=_milestone_amounts[i],
                status=PENDING,
                due_date=_milestone_due_dates[i],
                proof_uri="",
                review_deadline=0,
                dispute_raised_by=empty(address),
                evidence_uri="",
                ruling_winner=empty(address),
                ruling_confidence=0,
                ruling_uri="",
                appeal_deadline=0,
                secondary_ruling_winner=empty(address)
            )
        )


# ============================================================
# INTERNAL HELPERS
# ============================================================

@internal
@view
def _valid_milestone(
    _milestone_index: uint256
) -> bool:
    return _milestone_index < len(self.milestones)


# ============================================================
# READ FUNCTIONS
# ============================================================

@external
@view
def milestone_count() -> uint256:
    return len(self.milestones)


@external
@view
def get_milestone(
    _milestone_index: uint256
) -> (
    uint256,
    uint8,
    uint256,
    String[2048],
    uint256,
    address,
    address,
    uint8,
    String[2048],
    uint256,
    address
):
    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    return (
        m.amount,
        m.status,
        m.due_date,
        m.proof_uri,
        m.review_deadline,
        m.dispute_raised_by,
        m.ruling_winner,
        m.ruling_confidence,
        m.ruling_uri,
        m.appeal_deadline,
        m.secondary_ruling_winner
    )


# ============================================================
# FUND MILESTONE
# ============================================================

@external
@nonreentrant
def fund_milestone(
    _milestone_index: uint256
):
    assert msg.sender == client, "Only client"

    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    assert m.status == PENDING, "Milestone not pending"
    assert m.amount > 0, "Invalid amount"

    m.status = FUNDED
    self.milestones[_milestone_index] = m

    success: bool = extcall IERC20(token).transferFrom(
        client,
        self,
        m.amount
    )

    assert success, "Token transfer failed"

    log MilestoneFunded(
        milestone_index=_milestone_index,
        actor=msg.sender,
        amount=m.amount
    )


# ============================================================
# SUBMIT MILESTONE
# ============================================================

@external
def submit_milestone(
    _milestone_index: uint256,
    _proof_uri: String[2048]
):
    assert msg.sender == freelancer, "Only freelancer"

    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    assert m.status == FUNDED, "Milestone not funded"

    if m.due_date > 0:
        assert block.timestamp <= m.due_date, "Milestone overdue"

    m.status = SUBMITTED
    m.proof_uri = _proof_uri
    m.review_deadline = block.timestamp + review_period

    self.milestones[_milestone_index] = m

    log MilestoneSubmitted(
        milestone_index=_milestone_index,
        actor=msg.sender,
        proof_uri=_proof_uri,
        review_deadline=m.review_deadline
    )


# ============================================================
# APPROVE MILESTONE
# ============================================================

@external
@nonreentrant
def approve_milestone(
    _milestone_index: uint256
):
    assert msg.sender == client, "Only client"

    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    assert m.status == SUBMITTED, "Milestone not submitted"
    assert block.timestamp < m.review_deadline, "Review period expired"

    amount: uint256 = m.amount

    m.status = RELEASED
    self.milestones[_milestone_index] = m

    success: bool = extcall IERC20(token).transfer(
        freelancer,
        amount
    )

    assert success, "Token transfer failed"

    log MilestoneApproved(
        milestone_index=_milestone_index,
        actor=msg.sender
    )

    log MilestoneReleased(
        milestone_index=_milestone_index,
        actor=msg.sender,
        amount=amount,
        reason=REASON_APPROVED
    )


# ============================================================
# CLAIM AFTER TIMEOUT
# ============================================================

@external
@nonreentrant
def claim_after_timeout(
    _milestone_index: uint256
):
    assert msg.sender == freelancer, "Only freelancer"

    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    assert m.status == SUBMITTED, "Milestone not submitted"
    assert block.timestamp >= m.review_deadline, "Review period active"

    amount: uint256 = m.amount

    m.status = RELEASED
    self.milestones[_milestone_index] = m

    success: bool = extcall IERC20(token).transfer(
        freelancer,
        amount
    )

    assert success, "Token transfer failed"

    log MilestoneReleased(
        milestone_index=_milestone_index,
        actor=msg.sender,
        amount=amount,
        reason=REASON_TIMEOUT
    )


# ============================================================
# CANCEL MILESTONE
# ============================================================

@external
@nonreentrant
def cancel_milestone(
    _milestone_index: uint256
):
    assert msg.sender == client, "Only client"

    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    assert (
        m.status == PENDING
        or m.status == FUNDED
    ), "Cannot cancel milestone"

    amount: uint256 = m.amount
    was_funded: bool = m.status == FUNDED

    m.status = CANCELLED
    self.milestones[_milestone_index] = m

    if was_funded:

        success: bool = extcall IERC20(token).transfer(
            client,
            amount
        )

        assert success, "Token transfer failed"

        log MilestoneRefunded(
            milestone_index=_milestone_index,
            actor=msg.sender,
            amount=amount,
            reason=REASON_CLIENT_CANCELLED
        )

    log MilestoneCancelled(
        milestone_index=_milestone_index,
        actor=msg.sender
    )


# ============================================================
# RAISE DISPUTE
# ============================================================

@external
def raise_dispute(
    _milestone_index: uint256,
    _evidence_uri: String[2048]
):
    assert (
        msg.sender == client
        or msg.sender == freelancer
    ), "Unauthorized"

    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    assert m.status == SUBMITTED, "Milestone not submitted"

    m.status = DISPUTED
    m.dispute_raised_by = msg.sender
    m.evidence_uri = _evidence_uri

    self.milestones[_milestone_index] = m

    log DisputeRaised(
        milestone_index=_milestone_index,
        actor=msg.sender,
        evidence_uri=_evidence_uri
    )


# ============================================================
# FIRST ARBITRATOR RULING
# ============================================================

@external
def submit_ruling(
    _milestone_index: uint256,
    _winner: address,
    _confidence: uint8,
    _reasoning_uri: String[2048]
):
    assert msg.sender == arbitrator, "Only arbitrator"

    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    assert m.status == DISPUTED, "No active dispute"
    assert (
        _winner == client
        or _winner == freelancer
    ), "Invalid winner"

    assert _confidence <= 100, "Invalid confidence"

    m.ruling_winner = _winner
    m.ruling_confidence = _confidence
    m.ruling_uri = _reasoning_uri

    if _confidence >= 70:
        m.appeal_deadline = block.timestamp + appeal_window
    else:
        m.appeal_deadline = 0

    self.milestones[_milestone_index] = m

    log RulingSubmitted(
        milestone_index=_milestone_index,
        actor=msg.sender,
        winner=_winner,
        confidence=_confidence,
        reasoning_uri=_reasoning_uri,
        appeal_deadline=m.appeal_deadline
    )


# ============================================================
# APPEAL RULING
# ============================================================

@external
def appeal_ruling(
    _milestone_index: uint256
):
    assert (
        msg.sender == client
        or msg.sender == freelancer
    ), "Unauthorized"

    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    assert m.status == DISPUTED, "No active dispute"
    assert m.ruling_winner != empty(address), "No ruling"
    assert m.ruling_confidence >= 70, "Ruling not appealable"
    assert block.timestamp < m.appeal_deadline, "Appeal period expired"

    m.appeal_deadline = 0

    self.milestones[_milestone_index] = m

    log RulingAppealed(
        milestone_index=_milestone_index,
        actor=msg.sender
    )


# ============================================================
# SECONDARY RULING
# ============================================================

@external
def submit_secondary_ruling(
    _milestone_index: uint256,
    _winner: address,
    _reasoning_uri: String[2048]
):
    assert msg.sender == arbitrator, "Only arbitrator"

    assert _milestone_index < len(self.milestones), "Invalid milestone"

    m: Milestone = self.milestones[_milestone_index]

    assert m.status == DISPUTED, "No active dispute"

    assert (
        _winner == client
        or _winner == freelancer
    ), "Invalid winner"

    m.secondary_ruling_winner = _winner
    m.ruling_uri = _reasoning_uri

    self.milestones[_milestone_index] = m

    log SecondaryRulingSubmitted(
        milestone_index=_milestone_index,
        actor=msg.sender,
        winner=_winner,
        reasoning_uri=_reasoning_uri
    )


# ============================================================
# FINALIZE RULING
# ============================================================

@external
@nonreentrant
def finalize_ruling(_milestone_index: uint256):
    assert self._valid_milestone(_milestone_index)

    m: Milestone = self.milestones[_milestone_index]

    assert m.status == DISPUTED
    assert (
        msg.sender == client
        or msg.sender == freelancer
        or msg.sender == arbitrator
    )

    winner: address = empty(address)

    # ---------------------------------------------------------
    # Case 1: Secondary ruling exists.
    #
    # This is required when:
    # - primary confidence < 70, OR
    # - a high-confidence primary ruling was appealed.
    # ---------------------------------------------------------
    if m.secondary_ruling_winner != empty(address):
        winner = m.secondary_ruling_winner

    # ---------------------------------------------------------
    # Case 2: No secondary ruling.
    #
    # Only a high-confidence primary ruling can be finalized
    # directly, and only after the appeal window expires.
    # ---------------------------------------------------------
    else:
        assert m.ruling_winner != empty(address)

        # Confidence below 70 MUST go to secondary review.
        assert m.ruling_confidence >= 70

        # A high-confidence ruling must have an appeal deadline.
        assert m.appeal_deadline > 0

        # Appeal window must have expired.
        assert block.timestamp >= m.appeal_deadline

        winner = m.ruling_winner

    assert (
        winner == client
        or winner == freelancer
    )

    # ---------------------------------------------------------
    # Update state BEFORE external token transfer.
    # ---------------------------------------------------------
    if winner == freelancer:
        m.status = RELEASED
    else:
        m.status = REFUNDED

    self.milestones[_milestone_index] = m

    success: bool = False

    if winner == freelancer:
        success = extcall(
            IERC20(token).transfer(
                freelancer,
                m.amount
            )
        )

        assert success

        log MilestoneReleased(
            milestone_index=_milestone_index,
            actor=msg.sender,
            amount=m.amount,
            reason=REASON_APPROVED
        )

    else:
        success = extcall(
            IERC20(token).transfer(
                client,
                m.amount
            )
        )

        assert success

        log MilestoneRefunded(
            milestone_index=_milestone_index,
            actor=msg.sender,
            amount=m.amount,
            reason=REASON_CLIENT_CANCELLED
        )

    log RulingFinalized(
        milestone_index=_milestone_index,
        actor=msg.sender,
        winner=winner
    )