import time

from brownie import (
    MyStrategy,
    TheVault,
    MockStrategy,
    interface,
    accounts,
    chain,
)
from _setup.config import (
    WANT,
    WHALE_ADDRESS,
    PERFORMANCE_FEE_GOVERNANCE,
    PERFORMANCE_FEE_STRATEGIST,
    WITHDRAWAL_FEE,
    MANAGEMENT_FEE,
)
from helpers.constants import MaxUint256
from rich.console import Console

console = Console()

from dotmap import DotMap
import pytest


## Accounts ##
@pytest.fixture
def deployer():
    return accounts[0]


@pytest.fixture
def user():
    return accounts[9]


## Fund the account
@pytest.fixture
def want(deployer):
    """
    TODO: Customize this so you have the token you need for the strat
    """
    TOKEN_ADDRESS = WANT
    token = interface.IERC20Detailed(TOKEN_ADDRESS)
    WHALE = accounts.at(WHALE_ADDRESS, force=True)  ## Address with tons of token

    token.transfer(deployer, token.balanceOf(WHALE), {"from": WHALE})
    return token


@pytest.fixture
def strategist():
    return accounts[1]


@pytest.fixture
def keeper():
    return accounts[2]


@pytest.fixture
def guardian():
    return accounts[3]


@pytest.fixture
def governance():
    return accounts[4]


@pytest.fixture
def treasury():
    return accounts[5]


@pytest.fixture
def proxyAdmin():
    return accounts[6]


@pytest.fixture
def randomUser():
    return accounts[7]


@pytest.fixture
def badgerTree():
    return accounts[8]


@pytest.fixture
def deployed(
    want,
    deployer,
    strategist,
    keeper,
    guardian,
    governance,
    proxyAdmin,
    randomUser,
    badgerTree,
):
    """
    Deploys, vault and test strategy, mock token and wires them up.
    """
    want = want

    vault = TheVault.deploy({"from": deployer})
    vault.initialize(
        want,
        governance,
        keeper,
        guardian,
        governance,
        strategist,
        badgerTree,
        "",
        "",
        [
            PERFORMANCE_FEE_GOVERNANCE,
            PERFORMANCE_FEE_STRATEGIST,
            WITHDRAWAL_FEE,
            MANAGEMENT_FEE,
        ],
    )
    vault.setStrategist(deployer, {"from": governance})
    # NOTE: TheVault starts unpaused

    strategy = MyStrategy.deploy({"from": deployer})
    strategy.initialize(vault)
    # NOTE: Strategy starts unpaused

    vault.setStrategy(strategy, {"from": governance})

    return DotMap(
        deployer=deployer,
        vault=vault,
        strategy=strategy,
        want=want,
        governance=governance,
        proxyAdmin=proxyAdmin,
        randomUser=randomUser,
        performanceFeeGovernance=PERFORMANCE_FEE_GOVERNANCE,
        performanceFeeStrategist=PERFORMANCE_FEE_STRATEGIST,
        withdrawalFee=WITHDRAWAL_FEE,
        managementFee=MANAGEMENT_FEE,
        badgerTree=badgerTree,
    )


## Contracts ##
@pytest.fixture
def vault(deployed):
    return deployed.vault


@pytest.fixture
def strategy(deployed):
    return deployed.strategy


@pytest.fixture
def tokens(deployed):
    return [deployed.want]


@pytest.fixture
def locker(strategy):
    return interface.IAuraLocker(strategy.LOCKER())


### Fees ###
@pytest.fixture
def performanceFeeGovernance(deployed):
    return deployed.performanceFeeGovernance


@pytest.fixture
def performanceFeeStrategist(deployed):
    return deployed.performanceFeeStrategist


@pytest.fixture
def withdrawalFee(deployed):
    return deployed.withdrawalFee


@pytest.fixture
def auraStakingProxy():
    return interface.IAuraStakingProxy("0x0C602883797532a7218161f0b0ef3D868786F254")


@pytest.fixture
def setup_share_math(deployer, vault, want, governance):

    depositAmount = int(want.balanceOf(deployer) * 0.5)
    assert depositAmount > 0
    want.approve(vault.address, MaxUint256, {"from": deployer})
    vault.deposit(depositAmount, {"from": deployer})

    vault.earn({"from": governance})

    return DotMap(depositAmount=depositAmount)


@pytest.fixture
def setup_strat(governance, deployer, vault, strategy, want):
    """
    Convenience fixture that depoists and harvests for us
    """
    # Setup
    startingBalance = want.balanceOf(deployer)

    depositAmount = startingBalance // 2
    assert startingBalance >= depositAmount
    assert startingBalance >= 0
    # End Setup

    # Deposit
    assert want.balanceOf(vault) == 0

    want.approve(vault, MaxUint256, {"from": deployer})
    vault.deposit(depositAmount, {"from": deployer})

    available = vault.available()
    assert available > 0

    vault.earn({"from": governance})

    chain.sleep(10000 * 13)  # Mine so we get some interest
    return strategy


@pytest.fixture(autouse=True)
def distribute_auraBal(auraStakingProxy, keeper):
    auraStakingProxy.setKeeper(keeper, {"from": auraStakingProxy.owner()})
    auraStakingProxy.distribute(1, {'from': keeper})


## Forces reset before each test
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass
