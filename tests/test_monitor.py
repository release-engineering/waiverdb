# SPDX-License-Identifier: GPL-2.0+

import os
import pytest
import requests
import waiverdb.monitor

from six.moves import reload_module


def test_metrics(client):
    r = client.get('/api/v1.0/metrics')

    assert r.status_code == 200
    assert len([line for line in r.get_data(as_text=True).splitlines()
                if line.startswith('# TYPE messaging_')
                and line.endswith(' counter')]) == 4
    assert len([line for line in r.get_data(as_text=True).splitlines()
                if line.startswith('# TYPE db_')
                and line.endswith(' counter')]) == 4


def test_standalone_metrics_server_disabled_by_default():
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get('http://127.0.0.1:10040/metrics')


def test_standalone_metrics_server():
    os.environ['MONITOR_STANDALONE_METRICS_SERVER_ENABLE'] = 'true'
    reload_module(waiverdb.monitor)

    r = requests.get('http://127.0.0.1:10040/metrics')

    assert len([line for line in r.text.splitlines()
                if line.startswith('# TYPE messaging_')
                and line.endswith(' counter')]) == 4
    assert len([line for line in r.text.splitlines()
                if line.startswith('# TYPE db_')
                and line.endswith(' counter')]) == 4
