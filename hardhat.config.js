
// See https://hardhat.org/config/ for config options.
module.exports = {
  networks: {
    hardhat: {
      hardfork: "cancun",
      // Base fee of 0 allows use of 0 gas price when testing
      initialBaseFeePerGas: 0,
      accounts: {
        mnemonic: "test test test test test test test test test test test junk",
        path: "m/44'/60'/0'/0",
        count: 10,
        accountsBalance: "10000000000000000000000",
      },
      // uncomment for test_cannot_seal_twice_in_one_tx test
      // mining: {
      //   auto: false,
      //   interval: 1000
      // }
    },
  },
};