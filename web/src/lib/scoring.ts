// Scoring: reward learning, not raw usage.
//   points = novelty_bonus × complexity × spacing_multiplier
// - novelty decays ~10 → ~1 over the first ~10 uses (first time you learn a
//   command is worth a lot; the tenth time ~1 point).
// - complexity is the 1-5 AI rating.
// - spacing rewards spaced reuse: using something once a day beats 7× in 10 min.

export function noveltyBonus(priorUses: number): number {
  // priorUses = number of times this command was used BEFORE this one.
  // 0 prior uses → ~10; decays toward 1.
  return 1 + 9 * Math.exp(-priorUses / 4);
}

export function spacingMultiplier(hoursSinceLastUse: number | null): number {
  if (hoursSinceLastUse === null) return 1.0; // first ever use
  return Math.min(1.0, hoursSinceLastUse / 24);
}

export function computePoints(
  complexity: number,
  priorUses: number,
  hoursSinceLastUse: number | null,
): number {
  const pts = noveltyBonus(priorUses) * complexity * spacingMultiplier(hoursSinceLastUse);
  return Math.round(pts * 10) / 10; // one decimal
}
