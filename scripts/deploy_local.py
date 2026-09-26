import boa


def main():
    # ---------------------------------------------------------
    # Create local test accounts
    # ---------------------------------------------------------
    client = boa.env.generate_address("client")
    freelancer = boa.env.generate_address("freelancer")
    arbitrator = boa.env.generate_address("arbitrator")

    print("Client:     ", client)
    print("Freelancer: ", freelancer)
    print("Arbitrator: ", arbitrator)

    # ---------------------------------------------------------
    # Deploy MockUSDC
    # ---------------------------------------------------------
    token = boa.load("contracts/MockUSDC.vy")

    print("\nMockUSDC deployed:")
    print(token.address)

    # Give client 1,000,000 mUSDC = 1 USDC
    # Mock token uses 6 decimals.
    token.mint(
        client,
        1_000_000
    )

    print("Client balance:", token.balanceOf(client))

    # ---------------------------------------------------------
    # Escrow configuration
    # ---------------------------------------------------------
    review_period = 60
    appeal_window = 60

    spec_uri = "ipfs://job-spec"

    milestone_amounts = [
        500_000
    ]

    milestone_due_dates = [
        0
    ]

    # ---------------------------------------------------------
    # Deploy EscrowJob directly
    # ---------------------------------------------------------
    escrow = boa.load(
        "contracts/EscrowJob.vy",
        client,
        freelancer,
        arbitrator,
        token.address,
        review_period,
        appeal_window,
        spec_uri,
        milestone_amounts,
        milestone_due_dates,
    )

    print("\nEscrowJob deployed:")
    print(escrow.address)

    # ---------------------------------------------------------
    # Verify configuration
    # ---------------------------------------------------------
    print("\n--- Escrow Configuration ---")
    print("Client:       ", escrow.client())
    print("Freelancer:   ", escrow.freelancer())
    print("Arbitrator:   ", escrow.arbitrator())
    print("Token:        ", escrow.token())
    print("Review period:", escrow.review_period())
    print("Appeal window:", escrow.appeal_window())
    print("Spec URI:     ", escrow.spec_uri())

    # ---------------------------------------------------------
    # Verify milestone
    # ---------------------------------------------------------
    milestone = escrow.get_milestone(0)

    print("\n--- Milestone 0 ---")
    print("Amount:       ", milestone[0])
    print("Status:       ", milestone[1])
    print("Due date:     ", milestone[2])

    print("\nDeployment successful.")


if __name__ == "__main__":
    main()