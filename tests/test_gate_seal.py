from ape.exceptions import VirtualMachineError
import pytest
import random
from utils.constants import (
    MAX_SEAL_DURATION_SECONDS,
    MAX_SEALABLES,
    MIN_SEAL_DURATION_SECONDS,
    ZERO_ADDRESS,
    MAX_PROLONGATIONS,
    MAX_PROLONGATION_DURATION_SECONDS,
)


def test_committee_cannot_be_zero_address(
    project,
    deployer,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    try:
        project.GateSeal.deploy(
            ZERO_ADDRESS,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "sealing committee: zero address" in str(e)


def test_seal_duration_too_short(
    project,
    deployer,
    sealing_committee,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    try:
        project.GateSeal.deploy(
            sealing_committee,
            MIN_SEAL_DURATION_SECONDS - 1,
            sealables,
            expiry_timestamp,
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "seal duration: too short" in str(e)


def test_seal_duration_shortest(
    project,
    deployer,
    sealing_committee,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        MIN_SEAL_DURATION_SECONDS,
        sealables,
        expiry_timestamp,
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )

    assert (
        gate_seal.get_seal_duration_seconds() == MIN_SEAL_DURATION_SECONDS
    ), "seal duration can be at least 6 days"


def test_seal_duration_max(
    project,
    deployer,
    sealing_committee,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        MAX_SEAL_DURATION_SECONDS,
        sealables,
        expiry_timestamp,
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )

    assert (
        gate_seal.get_seal_duration_seconds() == MAX_SEAL_DURATION_SECONDS
    ), "seal duration can be up to 21 days"


def test_seal_duration_exceeds_max(
    project,
    deployer,
    sealing_committee,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    try:
        project.GateSeal.deploy(
            sealing_committee,
            MAX_SEAL_DURATION_SECONDS + 1,
            sealables,
            expiry_timestamp,
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "seal duration: exceeds max" in str(e)


def test_sealables_exceeds_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    try:
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            [],
            expiry_timestamp,
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "sealables: empty list" in str(e)


def test_expiry_timestamp_cannot_be_now(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    now,
    prolongations,
    prolongation_duration_seconds,
):
    try:
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            now,
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "expiry timestamp: must be in the future" in str(e)


def test_expiry_timestamp_cannot_exceed_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    try:
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp + 1,
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "expiry: exceeds max" in str(e)


@pytest.mark.parametrize("zero_address_index", range(MAX_SEALABLES))
def test_sealables_cannot_include_zero_address(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    zero_address_index,
    generate_sealables,
    prolongations,
    prolongation_duration_seconds,
):
    sealables = generate_sealables(MAX_SEALABLES)
    sealables[zero_address_index] = ZERO_ADDRESS

    try:
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "sealables: includes zero address" in str(e)


def test_sealables_cannot_include_duplicates(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    if len(sealables) == MAX_SEALABLES:
        sealables[-1] = sealables[0]
    else:
        sealables.append(sealables[0])

    try:
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "sealables: includes duplicates" in str(e)


def test_sealables_cannot_exceed_max_length(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    generate_sealables,
    prolongations,
    prolongation_duration_seconds,
):
    sealables = generate_sealables(MAX_SEALABLES + 1)

    try:
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            prolongations,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError:
        pass


def test_deploy_params_must_match(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        prolongations,
        prolongation_duration_seconds,
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
    assert not gate_seal.is_expired(), "should not be expired"


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
        assert event.sealed_by == sealing_committee
        assert event.sealed_for == seal_duration_seconds
        assert event.sealable == sealables[i]
        assert event.sealed_at == expected_timestamp

    assert (
        gate_seal.get_expiry_timestamp() == expected_timestamp
    ), "expiry timestamp matches"

    assert gate_seal.is_expired(), "gate seal must be expired immediately after sealing"

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
        assert event.sealed_by == sealing_committee
        assert event.sealed_for == seal_duration_seconds
        assert event.sealable == sealables_to_seal[i]
        assert event.sealed_at == expected_timestamp

    assert gate_seal.is_expired(), "gate seal must be expired immediately after sealing"

    for sealable in sealables:
        sealable_contract = project.SealableMock.at(sealable)
        if sealable in sealables_to_seal:
            assert sealable_contract.isPaused(), "sealable must be sealed"
        else:
            assert not sealable_contract.isPaused(), "sealable must not be sealed"


def test_seal_as_stranger(gate_seal, stranger, sealables):
    try:
        gate_seal.seal(sealables, sender=stranger)
    except VirtualMachineError as e:
        assert "sender: not SEALING_COMMITTEE" in str(e)


def test_seal_empty_subset(gate_seal, sealing_committee):
    try:
        gate_seal.seal([], sender=sealing_committee)
    except VirtualMachineError as e:
        assert "sealables: empty subset" in str(e)


def test_seal_duplicates(gate_seal, sealables, sealing_committee):
    if len(sealables) == MAX_SEALABLES:
        sealables[-1] = sealables[0]
    else:
        sealables.append(sealables[0])
    try:
        gate_seal.seal(sealables, sender=sealing_committee)
    except VirtualMachineError as e:
        assert "sealables: includes duplicates" in str(e)


def test_seal_nonintersecting_subset(accounts, gate_seal, sealing_committee):
    try:
        gate_seal.seal([accounts[0]], sender=sealing_committee)
    except VirtualMachineError as e:
        assert "sealables: includes a non-sealable" in str(e)


def test_seal_partially_intersecting_subset(
    accounts, gate_seal, sealing_committee, sealables
):
    try:
        gate_seal.seal([sealables[0], accounts[0]], sender=sealing_committee)
    except VirtualMachineError as e:
        assert "sealables: includes a non-sealable" in str(e)


def test_natural_expiry(
    networks,
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    gate_seal = project.GateSeal.deploy(
        sealing_committee,
        seal_duration_seconds,
        sealables,
        expiry_timestamp,
        prolongations,
        prolongation_duration_seconds,
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

    try:
        gate_seal.seal(sealables, sender=sealing_committee)
    except VirtualMachineError as e:
        assert "gate seal: expired" in str(e)


@pytest.mark.parametrize("failing_index", range(MAX_SEALABLES))
def test_single_failed_sealable_error_message(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    failing_index,
    generate_sealables,
    prolongations,
    prolongation_duration_seconds,
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
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )

    try:
        gate_seal.seal(
            sealables,
            sender=sealing_committee,
        )
    except VirtualMachineError as e:
        assert str(failing_index) in str(e)


@pytest.mark.parametrize("repeat", range(10))
def test_several_failed_sealables_error_message(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    generate_sealables,
    prolongations,
    prolongation_duration_seconds,
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
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )

    failed.sort()
    failed.reverse()
    try:
        gate_seal.seal(
            sealables,
            sender=sealing_committee,
        )
    except VirtualMachineError as e:
        assert "".join([str(n) for n in failed]) in str(e)


@pytest.mark.skip("only run this with automining disabled")
def test_cannot_seal_twice_in_one_tx(gate_seal, sealables, sealing_committee):
    gate_seal.seal(sealables, sender=sealing_committee)
    try:
        gate_seal.seal(sealables, sender=sealing_committee)
    except VirtualMachineError as e:
        assert "gate seal: expired" in str(e)


def test_raw_call_success_should_be_false_when_sealable_reverts_on_pause(
    project,
    deployer,
    generate_sealables,
    sealing_committee,
    seal_duration_seconds,
    expiry_timestamp,
    prolongations,
    prolongation_duration_seconds,
):
    """
        `raw_call` without `max_outsize` and with `revert_on_failure=True` for some reason returns the boolean value of memory[0] :^)

        Which is why we specify `max_outsize=32`, even though don't actually use it.

        To test that `success` returns actual value instead of returning bool of memory[0],
        we need to pause the contract before the sealing,
        so that the condition `success and is_paused()` is false (i.e `False and True`), see GateSeal.vy::seal()

    For that, we use `force_pause_for` on SealableMock to ignore any checks and forcefully pause the contract.
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
        prolongations,
        prolongation_duration_seconds,
        sender=deployer,
    )

    # making sure we have the right contract
    assert gate_seal.get_sealables() == sealables

    # forcefully pause the sealable before sealing
    sealables[0].force_pause_for(seal_duration_seconds, sender=deployer)
    assert sealables[0].isPaused(), "should be paused now"

    # seal() should revert because `raw_call` to sealable returns `success=False`, even though isPaused() is True.
    try:
        gate_seal.seal(sealables, sender=sealing_committee)
    except VirtualMachineError as e:
        assert "reverted with reason string '0'" in str(e)


def test_prolong_before_expiry(
    gate_seal,
    sealing_committee,
    prolongation_duration_seconds,
    prolongations,
):
    old_expiry = gate_seal.get_expiry_timestamp()
    gate_seal.prolong(sender=sealing_committee)
    assert (
        gate_seal.get_expiry_timestamp() == old_expiry + prolongation_duration_seconds
    )
    assert gate_seal.get_prolongations_remaining() == prolongations - 1


def test_prolong_after_expiry(
    networks,
    chain,
    gate_seal,
    sealing_committee,
    expiry_timestamp,
):
    networks.active_provider.set_timestamp(expiry_timestamp + 1)
    networks.active_provider.mine()

    try:
        gate_seal.prolong(sender=sealing_committee)
    except VirtualMachineError as e:
        assert "gate seal: expired" in str(e)


def test_prolong_only_committee(gate_seal, stranger):
    try:
        gate_seal.prolong(sender=stranger)
    except VirtualMachineError as e:
        assert "sender: not SEALING_COMMITTEE" in str(e)


def test_cannot_prolong_after_seal(gate_seal, sealing_committee, sealables):
    gate_seal.seal(sealables, sender=sealing_committee)
    try:
        gate_seal.prolong(sender=sealing_committee)
    except VirtualMachineError as e:
        assert "gate seal: expired" in str(e)


def test_prolongations_cannot_exceed_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongation_duration_seconds,
):
    try:
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            MAX_PROLONGATIONS + 1,
            prolongation_duration_seconds,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "prolongations: exceeds max" in str(e)


def test_prolongation_duration_cannot_exceed_max(
    project,
    deployer,
    sealing_committee,
    seal_duration_seconds,
    sealables,
    expiry_timestamp,
    prolongations,
):
    try:
        project.GateSeal.deploy(
            sealing_committee,
            seal_duration_seconds,
            sealables,
            expiry_timestamp,
            prolongations,
            MAX_PROLONGATION_DURATION_SECONDS + 1,
            sender=deployer,
        )
    except VirtualMachineError as e:
        assert "prolongation duration: exceeds max" in str(e)
