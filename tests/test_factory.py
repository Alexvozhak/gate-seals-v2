from ape.exceptions import VirtualMachineError
from utils.blueprint import verify_eip5202_blueprint
from ape.utils import ZERO_ADDRESS


def test_factory_blueprint_cannot_be_zero_address(project, deployer):
    try:
        project.GateSealFactory.deploy(ZERO_ADDRESS, sender=deployer)
        assert False, "Should have reverted"
    except VirtualMachineError as e:
        assert "blueprint: zero address" in str(e)


def test_blueprint_not_callable(project, blueprint_address):
    blueprint = project.GateSeal.at(blueprint_address)
    try:
        blueprint.get_sealing_committee()
        assert False, "did not crash"
    except VirtualMachineError:
        assert True


def test_blueprint_address_matches(blueprint_address, gate_seal_factory):
    assert (
        gate_seal_factory.get_blueprint() == blueprint_address
    ), "blueprint address does not match"


def test_compliance_with_eip_5202(project, blueprint_address):
    blueprint = project.provider.get_code(blueprint_address)
    verify_eip5202_blueprint(blueprint)
