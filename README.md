## Intro

This contracts are based on https://github.com/yearn/veYFI. The unnecessary contracts are removed. 

Changes:

* Exit fee, as Token, is collected into treasury (treasury should be an multisig, but can be an singel address)
* 1 TOKEN locked for 1 year is 1 vlTOKEN (No 4 years locking)
* 1% fee, in vlTOKEN, is taken by the author on every lock
* The author fee can be deactivated, then is redirected to the multisig as vlTOKEN

**🚩These changes are not audited,  this is my second or third smart contract I ever worked on and some test fail too!🚩**

## vlTOKEN

vlTOKEN (vote lock Token), is locking token similar to the ve-style program of Curve

### Max lock

TOKEN can be locked up to 1 years into vlTOKEN, which is non-transferable. They are at least locked for a week.

### vlTOKEN balance

The duration of the lock gives the amount of vlTOKEN relative to the amount locked, locking for one year gives you a vlTOKEN balance equal to the amount of TOKEN locked. Locking for 6 months gives you a vlTOKEN balance of 50% of the TOKEN locked.

The balance decay overtime and can be pushed back to max value by increasing the lock back to the max lock duration.


### vlTOKEN early exit fee

It’s possible to exit the lock early, in exchange for paying a penalty that gets distributed to the treasruy. The penalty is sent to the treasruy which sould be a multisig. (treasruy address is set on deploy, and can't be changed)

The penalty for exiting early is the following: 
```
    min(75%, lock_duration_left / 1 year * 100%)
```
So at most you are paying a 75% penalty that starts decreasing when your lock duration goes below 9 months.

Some example exit fee calculation:

https://docs.google.com/spreadsheets/d/16ckI2Z388GQUFH9RgaAhp9ia1j99RewKTzu_KwlN9V0/edit#gid=0

## vlTOKEN governance (suggestion)


### vlTOKEN Treasury

This is an suggestion and has to be socialy enforced, it's not in the contracts!

Panalty from exit is collected in the treasury multisig. 

Treasury is spent on members proposal. Multisig is executing body.

* sSet multisig treasury address in the vlTOKEN contract where the penalty is collected (at deploy)
* Quorum is 20% at the start, can be changed by vote
* Voting is on snapshot with vlTOKEN, but at some point should be fully on-chain. (Work to be done)

### members

* members need at least 1000 vlTOKEN to get access to the member area.


### Voting for the multisig

* A 3/5 multisig is used
* Candidates have to be members
* Candidates for the multisig have to send 1000 TOKEN to the treasury
* The 15 candidates with the most votes are eligible
* Out of the 15 candidates 5 are randomly drawn for the multisig

### Replacment on multisig

 * The 3/5 multisig is public voted at least yearly or if the majority of vlTOKEN holders ask for.
 * If one member wants to leave the multisig, an replacement vote is held
 * 3 candidates with the most votes are eligible
 * 1 candidate is randomly drawn


## Setup

Install ape framework. See [ape quickstart guide](https://docs.apeworx.io/ape/stable/userguides/quickstart.html)

Install dependencies
```bash
npm install
```

Install [Foundry](https://github.com/foundry-rs/foundry) for running tests
```bash
curl -L https://foundry.paradigm.xyz | bash
```

```bash
foundryup
```

## Compile

Install ape plugins
```bash
ape plugins install .
```

```bash
ape compile
```

## Test

```bash
ape test
```
