# Backend source index: migrations-scripts

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## alembic/env.py

128 lines; SHA-256 `1da5f94f946ed5abdb29e484e0430a070b2362bdf9cb3a41ccfee9594b42c422`. [Open source](../../alembic/env.py).

Backend imports: `app.models.admin`, `app.models.analytics`, `app.models.base`, `app.models.coupon`, `app.models.notification`, `app.models.order`, `app.models.payment`, `app.models.product`, `app.models.return_`, `app.models.review`, `app.models.seller`, `app.models.user`, `app.models.wallet`.

- `get_url` (sync), lines 54?58: No function docstring; consult the source body and layer walkthrough.
  Calls: `RuntimeError`, `os.environ.get`.
- `get_sync_url` (sync), lines 61?62: No function docstring; consult the source body and layer walkthrough.
  Calls: `get_url`, `get_url().replace`.
- `run_migrations_offline` (sync), lines 64?81: Run migrations in 'offline' mode — generates SQL without a live connection.
  Calls: `context.begin_transaction`, `context.configure`, `context.run_migrations`, `get_url`.
- `do_run_migrations` (sync), lines 84?96: No function docstring; consult the source body and layer walkthrough.
  Calls: `context.begin_transaction`, `context.configure`, `context.run_migrations`.
- `run_async_migrations` (async), lines 99?113: Run migrations using an async engine.
  Calls: `async_engine_from_config`, `config.get_section`, `connectable.connect`, `connectable.dispose`, `connection.run_sync`, `get_url`.
- `run_migrations_online` (sync), lines 116?122: Run migrations in 'online' mode — applies changes to a live database.
  Calls: `asyncio.run`, `config.attributes.get`, `do_run_migrations`, `run_async_migrations`.

## alembic/versions/001_create_users.py

215 lines; SHA-256 `9f58602d6347c68f6404c1a4daf5d505135aa6ea69a6b324d3123f0dbbebe6a0`. [Open source](../../alembic/versions/001_create_users.py).

- `upgrade` (sync), lines 21?207: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.create_index`, `op.create_table`, `op.execute`, `op.get_bind`, `postgresql.ENUM`, `postgresql.UUID`, `sa.Boolean`, `sa.CheckConstraint`, `sa.Column`, `sa.DateTime`, `sa.ForeignKeyConstraint`, `sa.PrimaryKeyConstraint` ? (16 distinct call expressions).
- `downgrade` (sync), lines 210?215: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_table`, `op.execute`.

## alembic/versions/002_create_sellers.py

109 lines; SHA-256 `590ede86d43d95c07579e245ad7433fbd1f03f8718598e7891b4bdb3ad9f7c61`. [Open source](../../alembic/versions/002_create_sellers.py).

- `upgrade` (sync), lines 20?102: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.create_check_constraint`, `op.create_index`, `op.create_table`, `op.create_unique_constraint`, `op.get_bind`, `postgresql.ENUM`, `postgresql.UUID`, `sa.Boolean`, `sa.Column`, `sa.ForeignKey`, `sa.Integer`, `sa.Numeric` ? (16 distinct call expressions).
- `downgrade` (sync), lines 105?109: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_table`, `op.execute`.

## alembic/versions/003_create_products.py

162 lines; SHA-256 `6c4cd2ce8948e2aab3fcd3abface3a55462e171c323d02cb3efdc1c512bc3f1d`. [Open source](../../alembic/versions/003_create_products.py).

- `upgrade` (sync), lines 22?151: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.create_check_constraint`, `op.create_index`, `op.create_table`, `op.create_unique_constraint`, `op.get_bind`, `postgresql.ENUM`, `postgresql.UUID`, `sa.Boolean`, `sa.Column`, `sa.ForeignKey`, `sa.Integer`, `sa.Numeric` ? (16 distinct call expressions).
- `downgrade` (sync), lines 154?162: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_table`, `op.execute`.

## alembic/versions/004_create_orders.py

175 lines; SHA-256 `84e6f8e7eb5ab3ad389163d2fbb548643a6d20ff632584dd7864ca4cfc84bcc3`. [Open source](../../alembic/versions/004_create_orders.py).

- `upgrade` (sync), lines 23?163: No function docstring; consult the source body and layer walkthrough.
  Calls: `enum_defs.items`, `enum_obj.create`, `op.create_check_constraint`, `op.create_index`, `op.create_table`, `op.create_unique_constraint`, `op.get_bind`, `postgresql.ENUM`, `postgresql.UUID`, `sa.Boolean`, `sa.Column`, `sa.ForeignKey` ? (17 distinct call expressions).
