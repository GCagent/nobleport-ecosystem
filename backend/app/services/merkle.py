"""
Merkle tree construction for ledger anchoring.

Uses deterministic canonical JSON serialization and SHA-256 hashing.
Leaf hashes are sorted before tree construction so the root is
order-independent for the same set of records.
"""

import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    """Deterministic JSON serialization. Sorts keys, strips whitespace."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def hash_record(record: dict) -> str:
    """SHA-256 hash of a canonicalized record."""
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()


def build_merkle_root(hashes: list[str]) -> str:
    """
    Build a Merkle root from a list of leaf hashes.

    - Empty input returns hash of empty bytes.
    - Leaves are sorted for deterministic ordering.
    - Odd layers are padded by duplicating the last element.
    """
    if not hashes:
        return hashlib.sha256(b"").hexdigest()

    layer = sorted(hashes)

    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])

        next_layer = []
        for i in range(0, len(layer), 2):
            combined = (layer[i] + layer[i + 1]).encode("utf-8")
            next_layer.append(hashlib.sha256(combined).hexdigest())

        layer = next_layer

    return layer[0]


def build_merkle_tree(hashes: list[str]) -> dict:
    """
    Build full Merkle tree and return root + all layers.
    Useful for generating inclusion proofs.
    """
    if not hashes:
        empty_root = hashlib.sha256(b"").hexdigest()
        return {"root": empty_root, "layers": [], "leaf_count": 0}

    layers = [sorted(hashes)]

    while len(layers[-1]) > 1:
        current = layers[-1]
        if len(current) % 2 == 1:
            current = current + [current[-1]]

        next_layer = []
        for i in range(0, len(current), 2):
            combined = (current[i] + current[i + 1]).encode("utf-8")
            next_layer.append(hashlib.sha256(combined).hexdigest())

        layers.append(next_layer)

    return {
        "root": layers[-1][0],
        "layers": layers,
        "leaf_count": len(hashes),
    }


def get_inclusion_proof(hashes: list[str], target_hash: str) -> list[dict] | None:
    """
    Generate a Merkle inclusion proof for a specific leaf hash.
    Returns list of {hash, position} pairs, or None if not found.
    """
    tree = build_merkle_tree(hashes)
    if tree["leaf_count"] == 0:
        return None

    sorted_hashes = sorted(hashes)
    if target_hash not in sorted_hashes:
        return None

    idx = sorted_hashes.index(target_hash)
    proof = []

    for layer in tree["layers"][:-1]:
        padded = layer if len(layer) % 2 == 0 else layer + [layer[-1]]

        if idx % 2 == 0:
            sibling_idx = idx + 1
            proof.append({"hash": padded[sibling_idx], "position": "right"})
        else:
            sibling_idx = idx - 1
            proof.append({"hash": padded[sibling_idx], "position": "left"})

        idx = idx // 2

    return proof


def verify_inclusion_proof(leaf_hash: str, proof: list[dict], root: str) -> bool:
    """Verify that a leaf hash is included in the tree with the given root."""
    current = leaf_hash

    for step in proof:
        sibling = step["hash"]
        if step["position"] == "left":
            combined = (sibling + current).encode("utf-8")
        else:
            combined = (current + sibling).encode("utf-8")
        current = hashlib.sha256(combined).hexdigest()

    return current == root
