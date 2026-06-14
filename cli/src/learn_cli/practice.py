"""Matching logic for `learn practice` (Model B, guided fill-in).

The target command is split into classified tokens (program / subcommand / flag
/ operand). As the user types, we compute which target slots are satisfied:

  - program, subcommand: exact, positional
  - flag: present by NAME, any order (value after `=` is free)
  - operand (arg value): any non-empty value, matched by position/count

This mirrors the signature philosophy — structure and flags are what's learned;
specific argument values don't matter.
"""

from __future__ import annotations

from .signature import FLAG, OPERAND, PROGRAM, SUBCOMMAND, classify_tokens


def _flag_name(tok: str) -> str:
    return tok.split("=", 1)[0]


def compute_filled(target: list[tuple[str, str]], user_input: str) -> list[bool]:
    """Return a per-target-slot list of whether the user has satisfied it."""
    user = classify_tokens(user_input)
    user_prog = next((t for t, k in user if k == PROGRAM), None)
    user_subs = [t for t, k in user if k == SUBCOMMAND]
    user_flags = {_flag_name(t) for t, k in user if k == FLAG}
    user_operands = sum(1 for _, k in user if k == OPERAND)

    filled: list[bool] = []
    sub_idx = 0
    operand_idx = 0
    for tok, kind in target:
        if kind == PROGRAM:
            filled.append(user_prog == tok)
        elif kind == SUBCOMMAND:
            filled.append(sub_idx < len(user_subs) and user_subs[sub_idx] == tok)
            sub_idx += 1
        elif kind == FLAG:
            filled.append(_flag_name(tok) in user_flags)
        else:  # OPERAND
            operand_idx += 1
            filled.append(user_operands >= operand_idx)
    return filled


def is_complete(target: list[tuple[str, str]], user_input: str) -> bool:
    filled = compute_filled(target, user_input)
    return bool(filled) and all(filled)
