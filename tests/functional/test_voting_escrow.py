from pytest import approx
import pytest
import ape
from ape import chain

H = 3600
DAY = 86400
WEEK = 7 * DAY
MAXTIME = 1 * 365 * 86400 // WEEK * WEEK
TOL = 120 / WEEK # tolerance for approx
MAX_N_WEEKS = 209


@pytest.fixture(autouse=True)
def setup_time(chain):
    chain.pending_timestamp += WEEK - (
        chain.pending_timestamp - (chain.pending_timestamp // WEEK * WEEK)
    )
    chain.mine()


def test_over_max_time(chain, accounts, token, vl_token):
    alice = accounts[0]
    amount = 1000 * 10**18
    power = amount // MAXTIME * MAXTIME
    token.mint(alice, amount * 20, sender=alice)
    token.approve(vl_token.address, amount * 20, sender=alice)

    now = chain.blocks.head.timestamp
    unlock_time = now + MAXTIME + 8 * WEEK + 3600
    vl_token.modify_lock(amount, unlock_time, sender=alice)  # MAXTIME and one month lock
    point = vl_token.point_history(alice.address, 1)
    assert point.bias == power
    assert point.slope == 0
    assert vl_token.totalSupply() == power
    chain.pending_timestamp += WEEK
    chain.mine()
    assert vl_token.totalSupply() == power
    chain.pending_timestamp += 8 * WEEK
    chain.mine()
    assert vl_token.totalSupply() < power
    assert vl_token.totalSupply() == vl_token.balanceOf(alice)

    vl_token.checkpoint(sender=alice)
    assert vl_token.totalSupply() == vl_token.balanceOf(alice)

    vl_token.modify_lock(amount, 0, sender=alice)
    chain.pending_timestamp += WEEK

    assert approx(vl_token.totalSupply(), rel=10e-14) == vl_token.balanceOf(alice)
    assert vl_token.totalSupply() == vl_token.balanceOf(alice)


def test_lock_slightly_over_limit_is_rounded_down(chain, accounts, token, vl_token):
    alice = accounts[0]
    amount = 1000 * 10**18
    power = amount // MAXTIME * MAXTIME

    token.mint(alice, amount * 20, sender=alice)
    token.approve(vl_token.address, amount * 20, sender=alice)

    now = chain.blocks.head.timestamp
    unlock_time = now + MAXTIME + WEEK + 3600
    vl_token.modify_lock(amount, unlock_time, sender=alice)  # MAXTIME ++
    assert vl_token.point_history(alice.address, 1).slope == 0
    assert vl_token.balanceOf(alice) == power
    assert (
        vl_token.slope_changes(vl_token, (chain.blocks.head.timestamp // WEEK + 1) * WEEK)
        != 0
    )
    assert vl_token.slope_changes(
        vl_token, (chain.blocks.head.timestamp // WEEK + 1) * WEEK
    ) == vl_token.slope_changes(alice, (chain.blocks.head.timestamp // WEEK + 1) * WEEK)
    chain.pending_timestamp += 2 * DAY
    chain.mine()
    vl_token.modify_lock(amount, 0, sender=alice)  # lock some more
    assert vl_token.balanceOf(alice) == (amount * 2) // MAXTIME * MAXTIME
    chain.pending_timestamp += WEEK
    chain.mine()
    assert vl_token.balanceOf(alice) < (amount * 2) // MAXTIME * MAXTIME


def test_get_prior_votes(chain, accounts, token, vl_token):
    alice = accounts[0]
    amount = 1000 * 10**18
    power = amount // MAXTIME * MAXTIME
    token.mint(alice, amount * 20, sender=alice)
    token.approve(vl_token.address, amount * 20, sender=alice)

    now = chain.blocks.head.timestamp
    unlock_time = now + MAXTIME + WEEK + 4
    vl_token.modify_lock(amount, unlock_time, sender=alice)  # MAXTIME ++

    for _ in range(5 * 7 * 24):
        chain.pending_timestamp += H - 1
        chain.mine()

    assert vl_token.getPriorVotes(alice, chain.blocks.head.number) < power


def test_lock_over_limit_goes_to_zero(chain, accounts, token, vl_token):
    alice = accounts[0]
    amount = 1000 * 10**18
    power = amount // MAXTIME * MAXTIME
    token.mint(alice, amount * 20, sender=alice)
    token.approve(vl_token.address, amount * 20, sender=alice)

    now = chain.blocks.head.timestamp
    unlock_time = now + MAXTIME + WEEK + 10
    vl_token.modify_lock(amount, unlock_time, sender=alice)  # MAXTIME ++
    assert vl_token.point_history(alice.address, 1).slope == 0
    assert vl_token.balanceOf(alice) == power
    assert (
        vl_token.slope_changes(vl_token, (chain.blocks.head.timestamp // WEEK + 1) * WEEK)
        != 0
    )
    chain.pending_timestamp += MAXTIME + WEEK
    chain.mine()
    assert vl_token.balanceOf(alice) == 0
    assert pytest.approx(vl_token.totalSupply(), abs=10**8) == 0


def test_multiple_lock_decay(accounts, token, vl_token):
    DURATION = MAXTIME // len(accounts)

    now = chain.blocks.head.timestamp
    for i in range(len(accounts)):
        account = accounts[i]
        amount = 10**22
        token.mint(account, amount, sender=account)
        token.approve(vl_token.address, amount, sender=account)
        vl_token.modify_lock(amount, (DURATION * (i + 1)) + now, sender=account)
    balance_sum = 0
    for i in range(len(accounts)):
        balance_sum += vl_token.balanceOf(accounts[i])
    assert pytest.approx(vl_token.totalSupply(), 10**14) == balance_sum
    assert vl_token.totalSupply() == balance_sum
    # Test decay
    for i in range(len(accounts)):
        chain.pending_timestamp += DURATION
        chain.mine()
        balance_sum = 0
        for i in range(len(accounts)):
            balance_sum += vl_token.balanceOf(accounts[i])
        assert pytest.approx(vl_token.totalSupply(), 10**14) == balance_sum
        assert vl_token.totalSupply() == balance_sum
    assert vl_token.totalSupply() == 0


def test_voting_powers(chain, accounts, token, vl_token):
    """
    Test voting power in the following scenario.
    Alice:
    ~~~~~~~
    ^
    | *       *
    | | \     |  \
    | |  \    |    \
    +-+---+---+------+---> t
    Bob:
    ~~~~~~~
    ^
    |         *
    |         | \
    |         |  \
    +-+---+---+---+--+---> t
    Alice has 100% of voting power in the first period.
    She has 2/3 power at the start of 2nd period, with Bob having 1/2 power
    (due to smaller locktime).
    Alice's power grows to 100% by Bob's unlock.
    Checking that totalSupply is appropriate.
    After the test is done, check all over again with getPriorVotes / totalSupplyAt
    """
    alice, bob = accounts[:2]
    amount = 1000 * 10**18
    token.mint(bob, amount, sender=bob)
    token.mint(alice, amount, sender=alice)

    stages = {}

    token.approve(vl_token.address, amount * 10, sender=alice)
    token.approve(vl_token.address, amount * 10, sender=bob)

    assert vl_token.totalSupply() == 0
    assert vl_token.balanceOf(alice) == 0
    assert vl_token.balanceOf(bob) == 0

    # Move to timing which is good for testing - beginning of a UTC week
    chain.pending_timestamp += (
        chain.blocks.head.timestamp // WEEK + 1
    ) * WEEK - chain.blocks.head.timestamp
    chain.mine()

    chain.pending_timestamp += (
        H - 1
    )  # substract one second because `chain.mine`` in hardhat moves time by one second.
    chain.mine()

    stages["before_deposits"] = (chain.blocks.head.number, chain.blocks.head.timestamp)

    vl_token.modify_lock(amount, chain.blocks.head.timestamp + WEEK, sender=alice)
    stages["alice_deposit"] = (chain.blocks.head.number, chain.blocks.head.timestamp)

    chain.pending_timestamp += H - 1
    chain.mine()

    assert approx(vl_token.totalSupply(), rel=TOL) == amount // MAXTIME * (WEEK - 2 * H)
    assert approx(vl_token.balanceOf(alice), rel=TOL) == amount // MAXTIME * (
        WEEK - 2 * H
    )
    assert vl_token.balanceOf(bob) == 0
    t0 = chain.blocks.head.timestamp

    stages["alice_in_0"] = []
    stages["alice_in_0"].append((chain.blocks.head.number, chain.blocks.head.timestamp))
    for i in range(7):
        for _ in range(24):
            chain.pending_timestamp += H - 1
            chain.mine()
        dt = chain.blocks.head.timestamp - t0
        assert approx(vl_token.totalSupply(), rel=TOL) == amount // MAXTIME * max(
            WEEK - 2 * H - dt, 0
        )

        assert approx(vl_token.balanceOf(alice), rel=TOL) == amount // MAXTIME * max(
            WEEK - 2 * H - dt, 0
        )

        assert vl_token.balanceOf(bob) == 0
        stages["alice_in_0"].append(
            (chain.blocks.head.number, chain.blocks.head.timestamp)
        )

    chain.pending_timestamp += H - 1

    assert vl_token.balanceOf(alice) == 0
    vl_token.withdraw(sender=alice)
    stages["alice_withdraw"] = (chain.blocks.head.number, chain.blocks.head.timestamp)
    assert vl_token.totalSupply() == 0
    assert vl_token.balanceOf(alice) == 0
    assert vl_token.balanceOf(bob) == 0

    chain.pending_timestamp += H - 1
    chain.mine()

    # Next week (for round counting)
    chain.pending_timestamp += (
        chain.blocks.head.timestamp // WEEK + 1
    ) * WEEK - chain.blocks.head.timestamp
    chain.mine()

    vl_token.modify_lock(amount, chain.blocks.head.timestamp + 2 * WEEK, sender=alice)
    stages["alice_deposit_2"] = (chain.blocks.head.number, chain.blocks.head.timestamp)

    assert approx(vl_token.totalSupply(), rel=TOL) == amount // MAXTIME * 2 * WEEK
    assert approx(vl_token.balanceOf(alice), rel=TOL) == amount // MAXTIME * 2 * WEEK
    assert vl_token.balanceOf(bob) == 0

    vl_token.modify_lock(amount, chain.blocks.head.timestamp + WEEK, sender=bob)
    stages["bob_deposit_2"] = (chain.blocks.head.number, chain.blocks.head.timestamp)

    assert approx(vl_token.totalSupply(), rel=TOL) == amount // MAXTIME * 3 * WEEK
    assert approx(vl_token.balanceOf(alice), rel=TOL) == amount // MAXTIME * 2 * WEEK
    assert approx(vl_token.balanceOf(bob), rel=TOL) == amount // MAXTIME * WEEK

    t0 = chain.blocks.head.timestamp
    chain.pending_timestamp += H - 1
    chain.mine()

    stages["alice_bob_in_2"] = []
    # Beginning of week: weight 3
    # End of week: weight 1
    for i in range(7):
        for _ in range(24):
            chain.pending_timestamp += H - 1
            chain.mine()
        dt = chain.blocks.head.timestamp - t0
        w_total = vl_token.totalSupply()
        w_alice = vl_token.balanceOf(alice)
        w_bob = vl_token.balanceOf(bob)
        assert w_total == w_alice + w_bob
        assert approx(w_alice, rel=TOL) == amount // MAXTIME * max(2 * WEEK - dt, 0)
        assert approx(w_bob, rel=TOL) == amount // MAXTIME * max(WEEK - dt, 0)
        stages["alice_bob_in_2"].append(
            (chain.blocks.head.number, chain.blocks.head.timestamp)
        )

    chain.pending_timestamp += H - 1
    chain.mine()

    vl_token.withdraw(sender=bob)
    t0 = chain.blocks.head.timestamp
    stages["bob_withdraw_1"] = (chain.blocks.head.number, chain.blocks.head.timestamp)
    w_total = vl_token.totalSupply()
    w_alice = vl_token.balanceOf(alice)
    assert w_alice == w_total
    assert approx(w_total, rel=TOL) == amount // MAXTIME * (WEEK - 2 * H)
    assert vl_token.balanceOf(bob) == 0

    chain.pending_timestamp += H - 1
    chain.mine()

    stages["alice_in_2"] = []
    for i in range(7):
        for _ in range(24):
            chain.pending_timestamp += H - 1
            chain.mine()
        dt = chain.blocks.head.timestamp - t0
        w_total = vl_token.totalSupply()
        w_alice = vl_token.balanceOf(alice)
        assert w_total == w_alice
        assert approx(w_total, rel=TOL) == amount // MAXTIME * max(WEEK - dt - 2 * H, 0)
        assert vl_token.balanceOf(bob) == 0
        stages["alice_in_2"].append(
            (chain.blocks.head.number, chain.blocks.head.timestamp)
        )

    vl_token.withdraw(sender=alice)
    stages["alice_withdraw_2"] = (chain.blocks.head.number, chain.blocks.head.timestamp)

    chain.pending_timestamp += H - 1
    chain.mine()

    stages["bob_withdraw_2"] = (chain.blocks.head.number, chain.blocks.head.timestamp)

    assert vl_token.totalSupply() == 0
    assert vl_token.balanceOf(alice) == 0
    assert vl_token.balanceOf(bob) == 0

    # Now test historical getPriorVotes and others

    assert vl_token.getPriorVotes(alice, stages["before_deposits"][0]) == 0
    assert vl_token.getPriorVotes(bob, stages["before_deposits"][0]) == 0
    assert vl_token.totalSupplyAt(stages["before_deposits"][0]) == 0

    w_alice = vl_token.getPriorVotes(alice, stages["alice_deposit"][0])
    assert approx(w_alice, rel=TOL) == amount // MAXTIME * (WEEK - H)
    assert vl_token.getPriorVotes(bob, stages["alice_deposit"][0]) == 0
    w_total = vl_token.totalSupplyAt(stages["alice_deposit"][0])
    assert w_alice == w_total

    for i, (block, t) in enumerate(stages["alice_in_0"]):
        w_alice = vl_token.getPriorVotes(alice, block)
        w_bob = vl_token.getPriorVotes(bob, block)
        w_total = vl_token.totalSupplyAt(block)
        assert w_bob == 0
        assert w_alice == w_total
        if w_alice == 0:
            continue
        time_left = WEEK * (7 - i) // 7 - 2 * H
        error_1h = (
            H / time_left
        )  # Rounding error of 1 block is possible, and we have 1h blocks
        assert approx(w_alice, rel=error_1h) == amount // MAXTIME * time_left

    w_total = vl_token.totalSupplyAt(stages["alice_withdraw"][0])
    w_alice = vl_token.getPriorVotes(alice, stages["alice_withdraw"][0])
    w_bob = vl_token.getPriorVotes(bob, stages["alice_withdraw"][0])
    assert w_alice == w_bob == w_total == 0

    w_total = vl_token.totalSupplyAt(stages["alice_deposit_2"][0])
    w_alice = vl_token.getPriorVotes(alice, stages["alice_deposit_2"][0])
    w_bob = vl_token.getPriorVotes(bob, stages["alice_deposit_2"][0])
    assert approx(w_total, rel=TOL) == amount // MAXTIME * 2 * WEEK
    assert w_total == w_alice
    assert w_bob == 0

    w_total = vl_token.totalSupplyAt(stages["bob_deposit_2"][0])
    w_alice = vl_token.getPriorVotes(alice, stages["bob_deposit_2"][0])
    w_bob = vl_token.getPriorVotes(bob, stages["bob_deposit_2"][0])
    assert w_total == w_alice + w_bob
    assert approx(w_total, rel=TOL) == amount // MAXTIME * 3 * WEEK
    assert approx(w_alice, rel=TOL) == amount // MAXTIME * 2 * WEEK

    t0 = stages["bob_deposit_2"][1]
    for i, (block, t) in enumerate(stages["alice_bob_in_2"]):
        w_alice = vl_token.getPriorVotes(alice, block)
        w_bob = vl_token.getPriorVotes(bob, block)
        w_total = vl_token.totalSupplyAt(block)
        assert w_total == w_alice + w_bob
        dt = t - t0
        error_1h = H / (
            2 * WEEK - i * DAY
        )  # Rounding error of 1 block is possible, and we have 1h blocks
        assert approx(w_alice, rel=error_1h) == amount // MAXTIME * max(
            2 * WEEK - dt, 0
        )
        assert approx(w_bob, rel=error_1h) == amount // MAXTIME * max(WEEK - dt, 0)

    w_total = vl_token.totalSupplyAt(stages["bob_withdraw_1"][0])
    w_alice = vl_token.getPriorVotes(alice, stages["bob_withdraw_1"][0])
    w_bob = vl_token.getPriorVotes(bob, stages["bob_withdraw_1"][0])
    assert w_total == w_alice
    assert approx(w_total, rel=TOL) == amount // MAXTIME * (WEEK - 2 * H)
    assert w_bob == 0

    t0 = stages["bob_withdraw_1"][1]
    for i, (block, t) in enumerate(stages["alice_in_2"]):
        w_alice = vl_token.getPriorVotes(alice, block)
        w_bob = vl_token.getPriorVotes(bob, block)
        w_total = vl_token.totalSupplyAt(block)
        assert w_total == w_alice
        assert w_bob == 0
        dt = t - t0
        error_1h = H / (
            WEEK - i * DAY + DAY
        )  # Rounding error of 1 block is possible, and we have 1h blocks
        assert approx(w_total, rel=error_1h) == amount // MAXTIME * max(
            WEEK - dt - 2 * H, 0
        )

    w_total = vl_token.totalSupplyAt(stages["bob_withdraw_2"][0])
    w_alice = vl_token.getPriorVotes(alice, stages["bob_withdraw_2"][0])
    w_bob = vl_token.getPriorVotes(bob, stages["bob_withdraw_2"][0])
    assert w_total == w_alice == w_bob == 0


def test_early_exit(chain, accounts, token, vl_token):
    alice, bob = accounts[:2]
    amount = 1000 * 10**18
    token.mint(bob, amount, sender=bob)
    token.mint(alice, amount, sender=alice)

    token.approve(vl_token.address, amount * 10, sender=alice)
    token.approve(vl_token.address, amount * 10, sender=bob)

    chain.pending_timestamp += (
        chain.blocks.head.timestamp // WEEK + 1
    ) * WEEK - chain.blocks.head.timestamp
    chain.mine()

    chain.pending_timestamp += H
    vl_token.modify_lock(amount, chain.blocks.head.timestamp + 2 * WEEK, sender=alice)
    vl_token.modify_lock(amount, chain.blocks.head.timestamp + WEEK, sender=bob)
    vl_token.withdraw(sender=bob)
    assert vl_token.totalSupply() == vl_token.balanceOf(alice)

    point_history_1 = dict(
        zip(["bias", "slope", "ts", "blk"], vl_token.point_history(vl_token, 1))
    )
    point_history_3 = dict(
        zip(["bias", "slope", "ts", "blk"], vl_token.point_history(vl_token, 3))
    )
    assert approx(point_history_1["bias"], rel=10e-4) == point_history_3["bias"]
    assert approx(point_history_1["slope"], rel=10e-4) == point_history_3["slope"]
    vl_token.withdraw(sender=alice)
    assert vl_token.totalSupply() == 0
    point_history_4 = dict(
        zip(["bias", "slope", "ts", "blk"], vl_token.point_history(vl_token, 4))
    )
    assert point_history_4["ts"] == chain.blocks.head.timestamp
    assert point_history_4["bias"] == 0
    assert point_history_4["slope"] == 0


def test_total_supply_in_the_past(chain, accounts, token, vl_token):
    alice = accounts[0]
    amount = 1000 * 10**18
    token.mint(alice, amount * 20, sender=alice)
    token.approve(vl_token.address, amount * 20, sender=alice)

    now = chain.blocks.head.timestamp
    unlock_time = now + MAXTIME
    vl_token.modify_lock(amount, unlock_time, sender=alice)
    checkpoint = chain.blocks.head.timestamp
    checkpoint_total_supply = vl_token.totalSupply()

    chain.pending_timestamp += WEEK
    vl_token.modify_lock(amount, 0, sender=alice)  # lock some more
    assert checkpoint_total_supply == vl_token.totalSupply(checkpoint)


def test_lock_cant_exceed_reply_range(chain, accounts, token, vl_token):
    alice = accounts[0]
    amount = 1000 * 10**18
    power = amount // MAXTIME * MAXTIME
    token.mint(alice, amount * 20, sender=alice)
    token.approve(vl_token.address, amount * 20, sender=alice)
    now = chain.blocks.head.timestamp
    unlock_time = now + MAX_N_WEEKS * WEEK
    with ape.reverts():
        vl_token.modify_lock(amount, unlock_time, sender=alice)