- `downgrade` (sync), lines 166?175: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_table`, `op.execute`.

## alembic/versions/005_create_payments.py

91 lines; SHA-256 `be8bc7bd86df0eb1480be999bd8dfe39d12195c200fa1fbc9409e77956b770c5`. [Open source](../../alembic/versions/005_create_payments.py).

- `upgrade` (sync), lines 21?84: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.create_check_constraint`, `op.create_index`, `op.create_table`, `op.create_unique_constraint`, `op.get_bind`, `payment_status_enum.create`, `postgresql.ENUM`, `postgresql.UUID`, `sa.Boolean`, `sa.Column`, `sa.ForeignKey`, `sa.Numeric` ? (15 distinct call expressions).
- `downgrade` (sync), lines 87?91: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_table`, `op.execute`.

## alembic/versions/006_create_wallet.py

110 lines; SHA-256 `d334c2abc40d5dc510d1a64bf2cbb7ec913423f4e19c2862360454fcfbbc4f6d`. [Open source](../../alembic/versions/006_create_wallet.py).

- `upgrade` (sync), lines 22?102: No function docstring; consult the source body and layer walkthrough.
  Calls: `enum_defs.items`, `enum_obj.create`, `op.create_check_constraint`, `op.create_index`, `op.create_table`, `op.create_unique_constraint`, `op.get_bind`, `postgresql.ENUM`, `postgresql.UUID`, `sa.Column`, `sa.ForeignKey`, `sa.Numeric` ? (15 distinct call expressions).
- `downgrade` (sync), lines 105?110: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_table`, `op.execute`.

## alembic/versions/007_create_admin.py

77 lines; SHA-256 `41d5a294d770a6cd8933a17bd3e00f581f52d2abb5976885e6cdfb00d07b382e`. [Open source](../../alembic/versions/007_create_admin.py).

- `upgrade` (sync), lines 31?72: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.bulk_insert`, `op.create_index`, `op.create_table`, `postgresql.UUID`, `sa.Boolean`, `sa.Column`, `sa.ForeignKey`, `sa.Integer`, `sa.String`, `sa.TIMESTAMP`, `sa.column`, `sa.table` ? (13 distinct call expressions).
- `downgrade` (sync), lines 75?77: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_table`.

## alembic/versions/008_create_notifications.py

77 lines; SHA-256 `32260feef598ae44b3bca94b230ba948fff13539c463a5ee1ef5a7ddaa108652`. [Open source](../../alembic/versions/008_create_notifications.py).

- `upgrade` (sync), lines 21?71: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.create_index`, `op.create_table`, `postgresql.UUID`, `sa.Boolean`, `sa.Column`, `sa.ForeignKey`, `sa.String`, `sa.TIMESTAMP`, `sa.text`.
- `downgrade` (sync), lines 74?77: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_table`.

## alembic/versions/009_create_returns.py

135 lines; SHA-256 `fde638313b5478db5c1e8390c8354bfdcaf05c00b89b4bee7253b380447acd32`. [Open source](../../alembic/versions/009_create_returns.py).

- `upgrade` (sync), lines 23?125: No function docstring; consult the source body and layer walkthrough.
  Calls: `bind.execute`, `bind.execute(sa.text('SELECT 1 FROM pg_type WHERE typname = :name'), {'name': name}).scalar`, `op.create_foreign_key`, `op.create_index`, `op.create_table`, `op.get_bind`, `postgresql.ENUM`, `postgresql.ENUM(*values, name=name).create`, `postgresql.UUID`, `sa.Column`, `sa.ForeignKey`, `sa.Integer` ? (14 distinct call expressions).
- `downgrade` (sync), lines 128?135: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_constraint`, `op.drop_table`, `op.execute`.

## alembic/versions/010_payfast_methods.py

12 lines; SHA-256 `6a5b3a4f92f2e70596da9bda861d708f558d6e6b1f0f0434efd2509595d20aec`. [Open source](../../alembic/versions/010_payfast_methods.py).

- `upgrade` (sync), lines 8?9: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.execute`.
- `downgrade` (sync), lines 11?12: No function docstring; consult the source body and layer walkthrough.

## alembic/versions/011_create_reviews.py

22 lines; SHA-256 `ce6c1003161846e98b3ef3d8bd6581817aa6204dfa6f1f1412060aa72fd73c82`. [Open source](../../alembic/versions/011_create_reviews.py).

- `upgrade` (sync), lines 9?16: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.execute`.
- `downgrade` (sync), lines 19?22: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.execute`.

## alembic/versions/012_marketplace_gaps.py

52 lines; SHA-256 `4957e8c9a5849f461c9ebe824a73819024987ec6ab351071629d8880bd8d1bdb`. [Open source](../../alembic/versions/012_marketplace_gaps.py).

- `upgrade` (sync), lines 16?39: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.add_column`, `op.create_index`, `op.create_table`, `op.create_unique_constraint`, `op.execute`, `postgresql.UUID`, `sa.Boolean`, `sa.Column`, `sa.DateTime`, `sa.ForeignKey`, `sa.Integer`, `sa.String` ? (13 distinct call expressions).
- `downgrade` (sync), lines 42?52: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_column`, `op.drop_constraint`, `op.drop_table`.

## alembic/versions/013_notification_archive.py

