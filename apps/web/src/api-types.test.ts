import { describe, expect, it } from "vitest";
import { JobStateValues, KodeGalatValues, ProcessingStageValues } from "./api-types";

describe("api-types (generated, TK-001)", () => {
  it("covers the job lifecycle states", () => {
    expect(JobStateValues).toContain("queued");
    expect(JobStateValues).toContain("completed");
    expect(JobStateValues).toHaveLength(8);
  });

  it("covers the processing stages", () => {
    expect(ProcessingStageValues).toEqual(["probing", "transcribing", "diarizing", "merging"]);
  });

  it("covers user-facing error codes", () => {
    expect(KodeGalatValues).toContain("QUOTA_EXCEEDED");
    expect(KodeGalatValues).toContain("WORKER_OFFLINE");
  });
});
