"""Tests for the Merkle tree service."""

from app.services.merkle import (
    canonical_json,
    hash_record,
    build_merkle_root,
    build_merkle_tree,
    get_inclusion_proof,
    verify_inclusion_proof,
)


def test_canonical_json_sort_keys():
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_hash_record_deterministic():
    record = {"id": "abc", "name": "test", "value": 42}
    h1 = hash_record(record)
    h2 = hash_record(record)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_empty_root():
    root = build_merkle_root([])
    assert len(root) == 64


def test_single_leaf():
    h = hash_record({"id": "1"})
    root = build_merkle_root([h])
    assert root == h


def test_two_leaves():
    h1 = hash_record({"id": "1"})
    h2 = hash_record({"id": "2"})
    root = build_merkle_root([h1, h2])
    assert root != h1
    assert root != h2
    assert len(root) == 64


def test_order_independent():
    h1 = hash_record({"id": "1"})
    h2 = hash_record({"id": "2"})
    root_a = build_merkle_root([h1, h2])
    root_b = build_merkle_root([h2, h1])
    assert root_a == root_b  # sorted internally


def test_merkle_tree_structure():
    hashes = [hash_record({"id": str(i)}) for i in range(4)]
    tree = build_merkle_tree(hashes)
    assert tree["leaf_count"] == 4
    assert len(tree["layers"]) == 3  # 4 -> 2 -> 1
    assert tree["root"] == tree["layers"][-1][0]


def test_inclusion_proof():
    hashes = [hash_record({"id": str(i)}) for i in range(8)]
    target = hashes[3]
    root = build_merkle_root(hashes)

    proof = get_inclusion_proof(hashes, target)
    assert proof is not None
    assert verify_inclusion_proof(target, proof, root)


def test_inclusion_proof_missing():
    hashes = [hash_record({"id": str(i)}) for i in range(4)]
    fake = hash_record({"id": "999"})
    proof = get_inclusion_proof(hashes, fake)
    assert proof is None


def test_proof_fails_with_wrong_root():
    hashes = [hash_record({"id": str(i)}) for i in range(4)]
    target = hashes[0]
    proof = get_inclusion_proof(hashes, target)
    assert proof is not None
    assert not verify_inclusion_proof(target, proof, "0" * 64)
