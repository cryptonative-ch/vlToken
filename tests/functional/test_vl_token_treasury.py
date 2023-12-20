import pytest
from ape import chain

H = 3600
DAY = 86400
WEEK = 7 * DAY
MAXTIME = 1 * 365 * 86400 // WEEK * WEEK  # 1 year
AMOUNT = 10**18
POWER = 2 * AMOUNT // MAXTIME * MAXTIME
MAX_N_WEEKS = 208
MAX_PENALTY_RATIO = 3 / 4  # 75% for early exit of max lock


@pytest.fixture(autouse=True)
def setup_time(chain):
    chain.pending_timestamp += WEEK - (
        chain.pending_timestamp - (chain.pending_timestamp // WEEK * WEEK)
    )
    chain.mine()


@pytest.fixture()
def bob(accounts, token, vl_token):
    bob = accounts[1]
    token.mint(bob, AMOUNT * 20, sender=bob)
    token.approve(vl_token.address, AMOUNT * 20, sender=bob)
    now = chain.blocks.head.timestamp
    # unlock_time = now + WEEK * MAX_N_WEEKS
    unlock_time = now + MAXTIME
    vl_token.modify_lock(2*AMOUNT, unlock_time, sender=bob)
    yield bob


@pytest.fixture()
def alice(accounts, token, vl_token):
    alice = accounts[0]
    token.mint(alice, AMOUNT * 20, sender=alice)
    token.approve(vl_token.address, AMOUNT * 20, sender=alice)

    yield alice


def test_treasury_filled_after_early_withdraw(alice, bob, treasury, token, vl_token):
    assert pytest.approx(vl_token.totalSupply(), rel=0.01)  == POWER
    now = chain.blocks.head.timestamp

    unlock_time = now + MAXTIME // 2  # 1/2 of MAXTIME

    vl_token.modify_lock(AMOUNT, unlock_time, sender=alice)
    
    alice_vl_token_balance = vl_token.balanceOf(alice)

    assert pytest.approx(alice_vl_token_balance, rel=0.01) == (AMOUNT / 2) 

    vl_token.withdraw(sender=alice)

    treasury_token_balance = token.balanceOf(treasury)
    alice_token_balance = token.balanceOf(alice)

    # for 1/2 MAXTIME vl token, the penalty is 50%
    # starts with 75% on 1/4, hits 50% on 1/2, then 25% on 3/4, 0 at 4/4

    assert pytest.approx(treasury_token_balance, rel=0.01) ==  MAX_PENALTY_RATIO * 2/3 * AMOUNT
    assert pytest.approx(alice_token_balance, rel=0.01) == 20 * AMOUNT - treasury_token_balance

    bob_vl_token_balance = vl_token.balanceOf(bob)
    assert pytest.approx(bob_vl_token_balance, rel=0.01) == 2 * AMOUNT

    duration = int(MAXTIME * 0.6)  # 0.6 of MAXTIME, 0.4 left

    chain.pending_timestamp += duration
    chain.mine()

    vl_token.withdraw(sender=bob)

    bob_vl_token_balance = vl_token.balanceOf(bob)
    assert pytest.approx(bob_vl_token_balance, rel=0.01) == 0

    treasury_token_balance_2 = token.balanceOf(treasury)
    treasury_diff = treasury_token_balance_2 - treasury_token_balance

    bob_token_balance = token.balanceOf(bob)

    tax = min(MAX_PENALTY_RATIO, (MAXTIME - duration) / MAXTIME )

    assert pytest.approx(treasury_diff, rel=0.01) ==  2 * AMOUNT * tax

    assert pytest.approx(bob_token_balance, rel=0.01) == 20 * AMOUNT - treasury_diff


    assert token.balanceOf(treasury) != 0
    assert vl_token.balanceOf(alice) == 0
    assert vl_token.balanceOf(bob) == 0
    assert vl_token.totalSupply() == 0