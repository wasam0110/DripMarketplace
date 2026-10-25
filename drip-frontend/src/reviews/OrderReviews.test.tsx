import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import type { OrderDetail } from '../orders/api'
import { OrderReviews } from './OrderReviews'

vi.mock('./ProductReviews', () => ({ ReviewForm: ({ productId, orderId }: { productId: string; orderId: string }) => <div data-testid="review-form">{productId}:{orderId}</div> }))
const productId = '11111111-1111-4111-8111-111111111111'
const order = { id: '22222222-2222-4222-8222-222222222222', status: 'completed', items: [
  { id: 'a', product_id: productId, product_name: 'Linen shirt' },
  { id: 'b', product_id: productId, product_name: 'Linen shirt' },
] } as OrderDetail

it('deduplicates variants and passes the authenticated order identifiers', () => {
  render(<OrderReviews order={order} />)
  expect(screen.getAllByRole('button', { name: 'Review Linen shirt' })).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Review Linen shirt' }))
  expect(screen.getByTestId('review-form')).toHaveTextContent(`${productId}:${order.id}`)
  expect(screen.queryByRole('button', { name: 'Review Linen shirt' })).not.toBeInTheDocument()
})

it('does not expose linked review controls for an undelivered order', () => {
  render(<OrderReviews order={{ ...order, status: 'shipped' }} />)
  expect(screen.queryByRole('region')).not.toBeInTheDocument()
})
