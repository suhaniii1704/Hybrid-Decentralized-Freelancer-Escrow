#pragma version 0.4.3

"""
@title MockUSDC
@notice Simple ERC20-style token used only for local escrow testing.
@dev Uses 6 decimals to match USDC.
"""

name: public(String[32])
symbol: public(String[16])
decimals: public(uint8)

totalSupply: public(uint256)

balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])


event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    amount: uint256


event Approval:
    owner: indexed(address)
    spender: indexed(address)
    amount: uint256


@deploy
def __init__():
    self.name = "Mock USDC"
    self.symbol = "mUSDC"
    self.decimals = 6


@external
def mint(
    to: address,
    amount: uint256
):
    assert to != empty(address), "Invalid recipient"

    self.balanceOf[to] += amount
    self.totalSupply += amount

    log Transfer(
        sender=empty(address),
        receiver=to,
        amount=amount
    )


@external
def approve(
    spender: address,
    amount: uint256
) -> bool:

    self.allowance[msg.sender][spender] = amount

    log Approval(
        owner=msg.sender,
        spender=spender,
        amount=amount
    )

    return True


@external
def transfer(
    to: address,
    amount: uint256
) -> bool:

    assert to != empty(address), "Invalid recipient"
    assert self.balanceOf[msg.sender] >= amount, "Insufficient balance"

    self.balanceOf[msg.sender] -= amount
    self.balanceOf[to] += amount

    log Transfer(
        sender=msg.sender,
        receiver=to,
        amount=amount
    )

    return True


@external
def transferFrom(
    from_: address,
    to: address,
    amount: uint256
) -> bool:

    assert to != empty(address), "Invalid recipient"
    assert self.balanceOf[from_] >= amount, "Insufficient balance"

    if msg.sender != from_:
        assert (
            self.allowance[from_][msg.sender] >= amount
        ), "Insufficient allowance"

        self.allowance[from_][msg.sender] -= amount

    self.balanceOf[from_] -= amount
    self.balanceOf[to] += amount

    log Transfer(
        sender=from_,
        receiver=to,
        amount=amount
    )

    return True