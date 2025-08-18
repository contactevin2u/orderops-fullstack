import { useState } from 'react'
import { api } from '../lib/api'

export default function Home() {
  const [text, setText] = useState('')
  const [parsed, setParsed] = useState<any>(null)
  const [creating, setCreating] = useState(false)
  const [resultMsg, setResultMsg] = useState('')

  async function handleParse(createOrder=false) {
    setResultMsg('')
    const data = await api('/parse', { method:'POST', body: JSON.stringify({ text, create_order:createOrder }) })
    setParsed(data.parsed || data)
    if (data.created_order_id) {
      setResultMsg(`Order created: ${data.order_code} (ID ${data.created_order_id})`)
    }
  }

  return (
    <div className="container">
      <h1>Order Intake (WhatsApp → Order)</h1>
      <div className="card">
        <label>Paste WhatsApp message:</label>
        <textarea rows={10} style={{width:'100%'}} value={text} onChange={e=>setText(e.target.value)} />
        <div className="actions">
          <button onClick={()=>handleParse(false)}>Parse Only</button>
          <button onClick={()=>handleParse(true)}>Parse & Create Order</button>
        </div>
        {resultMsg && <p><b>{resultMsg}</b></p>}
      </div>
      {parsed && (
        <div className="card">
          <h3>Parsed Preview</h3>
          <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(parsed, null, 2)}</pre>
        </div>
      )}
      <div className="card">
        <a href="/ops">Go to Operations</a>
      </div>
    </div>
  )
}
