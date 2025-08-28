import {
  enqueue,
  getPending,
  markCompleted,
} from "./Outbox";

jest.mock("@react-native-async-storage/async-storage", () => {
  const store: Record<string, string> = {};
  return {
    getItem: jest.fn((k: string) => Promise.resolve(store[k] ?? null)),
    setItem: jest.fn((k: string, v: string) => {
      store[k] = v;
      return Promise.resolve();
    }),
    removeItem: jest.fn((k: string) => {
      delete store[k];
      return Promise.resolve();
    }),
  };
});

describe("Outbox", () => {
  it("enqueue and complete", async () => {
    await enqueue({
      type: "UPDATE_STATUS",
      id: "1",
      orderId: "1",
      payload: { status: "DELIVERED" },
      retries: 0,
      ts: 0,
    });
    const pending = await getPending();
    expect(pending).toHaveLength(1);
    await markCompleted("1");
    const after = await getPending();
    expect(after).toHaveLength(0);
  });
});

