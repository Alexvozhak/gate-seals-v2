# GateSeal

GateSeal is a one-time emergency pause mechanism designed for Lido protocol's pausable contracts. It serves as an intermediate solution that allows a multisig committee to pause critical contracts immediately, bypassing the DAO vote process during emergencies.

## Overview

GateSeal acts as a panic button that can pause one or more contracts for a specified duration (6-21 days). This gives the DAO time to analyze the situation, decide on appropriate actions, hold votes, and implement fixes.

### Key Features

- **One-time use**: Each GateSeal can only be used once
- **Initial lifetime**: GateSeals have an initial lifetime (1 month to 1 year)
- **Lifetime extensions**: Can be extended up to 5 times, each extension equals the initial lifetime duration
- **Extension activation window**: Extensions can only be activated within a specified time window (1 week to 1 year) before expiry
- **Multiple targets**: Can pause up to 8 contracts simultaneously
- **Emergency response**: Provides immediate pause capability without waiting for DAO votes

## Architecture

### GateSeal Contract

The main contract that handles the sealing (pausing) logic:

- **Committee-controlled**: Only the designated multisig committee can seal contracts or extend lifetime
- **Time-constrained**: Has an expiry timestamp and controlled extension mechanism
- **Flexible targeting**: Can seal a subset of configured pausable contracts

### GateSealFactory Contract

A factory contract that simplifies GateSeal deployment using EIP-5202 blueprints:

- **Blueprint-based**: Uses pre-deployed blueprint for efficient contract creation
- **Parameter validation**: Validates all parameters before deployment
- **Deterministic addresses**: Uses CREATE2 for predictable contract addresses

## Parameters

### Constructor Parameters

1. **Sealing Committee** (`address`): The multisig address authorized to seal contracts and extend lifetime
2. **Seal Duration** (`uint256`): How long contracts remain paused when sealed (6-21 days)
3. **Sealables** (`address[]`): List of pausable contracts (1-8 contracts)
4. **Initial Lifetime** (`uint256`): Initial validity period of the GateSeal (1 month - 1 year)
5. **Max Extensions** (`uint256`): Maximum number of lifetime extensions allowed (0-5)
6. **Extension Activation Window** (`uint256`): Time before expiry when extensions can be activated (1 week - 1 year)

### Constraints

- **Seal Duration**: 6-21 days (518,400 - 1,814,400 seconds)
- **Initial Lifetime**: 1 month - 1 year (2,592,000 - 31,536,000 seconds)
- **Max Extensions**: 0-5 extensions
- **Extension Activation Window**: 1 week - 1 year, cannot exceed initial lifetime
- **Sealables**: 1-8 contracts, no duplicates, no zero addresses

## Usage

### Deployment

```solidity
// Deploy via factory
address gateSeal = factory.create_gate_seal(
    sealingCommittee,
    7 * 24 * 60 * 60,        // 7 days seal duration
    [contract1, contract2],   // sealable contracts
    90 * 24 * 60 * 60,       // 90 days initial lifetime
    3,                       // 3 extensions allowed
    30 * 24 * 60 * 60        // 30 days activation window
);
```

### Sealing Contracts

```solidity
// Seal all configured contracts
gateSeal.seal([contract1, contract2]);

// Seal subset of contracts
gateSeal.seal([contract1]);
```

### Extending Lifetime

```solidity
// Check if extension is possible
bool canExtend = gateSeal.can_extend_lifetime();

// Extend lifetime (only within activation window)
gateSeal.extendLifetime();
```

### Querying State

```solidity
// Get all seal information
(
    address committee,
    uint256 sealDuration,
    address[] memory sealables,
    uint256 initialLifetime,
    uint256 expiryTimestamp,
    uint256 maxExtensions,
    uint256 extensionsUsed,
    uint256 activationWindow,
    bool isUsed
) = gateSeal.get_seal_info();

// Check expiry status
bool expired = gateSeal.is_expired();
```

## Security Considerations

### Trust Assumptions

- **Multisig Security**: The sealing committee multisig must be properly secured
- **Committee Honesty**: Committee should only use GateSeal in genuine emergencies
- **Contract Permissions**: GateSeal must have pause permissions on target contracts

### Limitations

- **One-time Use**: Cannot be reused after sealing
- **Time Constraints**: Limited by expiry timestamp and extension rules
- **Committee Dependency**: Relies on multisig committee for operation

### Emergency Response

1. **Immediate Action**: Committee can pause contracts instantly during emergencies
2. **DAO Override**: DAO retains ability to resume contracts before seal duration expires
3. **Automatic Expiry**: GateSeal becomes unusable after expiry, forcing renewal process

## Development

### Prerequisites

- Python 3.8+
- [Ape Framework](https://docs.apeworx.io/ape/stable/)
- [Vyper](https://vyper.readthedocs.io/) 0.4.1+

### Installation

```bash
# Install dependencies
ape plugins install vyper hardhat

# Install Python dependencies
pip install -r requirements.txt
```

### Testing

```bash
# Run all tests
ape test

# Run specific test file
ape test tests/test_gate_seal.py

# Run with coverage
ape test --coverage
```

### Compilation

```bash
# Compile contracts
ape compile

# Compile specific contract
vyper contracts/GateSeal.vy
```

## Deployment Networks

GateSeal has been deployed on:

- **Mainnet**: Production deployments for Lido protocol
- **Holesky**: Testnet deployments for testing
- **Goerli**: Legacy testnet (deprecated)

See `deployed/` directory for specific contract addresses.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security

For security concerns, please contact the Lido team through appropriate channels. Do not create public issues for security vulnerabilities.