28 lines; SHA-256 `3ef8d8bd849348715f9413997b5bfc3b1bd093e0db6493632f5aa44501fb6a75`. [Open source](../../alembic/versions/013_notification_archive.py).

- `upgrade` (sync), lines 16?23: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.add_column`, `op.execute`, `sa.Boolean`, `sa.Column`, `sa.DateTime`, `sa.false`.
- `downgrade` (sync), lines 26?28: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_column`.

## alembic/versions/014_refund_request_audit.py

40 lines; SHA-256 `da18ab9a084e071d840ea9fe54505058d484f99482114ece2b9ce1db0204516a`. [Open source](../../alembic/versions/014_refund_request_audit.py).

- `upgrade` (sync), lines 17?33: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.add_column`, `op.create_foreign_key`, `op.create_index`, `op.execute`, `postgresql.UUID`, `sa.Column`.
- `downgrade` (sync), lines 36?40: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.drop_column`, `op.drop_constraint`, `op.drop_index`.

## alembic/versions/015_guest_returns.py

33 lines; SHA-256 `f0f9bfd44e86cb99fc299d46aef3cddbd24e5a551dcf1cf8d9b76544d0eb3a93`. [Open source](../../alembic/versions/015_guest_returns.py).

- `upgrade` (sync), lines 16?22: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.alter_column`, `postgresql.UUID`.
- `downgrade` (sync), lines 25?33: No function docstring; consult the source body and layer walkthrough.
  Calls: `op.alter_column`, `postgresql.UUID`.

## app/__init__.py

0 lines; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. [Open source](../../app/__init__.py).


## scripts/export_contract.py

104 lines; SHA-256 `1bd5a3ba9527c0a7150d4514c56418c4eec85deaeb331b84d29ba4492c8da710`. [Open source](../../scripts/export_contract.py).

- `main` (sync), lines 16?100: No function docstring; consult the source body and layer walkthrough.
  Calls: `', '.join`, `'\n'.join`, `(target / 'ENDPOINTS.md').write_text`, `(target / 'openapi.json').write_text`, `RuntimeError`, `app.openapi`, `dependencies`, `getattr`, `isinstance`, `json.dumps`, `len`, `lines.extend` ? (22 distinct call expressions).
- `main.dependencies` (sync), lines 42?47: No function docstring; consult the source body and layer walkthrough.
  Calls: `dependencies`, `getattr`, `names.add`, `names.update`, `set`, `type`.

## scripts/package_review.py

86 lines; SHA-256 `bee562248faf1fe43bf566a7634b0ac49d829b1b418e3571c44e7c7a944f9cc7`. [Open source](../../scripts/package_review.py).

- `selected_files` (sync), lines 33?54: No function docstring; consult the source body and layer walkthrough.
  Calls: `(ROOT / name).is_file`, `(ROOT / name).rglob`, `RuntimeError`, `any`, `part.startswith`, `path.is_file`, `path.is_symlink`, `path.relative_to`, `path.resolve`, `path.resolve().is_relative_to`, `paths.append`, `set` ? (13 distinct call expressions).
- `main` (sync), lines 57?82: No function docstring; consult the source body and layer walkthrough.
  Calls: `(output / 'WearHowZ_Task_6_Review.sha256').write_text`, `RuntimeError`, `ZipFile`, `archive.read`, `archive.testzip`, `archive.write`, `archive.writestr`, `destination.read_bytes`, `hashlib.sha256`, `hashlib.sha256(archive.read(name)).hexdigest`, `hashlib.sha256(destination.read_bytes()).hexdigest`, `hashlib.sha256(path.read_bytes()).hexdigest` ? (21 distinct call expressions).

## scripts/verify_connected_services.py

87 lines; SHA-256 `d333d1c614479eb87583c3e9f63a96bf670cf4cc25847a457eb4774743d604b3`. [Open source](../../scripts/verify_connected_services.py).

Backend imports: `app.core.config`, `app.integrations.resend_client`, `app.integrations.supabase_storage`.

- `parse_args` (sync), lines 19?31: No function docstring; consult the source body and layer walkthrough.
  Calls: `argparse.ArgumentParser`, `parser.add_argument`, `parser.parse_args`.
- `verify_storage` (async), lines 34?53: No function docstring; consult the source body and layer walkthrough.
  Calls: `RuntimeError`, `SupabaseStorage`, `any`, `item.get`, `print`, `sorted`, `storage.delete`, `storage.list_all_files`, `storage.upload`, `uuid4`.
  Mutation/I-O-related call names: `storage.delete`, `storage.upload`.
- `verify_email` (async), lines 56?64: No function docstring; consult the source body and layer walkthrough.
  Calls: `ResendClient`, `ResendClient().send`, `print`.
  Mutation/I-O-related call names: `ResendClient`, `ResendClient().send`.
- `main` (async), lines 67?83: No function docstring; consult the source body and layer walkthrough.
  Calls: `bool`, `parse_args`, `print`, `settings.API_BASE_URL.rstrip`, `verify_email`, `verify_storage`.


