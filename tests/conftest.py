import pytest
import time
from random import randint
from utils.blueprint import deploy_blueprint, construct_blueprint_deploy_bytecode
from utils.constants import (
    MAX_SEAL_DURATION_SECONDS,
    MIN_SEAL_DURATION_SECONDS,
    MIN_LIFETIME_DURATION_SECONDS,
    MAX_LIFETIME_DURATION_SECONDS,
    MAX_PROLONGATIONS,
    MIN_PROLONGATION_WINDOW_SECONDS,
    MAX_PROLONGATION_WINDOW_SECONDS,
    MAX_SEALABLES,
    SECONDS_PER_MONTH,
    SECONDS_PER_WEEK,
)

"""

    ACCOUNTS

"""


@pytest.fixture(scope="session")
def deployer(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def sealing_committee(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def stranger(accounts):
    return accounts[2]


"""

    CONTRACTS

"""


@pytest.fixture(scope="function")
def blueprint_address(project, deployer):
    gate_seal_bytecode = project.GateSeal.contract_type.deployment_bytecode.bytecode
    gate_seal_deploy_code = construct_blueprint_deploy_bytecode(gate_seal_bytecode)
    return deploy_blueprint(deployer, gate_seal_deploy_code)


@pytest.fixture(scope="function")
def gate_seal_factory(project, deployer, blueprint_address):
    return project.GateSealFactory.deploy(blueprint_address, sender=deployer)


@pytest.fixture(scope="function")
def sealables(project, deployer):
    # Create a single mock sealable for most tests
    sealable = project.SealableMock.deploy(False, False, sender=deployer)
    return [sealable.address]


@pytest.fixture(scope="function")
def seal_duration_seconds():
    # Random seal duration between min and max (6-21 days)
    return randint(MIN_SEAL_DURATION_SECONDS, MAX_SEAL_DURATION_SECONDS)


@pytest.fixture(scope="function")
def lifetime_duration_seconds():
    # Random lifetime duration between 1-6 months for testing
    return randint(MIN_LIFETIME_DURATION_SECONDS, SECONDS_PER_MONTH * 6)


@pytest.fixture(scope="function")
def max_prolongations():
    # Random prolongations between 1-5
    return randint(1, MAX_PROLONGATIONS)


@pytest.fixture(scope="function")
def prolongation_window_seconds(lifetime_duration_seconds):
    # Random window (1 week to 1 month, but not exceeding lifetime duration)
    max_window = min(MAX_PROLONGATION_WINDOW_SECONDS, lifetime_duration_seconds)
    return randint(MIN_PROLONGATION_WINDOW_SECONDS, max_window)


@pytest.fixture(scope="function")
def gate_seal(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    return project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        prolongation_window_seconds,
        sender=deployer,
    )


"""

    UTILITY FIXTURES

"""


@pytest.fixture(scope="function")
def multiple_sealables(project, deployer):
    """Create multiple sealable contracts for testing"""
    sealables = []
    for i in range(3):  # Create 3 sealables
        sealable = project.SealableMock.deploy(False, False, sender=deployer)
        sealables.append(sealable.address)
    return sealables


@pytest.fixture(scope="function")
def sealables_with_failures(project, deployer):
    """Create sealables where some will fail to pause"""
    sealables = []
    # Normal sealable
    normal = project.SealableMock.deploy(False, False, sender=deployer)
    sealables.append(normal.address)
    
    # Unpausable sealable (fails silently)
    unpausable = project.SealableMock.deploy(True, False, sender=deployer)
    sealables.append(unpausable.address)
    
    # Reverting sealable
    reverting = project.SealableMock.deploy(False, True, sender=deployer)
    sealables.append(reverting.address)
    
    return sealables


@pytest.fixture(scope="function")
def advanced_sealable(project, deployer):
    """Create an advanced sealable for complex testing scenarios"""
    return project.AdvancedSealableMock.deploy(
        False,  # gas_bomb_enabled
        False,  # revert_on_pause
        False,  # revert_on_is_paused
        0,      # gas_consumption_loops
        False,  # custom_is_paused_return
        sender=deployer,
    )


# Legacy fixtures for backward compatibility with old tests
@pytest.fixture(scope="function")
def prolongations():
    return randint(1, MAX_PROLONGATIONS)


@pytest.fixture(scope="function")
def prolongation_duration_seconds():
    return randint(SECONDS_PER_WEEK, SECONDS_PER_MONTH * 2)


@pytest.fixture(scope="function")
def expiry_timestamp():
    """Legacy fixture that returns a lambda for computing expiry timestamp"""
    return lambda: int(time.time()) + randint(SECONDS_PER_MONTH, SECONDS_PER_MONTH * 6)
