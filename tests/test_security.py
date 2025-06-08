import pytest
from ape.exceptions import VirtualMachineError
from utils.constants import MAX_SEALABLES


def test_seal_reentrancy_via_malicious_pausable(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test protection against reentrancy through malicious pausable contract"""
    # Create a malicious pausable contract
    malicious_pausable = project.AdvancedSealableMock.deploy(
        False,  # gas_bomb_enabled
        False,  # revert_on_pause
        False,  # revert_on_is_paused
        0,      # gas_consumption_loops
        False,  # custom_is_paused_return
        sender=deployer,
    )
    
    # Create GateSeal with malicious pausable
    sealables = [malicious_pausable.address]
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Set up reentrancy target
    malicious_pausable.setReentrancyTarget(gate_seal.address, sender=deployer)
    
    # Sealing should still work despite reentrancy attempt
    # The malicious contract will try to call prolongLifetime() during pauseFor()
    tx = gate_seal.seal(sealables, sender=sealing_committee)
    
    # Should have one Sealed event
    assert len(tx.events) == 1
    assert tx.events[0].event_name == "Sealed"
    
    # GateSeal should be expired (one-time use)
    assert gate_seal.is_expired()


def test_seal_with_gas_bomb_pausable(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test sealing with pausable contract that consumes excessive gas"""
    # Create gas bomb pausable
    gas_bomb_pausable = project.AdvancedSealableMock.deploy(
        True,   # gas_bomb_enabled
        False,  # revert_on_pause
        False,  # revert_on_is_paused
        1000,   # gas_consumption_loops - moderate amount
        False,  # custom_is_paused_return
        sender=deployer,
    )
    
    sealables = [gas_bomb_pausable.address]
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Should still be able to seal despite high gas consumption
    tx = gate_seal.seal(sealables, sender=sealing_committee)
    
    # Verify successful sealing
    assert len(tx.events) == 1
    assert tx.events[0].event_name == "Sealed"
    assert gas_bomb_pausable.isPaused()


def test_seal_with_reverting_pausable(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test sealing with pausable contract that always reverts"""
    # Create reverting pausable
    reverting_pausable = project.AdvancedSealableMock.deploy(
        False,  # gas_bomb_enabled
        True,   # revert_on_pause - will revert on pauseFor calls
        False,  # revert_on_is_paused
        0,      # gas_consumption_loops
        False,  # custom_is_paused_return
        sender=deployer,
    )
    
    # Create normal pausable for comparison
    normal_pausable = project.SealableMock.deploy(False, False, sender=deployer)
    
    sealables = [normal_pausable.address, reverting_pausable.address]
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Sealing should fail due to reverting pausable
    with pytest.raises(VirtualMachineError, match="failed sealable indexes: 1"):
        gate_seal.seal(sealables, sender=sealing_committee)


def test_seal_with_mixed_failing_sealables(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test sealing with mixture of working and failing sealables"""
    # Create different types of pausables
    normal_pausable = project.SealableMock.deploy(False, False, sender=deployer)
    reverting_pausable = project.AdvancedSealableMock.deploy(
        False, True, False, 0, False, sender=deployer  # revert_on_pause=True
    )
    is_paused_reverting = project.AdvancedSealableMock.deploy(
        False, False, True, 0, False, sender=deployer  # revert_on_is_paused=True
    )
    
    sealables = [normal_pausable.address, reverting_pausable.address, is_paused_reverting.address]
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Should fail with both failed sealables in error message
    with pytest.raises(VirtualMachineError, match="failed sealable indexes:"):
        gate_seal.seal(sealables, sender=sealing_committee)


def test_factory_dos_via_massive_sealables(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
    blueprint_address,
):
    """Test DoS resistance when creating GateSeal with maximum sealables"""
    factory = project.GateSealFactory.deploy(blueprint_address, sender=deployer)
    
    # Create maximum number of sealables
    sealables = []
    for i in range(MAX_SEALABLES):
        pausable = project.SealableMock.deploy(False, False, sender=deployer)
        sealables.append(pausable.address)
    
    # Should be able to create GateSeal with max sealables
    tx = factory.create_gate_seal(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Should succeed
    assert len(tx.events) == 1
    assert tx.events[0].event_name == "GateSealCreated"
    
    # Get the created GateSeal
    gate_seal_address = tx.events[0].gate_seal
    gate_seal = project.GateSeal.at(gate_seal_address)
    
    # Should be able to seal all sealables
    seal_tx = gate_seal.seal(sealables, sender=sealing_committee)
    assert len(seal_tx.events) == MAX_SEALABLES


def test_seal_already_paused_contracts(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test sealing contracts that are already paused"""
    # Create pausables and pre-pause them
    pausable1 = project.SealableMock.deploy(False, False, sender=deployer)
    pausable2 = project.SealableMock.deploy(False, False, sender=deployer)
    
    # Pre-pause one of them
    pausable1.pauseFor(1000, sender=deployer)
    assert pausable1.isPaused()
    assert not pausable2.isPaused()
    
    sealables = [pausable1.address, pausable2.address]
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Should be able to seal both (already paused and not paused)
    tx = gate_seal.seal(sealables, sender=sealing_committee)
    
    # Should have events for both
    assert len(tx.events) == 2
    for event in tx.events:
        assert event.event_name == "Sealed"
    
    # Both should be paused
    assert pausable1.isPaused()
    assert pausable2.isPaused()


def test_seal_with_custom_is_paused_behavior(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test sealing with pausable that returns custom isPaused values"""
    # Create pausable with custom isPaused behavior
    custom_pausable = project.AdvancedSealableMock.deploy(
        False,  # gas_bomb_enabled
        False,  # revert_on_pause
        False,  # revert_on_is_paused
        0,      # gas_consumption_loops
        True,   # custom_is_paused_return - returns opposite of actual state
        sender=deployer,
    )
    
    sealables = [custom_pausable.address]
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Initially not paused, but isPaused returns True (custom behavior)
    assert custom_pausable.isPaused() == True  # Custom behavior
    assert custom_pausable.getPausedUntil() == 0  # Actually not paused
    
    # Should still be able to seal because pauseFor will work
    # and our improved logic checks both before and after states
    tx = gate_seal.seal(sealables, sender=sealing_committee)
    
    # Should succeed because contract was "paused" according to isPaused
    assert len(tx.events) == 1
    assert tx.events[0].event_name == "Sealed"


def test_multiple_gate_seals_same_pausables(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
    accounts,
):
    """Test multiple GateSeals with overlapping sealables"""
    # Create shared pausables
    pausable1 = project.SealableMock.deploy(False, False, sender=deployer)
    pausable2 = project.SealableMock.deploy(False, False, sender=deployer)
    
    sealables = [pausable1.address, pausable2.address]
    
    # Create two GateSeals with same sealables but different committees
    gate_seal1 = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    gate_seal2 = project.GateSeal.deploy(
        accounts[3],  # different sealing committee
        seal_duration_seconds,
        sealables,
        expiry_timestamp(),
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # First GateSeal seals the contracts
    tx1 = gate_seal1.seal(sealables, sender=sealing_committee)
    assert len(tx1.events) == 2
    
    # Contracts should be paused
    assert pausable1.isPaused()
    assert pausable2.isPaused()
    
    # Second GateSeal should still be able to "seal" already paused contracts
    # because they are already in the desired state
    tx2 = gate_seal2.seal(sealables, sender=accounts[3])
    assert len(tx2.events) == 2  # Should succeed because contracts are already paused


def test_gas_consumption_linear_scaling(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """Test that gas consumption scales linearly with number of sealables"""
    gas_measurements = []
    
    for num_sealables in [1, 4, 8]:
        # Create sealables
        sealables = []
        for i in range(num_sealables):
            pausable = project.SealableMock.deploy(False, False, sender=deployer)
            sealables.append(pausable.address)
        
        gate_seal = project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp(),
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
        
        # Measure gas for sealing
        tx = gate_seal.seal(sealables, sender=sealing_committee)
        gas_measurements.append((num_sealables, tx.gas_used))
    
    # Check that gas consumption increases roughly linearly
    gas_1, gas_4, gas_8 = [gas for _, gas in gas_measurements]
    
    # Gas should increase with more sealables
    assert gas_4 > gas_1, "Gas should increase with more sealables"
    assert gas_8 > gas_4, "Gas should continue to increase"
    
    # Rough linearity check (allowing for some overhead)
    # gas_4 should be roughly 4x gas_1, gas_8 should be roughly 8x gas_1
    ratio_4_to_1 = gas_4 / gas_1
    ratio_8_to_1 = gas_8 / gas_1
    
    # Allow some tolerance for overhead
    assert 2 < ratio_4_to_1 < 6, f"4x sealables should use roughly 4x gas, got {ratio_4_to_1}x"
    assert 4 < ratio_8_to_1 < 12, f"8x sealables should use roughly 8x gas, got {ratio_8_to_1}x"