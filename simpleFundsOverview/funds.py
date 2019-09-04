#!/usr/bin/env python3
""" This plugin gives you a nicer overview of the funds that you own.

Instead of calling listfunds and adding all outputs and channels
this plugin does that for you.

Activate the plugin with: 
`lightningd --plugin=PATH/TO/LIGHTNING/contrib/plugins/funds/funds.py`

Call the plugin with: 
`lightning-cli funds`

The standard unit to depict the funds is set to satoshis. 
The unit can be changed by and arguments after `lightning-cli funds` 
for each call. It is also possible to change the standard unit when 
starting lightningd just pass `--funds_display_unit={unit}` where
unit can be s for satoshi, b for bits, m for milliBitcoin and B for BTC.


Author: Rene Pickhardt (https://ln.rene-pickhardt.de)
Contributor: Vincent Palazzo https://github.com/vincenzopalazzo

Development of the plugin was sponsored by fulmo.org
You can also support future work at https://tallyco.in/s/lnbook/
"""

import json
import requests

from lightning.lightning import LightningRpc
from lightning.plugin import Plugin
from os.path import join

rpc_interface = None
plugin = Plugin(autopatch=True)

callApi = "https://api.bitaps.com/market/v1/ticker/"

unit_aliases = {
    "bitcoin": "BTC",
    "btc": "BTC",
    "satoshi": "sat",
    "satoshis": "sat",
    "bit": "bit",
    "bits": "bit",
    "milli": "mBTC",
    "mbtc": "mBTC",
    "millibtc": "mBTC",
    "B": "BTC",
    "s": "sat",
    "m": "mBTC",
    "b": "bit",
}

unit_divisor = {
    "sat": 1,
    "bit": 100,
    "mBTC": 100 * 1000,
    "BTC": 100 * 1000 * 1000,
}

unit_value = {
    "B": "BTC",
    "btc": "BTC",
    "bitcoin": "BTC",

    "m": "mBTC",
    "milli": "mBTC",

    "b": "bit",
    "bit": "bit",
    "bits": "bit",

    "s": "sat",
    "satoshi": "sat",
    "satoshis": "sat",
}

trading_value = {
    "EUR": "btceur",
    "eur": "btceur",

    "USD": "btcusd",
    "usd": "btcusd",
}


@plugin.method("funds")
def funds(unit="s", trading="usd", plugin=None):
    """Lists the total funds the lightning node owns off- and onchain in {unit}.

    {unit} can take the following values:
    s, satoshi, satoshis to depict satoshis
    b, bit, bits to depict bits
    m, milli, btc to depict milliBitcoin
    B, bitcoin, btc to depict Bitcoins

    When not using Satoshis (default) the comma values are rounded off.

    {trading}
    EUR, eur = btc to euro value
    USD, usd = btc to usd value
    """
    plugin.log("call with unit: {}".format(unit), level="debug")
    if unit is None:
        unit = plugin.get_option("funds_display_unit")

    if unit != "B":
        unit = unit_aliases.get(unit.lower(), "sat")
    else:
        unit = unit_value.get(unit)
        plugin.log(unit)

    if trading is None:
        trading = trading_value.get("USD")
    else:
        trading = trading_value.get(trading)

    div = unit_divisor.get(unit)

    funds = rpc_interface.listfunds()

    onchain_value = sum([int(x["value"]) for x in funds["outputs"]])
    offchain_value = sum([int(x["channel_sat"]) for x in funds["channels"]])

    total_funds = onchain_value + offchain_value

    type_network = rpc_interface.getinfo()
    network = type_network['network']
    url = callApi + trading
    response = requests.get(url)
    print_trading = True
    if response.status_code is not 200:
        print_trading = False

    result_total = format(total_funds / div, '.8f')
    result_on_chain = format(onchain_value / div, '.8f')
    result_off_chain = format(offchain_value / div, '.8f')

    if print_trading is True:
        content = response.json()
        value = 0
        if content is not None:
            data = content['data']
            value = data['last']
        else:
            raise Exception("The http response non contains the json object")
        result_trading_on_chain = format(value * (onchain_value / unit_divisor.get('BTC')), '.8f')
        result_trading_off_chain = format(value * (offchain_value / unit_divisor.get('BTC')), '.8f')
        result_trading_total = format(value * (total_funds / unit_divisor.get('BTC')), '.8f')

        if trading == trading_value.get("usd"):
            trading = "USD"
        else:
            trading = "EUR"

        informations = ""
        if network.lower() == "testnet":
            informations = "The network is " + network + ", so the " + trading + " not are real :("
        else:
            informations = "The network is " + network + ", so the " + trading + " are real :D"

        return {
            'total ' + unit: result_total + ' ' + unit,
            'total ' + trading: result_trading_total + ' ' + trading,
            'onchain ' + unit: result_on_chain + ' ' + unit,
            'onchain ' + trading: result_trading_on_chain + ' ' + trading,
            'offchain' + unit: result_off_chain + ' ' + unit,
            'offchain ' + trading: result_trading_off_chain + ' ' + trading,
            'informations': informations,
        }
    else:
        return {
            'total ' + unit: result_total + ' ' + unit,
            'onchain ' + unit: result_on_chain + ' ' + unit,
            'offchain' + unit: result_off_chain + ' ' + unit,
        }


@plugin.init()
def init(options, configuration, plugin):
    global rpc_interface
    plugin.log("start initialization of the funds plugin", level="debug")
    basedir = configuration['lightning-dir']
    rpc_filename = configuration['rpc-file']
    path = join(basedir, rpc_filename)
    plugin.log("rpc interface located at {}".format(path))
    rpc_interface = LightningRpc(path)
    plugin.log("Funds Plugin successfully initialized")
    plugin.log("standard unit is set to {}".format(
        plugin.get_option("funds_display_unit")), level="debug")


# set the standard display unit to satoshis
plugin.add_option('funds_display_unit', 's',
                  'pass the unit which should be used by default for the simple funds overview plugin')
plugin.run()
