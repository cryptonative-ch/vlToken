import pytest
from ape import convert, chain
from eth._utils.address import generate_contract_address
from eth_utils import to_checksum_address, to_canonical_address

DAY = 86400
WEEK = 7 * DAY


@pytest.fixture
def token(accounts, project):
    dev = accounts[0]
    yield project.Token.deploy("TOKEN", sender=dev)


@pytest.fixture
def vl_token_and_treasury(accounts, project, token):
    # calculate the treasury address to pass to vl_token
    collector = accounts[2]
    treasury_address = to_checksum_address(
        generate_contract_address(
            to_canonical_address(str(accounts[0])), accounts[0].nonce + 1
        )
    )
    vl_token = project.VoteLockToken.deploy(token, treasury_address, collector, sender=accounts[0])
    start_time = (
        chain.pending_timestamp + 7 * 3600 * 24
    )  # MUST offset by a week otherwise token distributed are lost since no lock has been made yet.
    yield vl_token, treasury_address, collector


@pytest.fixture
def vl_token(vl_token_and_treasury):
    yield vl_token_and_treasury[0]


@pytest.fixture
def treasury(vl_token_and_treasury):
    yield vl_token_and_treasury[1]

@pytest.fixture
def collector(vl_token_and_treasury):
    yield vl_token_and_treasury[2]