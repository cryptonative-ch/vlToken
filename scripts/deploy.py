from pathlib import Path
from readline import append_history_file

import os
import click
from ape import accounts, project, chain, networks
from ape.cli import NetworkBoundCommand, network_option, account_option
from eth._utils.address import generate_contract_address
from eth_utils import to_checksum_address, to_canonical_address
from datetime import datetime

ARBITRUM_BASE_TOKEN_ADDRESS = os.getenv('ARBITRUM_BASE_TOKEN_ADDRESS')
ARBITRUM_TREASURY_ADDRESS = os.getenv('ARBITRUM_TREASURY_ADDRESS')
ARBITRUM_COLLECTOR_ADDRESS = os.getenv('ARBITRUM_COLLECTOR_ADDRESS')
# ARBITRUM_DEPLOY_ADDRESS = os.getenv('ARBITRUM_DEPLOY_ADDRESS')
# ARBITRUM_DEPLOY_NAME = os.getenv('ARBITRUM_DEPLOY_NAME')

# account = accounts.load(ARBITRUM_DEPLOY_NAME)

@click.group(short_help="Deploy the project")
def cli():
    pass


@cli.command(cls=NetworkBoundCommand)
#@network_option()
@account_option()
def deploy_vl_token(network, account):
 
    # deploy vlToken    
    #vl_token = project.VoteLockToken.deploy(ARBITRUM_BASE_TOKEN_ADDRESS, ARBITRUM_TREASURY_ADDRESS, ARBITRUM_COLLECTOR_ADDRESS, sender=account, publish=True)

    # vl_token = project.VoteLockToken.deploy(ARBITRUM_BASE_TOKEN_ADDRESS, ARBITRUM_TREASURY_ADDRESS, ARBITRUM_COLLECTOR_ADDRESS, sender=account)

    vl_token = account.deploy(project.VoteLockToken, ARBITRUM_BASE_TOKEN_ADDRESS, ARBITRUM_TREASURY_ADDRESS, ARBITRUM_COLLECTOR_ADDRESS, publish=True)

    print(vl_token.ABI)


@cli.command(cls=NetworkBoundCommand)
#@network_option()
@account_option()
def publish(network, account):
    print(account)
    print(network)


    networks.provider.network.explorer.publish_contract("0x829F71920a42678C3A5d19aF52EeB4A4c181b7Ca")