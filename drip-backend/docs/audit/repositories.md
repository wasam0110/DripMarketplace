# Backend source index: repositories

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## app/repositories/base.py

241 lines; SHA-256 `84bda1c2282a579bee5ed8d96d61ad716dafbd467fb7bc1d3678125ba73dbce1`. [Open source](../../app/repositories/base.py).

Backend imports: `app.core.exceptions`, `app.models.base`.

- Class `BaseRepository`, lines 27-241; bases: Generic[ModelT].
  Annotated fields: `model`.
- `BaseRepository.create` (async), lines 42-52: Create and flush a new record. Does NOT commit — caller controls tx.
  Calls: `cls.model`, `db.add`, `db.flush`, `db.refresh`.
  Mutation/I-O-related call names: `db.flush`.
- `BaseRepository.get_by_id` (async), lines 57-68: Fetch a single record by primary key. Returns None if not found.
  Calls: `cls.model.deleted_at.is_`, `db.execute`, `issubclass`, `result.scalar_one_or_none`, `select`, `select(cls.model).where`, `stmt.where`.
  Mutation/I-O-related call names: `cls.model.deleted_at.is_`.
- `BaseRepository.get_by_id_or_raise` (async), lines 71-82: Fetch by ID or raise NotFoundError.
  Calls: `NotFoundError`, `cls.get_by_id`, `str`.
- `BaseRepository.get_by_field` (async), lines 85-100: Fetch by any column field name. Returns None if not found.
  Calls: `AttributeError`, `cls.model.deleted_at.is_`, `db.execute`, `getattr`, `issubclass`, `result.scalar_one_or_none`, `select`, `select(cls.model).where`, `stmt.where`.
  Mutation/I-O-related call names: `cls.model.deleted_at.is_`.
- `BaseRepository.get_for_update` (async), lines 103-121: Fetch with SELECT FOR UPDATE (row-level lock).
  Calls: `cls.model.deleted_at.is_`, `db.execute`, `issubclass`, `result.scalar_one_or_none`, `select`, `select(cls.model).where`, `select(cls.model).where(cls.model.id == record_id).with_for_update`, `stmt.where`.
  Mutation/I-O-related call names: `cls.model.deleted_at.is_`.
- `BaseRepository.list_all` (async), lines 126-141: Return a page of records ordered by created_at DESC.
  Calls: `cls.model.created_at.desc`, `cls.model.deleted_at.is_`, `db.execute`, `hasattr`, `issubclass`, `list`, `result.scalars`, `result.scalars().all`, `select`, `stmt.limit`, `stmt.limit(limit).offset`, `stmt.order_by` ... (13 distinct call expressions).
  Mutation/I-O-related call names: `cls.model.deleted_at.is_`.
- `BaseRepository.count` (async), lines 144-154: Count all records (optionally including soft-deleted).
  Calls: `cls.model.deleted_at.is_`, `db.execute`, `func.count`, `issubclass`, `result.scalar_one`, `select`, `select(func.count()).select_from`, `stmt.where`.
  Mutation/I-O-related call names: `cls.model.deleted_at.is_`.
- `BaseRepository.update` (async), lines 159-172: Update fields on an existing instance. Flushes but does not commit.
  Calls: `AttributeError`, `db.flush`, `db.refresh`, `hasattr`, `kwargs.items`, `setattr`.
  Mutation/I-O-related call names: `db.flush`.
- `BaseRepository.bulk_update` (async), lines 175-193: Bulk-update records matching filters.
  Calls: `cls.model.deleted_at.is_`, `db.execute`, `db.flush`, `filters.items`, `getattr`, `issubclass`, `stmt.values`, `stmt.where`, `update`.
  Mutation/I-O-related call names: `cls.model.deleted_at.is_`, `db.flush`.
- `BaseRepository.soft_delete` (async), lines 198-211: Mark a record as deleted without removing it from the database.
  Calls: `TypeError`, `db.flush`, `instance.soft_delete`, `isinstance`.
  Mutation/I-O-related call names: `db.flush`, `instance.soft_delete`.
- `BaseRepository.restore` (async), lines 214-224: Restore a soft-deleted record.
  Calls: `TypeError`, `db.flush`, `instance.restore`, `isinstance`.
  Mutation/I-O-related call names: `db.flush`.
- `BaseRepository.exists` (async), lines 229-241: Check if a record exists matching the given field=value pairs.
  Calls: `cls.model.deleted_at.is_`, `db.execute`, `filters.items`, `func.count`, `getattr`, `issubclass`, `result.scalar_one`, `select`, `select(func.count()).select_from`, `stmt.where`.
  Mutation/I-O-related call names: `cls.model.deleted_at.is_`.

## app/repositories/inventory_repo.py

82 lines; SHA-256 `83e9c95e265b2407975e50f2a8bce1b44b5a2dd85bb383237ffa4c97d4c3fbd3`. [Open source](../../app/repositories/inventory_repo.py).

Backend imports: `app.core.exceptions`, `app.models.product`.

