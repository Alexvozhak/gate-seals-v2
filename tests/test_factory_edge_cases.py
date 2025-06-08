import pytest
from ape.exceptions import VirtualMachineError
from utils.constants import (
    MAX_SEALABLES,
    MAX_PROLONGATIONS,
    MAX_PROLONGATION_DURATION_SECONDS,
    MIN_SEAL_DURATION_SECONDS,
    MAX_SEAL_DURATION_SECONDS,
    MAX_EXPIRY_PERIOD_SECONDS,
    ZERO_ADDRESS,
)


def test_factory_validate_params_valid_cases(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test validate_gate_seal_params with valid parameters"""
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
    )
    assert is_valid == True


def test_factory_validate_params_zero_committee(
    gate_seal_factory,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test validate_gate_seal_params with zero address committee"""
    is_valid = gate_seal_factory.validate_gate_seal_params(
        ZERO_ADDRESS,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
    )
    assert is_valid == False


def test_factory_validate_params_seal_duration_too_short(
    gate_seal_factory,
    sealing_committee,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test validate_gate_seal_params with too short seal duration"""
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        MIN_SEAL_DURATION_SECONDS - 1,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
    )
    assert is_valid == False


def test_factory_validate_params_seal_duration_too_long(
    gate_seal_factory,
    sealing_committee,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test validate_gate_seal_params with too long seal duration"""
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        MAX_SEAL_DURATION_SECONDS + 1,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
    )
    assert is_valid == False


def test_factory_validate_params_empty_sealables(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test validate_gate_seal_params with empty sealables list"""
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        [],
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
    )
    assert is_valid == False


def test_factory_validate_params_sealables_with_zero_address(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
    sealables,
):
    """Test validate_gate_seal_params with zero address in sealables"""
    sealables_with_zero = sealables + [ZERO_ADDRESS]
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        sealables_with_zero,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
    )
    assert is_valid == False


def test_factory_validate_params_duplicate_sealables(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
    sealables,
):
    """Test validate_gate_seal_params with duplicate sealables"""
    sealables_with_duplicate = sealables + [sealables[0]]
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        sealables_with_duplicate,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
    )
    assert is_valid == False


def test_factory_validate_params_past_expiry(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    prolongations,
    prolongation_duration_seconds,
    chain,
):
    """Test validate_gate_seal_params with expiry in the past"""
    past_timestamp = chain.pending_timestamp - 1000
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        past_timestamp,
        prolongations,
        prolongation_duration_seconds,
    )
    assert is_valid == False


def test_factory_validate_params_expiry_too_far(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    prolongations,
    prolongation_duration_seconds,
    chain,
):
    """Test validate_gate_seal_params with expiry too far in future"""
    too_far_timestamp = chain.pending_timestamp + MAX_EXPIRY_PERIOD_SECONDS + 1
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        too_far_timestamp,
        prolongations,
        prolongation_duration_seconds,
    )
    assert is_valid == False


def test_factory_validate_params_too_many_prolongations(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongation_duration_seconds,
):
    """Test validate_gate_seal_params with too many prolongations"""
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        MAX_PROLONGATIONS + 1,
        prolongation_duration_seconds,
    )
    assert is_valid == False


def test_factory_validate_params_zero_prolongations_nonzero_duration(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    """Test validate_gate_seal_params with zero prolongations but nonzero duration"""
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        0,  # zero prolongations
        1000,  # but nonzero duration
    )
    assert is_valid == False


def test_factory_validate_params_nonzero_prolongations_zero_duration(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    """Test validate_gate_seal_params with nonzero prolongations but zero duration"""
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        1,  # nonzero prolongations
        0,  # but zero duration
    )
    assert is_valid == False


def test_factory_validate_params_prolongation_duration_too_long(
    gate_seal_factory,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    """Test validate_gate_seal_params with prolongation duration too long"""
    is_valid = gate_seal_factory.validate_gate_seal_params(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        1,
        MAX_PROLONGATION_DURATION_SECONDS + 1,
    )
    assert is_valid == False


def test_factory_creation_with_extreme_parameters(
    project,
    deployer,
    blueprint_address,
    generate_sealables,
):
    """Test factory creation with maximum valid parameters"""
    factory = project.GateSealFactory.deploy(blueprint_address, sender=deployer)
    
    # Use maximum values for all parameters
    committee = deployer.address
    seal_duration = MAX_SEAL_DURATION_SECONDS
    sealables = generate_sealables(MAX_SEALABLES)
    expiry = deployer.provider.get_block("latest").timestamp + MAX_EXPIRY_PERIOD_SECONDS
    prolongations = MAX_PROLONGATIONS
    prolongation_duration = MAX_PROLONGATION_DURATION_SECONDS
    
    # Should validate successfully
    is_valid = factory.validate_gate_seal_params(
        committee,
        seal_duration,
        sealables,
        expiry,
        prolongations,
        prolongation_duration,
    )
    assert is_valid == True
    
    # Should be able to create GateSeal with these parameters
    tx = factory.create_gate_seal(
        committee,
        seal_duration,
        sealables,
        expiry,
        prolongations,
        prolongation_duration,
        sender=deployer,
    )
    
    assert len(tx.events) == 1
    assert tx.events[0].event_name == "GateSealCreated"


def test_factory_creation_with_minimum_parameters(
    project,
    deployer,
    blueprint_address,
    generate_sealables,
):
    """Test factory creation with minimum valid parameters"""
    factory = project.GateSealFactory.deploy(blueprint_address, sender=deployer)
    
    # Use minimum values for all parameters
    committee = deployer.address
    seal_duration = MIN_SEAL_DURATION_SECONDS
    sealables = generate_sealables(1)  # minimum 1 sealable
    expiry = deployer.provider.get_block("latest").timestamp + 1000  # near future
    prolongations = 0  # minimum prolongations
    prolongation_duration = 0  # must be zero when prolongations = 0
    
    # Should validate successfully
    is_valid = factory.validate_gate_seal_params(
        committee,
        seal_duration,
        sealables,
        expiry,
        prolongations,
        prolongation_duration,
    )
    assert is_valid == True
    
    # Should be able to create GateSeal with these parameters
    tx = factory.create_gate_seal(
        committee,
        seal_duration,
        sealables,
        expiry,
        prolongations,
        prolongation_duration,
        sender=deployer,
    )
    
    assert len(tx.events) == 1
    assert tx.events[0].event_name == "GateSealCreated"


def test_factory_with_invalid_blueprint(
    project,
    deployer,
    accounts,
):
    """Test factory creation with invalid blueprint address"""
    # Try to create factory with EOA address instead of contract
    eoa_address = accounts[5].address
    
    with pytest.raises(VirtualMachineError, match="blueprint: zero address"):
        project.GateSealFactory.deploy(ZERO_ADDRESS, sender=deployer)


def test_factory_multiple_deployments_different_params(
    project,
    deployer,
    gate_seal_factory,
    sealing_committee,
    generate_sealables,
    accounts,
):
    """Test creating multiple GateSeals with different parameters"""
    deployments = []
    
    # Deploy multiple GateSeals with varying parameters
    for i in range(3):
        committee = accounts[i + 2].address  # Different committee for each
        seal_duration = MIN_SEAL_DURATION_SECONDS + (i * 100000)  # Different durations
        sealables = generate_sealables(2 + i)  # Different number of sealables
        expiry = deployer.provider.get_block("latest").timestamp + (30 * 24 * 3600) + (i * 10000)
        prolongations = i + 1  # Different prolongations count
        prolongation_duration = (i + 1) * 1000000  # Different prolongation durations
        
        tx = gate_seal_factory.create_gate_seal(
            committee,
            seal_duration,
            sealables,
            expiry,
            prolongations,
            prolongation_duration,
            sender=deployer,
        )
        
        assert len(tx.events) == 1
        assert tx.events[0].event_name == "GateSealCreated"
        
        gate_seal_address = tx.events[0].gate_seal
        gate_seal = project.GateSeal.at(gate_seal_address)
        
        # Verify parameters are set correctly
        assert gate_seal.get_sealing_committee() == committee
        assert gate_seal.get_seal_duration_seconds() == seal_duration
        assert gate_seal.get_sealables() == sealables
        assert gate_seal.get_prolongations_remaining() == prolongations
        assert gate_seal.get_prolongation_duration_seconds() == prolongation_duration
        
        deployments.append(gate_seal_address)
    
    # All deployments should be unique
    assert len(set(deployments)) == 3, "All deployments should be unique"


def test_factory_gas_cost_measurement(
    project,
    deployer,
    gate_seal_factory,
    sealing_committee,
    generate_sealables,
):
    """Test gas cost of factory deployment with different sealables count"""
    gas_costs = []
    
    for num_sealables in [1, 4, 8]:
        sealables = generate_sealables(num_sealables)
        
        tx = gate_seal_factory.create_gate_seal(
            sealing_committee,
            MIN_SEAL_DURATION_SECONDS,
            sealables,
            deployer.provider.get_block("latest").timestamp + 1000000,
            1,
            1000000,
            sender=deployer,
        )
        
        gas_costs.append((num_sealables, tx.gas_used))
    
    # Gas cost should increase with more sealables but not dramatically
    gas_1, gas_4, gas_8 = [gas for _, gas in gas_costs]
    
    assert gas_4 > gas_1, "Gas should increase with more sealables"
    assert gas_8 > gas_4, "Gas should continue to increase"
    
    # But increase should be reasonable (not exponential)
    ratio_8_to_1 = gas_8 / gas_1
    assert ratio_8_to_1 < 3, f"8x sealables should not use more than 3x gas, got {ratio_8_to_1}x"