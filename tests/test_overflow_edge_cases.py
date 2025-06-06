import pytest
from ape.exceptions import VirtualMachineError
from utils.constants import (
    MAX_PROLONGATION_DURATION_SECONDS,
    MAX_PROLONGATIONS,
    SECONDS_PER_DAY,
)


def test_prolong_timestamp_overflow_edge(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    prolongations,
):
    """Test overflow protection in prolong() function"""
    # Create GateSeal with expiry very close to uint256 max
    uint256_max = 2**256 - 1
    near_overflow_expiry = uint256_max - MAX_PROLONGATION_DURATION_SECONDS + 1
    
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        near_overflow_expiry,
        1,  # one prolongation
        MAX_PROLONGATION_DURATION_SECONDS,
        sender=deployer,
    )
    
    # Attempting to prolong should fail due to overflow protection
    with pytest.raises(VirtualMachineError, match="expiry: overflow"):
        gate_seal.prolong(sender=sealing_committee)


def test_expiry_at_exact_block_timestamp(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    prolongations,
    prolongation_duration_seconds,
    chain,
):
    """Test behavior when GateSeal expires exactly at current block timestamp"""
    current_time = chain.pending_timestamp
    expiry_at_current_time = current_time
    
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_at_current_time + 1,  # Expires in next block
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Mine one block to reach expiry
    chain.mine()
    
    # Should be expired now
    assert gate_seal.is_expired(), "GateSeal should be expired"
    assert gate_seal.get_time_until_expiry() == 0, "Time until expiry should be 0"
    assert not gate_seal.can_prolong(), "Should not be able to prolong expired GateSeal"
    
    # Should not be able to seal
    with pytest.raises(VirtualMachineError, match="gate seal: expired"):
        gate_seal.seal(sealables, sender=sealing_committee)
        
    # Should not be able to prolong
    with pytest.raises(VirtualMachineError, match="gate seal: expired"):
        gate_seal.prolong(sender=sealing_committee)


def test_seal_exactly_at_expiry_edge(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    prolongations,
    prolongation_duration_seconds,
    chain,
):
    """Test sealing in the last possible moment before expiry"""
    current_time = chain.pending_timestamp
    expiry_time = current_time + 2  # Expires in 2 seconds
    
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_time,
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Should be able to seal before expiry
    assert not gate_seal.is_expired(), "Should not be expired yet"
    
    # Seal should work
    tx = gate_seal.seal(sealables, sender=sealing_committee)
    
    # Verify sealing events
    assert len(tx.events) == len(sealables), "Should have sealing events for all sealables"
    for event in tx.events:
        assert event.event_name == "Sealed"
        
    # Should be expired immediately after sealing
    assert gate_seal.is_expired(), "Should be expired after sealing"


def test_prolong_chain_maximum(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    chain,
):
    """Test using all available prolongations in sequence"""
    initial_expiry = chain.pending_timestamp + SECONDS_PER_DAY * 30  # 30 days from now
    prolongation_duration = SECONDS_PER_DAY * 30  # 30 days per prolongation
    
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        initial_expiry,
        MAX_PROLONGATIONS,
        prolongation_duration,
        sender=deployer,
    )
    
    # Use all prolongations
    for i in range(MAX_PROLONGATIONS):
        expected_prolongations_remaining = MAX_PROLONGATIONS - i
        assert gate_seal.get_prolongations_remaining() == expected_prolongations_remaining
        assert gate_seal.can_prolong(), f"Should be able to prolong at iteration {i}"
        
        current_expiry = gate_seal.get_expiry_timestamp()
        tx = gate_seal.prolong(sender=sealing_committee)
        
        # Check event
        assert len(tx.events) == 1
        event = tx.events[0]
        assert event.event_name == "ProlongationUsed"
        assert event.new_expiry == current_expiry + prolongation_duration
        assert event.prolongations_remaining == expected_prolongations_remaining - 1
        
        # Verify state changes
        assert gate_seal.get_expiry_timestamp() == current_expiry + prolongation_duration
        assert gate_seal.get_prolongations_remaining() == expected_prolongations_remaining - 1
    
    # No more prolongations should be available
    assert gate_seal.get_prolongations_remaining() == 0
    assert not gate_seal.can_prolong(), "Should not be able to prolong anymore"
    
    # Attempting another prolongation should fail
    with pytest.raises(VirtualMachineError, match="prolongations: exhausted"):
        gate_seal.prolong(sender=sealing_committee)


def test_prolongation_near_uint256_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    """Test prolongation when current expiry is near uint256 maximum"""
    # Set expiry to a large value but not close enough to overflow
    large_expiry = 2**200  # Large but safe value
    small_prolongation = 1000  # Small prolongation duration
    
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        large_expiry,
        1,
        small_prolongation,
        sender=deployer,
    )
    
    # This should work fine
    original_expiry = gate_seal.get_expiry_timestamp()
    gate_seal.prolong(sender=sealing_committee)
    
    assert gate_seal.get_expiry_timestamp() == original_expiry + small_prolongation


def test_time_until_expiry_edge_cases(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    prolongations,
    prolongation_duration_seconds,
    chain,
):
    """Test get_time_until_expiry() in various edge cases"""
    current_time = chain.pending_timestamp
    expiry_time = current_time + 100
    
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_time,
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Should return time until expiry
    time_until = gate_seal.get_time_until_expiry()
    assert time_until > 0 and time_until <= 100
    
    # Mine blocks to approach expiry
    chain.mine(timestamp=expiry_time - 1)
    
    # Should return small positive value
    time_until = gate_seal.get_time_until_expiry()
    assert time_until == 1
    
    # Mine one more block to reach expiry
    chain.mine(timestamp=expiry_time)
    
    # Should return 0 when expired
    assert gate_seal.get_time_until_expiry() == 0
    assert gate_seal.is_expired()
    
    # Should still return 0 after expiry
    chain.mine(timestamp=expiry_time + 1000)
    assert gate_seal.get_time_until_expiry() == 0


def test_prolong_exactly_at_expiry(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    prolongations,
    prolongation_duration_seconds,
    chain,
):
    """Test attempting to prolong exactly when GateSeal expires"""
    current_time = chain.pending_timestamp
    expiry_time = current_time + 1
    
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_time,
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )
    
    # Mine to exact expiry time
    chain.mine(timestamp=expiry_time)
    
    # Should not be able to prolong at expiry
    assert gate_seal.is_expired()
    with pytest.raises(VirtualMachineError, match="gate seal: expired"):
        gate_seal.prolong(sender=sealing_committee)