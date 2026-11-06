import { expect, it } from 'vitest'
import { confirmSellerLogo, safeLogoUrl, validateSellerLogo } from './logo'
const profile = { id: '11111111-1111-4111-8111-111111111111', brand_name: 'Fixture Label', logo_url: null }
const url = 'https://images.example.test/brand.webp'
it('accepts a missing saved logo without inventing an image', () => expect(validateSellerLogo(profile)).toEqual(profile))
it('accepts an HTTPS saved logo', () => expect(validateSellerLogo({ ...profile, logo_url: url }).logo_url).toBe(url))
it.each([undefined, null, '', 'javascript:alert(1)', 'data:image/png;base64,AAAA', 'blob:example', 'http://images.example.test/a', 'https://user:pass@example.test/a', '//images.example.test/a'])('rejects unsafe upload URL %#', (value) => expect(() => safeLogoUrl(value)).toThrow())
it.each([null, {}, { ...profile, id: 'not-a-seller' }, { ...profile, brand_name: '' }, { ...profile, logo_url: undefined }])('rejects incomplete profile %#', (value) => expect(() => validateSellerLogo(value as typeof profile)).toThrow())
it('requires read-back identity and URL to match', () => {
  expect(confirmSellerLogo({ ...profile, logo_url: url }, profile.id, url).logo_url).toBe(url)
  expect(() => confirmSellerLogo(profile, profile.id, url)).toThrow()
  expect(() => confirmSellerLogo({ ...profile, logo_url: url }, 'another-seller', url)).toThrow()
})
