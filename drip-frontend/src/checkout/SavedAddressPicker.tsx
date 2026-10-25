import { useId, useState } from 'react'
import { Link } from 'react-router'
import { validateAddresses, type Address } from '../account/contracts'
import { Button, ErrorNotice } from '../components/ui'
import { useOrderRead } from '../orders/api'

export function SavedAddressPicker({ disabled, onUse }: { disabled: boolean; onUse: (address: Pick<Address, 'street' | 'city' | 'province'>) => void }) {
  const resource = useOrderRead('/me/addresses', true, validateAddresses)
  const [selected, setSelected] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState<unknown>(null)
  const fieldId = useId()
  const address = resource.data?.find((item) => item.id === selected)
  function useAddress() {
    if (disabled || !address || resource.loading) return
    const { street, city, province } = address
    if (street.trim().length < 5 || street.length > 500 || [city, province].some((value) => value.trim().length < 2 || value.length > 100)) {
      setError(new Error('This saved address needs correction. Edit it in your account or enter delivery details manually.')); return
    }
    onUse({ street, city, province }); setError(null)
    setNotice('Copied street, city and province. Check the delivery fields below and enter the recipient and mobile number. Checkout edits will not change your saved address.')
  }
  return <div className="auth-form">
    <p>Use a saved address or enter delivery details below. Nothing is selected automatically, including your default.</p>
    {resource.loading && <p role="status">Loading saved addresses…</p>}
    {Boolean(resource.error || error) && <ErrorNotice error={resource.error || error} />}
    {Boolean(resource.error) && <p>You can still enter delivery details manually.</p>}
    {resource.data && (resource.data.length ? <>
      <div className="field"><label htmlFor={fieldId}>Saved delivery address</label><select id={fieldId} value={selected} disabled={disabled} onChange={(event) => { setSelected(event.target.value); setNotice(''); setError(null) }}>
        <option value="">Choose a saved address</option>{resource.data.map((item) => <option key={item.id} value={item.id}>{item.label || 'Delivery address'}{item.is_default ? ' (default)' : ''} — {item.street}, {item.city}, {item.province}</option>)}
      </select></div>
      <Button className="button-secondary" disabled={disabled || !address} onClick={useAddress}>Use selected address</Button>
    </> : <p>No saved addresses. Enter your delivery details below.</p>)}
    <div className="option-row"><Button className="button-secondary" disabled={disabled || resource.loading} onClick={() => { setSelected(''); setError(null); setNotice(''); resource.retry() }}>Refresh saved addresses</Button>
      <Link className="text-link" to="/account/addresses">Manage saved addresses</Link></div>
    <p role="status">{notice}</p>
  </div>
}
