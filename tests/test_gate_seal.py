from ape import reverts
import pytest
import random
from ape.exceptions import ContractLogicError


from utils.constants import (
    MAX_SEAL_DURATION_SECONDS,
    MAX_SEALABLES,
    MIN_SEAL_DURATION_SECONDS,
    ZERO_ADDRESS,
    MIN_LIFETIME_DURATION_SECONDS,
    MAX_LIFETIME_DURATION_SECONDS,
    MAX_PROLONGATIONS,
    MIN_PROLONGATION_WINDOW_SECONDS,
    MAX_PROLONGATION_WINDOW_SECONDS,
    SECONDS_PER_DAY,
    SECONDS_PER_WEEK,
    SECONDS_PER_MONTH,
)


def test_committee_cannot_be_zero_address(
    project,
    deployer,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    with pytest.raises(ContractLogicError, match="committee cannot be zero address"):
        project.GateSeal.deploy(
            ZERO_ADDRESS,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_gate_seal_can_be_created_with_valid_parameters(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration_seconds,
        max_prolongations,
        prolongation_window_seconds,
        sender=deployer,
    )

    # Check all parameters are set correctly
    assert gate_seal.sealing_committee() == sealing_committee
    assert gate_seal.seal_duration_seconds() == seal_duration_seconds
    assert gate_seal.sealables() == sealables
    assert gate_seal.lifetime_duration_seconds() == lifetime_duration_seconds
    assert gate_seal.expiry_timestamp() > 0  # should be set
    assert gate_seal.max_prolongations() == max_prolongations
    assert gate_seal.prolongations_used() == 0
    assert gate_seal.prolongation_window_seconds() == prolongation_window_seconds
    assert gate_seal.is_expired() == False  # not expired initially


def test_seal_duration_validation(
    project,
    deployer,
    sealing_committee,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
    prolongation_window_seconds,
):
    # Too short
    with pytest.raises(ContractLogicError, match="seal duration too short"):
        project.GateSeal.deploy(
            sealing_committee,
            MIN_SEAL_DURATION_SECONDS - 1,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )

    # Too long
    with pytest.raises(ContractLogicError, match="seal duration too long"):
        project.GateSeal.deploy(
            sealing_committee,
            MAX_SEAL_DURATION_SECONDS + 1,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_lifetime_duration_validation(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    max_prolongations,
    prolongation_window_seconds,
):
    # Too short lifetime duration
    with pytest.raises(ContractLogicError, match="lifetime duration too short"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            MIN_LIFETIME_DURATION_SECONDS - 1,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )

    # Too long lifetime duration
    with pytest.raises(ContractLogicError, match="lifetime duration too long"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            MAX_LIFETIME_DURATION_SECONDS + 1,
            max_prolongations,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_prolongations_validation(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    prolongation_window_seconds,
):
    # Too many prolongations
    with pytest.raises(ContractLogicError, match="too many prolongations"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            MAX_PROLONGATIONS + 1,
            prolongation_window_seconds,
            sender=deployer,
        )


def test_prolongation_window_validation(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    lifetime_duration_seconds,
    max_prolongations,
):
    # Too short window
    with pytest.raises(ContractLogicError, match="activation window too short"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            MIN_PROLONGATION_WINDOW_SECONDS - 1,
            sender=deployer,
        )

    # Too long window
    with pytest.raises(ContractLogicError, match="activation window too long"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            MAX_PROLONGATION_WINDOW_SECONDS + 1,
            sender=deployer,
        )

    # Window cannot exceed lifetime duration
    with pytest.raises(ContractLogicError, match="activation window cannot exceed lifetime duration"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            lifetime_duration_seconds,
            max_prolongations,
            lifetime_duration_seconds + 1,
            sender=deployer,
        )


def test_seal_success_with_valid_sealables(
    gate_seal,
    sealing_committee,
    sealables,
):
    # Should successfully seal
    gate_seal.seal(sealables, sender=sealing_committee)

    # Should be expired immediately after use (one-time panic button)
    assert gate_seal.is_expired() == True


def test_seal_fails_if_not_sealing_committee(
    gate_seal,
    stranger,
    sealables,
):
    with pytest.raises(ContractLogicError, match="unauthorized caller"):
        gate_seal.seal(sealables, sender=stranger)


def test_seal_fails_if_already_used(
    gate_seal,
    sealing_committee,
    sealables,
):
    # Use the seal first
    gate_seal.seal(sealables, sender=sealing_committee)

    # Second attempt should fail because GateSeal expired immediately after first use
    with pytest.raises(ContractLogicError, match="gate seal expired"):
        gate_seal.seal(sealables, sender=sealing_committee)


def test_prolong_lifetime_success(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    max_prolongations,
):
    # Create GateSeal with short lifetime duration and short activation window
    lifetime_duration = SECONDS_PER_WEEK * 2  # 2 weeks
    activation_window = SECONDS_PER_WEEK  # 1 week

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration,
        max_prolongations,
        activation_window,
        sender=deployer,
    )

    initial_expiry = gate_seal.expiry_timestamp()

    # Fast forward to activation window
    chain = project.provider.network.ecosystem.get_chain("ethereum")
    chain.mine(deltatime=lifetime_duration - activation_window + 1)

    # Should be able to prolong
    assert gate_seal.can_prolong_lifetime() == True

    # Prolong lifetime
    gate_seal.prolongLifetime(sender=sealing_committee)

    # Check that expiry was extended
    new_expiry = gate_seal.expiry_timestamp()
    assert new_expiry == initial_expiry + lifetime_duration

    # Check prolongations used
    assert gate_seal.prolongations_used() == 1


def test_prolong_lifetime_fails_outside_activation_window(
    gate_seal,
    sealing_committee,
):
    # Too early - should fail
    with pytest.raises(ContractLogicError, match="outside activation window"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_prolong_lifetime_fails_if_no_prolongations_remaining(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    # Create GateSeal with 0 prolongations
    lifetime_duration = SECONDS_PER_WEEK * 2  # 2 weeks
    activation_window = SECONDS_PER_WEEK  # 1 week

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration,
        0,  # no prolongations
        activation_window,
        sender=deployer,
    )

    # Fast forward to activation window
    chain = project.provider.network.ecosystem.get_chain("ethereum")
    chain.mine(deltatime=lifetime_duration - activation_window + 1)

    # Should not be able to prolong
    assert gate_seal.can_prolong_lifetime() == False

    # Prolong should fail
    with pytest.raises(ContractLogicError, match="no prolongations remaining"):
        gate_seal.prolongLifetime(sender=sealing_committee)


def test_prolong_lifetime_fails_if_not_committee(
    project,
    deployer,
    sealing_committee,
    stranger,
    seal_duration_seconds,
    sealables,
    max_prolongations,
):
    # Create GateSeal with short lifetime duration
    lifetime_duration = SECONDS_PER_WEEK * 2  # 2 weeks
    activation_window = SECONDS_PER_WEEK  # 1 week

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration,
        max_prolongations,
        activation_window,
        sender=deployer,
    )

    # Fast forward to activation window
    chain = project.provider.network.ecosystem.get_chain("ethereum")
    chain.mine(deltatime=lifetime_duration - activation_window + 1)

    # Stranger cannot prolong
    with pytest.raises(ContractLogicError, match="unauthorized caller"):
        gate_seal.prolongLifetime(sender=stranger)


def test_is_expired_functionality(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    max_prolongations,
    prolongation_window_seconds,
):
    # Create GateSeal with very short lifetime
    lifetime_duration = 1  # 1 second

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration,
        max_prolongations,
        prolongation_window_seconds,
        sender=deployer,
    )

    # Should not be expired initially
    assert gate_seal.is_expired() == False

    # Fast forward past expiry
    chain = project.provider.network.ecosystem.get_chain("ethereum")
    chain.mine(deltatime=lifetime_duration + 1)

    # Should be expired now
    assert gate_seal.is_expired() == True


def test_seal_duration_too_short(
    project, deployer, sealing_committee, sealables, expiry_timestamp
):
    with reverts("seal duration: too short"):
        project.GateSeal.deploy(
            sealing_committee,
            MIN_SEAL_DURATION_SECONDS - 1,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_seal_duration_shortest(
    project, deployer, sealing_committee, sealables, expiry_timestamp
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        MIN_SEAL_DURATION_SECONDS,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    assert (
        gate_seal.get_seal_duration_seconds() == MIN_SEAL_DURATION_SECONDS
    ), "seal duration can be at least 4 days"


def test_seal_duration_max(
    project,
    deployer,
    sealing_committee,
    sealables,
    expiry_timestamp,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        MAX_SEAL_DURATION_SECONDS,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    assert (
        gate_seal.get_seal_duration_seconds() == MAX_SEAL_DURATION_SECONDS
    ), "seal duration can be up to 14 days"


def test_seal_duration_exceeds_max(
    project,
    deployer,
    sealing_committee,
    sealables,
    expiry_timestamp,
):
    with reverts("seal duration: exceeds max"):
        project.GateSeal.deploy(
            sealing_committee,
            MAX_SEAL_DURATION_SECONDS + 1,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_sealables_exceeds_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
):
    with reverts("sealables: empty list"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            [],
            expiry_timestamp,
            sender=deployer,
        )


def test_expiry_timestamp_cannot_be_now(
    project, deployer, sealing_committee, seal_duration_seconds, sealables, now
):
    with reverts("expiry timestamp: must be in the future"):
        project.GateSeal.deploy(
            sealing_committee, seal_duration_seconds, sealables, now, sender=deployer
        )


def test_expiry_timestamp_cannot_exceed_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    with reverts("expiry timestamp: exceeds max expiry period"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp + 1,
            sender=deployer,
        )


@pytest.mark.parametrize("zero_address_index", range(MAX_SEALABLES))
def test_sealables_cannot_include_zero_address(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    zero_address_index,
    generate_sealables,
):
    sealables = generate_sealables(MAX_SEALABLES)
    sealables[zero_address_index] = ZERO_ADDRESS

    with reverts("sealables: includes zero address"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_sealables_cannot_include_duplicates(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    if len(sealables) == MAX_SEALABLES:
        sealables[-1] = sealables[0]
    else:
        sealables.append(sealables[0])

    with reverts("sealables: includes duplicates"):
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_sealables_cannot_exceed_max_length(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    generate_sealables,
):
    sealables = generate_sealables(MAX_SEALABLES + 1)

    with reverts():
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            sender=deployer,
        )


def test_deploy_params_must_match(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    assert (
        gate_seal.get_sealing_committee() == sealing_committee
    ), "sealing committee doesn't match"
    assert (
        gate_seal.get_seal_duration_seconds() == seal_duration_seconds
    ), "seal duration doesn't match"
    assert gate_seal.get_sealables() == sealables, "sealables don't match"
    assert (
        gate_seal.get_expiry_timestamp() == expiry_timestamp
    ), "expiry timestamp don't match"
    assert gate_seal.is_expired() == False, "should not be expired"


def test_seal_all(
    networks,
    chain,
    project,
    gate_seal,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    expected_timestamp = chain.pending_timestamp
    tx = gate_seal.seal(sealables, sender=sealing_committee)

    for i, event in enumerate(tx.events):
        assert event.event_name == "Sealed"
        assert event.gate_seal == gate_seal.address
        assert event.sealed_by == sealing_committee
        assert event.sealed_for == seal_duration_seconds
        assert event.sealable == sealables[i]
        assert event.sealed_at == expected_timestamp

    assert (
        gate_seal.get_expiry_timestamp() == expected_timestamp
    ), "expiry timestamp matches"

    assert (
        gate_seal.is_expired() == True
    ), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        assert project.SealableMock.at(sealable).isPaused(), "sealable must be sealed"


def test_seal_partial(
    networks,
    chain,
    project,
    gate_seal,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    expected_timestamp = chain.pending_timestamp
    sealables_to_seal = [sealables[0]]

    tx = gate_seal.seal(sealables_to_seal, sender=sealing_committee)

    for i, event in enumerate(tx.events):
        assert event.event_name == "Sealed"
        assert event.gate_seal == gate_seal.address
        assert event.sealed_by == sealing_committee
        assert event.sealed_for == seal_duration_seconds
        assert event.sealable == sealables_to_seal[i]
        assert event.sealed_at == expected_timestamp

    assert (
        gate_seal.is_expired() == True
    ), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        sealable_contract = project.SealableMock.at(sealable)
        if sealable in sealables_to_seal:
            assert sealable_contract.isPaused(), "sealable must be sealed"
        else:
            assert not sealable_contract.isPaused(), "sealable must not be sealed"


def test_seal_empty_subset(gate_seal, sealing_committee):
    with reverts("sealables: empty subset"):
        gate_seal.seal([], sender=sealing_committee)


def test_seal_duplicates(gate_seal, sealables, sealing_committee):
    if len(sealables) == MAX_SEALABLES:
        sealables[-1] = sealables[0]
    else:
        sealables.append(sealables[0])
    with reverts("sealables: includes duplicates"):
        gate_seal.seal(sealables, sender=sealing_committee)


def test_seal_nonintersecting_subset(accounts, gate_seal, sealing_committee):
    with reverts("sealables: includes a non-sealable"):
        gate_seal.seal([accounts[0]], sender=sealing_committee)


def test_seal_partially_intersecting_subset(
    accounts, gate_seal, sealing_committee, sealables
):
    with reverts("sealables: includes a non-sealable"):
        gate_seal.seal([sealables[0], accounts[0]], sender=sealing_committee)


def test_natural_expiry(
    networks,
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    networks.active_provider.set_timestamp(expiry_timestamp - 1)
    networks.active_provider.mine()

    assert not gate_seal.is_expired(), "expired prematurely"

    networks.active_provider.set_timestamp(expiry_timestamp)
    networks.active_provider.mine()

    assert gate_seal.is_expired(), "must already be expired"


def test_seal_only_once(gate_seal, sealing_committee, sealables):
    gate_seal.seal(sealables, sender=sealing_committee)

    with reverts("gate seal: expired"):
        gate_seal.seal(sealables, sender=sealing_committee)


@pytest.mark.parametrize("failing_index", range(MAX_SEALABLES))
def test_single_failed_sealable_error_message(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    failing_index,
    generate_sealables,
):
    sealables = generate_sealables(MAX_SEALABLES)
    unpausable = random.choice([True, False])
    should_revert = not unpausable
    sealables[failing_index] = generate_sealables(1, unpausable, should_revert)[0]

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    with reverts(f"{failing_index}"):
        gate_seal.seal(
            sealables,
            sender=sealing_committee,
        )


@pytest.mark.parametrize("repeat", range(10))
def test_several_failed_sealables_error_message(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    generate_sealables,
    repeat,
):
    sealables = generate_sealables(MAX_SEALABLES)

    failed = random.sample(range(MAX_SEALABLES), random.choice(range(1, MAX_SEALABLES)))

    for index in failed:
        sealables[index] = generate_sealables(1, True)[0]

    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    failed.sort()
    failed.reverse()
    with reverts("".join([str(n) for n in failed])):
        gate_seal.seal(
            sealables,
            sender=sealing_committee,
        )


@pytest.mark.skip("only run this with automining disabled")
def test_cannot_seal_twice_in_one_tx(gate_seal, sealables, sealing_committee):
    gate_seal.seal(sealables, sender=sealing_committee)
    with reverts("gate seal: expired"):
        gate_seal.seal(sealables, sender=sealing_committee)


def test_raw_call_success_should_be_false_when_sealable_reverts_on_pause(
    project,
    deployer,
    generate_sealables,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
):
    """
    `raw_call` without `max_outsize` and with `revert_on_failure=True` for some reason returns the boolean value of memory[0] :^)

    Which is why we specify `max_outsize=32`, even though don't actually use it.

    To test that `success` returns actual value instead of returning bool of memory[0],
    we need to pause the contract before the sealing,
    so that the condition `success and is_paused()` is false (i.e `False and True`), see GateSeal.vy::seal()

    For that, we use `__force_pause_for` on SealableMock to ignore any checks and forcefully pause the contract.
    After calling this function, the SealableMock is paused but the call to `pauseFor` will still revert,
    thus the returned `success` should be False, the condition fails and the call reverts altogether.

    Without `max_outsize=32`, the transaction would not revert.
    """

    unpausable = False
    should_revert = True
    # we'll use only 1 sealable
    sealables = generate_sealables(1, unpausable, should_revert)

    # deploy GateSeal
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        sender=deployer,
    )

    # making sure we have the right contract
    assert gate_seal.get_sealables() == sealables

    # forcefully pause the sealable before sealing
    sealables[0].__force_pause_for(seal_duration_seconds, sender=deployer)
    assert sealables[0].isPaused(), "should be paused now"

    # seal() should revert because `raw_call` to sealable returns `success=False`, even though isPaused() is True.
    with reverts("0"):
        gate_seal.seal(sealables, sender=sealing_committee)


def test_gate_seal_expires_immediately_after_use(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
):
    # Create GateSeal with long lifetime
    lifetime_duration = SECONDS_PER_MONTH * 6  # 6 months
    window = SECONDS_PER_WEEK  # 1 week
    
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        lifetime_duration,
        5,  # max prolongations
        window,
        sender=deployer,
    )
    
    # Initially should not be expired
    assert gate_seal.is_expired() == False
    
    # Get initial expiry timestamp (should be far in the future)
    initial_expiry = gate_seal.expiry_timestamp()
    chain = project.provider.network.ecosystem.get_chain("ethereum")
    current_time = chain.pending_timestamp
    
    # Verify expiry is in the future
    assert initial_expiry > current_time
    
    # Use the seal
    gate_seal.seal(sealables, sender=sealing_committee)
    
    # Should be expired immediately (expiry_timestamp set to current block.timestamp)
    assert gate_seal.is_expired() == True
    
    # Expiry timestamp should be current time or very close to it
    new_expiry = gate_seal.expiry_timestamp()
    assert new_expiry <= chain.pending_timestamp
    
    # Cannot be used again
    with pytest.raises(ContractLogicError, match="gate seal expired"):
        gate_seal.seal(sealables, sender=sealing_committee)
    
    # Cannot be prolonged after use
    with pytest.raises(ContractLogicError, match="gate seal expired"):
        gate_seal.prolongLifetime(sender=sealing_committee)