- Class `InventoryRepository`, lines 14-82; bases: .
- `InventoryRepository.__init__` (sync), lines 15-16: No function docstring; consult the source body and layer walkthrough.
- `InventoryRepository.create` (async), lines 18-22: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductInventory`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `InventoryRepository.get_by_variant` (async), lines 24-28: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(ProductInventory).where`, `self.db.execute`.
- `InventoryRepository.update_stock` (async), lines 30-35: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(ProductInventory).where`, `update(ProductInventory).where(ProductInventory.variant_id == variant_id).values`.
- `InventoryRepository.reserve` (async), lines 37-54: Atomically reserve stock. Returns False if insufficient stock.
  Calls: `datetime.utcnow`, `result.scalar_one_or_none`, `self.db.execute`, `update`, `update(ProductInventory).where`, `update(ProductInventory).where(ProductInventory.variant_id == variant_id, ProductInventory.stock - ProductInventory.reserved >= quantity).values`, `update(ProductInventory).where(ProductInventory.variant_id == variant_id, ProductInventory.stock - ProductInventory.reserved >= quantity).values(reserved=ProductInventory.reserved + quantity, updated_at=datetime.utcnow()).returning`.
- `InventoryRepository.release` (async), lines 56-68: Release reserved stock back (order cancelled).
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(ProductInventory).where`, `update(ProductInventory).where(ProductInventory.variant_id == variant_id, ProductInventory.reserved >= quantity).values`.
- `InventoryRepository.deduct` (async), lines 70-82: Deduct reserved → confirmed sale (order delivered).
  Calls: `BusinessRuleError`, `datetime.utcnow`, `self.db.execute`, `update`, `update(ProductInventory).where`, `update(ProductInventory).where(ProductInventory.variant_id == variant_id, ProductInventory.reserved >= quantity, ProductInventory.stock >= quantity).values`.

## app/repositories/notification_repo.py

119 lines; SHA-256 `24689dc583f34766941cd7b7767ba2faa7d7a7d6c88b6cc5e3d8c92e19ef4d35`. [Open source](../../app/repositories/notification_repo.py).

Backend imports: `app.models.notification`.

- Class `NotificationRepository`, lines 13-88; bases: .
- `NotificationRepository.__init__` (sync), lines 14-15: No function docstring; consult the source body and layer walkthrough.
- `NotificationRepository.create` (async), lines 17-21: No function docstring; consult the source body and layer walkthrough.
  Calls: `Notification`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `NotificationRepository.list_by_user` (async), lines 23-41: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `Notification.is_archived.is_`, `Notification.is_read.is_`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(Notification.created_at)).offset`, `q.order_by(desc(Notification.created_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars`, `result.scalars().all` ... (16 distinct call expressions).
- `NotificationRepository.unread_count` (async), lines 43-51: No function docstring; consult the source body and layer walkthrough.
  Calls: `Notification.is_archived.is_`, `Notification.is_read.is_`, `func.count`, `result.scalar_one`, `select`, `select(func.count(Notification.id)).where`, `self.db.execute`.
- `NotificationRepository.mark_read` (async), lines 53-60: No function docstring; consult the source body and layer walkthrough.
  Calls: `func.coalesce`, `func.now`, `result.scalar_one_or_none`, `self.db.execute`, `update`, `update(Notification).where`, `update(Notification).where(Notification.id == notification_id, Notification.user_id == user_id).values`, `update(Notification).where(Notification.id == notification_id, Notification.user_id == user_id).values(is_read=True, read_at=func.coalesce(Notification.read_at, func.now())).returning`.
- `NotificationRepository.mark_all_read` (async), lines 62-69: No function docstring; consult the source body and layer walkthrough.
  Calls: `Notification.is_read.is_`, `func.coalesce`, `func.now`, `len`, `result.scalars`, `result.scalars().all`, `self.db.execute`, `update`, `update(Notification).where`, `update(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False)).values`, `update(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False)).values(is_read=True, read_at=func.coalesce(Notification.read_at, func.now())).returning`.
- `NotificationRepository.get_preferences` (async), lines 71-75: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(NotificationPreference).where`, `self.db.execute`.
- `NotificationRepository.upsert_preferences` (async), lines 77-88: No function docstring; consult the source body and layer walkthrough.
  Calls: `NotificationPreference`, `datetime.utcnow`, `kwargs.items`, `self.db.add`, `self.db.flush`, `self.get_preferences`, `setattr`.
  Mutation/I-O-related call names: `self.db.flush`.
