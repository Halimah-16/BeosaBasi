import { describe, expect, it } from "vitest";
import { healthLabel } from "./health";

describe("healthLabel", () => {
  it("returns ok", () => {
    expect(healthLabel()).toBe("ok");
  });
});
