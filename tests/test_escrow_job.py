import boa
import pytest


@pytest.fixture
def accounts():
    client = boa.env.generate_address("client")
    freelancer = boa.env.generate_address("freelancer")
    arbitrator = boa.env.generate_address("arbitrator")

    return {
        "client": client,
        "freelancer": freelancer,
        "arbitrator": arbitrator,
    }


@pytest.fixture
def token(accounts):
    token = boa.load(
        "contracts/MockUSDC.vy"
    )

    token.mint(
        accounts["client"],
        1_000_000
    )

    return token


@pytest.fixture
def escrow(accounts, token):
    escrow = boa.load(
        "contracts/EscrowJob.vy",
        accounts["client"],
        accounts["freelancer"],
        accounts["arbitrator"],
        token.address,
        60,
        60,
        "ipfs://job-spec",
        [500_000],
        [0],
    )

    return escrow


def test_happy_path(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]

    milestone_amount = 500_000

    # --------------------------------------------------------
    # 1. Initial state
    # --------------------------------------------------------

    assert escrow.milestone_count() == 1

    milestone = escrow.get_milestone(0)

    assert milestone[0] == milestone_amount
    assert milestone[1] == 0  # PENDING

    # --------------------------------------------------------
    # 2. Client approves escrow to spend MockUSDC
    # --------------------------------------------------------

    token.approve(
        escrow.address,
        milestone_amount,
        sender=client
    )

    assert token.allowance(
        client,
        escrow.address
    ) == milestone_amount

    # --------------------------------------------------------
    # 3. Client funds milestone
    # PENDING -> FUNDED
    # --------------------------------------------------------

    escrow.fund_milestone(
        0,
        sender=client
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 1  # FUNDED

    assert token.balanceOf(
        client
    ) == 500_000

    assert token.balanceOf(
        escrow.address
    ) == milestone_amount

    # --------------------------------------------------------
    # 4. Freelancer submits milestone
    # FUNDED -> SUBMITTED
    # --------------------------------------------------------

    escrow.submit_milestone(
        0,
        "ipfs://proof-1",
        sender=freelancer
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 2  # SUBMITTED
    assert milestone[3] == "ipfs://proof-1"

    # Review deadline should be set.
    assert milestone[4] > 0

    # --------------------------------------------------------
    # 5. Client approves milestone
    # SUBMITTED -> RELEASED
    # --------------------------------------------------------

    escrow.approve_milestone(
        0,
        sender=client
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 4  # RELEASED

    # Freelancer receives the escrowed amount.
    assert token.balanceOf(
        freelancer
    ) == milestone_amount

    # Escrow should no longer hold the milestone funds.
    assert token.balanceOf(
        escrow.address
    ) == 0


def test_claim_after_timeout(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]

    milestone_amount = 500_000

    # Approve escrow to spend client's MockUSDC.
    token.approve(
        escrow.address,
        milestone_amount,
        sender=client
    )

    # PENDING -> FUNDED
    escrow.fund_milestone(
        0,
        sender=client
    )

    # FUNDED -> SUBMITTED
    escrow.submit_milestone(
        0,
        "ipfs://proof-timeout",
        sender=freelancer
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 2  # SUBMITTED

    review_deadline = milestone[4]

    assert review_deadline > boa.env.evm.patch.timestamp

    # Move blockchain time to the review deadline.
    boa.env.time_travel(
        seconds=60
    )

    # Freelancer claims after timeout.
    escrow.claim_after_timeout(
        0,
        sender=freelancer
    )

    milestone = escrow.get_milestone(0)

    # SUBMITTED -> RELEASED
    assert milestone[1] == 4

    # Freelancer receives the funds.
    assert token.balanceOf(
        freelancer
    ) == milestone_amount

    # Escrow balance is empty.
    assert token.balanceOf(
        escrow.address
    ) == 0


def test_cancel_funded_milestone(
    accounts,
    token,
    escrow
):
    client = accounts["client"]

    milestone_amount = 500_000

    # Approve escrow to spend client's MockUSDC.
    token.approve(
        escrow.address,
        milestone_amount,
        sender=client
    )

    # PENDING -> FUNDED
    escrow.fund_milestone(
        0,
        sender=client
    )

    assert token.balanceOf(
        escrow.address
    ) == milestone_amount

    # FUNDED -> CANCELLED
    escrow.cancel_milestone(
        0,
        sender=client
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 6  # CANCELLED

    # Funds returned to client.
    assert token.balanceOf(
        client
    ) == 1_000_000

    # Escrow no longer holds the funds.
    assert token.balanceOf(
        escrow.address
    ) == 0


def test_raise_dispute_and_submit_ruling(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]
    arbitrator = accounts["arbitrator"]

    milestone_amount = 500_000

    # Client approves escrow.
    token.approve(
        escrow.address,
        milestone_amount,
        sender=client
    )

    # PENDING -> FUNDED
    escrow.fund_milestone(
        0,
        sender=client
    )

    # FUNDED -> SUBMITTED
    escrow.submit_milestone(
        0,
        "ipfs://proof-dispute",
        sender=freelancer
    )

    # SUBMITTED -> DISPUTED
    escrow.raise_dispute(
        0,
        "ipfs://evidence-client",
        sender=client
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 3  # DISPUTED
    assert milestone[5] == client

    # Arbitrator submits a high-confidence ruling
    # in favour of the freelancer.
    escrow.submit_ruling(
        0,
        freelancer,
        80,
        "ipfs://ruling-1",
        sender=arbitrator
    )

    milestone = escrow.get_milestone(0)

    assert milestone[6] == freelancer
    assert milestone[7] == 80
    assert milestone[8] == "ipfs://ruling-1"

    # Confidence >= 70 should create an appeal window.
    assert milestone[9] > 0


def test_raise_dispute_and_submit_ruling(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]
    arbitrator = accounts["arbitrator"]

    amount = 500_000

    token.approve(escrow.address, amount, sender=client)
    escrow.fund_milestone(0, sender=client)

    escrow.submit_milestone(
        0,
        "ipfs://proof",
        sender=freelancer
    )

    escrow.raise_dispute(
        0,
        "ipfs://evidence",
        sender=client
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 3  # DISPUTED
    assert milestone[5] == client

    escrow.submit_ruling(
        0,
        freelancer,
        80,
        "ipfs://ruling",
        sender=arbitrator
    )

    milestone = escrow.get_milestone(0)

    assert milestone[6] == freelancer
    assert milestone[7] == 80
    assert milestone[8] == "ipfs://ruling"
    assert milestone[9] > 0


def test_appeal_and_secondary_ruling(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]
    arbitrator = accounts["arbitrator"]

    amount = 500_000

    token.approve(escrow.address, amount, sender=client)
    escrow.fund_milestone(0, sender=client)

    escrow.submit_milestone(
        0,
        "ipfs://proof",
        sender=freelancer
    )

    escrow.raise_dispute(
        0,
        "ipfs://evidence",
        sender=client
    )

    escrow.submit_ruling(
        0,
        freelancer,
        80,
        "ipfs://primary-ruling",
        sender=arbitrator
    )

    # Freelancer/client can appeal a high-confidence ruling.
    escrow.appeal_ruling(
        0,
        sender=client
    )

    milestone = escrow.get_milestone(0)

    assert milestone[9] == 0

    # Secondary review.
    escrow.submit_secondary_ruling(
        0,
        client,
        "ipfs://secondary-ruling",
        sender=arbitrator
    )

    milestone = escrow.get_milestone(0)

    assert milestone[10] == client


def test_finalize_ruling_for_freelancer(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]
    arbitrator = accounts["arbitrator"]

    amount = 500_000

    token.approve(escrow.address, amount, sender=client)
    escrow.fund_milestone(0, sender=client)

    escrow.submit_milestone(
        0,
        "ipfs://proof",
        sender=freelancer
    )

    escrow.raise_dispute(
        0,
        "ipfs://evidence",
        sender=client
    )

    escrow.submit_ruling(
        0,
        freelancer,
        80,
        "ipfs://ruling",
        sender=arbitrator
    )

    milestone = escrow.get_milestone(0)
    appeal_deadline = milestone[9]

    boa.env.time_travel(
        seconds=appeal_deadline - boa.env.evm.patch.timestamp
    )

    escrow.finalize_ruling(
        0,
        sender=arbitrator
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 4  # RELEASED
    assert token.balanceOf(freelancer) == amount
    assert token.balanceOf(escrow.address) == 0


def test_finalize_ruling_for_client(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]
    arbitrator = accounts["arbitrator"]

    amount = 500_000

    token.approve(escrow.address, amount, sender=client)
    escrow.fund_milestone(0, sender=client)

    escrow.submit_milestone(
        0,
        "ipfs://proof",
        sender=freelancer
    )

    escrow.raise_dispute(
        0,
        "ipfs://evidence",
        sender=freelancer
    )

    escrow.submit_ruling(
        0,
        client,
        80,
        "ipfs://ruling",
        sender=arbitrator
    )

    milestone = escrow.get_milestone(0)
    appeal_deadline = milestone[9]

    boa.env.time_travel(
        seconds=appeal_deadline - boa.env.evm.patch.timestamp
    )

    escrow.finalize_ruling(
        0,
        sender=arbitrator
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 5  # REFUNDED
    assert token.balanceOf(client) == 1_000_000
    assert token.balanceOf(escrow.address) == 0


def test_low_confidence_requires_secondary_ruling(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]
    arbitrator = accounts["arbitrator"]

    amount = 500_000

    token.approve(escrow.address, amount, sender=client)
    escrow.fund_milestone(0, sender=client)

    escrow.submit_milestone(
        0,
        "ipfs://proof",
        sender=freelancer
    )

    escrow.raise_dispute(
        0,
        "ipfs://evidence",
        sender=client
    )

    # Confidence below 70 routes to secondary review.
    escrow.submit_ruling(
        0,
        freelancer,
        60,
        "ipfs://low-confidence",
        sender=arbitrator
    )

    milestone = escrow.get_milestone(0)

    assert milestone[7] == 60
    assert milestone[9] == 0

    escrow.submit_secondary_ruling(
        0,
        freelancer,
        "ipfs://secondary",
        sender=arbitrator
    )

    escrow.finalize_ruling(
        0,
        sender=arbitrator
    )

    milestone = escrow.get_milestone(0)

    assert milestone[1] == 4
    assert token.balanceOf(freelancer) == amount
    assert token.balanceOf(escrow.address) == 0


def test_only_client_can_fund(
    accounts,
    token,
    escrow
):
    freelancer = accounts["freelancer"]

    with pytest.raises(Exception):
        escrow.fund_milestone(
            0,
            sender=freelancer
        )


def test_only_freelancer_can_submit(
    accounts,
    token,
    escrow
):
    client = accounts["client"]

    with pytest.raises(Exception):
        escrow.submit_milestone(
            0,
            "ipfs://proof",
            sender=client
        )


def test_only_arbitrator_can_submit_ruling(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]

    amount = 500_000

    token.approve(escrow.address, amount, sender=client)
    escrow.fund_milestone(0, sender=client)

    escrow.submit_milestone(
        0,
        "ipfs://proof",
        sender=freelancer
    )

    escrow.raise_dispute(
        0,
        "ipfs://evidence",
        sender=client
    )

    with pytest.raises(Exception):
        escrow.submit_ruling(
            0,
            freelancer,
            80,
            "ipfs://fake",
            sender=client
        )


def test_invalid_milestone_reverts(
    accounts,
    escrow
):
    client = accounts["client"]

    with pytest.raises(Exception):
        escrow.fund_milestone(
            99,
            sender=client
        )


def test_cannot_approve_after_review_deadline(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]

    amount = 500_000

    token.approve(escrow.address, amount, sender=client)
    escrow.fund_milestone(0, sender=client)

    escrow.submit_milestone(
        0,
        "ipfs://proof",
        sender=freelancer
    )

    milestone = escrow.get_milestone(0)
    deadline = milestone[4]

    boa.env.time_travel(
        seconds=deadline - boa.env.evm.patch.timestamp
    )

    with pytest.raises(Exception):
        escrow.approve_milestone(
            0,
            sender=client
        )


def test_cannot_double_fund(
    accounts,
    token,
    escrow
):
    client = accounts["client"]

    token.approve(
        escrow.address,
        1_000_000,
        sender=client
    )

    escrow.fund_milestone(
        0,
        sender=client
    )

    with pytest.raises(Exception):
        escrow.fund_milestone(
            0,
            sender=client
        )


def test_low_confidence_cannot_finalize_without_secondary_ruling(
    accounts,
    token,
    escrow
):
    client = accounts["client"]
    freelancer = accounts["freelancer"]
    arbitrator = accounts["arbitrator"]

    amount = 500_000

    token.approve(
        escrow.address,
        amount,
        sender=client
    )

    escrow.fund_milestone(
        0,
        sender=client
    )

    escrow.submit_milestone(
        0,
        "ipfs://proof",
        sender=freelancer
    )

    escrow.raise_dispute(
        0,
        "ipfs://evidence",
        sender=client
    )

    # Low-confidence ruling: should route to secondary review.
    escrow.submit_ruling(
        0,
        freelancer,
        60,
        "ipfs://low-confidence-ruling",
        sender=arbitrator
    )

    # Primary low-confidence ruling must NOT be
    # directly finalizable.
    with pytest.raises(Exception):
        escrow.finalize_ruling(
            0,
            sender=arbitrator
        )