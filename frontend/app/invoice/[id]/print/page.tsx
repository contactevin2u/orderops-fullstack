import InvoiceFortune500, { InvoiceData } from "@/components/InvoiceFortune500";
import { getOrder } from "@/utils/api";

export const dynamic = "force-dynamic";

function isoDate(d?: string | number | Date) {
  const dt = new Date(d ?? Date.now());
  return isNaN(dt.getTime()) ? new Date().toISOString().slice(0, 10) : dt.toISOString().slice(0, 10);
}

function parseBankLine(bank?: string) {
  if (!bank) return { bankName: "", accountNo: "" };
  const m = bank.match(/^([\w\s\-.&]+?)[:\s-]*([0-9\- ]{6,})/i);
  return m ? { bankName: m[1].trim(), accountNo: m[2].replace(/\s+/g, "") } : { bankName: bank, accountNo: "" };
}

function mapOrderToInvoice(order: any): InvoiceData {
  const profile = order?.company_profile ?? order?.company ?? {};
  const customer = order?.customer ?? order?.bill_to ?? {};
  const itemsSrc = Array.isArray(order?.items) ? order.items : [];

  const taxLabel: string = profile.tax_label || "SST";
  const taxPercent: number = typeof profile.tax_percent === "number" ? profile.tax_percent : 0;

  const items = itemsSrc.map((it: any) => {
    const unitPrice = Number(it?.unit_price ?? it?.price ?? 0);
    const qty = Number(it?.qty ?? it?.quantity ?? 0);
    const discount = Number(it?.discount ?? 0);
    return {
      sku: it?.sku || it?.code || "",
      name: it?.name || it?.title || "",
      note: it?.note || undefined,
      qty,
      unit: (it?.unit as string) || "unit",
      unitPrice,
      discount: discount > 1 ? discount / 100 : discount,
      taxRate: taxPercent ? taxPercent / 100 : 0,
    };
  });

  const shipping = Number(order?.delivery_fee ?? 0);
  const other =
    Number(order?.return_delivery_fee ?? 0) +
    Number(order?.penalty_fee ?? 0) -
    Number(order?.discount ?? 0);
  const rounding = Number(order?.rounding ?? 0);
  const depositPaid = Number(order?.paid_amount ?? order?.deposit_paid ?? 0);

  const { bankName, accountNo } = parseBankLine(profile.bank_account || profile.bank);

  const currency: string = profile.currency || order?.currency || "MYR";

  return {
    brand: {
      logoUrl:
        profile.logo_url ||
        "https://static.wixstatic.com/media/20c5f7_f890d2de838e43ccb1b30e72b247f0b2~mv2.png",
      name: profile.name || "AA ALIVE SDN BHD",
      regNo: profile.reg_no || "MDA-Registered",
      address: profile.address || "",
      phone: profile.phone || "+60 11-2868 6592",
      email: profile.email || "contact@evin2u.com",
      website: profile.website || "https://katil-hospital.my",
      brandColor: profile.brand_color || "#0F766E",
    },
    meta: {
      title: "TAX INVOICE / INVOIS CUKAI",
      number: order?.code || String(order?.id ?? ""),
      issueDate: isoDate(order?.created_at || order?.date || Date.now()),
      dueDate: isoDate(order?.due_date || Date.now()),
      currency,
      taxLabel,
      taxId: profile.tax_id || (taxPercent ? `${taxLabel} ${taxPercent}%` : undefined),
      poNumber: order?.po_number || undefined,
      reference: order?.notes || order?.reference || undefined,
    },
    billTo: {
      label: "Bill To / Dibayar Kepada",
      name: customer?.name || customer?.company || "",
      attn: customer?.attn || undefined,
      address: customer?.address || "",
      email: customer?.email || undefined,
    },
    shipTo: undefined,
    items,
    summary: {
      shipping,
      other,
      rounding,
      depositPaid,
    },
    payment: {
      bankName,
      accountName: profile.account_name || profile.name || "AA ALIVE SDN BHD",
      accountNo,
      swift: profile.swift || undefined,
      note:
        profile.footer_note ||
        "Please pay within 14 days. Late payment may incur charges.",
      qrDataUrl: profile.qr_data_url || undefined, // set in company profile to render your DuitNow QR
    },
    footer: {
      terms: [
        "Goods remain the property of AA ALIVE SDN BHD until full payment is received.",
        "Warranty: 12 months against manufacturing defects unless stated otherwise.",
        "Return policy per contract. / Polisi pemulangan mengikut kontrak.",
      ],
      note: "Thank you for your business! / Terima kasih atas sokongan anda!",
    },
  };
}

export default async function Page({ params }: { params: { id: string } }) {
  try {
    const order = await getOrder(params.id);
    const invoice = mapOrderToInvoice(order);
    return <InvoiceFortune500 invoice={invoice} />;
  } catch (err) {
    console.error("Failed to load invoice", err);
    return <div>Failed to load invoice.</div>;
  }
}

