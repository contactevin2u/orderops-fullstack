import Layout from "@/components/Layout";
import Link from "next/link";
import React from "react";
import useSWR from "swr";
import ErrorBoundary from "@/components/ErrorBoundary";
import { listOrders } from "@/utils/api";
import { useTranslation } from "react-i18next";

export default function OrdersPage(){
  const { t } = useTranslation();
  const [q,setQ] = React.useState("");
  const [status,setStatus] = React.useState("");
  const [type,setType] = React.useState("");
  const [params,setParams] = React.useState({ q:"", status:"", type:"" });

  const fetchOrders = React.useCallback(()=>{
    return listOrders(params.q||undefined, params.status||undefined, params.type||undefined, 200);
  },[params]);

  const { data, error, isLoading, mutate } = useSWR(["orders", params], fetchOrders, { revalidateOnMount: false });

  React.useEffect(()=>{ mutate(); }, [params, mutate]);

  React.useEffect(()=>{
    const t = setTimeout(()=>setParams({ q, status, type }),300);
    return ()=>clearTimeout(t);
  },[q,status,type]);

  const items = data?.items || [];

  return (
    <Layout>
      <div className="card">
        <h2 style={{marginTop:0}}>{t('nav.orders')}</h2>
        <details style={{marginBottom:8}}>
          <summary>{t('help.orders.title')}</summary>
          <p>{t('help.orders.body')}</p>
        </details>
        <div className="row">
          <div className="col">
            <label className="sr-only" htmlFor="q">{t('orders.search')}</label>
            <input id="q" className="input" placeholder={t('orders.search')} value={q} onChange={e=>setQ(e.target.value)} />
          </div>
          <div className="col">
            <label className="sr-only" htmlFor="status">{t('orders.status')}</label>
            <select id="status" className="select" value={status} onChange={e=>setStatus(e.target.value)}>
              <option value="">{t('orders.allStatus')}</option>
              <option>NEW</option><option>ACTIVE</option><option>COMPLETED</option><option>RETURNED</option><option>CANCELLED</option>
            </select>
          </div>
          <div className="col">
            <label className="sr-only" htmlFor="type">{t('orders.type')}</label>
            <select id="type" className="select" value={type} onChange={e=>setType(e.target.value)}>
              <option value="">{t('orders.allTypes')}</option>
              <option>OUTRIGHT</option><option>INSTALLMENT</option><option>RENTAL</option>
            </select>
          </div>
          <div className="col" style={{display:'flex',alignItems:'center',gap:8}}>
            <Link className="btn secondary" href="/orders/new">{t('orders.create')}</Link>
          </div>
        </div>
        <p style={{fontSize:'0.875rem'}}>{t('orders.results',{count:items.length})}</p>
        <ErrorBoundary fallback={<div style={{opacity:.7}}>{t('orders.error')}</div>}>
          {error ? <ErrorThrower error={error} /> : <OrdersTable items={items} />}
        </ErrorBoundary>
      </div>
    </Layout>
  );
}

function ErrorThrower({ error }: { error: any }): JSX.Element | null {
  throw error;
  return null;
}

function OrdersTable({ items }: { items: any[] }) {
  return (
    <div style={{overflowX:"auto", marginTop:12}}>
      <table className="table">
        <thead><tr><th>Code</th><th>Type</th><th>Status</th><th>Total</th><th>Paid</th><th>Balance</th></tr></thead>
        <tbody>
          {items.map((o:any)=>(
            <tr key={o.id}>
              <td><Link href={`/orders/${o.id}`}>{o.code||o.id}</Link></td>
              <td>{o.type}</td>
              <td><span className="badge">{o.status}</span></td>
              <td style={{textAlign:"right"}}>RM {Number(o.total||0).toFixed(2)}</td>
              <td style={{textAlign:"right"}}>RM {Number(o.paid_amount||0).toFixed(2)}</td>
              <td style={{textAlign:"right"}}>RM {Number(o.balance||0).toFixed(2)}</td>
            </tr>
          ))}
          {items.length===0 && <tr><td colSpan={6} style={{opacity:.7}}>No orders found</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
