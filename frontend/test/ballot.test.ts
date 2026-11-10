import { describe, expect, it } from "vitest";
import * as b from "@/lib/ballot";

describe("ballot rules", () => {
  it("points are 3/2/1 with visible labels", () => {
    expect([0, 1, 2].map(b.points)).toEqual([3, 2, 1]);
    expect([0, 1, 2].map(b.pointsLabel)).toEqual(["3 pts", "2 pts", "1 pt"]);
    expect([0, 1, 2].map(b.ordinal)).toEqual(["1.º", "2.º", "3.º"]);
  });

  it("does not allow repeating a candidate and does not move it silently", () => {
    let p = b.setPick(b.emptyPicks(), 0, "A");
    expect(b.disabledReason(p, 1, "A")).toBe("Ya es tu 1.º lugar");
    const after = b.setPick(p, 1, "A");
    expect(after).toEqual(["A", null, null]);
    p = b.setPick(p, 1, "B");
    expect(b.disabledReason(p, 0, "A")).toBeNull(); // own slot is not a conflict
    expect(b.disabledReason(p, 2, "B")).toBe("Ya es tu 2.º lugar");
  });

  it("replacing a slot with a different candidate frees the previous one", () => {
    let p = b.setPick(b.emptyPicks(), 0, "A");
    p = b.setPick(p, 0, "B");
    expect(b.disabledReason(p, 1, "A")).toBeNull();
  });

  it("completeness and first empty slot message", () => {
    let p = b.setPick(b.setPick(b.emptyPicks(), 0, "A"), 2, "C");
    expect(b.isComplete(p)).toBe(false);
    expect(b.firstEmptySlot(p)).toBe(1);
    expect(b.missingMessage(p)).toBe("Falta elegir tu 2.º lugar.");
    p = b.setPick(p, 1, "B");
    expect(b.isComplete(p)).toBe(true);
    expect(b.missingMessage(p)).toBeNull();
    expect(b.toPickIds(p)).toEqual(["A", "B", "C"]);
    expect(() => b.toPickIds(b.emptyPicks())).toThrow();
    expect(b.isComplete(["A", "A", "B"])).toBe(false);
  });

  it("needs at least 3 candidates", () => {
    expect(b.canVoteIn(2)).toBe(false);
    expect(b.canVoteIn(3)).toBe(true);
  });
});
