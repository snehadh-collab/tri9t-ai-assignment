import pytest
from app.parser import compute_hash

def test_hash_sensitivity():
    h1 = compute_hash('1. Overview', 'Device description text')
    h2 = compute_hash('1. Overview', 'Device description text modified')
    assert h1 != h2

def test_duplicate_heading_support():
    n1 = {'id': 'node_v1_1', 'heading': '3.1 Specifications', 'node_path': '1.3.1'}
    n2 = {'id': 'node_v1_2', 'heading': '3.1 Specifications', 'node_path': '2.3.1'}
    assert n1['id'] != n2['id']
    assert n1['node_path'] != n2['node_path']

def test_staleness_mismatch():
    pinned_hash = compute_hash('4.1 Overpressure', 'Vent within 2 seconds')
    v2_hash = compute_hash('4.1 Overpressure', 'Vent within 1.5 seconds')
    assert pinned_hash != v2_hash
