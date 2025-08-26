import Link from 'next/link';

export default function AdminNav(){
  return (
    <nav style={{display:'flex',gap:8,padding:8,borderBottom:'1px solid #eee',background:'#fff'}}>
      <Link className="btn secondary" href="/admin/routes">Routes</Link>
      <Link className="btn secondary" href="/orders">Orders</Link>
      <Link className="btn" href="/admin/driver-commissions">Driver Commissions</Link>
    </nav>
  );
}
