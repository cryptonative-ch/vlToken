import ape
import pytest
from ape import chain

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
DAY = 86400
WEEK = 7 * DAY


@pytest.fixture(autouse=True)
def setup_time(chain):
    chain.pending_timestamp += WEEK - (
        chain.pending_timestamp - (chain.pending_timestamp // WEEK * WEEK)
    )
    chain.mine()


def test_vl_token_claim(token, vl_token, whale, vl_token_rewards, gov):
    whale_amount = 10**22
    token.mint(whale, whale_amount, sender=whale)
    token.approve(vl_token, whale_amount, sender=whale)
    vl_token.modify_lock(
        whale_amount, chain.pending_timestamp + 86400 * 365, sender=whale
    )
    chain.pending_timestamp += 86400 * 7
    rewards = 10**18
    token.mint(gov, rewards, sender=gov)

    token.approve(vl_token_rewards, rewards, sender=gov)

    chain.pending_timestamp += 86400
    current_begning_of_week = int(chain.pending_timestamp / (86400 * 7)) * 86400 * 7
    vl_token.checkpoint(sender=gov)

    vl_token_rewards.checkpoint_total_supply(sender=gov)
    vl_token_rewards.burn(rewards, sender=gov)

    assert rewards == vl_token_rewards.tokens_per_week(current_begning_of_week)
    chain.pending_timestamp += 3600
    vl_token_rewards.claim(sender=whale)
    assert token.balanceOf(whale) == 0

    chain.pending_timestamp += 86400 * 14
    chain.mine()
    vl_token_rewards.claim(sender=whale)
    assert token.balanceOf(whale) == rewards


def test_vl_token_claim_for(token, vl_token, whale, fish, vl_token_rewards, gov):
    whale_amount = 10**22
    token.mint(whale, whale_amount, sender=whale)
    token.approve(vl_token, whale_amount, sender=whale)
    vl_token.modify_lock(
        whale_amount, chain.pending_timestamp + 3600 * 24 * 365, sender=whale
    )
    chain.pending_timestamp += 86400 * 7
    rewards = 10**18
    token.mint(gov, rewards, sender=gov)

    token.approve(vl_token_rewards, rewards, sender=gov)

    chain.pending_timestamp += 3600 * 24
    current_begning_of_week = int(chain.pending_timestamp / (86400 * 7)) * 86400 * 7

    vl_token_rewards.checkpoint_total_supply(sender=gov)
    vl_token_rewards.burn(rewards, sender=gov)

    assert rewards == vl_token_rewards.tokens_per_week(current_begning_of_week)
    chain.pending_timestamp += 3600
    vl_token_rewards.claim(sender=whale)
    assert token.balanceOf(whale) == 0

    chain.pending_timestamp += 3600 * 24 * 14
    chain.mine()
    vl_token_rewards.claim(whale, sender=fish)
    assert token.balanceOf(whale) == rewards