- Class `EmailLogRepository`, lines 91-119; bases: .
- `EmailLogRepository.__init__` (sync), lines 92-93: No function docstring; consult the source body and layer walkthrough.
- `EmailLogRepository.create` (async), lines 95-99: No function docstring; consult the source body and layer walkthrough.
  Calls: `EmailLog`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `EmailLogRepository.list_admin` (async), lines 101-119: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `EmailLog.recipient_email.ilike`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(EmailLog.sent_at)).offset`, `q.order_by(desc(EmailLog.sent_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars`, `result.scalars().all`, `select` ... (14 distinct call expressions).

## app/repositories/order_repo.py

213 lines; SHA-256 `1f58293635a33348569eb5e563074ed0b0deecf283b5b7236f55ddb0952a2eb8`. [Open source](../../app/repositories/order_repo.py).

Backend imports: `app.models.order`.

- Class `OrderRepository`, lines 18-135; bases: .
- `OrderRepository.__init__` (sync), lines 19-20: No function docstring; consult the source body and layer walkthrough.
- `OrderRepository.create` (async), lines 22-27: No function docstring; consult the source body and layer walkthrough.
  Calls: `Order`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `OrderRepository.create_address` (async), lines 29-33: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderAddress`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `OrderRepository.create_item` (async), lines 35-39: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderItem`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `OrderRepository.add_status_history` (async), lines 41-58: No function docstring; consult the source body and layer walkthrough.
  Calls: `OrderStatusHistory`, `self.db.add`.
- `OrderRepository.get_by_id` (async), lines 60-75: No function docstring; consult the source body and layer walkthrough.
  Calls: `q.where`, `q.with_for_update`, `result.scalar_one_or_none`, `select`, `select(Order).options`, `select(Order).options(selectinload(Order.address), selectinload(Order.items), selectinload(Order.seller_orders).selectinload(SellerOrder.seller)).where`, `selectinload`, `selectinload(Order.seller_orders).selectinload`, `self.db.execute`.
- `OrderRepository.get_by_number` (async), lines 77-87: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(Order).options`, `select(Order).options(selectinload(Order.address), selectinload(Order.items), selectinload(Order.seller_orders).selectinload(SellerOrder.seller)).where`, `selectinload`, `selectinload(Order.seller_orders).selectinload`, `self.db.execute`.
- `OrderRepository.get_customer_orders` (async), lines 89-104: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `desc`, `func.count`, `result.scalars`, `result.scalars().all`, `select`, `select(Order).options`, `select(Order).options(selectinload(Order.items)).where`, `select(Order).options(selectinload(Order.items)).where(Order.user_id == user_id).order_by`, `select(Order).options(selectinload(Order.items)).where(Order.user_id == user_id).order_by(desc(Order.created_at)).offset`, `select(Order).options(selectinload(Order.items)).where(Order.user_id == user_id).order_by(desc(Order.created_at)).offset((page - 1) * per_page).limit`, `select(func.count(Order.id)).where` ... (14 distinct call expressions).
- `OrderRepository.update_status` (async), lines 106-129: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `old_order.scalar_one_or_none`, `select`, `select(Order.status).where`, `self.add_status_history`, `self.db.execute`, `update`, `update(Order).where`, `update(Order).where(Order.id == order_id).values`.
- `OrderRepository.number_exists` (async), lines 131-135: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(Order.id).where`, `self.db.execute`.
- Class `SellerOrderRepository`, lines 138-213; bases: .
- `SellerOrderRepository.__init__` (sync), lines 139-140: No function docstring; consult the source body and layer walkthrough.
- `SellerOrderRepository.create` (async), lines 142-147: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerOrder`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `SellerOrderRepository.get_by_id` (async), lines 149-164: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(SellerOrder).options`, `select(SellerOrder).options(selectinload(SellerOrder.order).selectinload(Order.address), selectinload(SellerOrder.order).selectinload(Order.items), selectinload(SellerOrder.seller)).where`, `selectinload`, `selectinload(SellerOrder.order).selectinload`, `self.db.execute`.
- `SellerOrderRepository.get_by_seller` (async), lines 166-190: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `SellerOrderStatus`, `desc`, `func.count`, `q.options`, `q.options(selectinload(SellerOrder.order).selectinload(Order.items), selectinload(SellerOrder.order).selectinload(Order.address)).order_by`, `q.options(selectinload(SellerOrder.order).selectinload(Order.items), selectinload(SellerOrder.order).selectinload(Order.address)).order_by(desc(SellerOrder.created_at)).offset`, `q.options(selectinload(SellerOrder.order).selectinload(Order.items), selectinload(SellerOrder.order).selectinload(Order.address)).order_by(desc(SellerOrder.created_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars`, `result.scalars().all` ... (18 distinct call expressions).
- `SellerOrderRepository.update_status` (async), lines 192-213: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(SellerOrder).where`, `update(SellerOrder).where(SellerOrder.id == seller_order_id).values`.

## app/repositories/payment_repo.py

165 lines; SHA-256 `1d6b18e92f12a8731a2b25ab9bf52272869a59db940809f6f197ef2c8ee5ddce`. [Open source](../../app/repositories/payment_repo.py).

Backend imports: `app.models.payment`.

- Class `PaymentRepository`, lines 15-165; bases: .
- `PaymentRepository.__init__` (sync), lines 16-17: No function docstring; consult the source body and layer walkthrough.
- `PaymentRepository.create` (async), lines 19-24: No function docstring; consult the source body and layer walkthrough.
  Calls: `Payment`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `PaymentRepository.get_by_id` (async), lines 26-32: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(Payment).options`, `select(Payment).options(selectinload(Payment.refunds)).where`, `selectinload`, `self.db.execute`.
- `PaymentRepository.get_by_order_id` (async), lines 34-38: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(Payment).where`, `self.db.execute`.
- `PaymentRepository.get_by_gateway_reference` (async), lines 40-44: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(Payment).where`, `self.db.execute`.
- `PaymentRepository.update_status` (async), lines 46-67: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.db.execute`, `update`, `update(Payment).where`, `update(Payment).where(Payment.id == payment_id).values`.
- `PaymentRepository.log_callback` (async), lines 69-84: No function docstring; consult the source body and layer walkthrough.
  Calls: `PaymentCallback`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `PaymentRepository.create_refund` (async), lines 86-91: No function docstring; consult the source body and layer walkthrough.
  Calls: `Refund`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `PaymentRepository.get_total_refunded` (async), lines 93-98: No function docstring; consult the source body and layer walkthrough.
  Calls: `func.coalesce`, `func.sum`, `result.scalar_one`, `select`, `select(func.coalesce(func.sum(Refund.amount), 0)).where`, `self.db.execute`.
- `PaymentRepository.list_refunds_admin` (async), lines 100-126: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(select(func.count()).select_from(query.subquery()))).scalar_one`, `Refund.processed_at.is_`, `Refund.processed_at.is_not`, `desc`, `func.count`, `query.order_by`, `query.order_by(desc(Refund.created_at), desc(Refund.id)).offset`, `query.order_by(desc(Refund.created_at), desc(Refund.id)).offset((page - 1) * per_page).limit`, `query.subquery`, `query.where`, `result.scalars`, `result.scalars().all` ... (18 distinct call expressions).
- `PaymentRepository.get_refund_admin` (async), lines 128-137: No function docstring; consult the source body and layer walkthrough.
  Calls: `select`, `select(Refund).options`, `select(Refund).options(selectinload(Refund.payment).selectinload(Payment.order), selectinload(Refund.payment).selectinload(Payment.refunds)).where`, `select(Refund).options(selectinload(Refund.payment).selectinload(Payment.order), selectinload(Refund.payment).selectinload(Payment.refunds)).where(Refund.id == refund_id).execution_options`, `selectinload`, `selectinload(Refund.payment).selectinload`, `self.db.scalar`.
- `PaymentRepository.get_payment_refunds` (async), lines 139-145: No function docstring; consult the source body and layer walkthrough.
  Calls: `select`, `select(Payment).options`, `select(Payment).options(selectinload(Payment.order), selectinload(Payment.refunds)).where`, `select(Payment).options(selectinload(Payment.order), selectinload(Payment.refunds)).where(Payment.id == payment_id).execution_options`, `selectinload`, `self.db.scalar`.
- `PaymentRepository.list_admin` (async), lines 147-165: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `PaymentStatus`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(Payment.created_at)).offset`, `q.order_by(desc(Payment.created_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars`, `result.scalars().all`, `select` ... (16 distinct call expressions).

## app/repositories/product_repo.py

329 lines; SHA-256 `97f91a7cca5c75d5cbfad0aac327e3c8a7bfec84ddf7bcba0f6b3095d55e3365`. [Open source](../../app/repositories/product_repo.py).

Backend imports: `app.core.exceptions`, `app.models.product`, `app.models.seller`.

- Class `ProductRepository`, lines 21-303; bases: .
- `ProductRepository.__init__` (sync), lines 22-23: No function docstring; consult the source body and layer walkthrough.
- `ProductRepository.create` (async), lines 27-32: No function docstring; consult the source body and layer walkthrough.
  Calls: `Product`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `ProductRepository.add_image` (async), lines 34-39: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductImage`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `ProductRepository.get_by_id` (async), lines 43-63: No function docstring; consult the source body and layer walkthrough.
  Calls: `Product.deleted_at.is_`, `q.execution_options`, `q.options`, `q.with_for_update`, `result.scalar_one_or_none`, `select`, `select(Product).where`, `selectinload`, `selectinload(Product.variants).selectinload`, `self.db.execute`.
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `ProductRepository.get_by_slug` (async), lines 65-82: No function docstring; consult the source body and layer walkthrough.
  Calls: `Product.admin_hidden.is_`, `Product.deleted_at.is_`, `Product.is_published.is_`, `result.scalar_one_or_none`, `select`, `select(Product).options`, `select(Product).options(selectinload(Product.images), selectinload(Product.variants).selectinload(ProductVariant.inventory), selectinload(Product.seller), selectinload(Product.category), selectinload(Product.tags)).where`, `selectinload`, `selectinload(Product.variants).selectinload`, `self.db.execute`.
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `ProductRepository.slug_exists` (async), lines 84-88: No function docstring; consult the source body and layer walkthrough.
  Calls: `Product.deleted_at.is_`, `result.scalar_one_or_none`, `select`, `select(Product.id).where`, `self.db.execute`.
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `ProductRepository.get_seller_products` (async), lines 90-120: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `Product.deleted_at.is_`, `Product.is_published.is_`, `desc`, `func.count`, `q.options`, `q.options(selectinload(Product.images), selectinload(Product.variants).selectinload(ProductVariant.inventory), selectinload(Product.category)).order_by`, `q.options(selectinload(Product.images), selectinload(Product.variants).selectinload(ProductVariant.inventory), selectinload(Product.category)).order_by(desc(Product.created_at)).offset`, `q.options(selectinload(Product.images), selectinload(Product.variants).selectinload(ProductVariant.inventory), selectinload(Product.category)).order_by(desc(Product.created_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars` ... (19 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`.
- `ProductRepository.list_catalogue` (async), lines 122-216: No function docstring; consult the source body and layer walkthrough.
  Calls: `BusinessRuleError`, `Decimal`, `Product.admin_hidden.is_`, `Product.deleted_at.is_`, `Product.description.ilike`, `Product.is_published.is_`, `Product.name.ilike`, `Product.sale_price.isnot`, `Product.variants.any`, `ProductVariant.colour.in_`, `ProductVariant.is_active.is_`, `ProductVariant.size_value.in_` ... (51 distinct call expressions).
  Mutation/I-O-related call names: `Product.deleted_at.is_`, `Seller.deleted_at.is_`.
- `ProductRepository.search_suggestions` (async), lines 218-244: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(select(Product).options(selectinload(Product.images), selectinload(Product.seller)).where(Product.name.ilike(search), Product.admin_hidden.is_(False), Product.seller.has(and_(Seller.status == SellerStatus.active, Seller.deleted_at.is_(None))), Product.is_published.is_(True), Product.deleted_at.is_(None)).limit(limit))).scalars`, `(await self.db.execute(select(Product).options(selectinload(Product.images), selectinload(Product.seller)).where(Product.name.ilike(search), Product.admin_hidden.is_(False), Product.seller.has(and_(Seller.status == SellerStatus.active, Seller.deleted_at.is_(None))), Product.is_published.is_(True), Product.deleted_at.is_(None)).limit(limit))).scalars().all`, `(await self.db.execute(select(Seller).where(Seller.brand_name.ilike(search), Seller.status == SellerStatus.active, Seller.deleted_at.is_(None)).limit(limit))).scalars`, `(await self.db.execute(select(Seller).where(Seller.brand_name.ilike(search), Seller.status == SellerStatus.active, Seller.deleted_at.is_(None)).limit(limit))).scalars().all`, `Product.admin_hidden.is_`, `Product.deleted_at.is_`, `Product.is_published.is_`, `Product.name.ilike`, `Product.seller.has`, `Seller.brand_name.ilike`, `Seller.deleted_at.is_`, `and_` ... (20 distinct call expressions).
  Mutation/I-O-related call names: `(await self.db.execute(select(Product).options(selectinload(Product.images), selectinload(Product.seller)).where(Product.name.ilike(search), Product.admin_hidden.is_(False), Product.seller.has(and_(Seller.status == SellerStatus.active, Seller.deleted_at.is_(None))), Product.is_published.is_(True), Product.deleted_at.is_(None)).limit(limit))).scalars`, `(await self.db.execute(select(Product).options(selectinload(Product.images), selectinload(Product.seller)).where(Product.name.ilike(search), Product.admin_hidden.is_(False), Product.seller.has(and_(Seller.status == SellerStatus.active, Seller.deleted_at.is_(None))), Product.is_published.is_(True), Product.deleted_at.is_(None)).limit(limit))).scalars().all`, `(await self.db.execute(select(Seller).where(Seller.brand_name.ilike(search), Seller.status == SellerStatus.active, Seller.deleted_at.is_(None)).limit(limit))).scalars`, `(await self.db.execute(select(Seller).where(Seller.brand_name.ilike(search), Seller.status == SellerStatus.active, Seller.deleted_at.is_(None)).limit(limit))).scalars().all`, `Product.deleted_at.is_`, `Seller.deleted_at.is_`, `select(Product).options(selectinload(Product.images), selectinload(Product.seller)).where(Product.name.ilike(search), Product.admin_hidden.is_(False), Product.seller.has(and_(Seller.status == SellerStatus.active, Seller.deleted_at.is_(None))), Product.is_published.is_(True), Product.deleted_at.is_(None)).limit`, `select(Seller).where(Seller.brand_name.ilike(search), Seller.status == SellerStatus.active, Seller.deleted_at.is_(None)).limit`.
- `ProductRepository.update` (async), lines 248-254: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `self.db.flush`, `self.get_by_id`, `update`, `update(Product).where`, `update(Product).where(Product.id == product_id).values`.
  Mutation/I-O-related call names: `self.db.flush`.
- `ProductRepository.set_published` (async), lines 256-261: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(Product).where`, `update(Product).where(Product.id == product_id).values`.
- `ProductRepository.soft_delete` (async), lines 263-268: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(Product).where`, `update(Product).where(Product.id == product_id).values`.
- `ProductRepository.increment_view_count` (async), lines 270-275: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.db.execute`, `update`, `update(Product).where`, `update(Product).where(Product.id == product_id).values`.
- `ProductRepository.get_image_count` (async), lines 279-283: No function docstring; consult the source body and layer walkthrough.
  Calls: `func.count`, `result.scalar_one`, `select`, `select(func.count(ProductImage.id)).where`, `self.db.execute`.
- `ProductRepository.set_primary_image` (async), lines 285-295: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.db.execute`, `update`, `update(ProductImage).where`, `update(ProductImage).where(ProductImage.id == image_id).values`, `update(ProductImage).where(ProductImage.product_id == product_id).values`.
- `ProductRepository.get_category` (async), lines 299-303: No function docstring; consult the source body and layer walkthrough.
  Calls: `Category.is_active.is_`, `result.scalar_one_or_none`, `select`, `select(Category).where`, `self.db.execute`.
- Class `VariantRepository`, lines 306-329; bases: .
- `VariantRepository.__init__` (sync), lines 307-308: No function docstring; consult the source body and layer walkthrough.
- `VariantRepository.create` (async), lines 310-315: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductVariant`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `VariantRepository.get_by_product` (async), lines 317-323: No function docstring; consult the source body and layer walkthrough.
  Calls: `ProductVariant.is_active.is_`, `result.scalars`, `result.scalars().all`, `select`, `select(ProductVariant).options`, `select(ProductVariant).options(selectinload(ProductVariant.inventory)).where`, `selectinload`, `self.db.execute`.
- `VariantRepository.sku_exists` (async), lines 325-329: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(ProductVariant.id).where`, `self.db.execute`.

## app/repositories/return_repo.py

215 lines; SHA-256 `748ff91d29b80d43903d10a2ca1a44e3fb19f53a855cbdc5f3a3b3a9030af0c4`. [Open source](../../app/repositories/return_repo.py).

Backend imports: `app.models.order`, `app.models.return_`.

- Class `ReturnRepository`, lines 22-139; bases: .
- `ReturnRepository.__init__` (sync), lines 23-24: No function docstring; consult the source body and layer walkthrough.
- `ReturnRepository.create` (async), lines 26-31: No function docstring; consult the source body and layer walkthrough.
  Calls: `Return`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `ReturnRepository.add_item` (async), lines 33-37: No function docstring; consult the source body and layer walkthrough.
  Calls: `ReturnItem`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `ReturnRepository.get_by_id` (async), lines 39-55: No function docstring; consult the source body and layer walkthrough.
  Calls: `q.execution_options`, `q.where`, `q.with_for_update`, `result.scalar_one_or_none`, `select`, `select(Return).options`, `select(Return).options(selectinload(Return.items), selectinload(Return.dispute).selectinload(Dispute.messages)).where`, `selectinload`, `selectinload(Return.dispute).selectinload`, `self.db.execute`.
- `ReturnRepository.list_by_user` (async), lines 57-67: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(Return.requested_at)).offset`, `q.order_by(desc(Return.requested_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `result.scalars`, `result.scalars().all`, `select`, `select(Return).options`, `select(Return).options(selectinload(Return.items)).where` ... (15 distinct call expressions).
- `ReturnRepository.list_admin` (async), lines 69-81: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `ReturnStatus`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(Return.requested_at)).offset`, `q.order_by(desc(Return.requested_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars`, `result.scalars().all`, `select` ... (16 distinct call expressions).
- `ReturnRepository.get_by_seller` (async), lines 83-99: No function docstring; consult the source body and layer walkthrough.
  Calls: `query.with_for_update`, `result.scalar_one_or_none`, `select`, `select(Return).join`, `select(Return).join(SellerOrder, SellerOrder.id == Return.seller_order_id).options`, `select(Return).join(SellerOrder, SellerOrder.id == Return.seller_order_id).options(selectinload(Return.items), selectinload(Return.dispute).selectinload(Dispute.messages)).where`, `select(Return).join(SellerOrder, SellerOrder.id == Return.seller_order_id).options(selectinload(Return.items), selectinload(Return.dispute).selectinload(Dispute.messages)).where(Return.id == return_id, SellerOrder.seller_id == seller_id).execution_options`, `selectinload`, `selectinload(Return.dispute).selectinload`, `self.db.execute`.
- `ReturnRepository.list_seller` (async), lines 101-123: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one`, `ReturnStatus`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(Return.requested_at)).offset`, `q.order_by(desc(Return.requested_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `rows.scalars`, `rows.scalars().all`, `select` ... (18 distinct call expressions).
- `ReturnRepository.update_status` (async), lines 125-139: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.db.execute`, `update`, `update(Return).where`, `update(Return).where(Return.id == return_id).values`.
- Class `DisputeRepository`, lines 142-215; bases: .
- `DisputeRepository.__init__` (sync), lines 143-144: No function docstring; consult the source body and layer walkthrough.
- `DisputeRepository.create` (async), lines 146-151: No function docstring; consult the source body and layer walkthrough.
  Calls: `Dispute`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `DisputeRepository.get_by_id` (async), lines 153-164: No function docstring; consult the source body and layer walkthrough.
  Calls: `query.with_for_update`, `result.scalar_one_or_none`, `select`, `select(Dispute).options`, `select(Dispute).options(selectinload(Dispute.messages)).where`, `selectinload`, `self.db.execute`.
- `DisputeRepository.get_by_return_id` (async), lines 166-177: No function docstring; consult the source body and layer walkthrough.
  Calls: `query.with_for_update`, `result.scalar_one_or_none`, `select`, `select(Dispute).options`, `select(Dispute).options(selectinload(Dispute.messages)).where`, `selectinload`, `self.db.execute`.
- `DisputeRepository.add_message` (async), lines 179-183: No function docstring; consult the source body and layer walkthrough.
  Calls: `DisputeMessage`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `DisputeRepository.list_admin` (async), lines 185-197: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `DisputeStatus`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(Dispute.created_at)).offset`, `q.order_by(desc(Dispute.created_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars`, `result.scalars().all`, `select` ... (16 distinct call expressions).
- `DisputeRepository.resolve` (async), lines 199-215: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(Dispute).where`, `update(Dispute).where(Dispute.id == dispute_id).values`.

## app/repositories/seller_repo.py

243 lines; SHA-256 `641a1534fdc484826d9fadd525b42149cc08e6033acb9654d89835b1b79635c7`. [Open source](../../app/repositories/seller_repo.py).

Backend imports: `app.core.exceptions`, `app.models.product`, `app.models.seller`.

- Class `SellerRepository`, lines 15-129; bases: .
- `SellerRepository.__init__` (sync), lines 16-17: No function docstring; consult the source body and layer walkthrough.
- `SellerRepository.create` (async), lines 19-24: No function docstring; consult the source body and layer walkthrough.
  Calls: `Seller`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `SellerRepository.get_by_id` (async), lines 26-32: No function docstring; consult the source body and layer walkthrough.
  Calls: `Seller.deleted_at.is_`, `result.scalar_one_or_none`, `select`, `select(Seller).options`, `select(Seller).options(selectinload(Seller.wallet), selectinload(Seller.bank_accounts)).where`, `selectinload`, `self.db.execute`.
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `SellerRepository.get_by_user_id` (async), lines 34-40: No function docstring; consult the source body and layer walkthrough.
  Calls: `Seller.deleted_at.is_`, `result.scalar_one_or_none`, `select`, `select(Seller).options`, `select(Seller).options(selectinload(Seller.wallet), selectinload(Seller.bank_accounts)).where`, `selectinload`, `self.db.execute`.
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `SellerRepository.get_by_slug` (async), lines 42-46: No function docstring; consult the source body and layer walkthrough.
  Calls: `Seller.deleted_at.is_`, `result.scalar_one_or_none`, `select`, `select(Seller).where`, `self.db.execute`.
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `SellerRepository.get_by_brand_name` (async), lines 48-55: No function docstring; consult the source body and layer walkthrough.
  Calls: `Seller.deleted_at.is_`, `brand_name.lower`, `func.lower`, `result.scalar_one_or_none`, `select`, `select(Seller).where`, `self.db.execute`.
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `SellerRepository.exists_for_user` (async), lines 57-63: No function docstring; consult the source body and layer walkthrough.
  Calls: `Seller.deleted_at.is_`, `result.scalar_one_or_none`, `select`, `select(Seller.id).where`, `self.db.execute`.
  Mutation/I-O-related call names: `Seller.deleted_at.is_`.
- `SellerRepository.update_status` (async), lines 65-79: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id).values`.
- `SellerRepository.update_profile` (async), lines 81-85: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `self.db.flush`, `self.get_by_id`, `update`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id).values`.
  Mutation/I-O-related call names: `self.db.flush`.
- `SellerRepository.update_logo` (async), lines 87-92: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id).values`.
- `SellerRepository.add_slots` (async), lines 94-101: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `self.db.flush`, `self.get_by_id`, `update`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id).values`.
  Mutation/I-O-related call names: `self.db.flush`.
- `SellerRepository.increment_slots_used` (async), lines 103-108: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id).values`.
- `SellerRepository.decrement_slots_used` (async), lines 110-115: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(Seller).where`, `update(Seller).where(Seller.id == seller_id, Seller.slots_used > 0).values`.
- `SellerRepository.count_published_products` (async), lines 117-129: Requires Block 4 (Products). Returns 0 until then.
  Calls: `Product.is_published.is_`, `func.count`, `result.scalar_one`, `select`, `select(func.count(Product.id)).where`, `self.db.execute`.
- Class `WalletRepository`, lines 132-203; bases: .
- `WalletRepository.__init__` (sync), lines 133-134: No function docstring; consult the source body and layer walkthrough.
- `WalletRepository.create_for_seller` (async), lines 136-140: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerWallet`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `WalletRepository.get_by_seller_id` (async), lines 142-149: No function docstring; consult the source body and layer walkthrough.
  Calls: `query.with_for_update`, `query.with_for_update().execution_options`, `result.scalar_one_or_none`, `select`, `select(SellerWallet).where`, `self.db.execute`.
- `WalletRepository.credit_pending` (async), lines 151-160: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(SellerWallet).where`, `update(SellerWallet).where(SellerWallet.seller_id == seller_id).values`.
- `WalletRepository.release_pending_to_available` (async), lines 162-171: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(SellerWallet).where`, `update(SellerWallet).where(SellerWallet.seller_id == seller_id).values`.
- `WalletRepository.charge_commission` (async), lines 173-181: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(SellerWallet).where`, `update(SellerWallet).where(SellerWallet.seller_id == seller_id).values`.
- `WalletRepository.debit_available` (async), lines 183-197: No function docstring; consult the source body and layer walkthrough.
  Calls: `InsufficientBalanceError`, `datetime.utcnow`, `self.db.execute`, `update`, `update(SellerWallet).where`, `update(SellerWallet).where(SellerWallet.seller_id == seller_id, SellerWallet.available_balance >= amount).values`.
- `WalletRepository.credit_available` (async), lines 199-203: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(SellerWallet).where`, `update(SellerWallet).where(SellerWallet.seller_id == seller_id).values`.
- Class `BankAccountRepository`, lines 206-243; bases: .
- `BankAccountRepository.__init__` (sync), lines 207-208: No function docstring; consult the source body and layer walkthrough.
- `BankAccountRepository.list_by_seller` (async), lines 210-216: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalars`, `result.scalars().all`, `select`, `select(SellerBankAccount).where`, `select(SellerBankAccount).where(SellerBankAccount.seller_id == seller_id).order_by`, `self.db.execute`.
- `BankAccountRepository.create` (async), lines 218-223: No function docstring; consult the source body and layer walkthrough.
  Calls: `SellerBankAccount`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `BankAccountRepository.clear_default` (async), lines 225-230: No function docstring; consult the source body and layer walkthrough.
  Calls: `self.db.execute`, `update`, `update(SellerBankAccount).where`, `update(SellerBankAccount).where(SellerBankAccount.seller_id == seller_id).values`.
- `BankAccountRepository.delete` (async), lines 232-243: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(SellerBankAccount).where`, `self.db.delete`, `self.db.execute`.
  Mutation/I-O-related call names: `self.db.delete`.

## app/repositories/user_repo.py

160 lines; SHA-256 `20e06e84d1febf660c03757305573efe8e1d1c3716fa8776269172299b2da093`. [Open source](../../app/repositories/user_repo.py).

Backend imports: `app.models.user`, `app.repositories.base`.

- Class `UserRepository`, lines 19-82; bases: BaseRepository[User].
- `UserRepository.get_by_email` (async), lines 25-31: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await db.execute(stmt)).scalar_one_or_none`, `User.deleted_at.is_`, `db.execute`, `email.lower`, `email.lower().strip`, `select`, `select(User).where`, `stmt.where`.
  Mutation/I-O-related call names: `User.deleted_at.is_`.
- `UserRepository.get_by_google_id` (async), lines 34-36: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await db.execute(stmt)).scalar_one_or_none`, `User.deleted_at.is_`, `db.execute`, `select`, `select(User).where`.
  Mutation/I-O-related call names: `User.deleted_at.is_`.
- `UserRepository.email_exists` (async), lines 39-44: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await db.execute(stmt)).scalar_one_or_none`, `User.deleted_at.is_`, `db.execute`, `email.lower`, `email.lower().strip`, `select`, `select(User.id).where`.
  Mutation/I-O-related call names: `User.deleted_at.is_`.
- `UserRepository.verify_email` (async), lines 49-55: No function docstring; consult the source body and layer walkthrough.
  Calls: `db.execute`, `db.flush`, `update`, `update(User).where`, `update(User).where(User.id == user_id).values`.
  Mutation/I-O-related call names: `db.flush`.
- `UserRepository.update_password` (async), lines 58-64: No function docstring; consult the source body and layer walkthrough.
  Calls: `db.execute`, `db.flush`, `update`, `update(User).where`, `update(User).where(User.id == user_id).values`.
  Mutation/I-O-related call names: `db.flush`.
- `UserRepository.update_last_login` (async), lines 67-73: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.now`, `db.execute`, `db.flush`, `update`, `update(User).where`, `update(User).where(User.id == user_id).values`.
  Mutation/I-O-related call names: `db.flush`.
- `UserRepository.set_totp` (async), lines 76-82: No function docstring; consult the source body and layer walkthrough.
  Calls: `db.execute`, `db.flush`, `update`, `update(User).where`, `update(User).where(User.id == user_id).values`.
  Mutation/I-O-related call names: `db.flush`.
- Class `SessionRepository`, lines 85-138; bases: .
- `SessionRepository.create` (async), lines 89-107: No function docstring; consult the source body and layer walkthrough.
  Calls: `UserSession`, `db.add`, `db.flush`.
  Mutation/I-O-related call names: `db.flush`.
- `SessionRepository.get_by_token_hash` (async), lines 110-115: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await db.execute(stmt.with_for_update())).scalar_one_or_none`, `datetime.now`, `db.execute`, `select`, `select(UserSession).where`, `stmt.with_for_update`.
- `SessionRepository.delete_by_token_hash` (async), lines 118-120: No function docstring; consult the source body and layer walkthrough.
  Calls: `db.execute`, `db.flush`, `delete`, `delete(UserSession).where`.
  Mutation/I-O-related call names: `db.flush`, `delete`, `delete(UserSession).where`.
- `SessionRepository.delete_all_for_user` (async), lines 123-129: Invalidate all sessions for a user (password change / account deletion).
  Calls: `db.execute`, `db.flush`, `delete`, `delete(UserSession).where`.
  Mutation/I-O-related call names: `db.flush`, `delete`, `delete(UserSession).where`.
- `SessionRepository.cleanup_expired` (async), lines 132-138: Delete all expired sessions. Called by maintenance task.
  Calls: `datetime.now`, `db.execute`, `db.flush`, `delete`, `delete(UserSession).where`.
  Mutation/I-O-related call names: `db.flush`, `delete`, `delete(UserSession).where`.
- Class `AddressRepository`, lines 141-160; bases: BaseRepository[UserAddress].
- `AddressRepository.list_for_user` (async), lines 145-151: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await db.execute(stmt)).scalars`, `(await db.execute(stmt)).scalars().all`, `UserAddress.created_at.desc`, `UserAddress.is_default.desc`, `db.execute`, `list`, `select`, `select(UserAddress).where`, `select(UserAddress).where(UserAddress.user_id == user_id).order_by`.
- `AddressRepository.clear_default` (async), lines 154-160: No function docstring; consult the source body and layer walkthrough.
  Calls: `db.execute`, `db.flush`, `update`, `update(UserAddress).where`, `update(UserAddress).where(UserAddress.user_id == user_id).values`.
  Mutation/I-O-related call names: `db.flush`.

## app/repositories/wallet_repo.py

166 lines; SHA-256 `b52324319da5ea1537a3cd1886b4ece2af94cd3b0be94f0cf49acc111d5c6af8`. [Open source](../../app/repositories/wallet_repo.py).

Backend imports: `app.models.seller`, `app.models.wallet`.

- Class `CommissionRepository`, lines 15-63; bases: .
- `CommissionRepository.__init__` (sync), lines 16-17: No function docstring; consult the source body and layer walkthrough.
- `CommissionRepository.create` (async), lines 19-23: No function docstring; consult the source body and layer walkthrough.
  Calls: `CommissionLedger`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `CommissionRepository.exists_for_seller_order` (async), lines 25-31: No function docstring; consult the source body and layer walkthrough.
  Calls: `result.scalar_one_or_none`, `select`, `select(CommissionLedger.id).where`, `self.db.execute`.
- `CommissionRepository.list_by_seller` (async), lines 33-63: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `(await self.db.execute(summary_q)).one`, `desc`, `func.coalesce`, `func.count`, `func.sum`, `q.order_by`, `q.order_by(desc(CommissionLedger.settled_at)).offset`, `q.order_by(desc(CommissionLedger.settled_at)).offset((page - 1) * per_page).limit`, `q.subquery`, `result.scalars`, `result.scalars().all` ... (17 distinct call expressions).
- Class `WalletTransactionRepository`, lines 66-92; bases: .
- `WalletTransactionRepository.__init__` (sync), lines 67-68: No function docstring; consult the source body and layer walkthrough.
- `WalletTransactionRepository.create` (async), lines 70-74: No function docstring; consult the source body and layer walkthrough.
  Calls: `WalletTransaction`, `self.db.add`, `self.db.flush`.
  Mutation/I-O-related call names: `self.db.flush`.
- `WalletTransactionRepository.list_by_seller` (async), lines 76-92: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `WalletTxType`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(WalletTransaction.created_at), desc(WalletTransaction.id)).offset`, `q.order_by(desc(WalletTransaction.created_at), desc(WalletTransaction.id)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars`, `result.scalars().all`, `select` ... (15 distinct call expressions).
- Class `PayoutRepository`, lines 95-166; bases: .
- `PayoutRepository.__init__` (sync), lines 96-97: No function docstring; consult the source body and layer walkthrough.
- `PayoutRepository.create` (async), lines 99-104: No function docstring; consult the source body and layer walkthrough.
  Calls: `Payout`, `self.db.add`, `self.db.flush`, `self.db.refresh`.
  Mutation/I-O-related call names: `self.db.flush`.
