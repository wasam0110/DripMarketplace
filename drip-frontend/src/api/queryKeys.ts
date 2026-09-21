export const qk = {
  products: {
    all:     ()           => ['products'] as const,
    list:    (f: object)  => ['products', 'list', f] as const,
    detail:  (id: string) => ['products', 'detail', id] as const,
    reviews: (id: string) => ['products', id, 'reviews'] as const,
  },
  cart:   { all: () => ['cart'] as const },
  orders: {
    list:   (f: object)  => ['orders', f] as const,
    detail: (id: string) => ['orders', id] as const,
  },
  seller: {
    profile:   ()            => ['seller', 'profile'] as const,
    dashboard: (p: string)   => ['seller', 'dashboard', p] as const,
    orders:    (f: object)   => ['seller', 'orders', f] as const,
    inventory: (f: object)   => ['seller', 'inventory', f] as const,
    wallet:    ()            => ['seller', 'wallet'] as const,
    products:  (f: object)   => ['seller', 'products', f] as const,
  },
  admin: {
    dashboard: (p: string)  => ['admin', 'dashboard', p] as const,
    sellers:   (f: object)  => ['admin', 'sellers', f] as const,
    cod:       ()           => ['admin', 'cod-queue'] as const,
    orders:    (f: object)  => ['admin', 'orders', f] as const,
    payouts:   (f: object)  => ['admin', 'payouts', f] as const,
  },
  customer: {
    profile:   ()           => ['customer', 'profile'] as const,
    addresses: ()           => ['customer', 'addresses'] as const,
    wishlist:  ()           => ['customer', 'wishlist'] as const,
    reviews:   ()           => ['customer', 'reviews'] as const,
  },
} as const
