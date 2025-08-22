import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect } from "vitest";
import OrderMini from "../OrderMini";
import { Order } from "@/utils/api";

describe("OrderMini", () => {
  it("renders order data", () => {
    const order: Order = {
      id: 1,
      code: "ABC123",
      type: "OUTRIGHT",
      status: "NEW",
      total: 100,
      paid_amount: 50,
      balance: 50,
    };
    const html = renderToStaticMarkup(
      <table><tbody><OrderMini order={order} /></tbody></table>
    );
    expect(html).toContain("ABC123");
    expect(html).toContain("OUTRIGHT");
    expect(html).toContain("NEW");
    expect(html).toContain("RM 100.00");
    expect(html).toContain("RM 50.00");
  });
});
