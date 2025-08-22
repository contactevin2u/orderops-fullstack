import Link from "next/link";
import StatusBadge from "./StatusBadge";
import { Order } from "@/utils/api";

export default function OrderMini({order}:{order:Order}){
  return (
    <tr>
      <td><Link href={`/orders/${order.id}`}>{order.code || order.id}</Link></td>
      <td>{order.type}</td>
      <td><StatusBadge value={order.status} /></td>
      <td style={{textAlign:"right"}}>RM {Number(order.total||0).toFixed(2)}</td>
      <td style={{textAlign:"right"}}>RM {Number(order.paid_amount||0).toFixed(2)}</td>
      <td style={{textAlign:"right"}}>RM {Number(order.balance||0).toFixed(2)}</td>
    </tr>
  );
}