- `PayoutRepository.get_by_id` (async), lines 106-113: No function docstring; consult the source body and layer walkthrough.
  Calls: `query.with_for_update`, `query.with_for_update().execution_options`, `result.scalar_one_or_none`, `select`, `select(Payout).where`, `self.db.execute`.
- `PayoutRepository.list_by_seller` (async), lines 115-131: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `PayoutStatus`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(Payout.requested_at), desc(Payout.id)).offset`, `q.order_by(desc(Payout.requested_at), desc(Payout.id)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars`, `result.scalars().all`, `select` ... (15 distinct call expressions).
- `PayoutRepository.list_admin` (async), lines 133-148: No function docstring; consult the source body and layer walkthrough.
  Calls: `(await self.db.execute(count_q)).scalar_one`, `PayoutStatus`, `desc`, `func.count`, `q.order_by`, `q.order_by(desc(Payout.requested_at), desc(Payout.id)).offset`, `q.order_by(desc(Payout.requested_at), desc(Payout.id)).offset((page - 1) * per_page).limit`, `q.subquery`, `q.where`, `result.scalars`, `result.scalars().all`, `select` ... (14 distinct call expressions).
- `PayoutRepository.update_status` (async), lines 150-166: No function docstring; consult the source body and layer walkthrough.
  Calls: `datetime.utcnow`, `self.db.execute`, `update`, `update(Payout).where`, `update(Payout).where(Payout.id == payout_id).values`.


