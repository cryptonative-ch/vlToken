import pytest

DAY = 86400
WEEK = 7 * DAY


@pytest.fixture
def gov(accounts):
    yield accounts[0]


@pytest.fixture
def whale(accounts):
    a = accounts[1]
    yield a


@pytest.fixture
def shark(accounts):
    a = accounts[2]
    yield a


@pytest.fixture
def fish(accounts):
    a = accounts[3]
    yield a


@pytest.fixture
def panda(accounts):
    yield accounts[4]


@pytest.fixture
def doggie(accounts):
    yield accounts[5]


@pytest.fixture
def bunny(accounts):
    yield accounts[6]


@pytest.fixture
def token(project, gov):
    yield gov.deploy(project.Token, "TOKEN")


@pytest.fixture
def create_token(project, gov):
    def create_token(name):
        return gov.deploy(project.Token, name)

    yield create_token

'''
@pytest.fixture
def vl_token_rewards(vl_token_and_reward_pool):
    (_, vl_token_rewards) = vl_token_and_reward_pool
    yield vl_token_rewards
'''