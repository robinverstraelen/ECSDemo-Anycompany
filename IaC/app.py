#!/usr/bin/env python3

from aws_cdk import core
from vars import region, account_id

from ia_c.ia_c_stack import IaCStack


app = core.App()
IaCStack(app, "WebShopDemo", env={'region': region, 'account': account_id})

app.synth()
