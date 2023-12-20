import pytest
from ape import chain

H = 3600
DAY = 86400
WEEK = 7 * DAY
MAXTIME = 1 * 365 * 86400 // WEEK * WEEK  # 1 year
AMOUNT = 10**18
POWER = AMOUNT // MAXTIME * MAXTIME
MAX_N_WEEKS = 208


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
    unlock_time = now + WEEK * MAX_N_WEEKS
    vl_token.modify_lock(AMOUNT, unlock_time, sender=bob)
    yield bob


@pytest.fixture()
def alice(accounts, token, vl_token):
    alice = accounts[0]
    token.mint(alice, AMOUNT * 20, sender=alice)
    token.approve(vl_token.address, AMOUNT * 20, sender=alice)

    yield alice


def test_new_lock_less_than_max(alice, bob, vl_token):
    assert vl_token.totalSupply() == POWER
    now = chain.blocks.head.timestamp
    duration = MAXTIME // 5  # 1/5 of 1 year
    unlock_time = now + duration 
    vl_token.modify_lock(AMOUNT, unlock_time, sender=alice)
    # rel is depending on the ratio of the duration and the floor of the duration to full weeks
    # with short duration, ratio goes up, so rel must be bigger to pass
    assert pytest.approx(vl_token.balanceOf(alice), rel=0.05) == (AMOUNT / 5)

    point = vl_token.point_history(alice, 1)
    lock = vl_token.locked(alice)
    assert point.slope == AMOUNT // MAXTIME
    assert lock.end == unlock_time // WEEK * WEEK

    chain.pending_timestamp += duration
    chain.mine()

    assert vl_token.balanceOf(alice) == 0
    assert vl_token.totalSupply() == POWER
    assert vl_token.balanceOf(bob) == POWER


def test_new_lock_over_max(alice, bob, vl_token):
    assert vl_token.totalSupply() == POWER
    now = chain.blocks.head.timestamp
    unlock_time = now + MAXTIME + 4 * WEEK
    vl_token.modify_lock(AMOUNT, unlock_time, sender=alice)
    assert vl_token.balanceOf(alice) == POWER

    point = vl_token.point_history(alice, 1)
    lock = vl_token.locked(alice)
    assert point.slope == 0
    assert lock.end == unlock_time // WEEK * WEEK
    slop_change_time = lock.end - MAXTIME
    assert vl_token.slope_changes(alice, slop_change_time) == AMOUNT // MAXTIME
    assert vl_token.slope_changes(alice, lock.end) == -(AMOUNT // MAXTIME)

    chain.pending_timestamp += MAXTIME + 4 * WEEK
    chain.mine()
    assert vl_token.balanceOf(alice) == 0
    assert vl_token.totalSupply() == POWER
    assert vl_token.balanceOf(bob) == POWER


def test_change_lock_from_above_max_to_max(alice, bob, vl_token):
    assert vl_token.totalSupply() == POWER
    now = chain.blocks.head.timestamp
    unlock_time = now + MAXTIME + 4 * WEEK
    vl_token.modify_lock(AMOUNT, unlock_time, sender=alice)
    point = vl_token.point_history(alice, 1)
    lock = vl_token.locked(alice)
    assert point.slope == 0
    assert lock.end == unlock_time // WEEK * WEEK
    slop_change_time = lock.end - MAXTIME
    assert vl_token.slope_changes(alice, slop_change_time) == AMOUNT // MAXTIME
    assert vl_token.slope_changes(alice, lock.end) == -(AMOUNT // MAXTIME)

    vl_token.modify_lock(0, now + MAXTIME + WEEK, sender=alice)

    new_point = vl_token.point_history(alice, 2)
    new_lock = vl_token.locked(alice)
    assert new_point.slope == 0
    assert new_lock.end == (now + MAXTIME + WEEK) // WEEK * WEEK
    new_slop_change_time = new_lock.end - MAXTIME
    assert vl_token.slope_changes(alice, new_slop_change_time) == AMOUNT // MAXTIME
    assert vl_token.slope_changes(alice, new_lock.end) == -(AMOUNT // MAXTIME)
    assert vl_token.slope_changes(alice, slop_change_time) == 0
    assert vl_token.slope_changes(alice, lock.end) == 0


def test_checkpoint_after_kink_starts(alice, bob, vl_token):
    assert vl_token.totalSupply() == POWER
    now = chain.blocks.head.timestamp
    unlock_time = now + MAXTIME + 4 * WEEK
    vl_token.modify_lock(AMOUNT, unlock_time, sender=alice)
    point = vl_token.point_history(alice, 1)
    lock = vl_token.locked(alice)
    assert point.slope == 0
    assert lock.end == unlock_time // WEEK * WEEK
    slop_change_time = lock.end - MAXTIME
    assert vl_token.slope_changes(alice, slop_change_time) == AMOUNT // MAXTIME
    assert vl_token.slope_changes(alice, lock.end) == -(AMOUNT // MAXTIME)

    chain.pending_timestamp += 5 * WEEK
    chain.mine()
    assert vl_token.balanceOf(alice) < POWER
    vl_token.modify_lock(10**6, 0, sender=alice)  # trigger checkpoint.
    new_point = vl_token.point_history(alice, 2)
    assert new_point.slope == (AMOUNT + 10**6) // MAXTIME
    assert (
        vl_token.slope_changes(alice, slop_change_time) == AMOUNT // MAXTIME
    )  # no change in old slope
    assert vl_token.slope_changes(alice, lock.end) == -(AMOUNT // MAXTIME)
