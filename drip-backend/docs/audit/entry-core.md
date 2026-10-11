# Backend source index: entry-core

Generated on 11 October 2026 from tracked backend Python source. This is an AST navigation index, not an independently authored line-by-line explanation or a correctness claim. Source docstrings may be stale; the review findings take precedence. Calls shown are syntactic references (at most 12 per function), not a resolved runtime call graph.

## app/api/deps.py

212 lines; SHA-256 `0a61c95b345273ca235bba18d1c7f9c62412e14c79a0532814c6c59b8030de2c`. [Open source](../../app/api/deps.py).

Backend imports: `app.core.database`, `app.core.exceptions`, `app.core.logging`, `app.core.security`, `app.models.user`, `app.repositories.seller_repo`.

- `_extract_token` (async), lines 46?52: Extract Bearer token from Authorization header. Returns None if absent.
  Calls: `Depends`, `credentials.scheme.lower`.
- `_validate_token` (async), lines 58?78: Decode and validate the access token.
  Calls: `AuthenticationError`, `TokenInvalidError`, `decode_access_token`, `is_token_revoked`, `payload.get`.
- `get_current_user_payload` (async), lines 84?108: Validate the access token and return the decoded payload.
  Calls: `Depends`, `EmailNotVerifiedError`, `TokenInvalidError`, `UUID`, `_validate_token`, `db.get`, `payload.get`.
- `get_optional_user_payload` (async), lines 111?121: Like get_current_user_payload but returns None for unauthenticated requests.
  Calls: `Depends`, `get_current_user_payload`.
- `require_customer` (async), lines 127?131: Require any authenticated user (customer, seller, or admin).
  Calls: `Depends`.
- `require_seller` (async), lines 134?159: Require an authenticated seller with an active brand account.
  Calls: `Depends`, `PermissionDeniedError`, `SellerNotActiveError`, `SellerRepository`, `SellerRepository(db).get_by_user_id`, `SellerSuspendedError`, `UUID`, `payload.get`, `str`.
- `require_admin` (async), lines 162?168: Require an admin user. Most restrictive — admins only.
  Calls: `Depends`, `PermissionDeniedError`, `payload.get`.
- `assert_owns_resource` (sync), lines 174?188: Raise PermissionDeniedError if the current user doesn't own the resource.
  Calls: `PermissionDeniedError`, `payload.get`, `str`.
- `assert_owns_seller_resource` (sync), lines 191?204: Raise PermissionDeniedError if the seller token doesn't own the seller resource.
  Calls: `PermissionDeniedError`, `payload.get`, `str`.

## app/core/config.py

207 lines; SHA-256 `898a1e6b561d8ec82065afb2960a04ffde212c11bb9004003ce65b2aa08cb4e8`. [Open source](../../app/core/config.py).

- Class `Settings`, lines 17?197; bases: BaseSettings.
  Annotated fields: `ENVIRONMENT`, `APP_NAME`, `APP_VERSION`, `API_PREFIX`, `DEBUG`, `ALLOWED_ORIGINS`, `DATABASE_URL`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT`, `REDIS_URL`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET_PRODUCTS`, `SUPABASE_STORAGE_BUCKET_AVATARS`, `SUPABASE_STORAGE_BUCKET_BRANDS`, `SUPABASE_STORAGE_BUCKET_INVOICES`, `SUPABASE_ORPHAN_CLEANUP_ENABLED`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CURRENCY`, `RESEND_API_KEY`, `FROM_EMAIL`, `FROM_NAME`, `DRIP_WHATSAPP_NUMBER`, `COMMISSION_RATE`, `REGISTRATION_FEE`, `BASE_SLOTS`, `EXTRA_SLOT_PRICE`, `FREE_SHIPPING_THRESHOLD`, `STANDARD_SHIPPING_FEE`, `COD_TIMEOUT_MINUTES`, `PAYMENT_TIMEOUT_MINUTES`, `WALLET_HOLD_DAYS`, `MIN_WITHDRAWAL_AMOUNT`, `MAX_WITHDRAWAL_AMOUNT`, `MAX_COD_ORDER_AMOUNT`, `SENTRY_DSN`, `PAYFAST_MERCHANT_ID`, `PAYFAST_SECURED_KEY`, `PAYFAST_MERCHANT_NAME`, `PAYFAST_SANDBOX`, `PAYFAST_TOKEN_URL`, `PAYFAST_CHECKOUT_URL`, `PAYFAST_API_BASE_URL`, `PAYFAST_REQUEST_TIMEOUT_SECONDS`, `PAYFAST_ENABLED`, `PAYFAST_IPN_IPS`, `PAYFAST_TRUSTED_PROXY_IPS`, `GUEST_ORDER_TOKEN_DAYS`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FRONTEND_URL`, `API_BASE_URL`.
- `Settings.validate_database_url` (sync), lines 94?100: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`, `v.startswith`.
- `Settings.validate_commission_rate` (sync), lines 104?107: No function docstring; consult the source body and layer walkthrough.
  Calls: `ValueError`, `field_validator`.
- `Settings.parse_origins` (sync), lines 113?116: No function docstring; consult the source body and layer walkthrough.
  Calls: `field_validator`, `isinstance`, `o.strip`, `v.split`.
- `Settings.validate_production_secrets` (sync), lines 119?151: In production, critical secrets must be set.
  Calls: `ValueError`, `bool`, `getattr`, `getattr(self, key, '').strip`, `getattr(self, name).startswith`, `model_validator`, `self.FROM_EMAIL.endswith`.
- `Settings.is_development` (sync), lines 183?184: No function docstring; consult the source body and layer walkthrough.
- `Settings.is_production` (sync), lines 187?188: No function docstring; consult the source body and layer walkthrough.
- `Settings.docs_url` (sync), lines 191?193: Disable OpenAPI docs in production.
- `Settings.redoc_url` (sync), lines 196?197: No function docstring; consult the source body and layer walkthrough.
- `get_settings` (sync), lines 201?203: No function docstring; consult the source body and layer walkthrough.
  Calls: `Settings`, `lru_cache`, `os.environ.get`.

## app/core/database.py

167 lines; SHA-256 `acdd282cac2e94d11af4a515c24135b4e2c17cb20bc5dfcf0abbf3f8f5cc61d3`. [Open source](../../app/core/database.py).

Backend imports: `app.core.config`, `app.core.logging`.

- `create_engine_and_session` (sync), lines 38?76: Create the async engine and session factory.
  Calls: `async_sessionmaker`, `create_async_engine`, `event.listens_for`, `logger.debug`.
- `create_engine_and_session.on_connect` (sync), lines 65?66: No function docstring; consult the source body and layer walkthrough.
  Calls: `event.listens_for`, `logger.debug`.
- `init_db` (async), lines 79?91: Called at app startup. Creates engine and verifies connectivity.
  Calls: `_engine.connect`, `conn.execute`, `create_engine_and_session`, `logger.error`, `logger.info`, `str`, `text`.
- `close_db` (async), lines 94?101: Called at app shutdown. Disposes the connection pool.
  Calls: `_engine.dispose`, `logger.info`.
- `AsyncSessionLocal` (sync), lines 104?108: Create a worker session from the factory initialized at worker startup.
  Calls: `RuntimeError`, `_session_factory`.
- `get_db` (async), lines 113?138: FastAPI dependency that yields a database session per request.
  Calls: `RuntimeError`, `_session_factory`, `session.close`, `session.rollback`.
  Mutation/I-O-related call names: `session.rollback`.
- `atomic` (async), lines 144?155: Context manager for explicit transaction control within a service.
  Calls: `session.begin`.
- `_json_serializer` (sync), lines 160?162: No function docstring; consult the source body and layer walkthrough.
  Calls: `orjson.dumps`, `orjson.dumps(obj).decode`.
- `_json_deserializer` (sync), lines 165?167: No function docstring; consult the source body and layer walkthrough.
  Calls: `orjson.loads`.

## app/core/exceptions.py

278 lines; SHA-256 `8253c4c28e2ee363aff4564c958ecc8c47981e6d6d653c6e69bdc7663412435c`. [Open source](../../app/core/exceptions.py).

- Class `DRIPException`, lines 20?52; bases: Exception.
  Annotated fields: `http_status`, `default_code`, `default_message`.
- `DRIPException.__init__` (sync), lines 27?38: No function docstring; consult the source body and layer walkthrough.
  Calls: `super`, `super().__init__`.
- `DRIPException.to_response` (sync), lines 40?52: Safe representation for the API response body.
- Class `ValidationError`, lines 57?68; bases: DRIPException.
- `ValidationError.__init__` (sync), lines 63?68: No function docstring; consult the source body and layer walkthrough.
  Calls: `super`, `super().__init__`.
- Class `BusinessRuleError`, lines 71?75; bases: DRIPException.
- Class `AuthenticationError`, lines 80?83; bases: DRIPException.
- Class `InvalidCredentialsError`, lines 86?88; bases: AuthenticationError.
- Class `TokenExpiredError`, lines 91?93; bases: AuthenticationError.
- Class `TokenInvalidError`, lines 96?98; bases: AuthenticationError.
- Class `EmailNotVerifiedError`, lines 101?103; bases: AuthenticationError.
- Class `TwoFactorRequiredError`, lines 106?108; bases: AuthenticationError.
- Class `TwoFactorInvalidError`, lines 111?113; bases: AuthenticationError.
- Class `PermissionDeniedError`, lines 118?121; bases: DRIPException.
- Class `SellerSuspendedError`, lines 124?126; bases: PermissionDeniedError.
- Class `SellerNotActiveError`, lines 129?131; bases: PermissionDeniedError.
- Class `NotFoundError`, lines 136?145; bases: DRIPException.
- `NotFoundError.__init__` (sync), lines 141?145: No function docstring; consult the source body and layer walkthrough.
  Calls: `super`, `super().__init__`.
- Class `ConflictError`, lines 150?153; bases: DRIPException.
- Class `DuplicateEmailError`, lines 156?158; bases: ConflictError.
- Class `DuplicateBrandNameError`, lines 161?163; bases: ConflictError.
- Class `DuplicateSkuError`, lines 166?168; bases: ConflictError.
- Class `DuplicateReviewError`, lines 171?173; bases: ConflictError.
- Class `InsufficientStockError`, lines 178?187; bases: BusinessRuleError.
- `InsufficientStockError.__init__` (sync), lines 182?187: No function docstring; consult the source body and layer walkthrough.
  Calls: `super`, `super().__init__`.
- Class `NoSlotsAvailableError`, lines 190?192; bases: BusinessRuleError.
- Class `InvalidStatusTransitionError`, lines 195?202; bases: BusinessRuleError.
- `InvalidStatusTransitionError.__init__` (sync), lines 198?202: No function docstring; consult the source body and layer walkthrough.
  Calls: `super`, `super().__init__`.
- Class `OrderCancellationError`, lines 205?207; bases: BusinessRuleError.
- Class `InsufficientBalanceError`, lines 210?212; bases: BusinessRuleError.
- Class `CouponInvalidError`, lines 215?217; bases: BusinessRuleError.
- Class `CouponLimitReachedError`, lines 220?222; bases: BusinessRuleError.
- Class `PaymentVerificationError`, lines 225?228; bases: BusinessRuleError.
- Class `CODLimitExceededError`, lines 231?233; bases: BusinessRuleError.
- Class `RateLimitError`, lines 238?245; bases: DRIPException.
- `RateLimitError.__init__` (sync), lines 243?245: No function docstring; consult the source body and layer walkthrough.
  Calls: `super`, `super().__init__`.
- Class `ServerError`, lines 250?253; bases: DRIPException.
- Class `DatabaseError`, lines 256?258; bases: ServerError.
- Class `StorageError`, lines 261?263; bases: ServerError.
- Class `PaymentGatewayError`, lines 266?268; bases: ServerError.
- Class `PaymentRequiredError`, lines 271?274; bases: BusinessRuleError.
- Class `ExternalServiceError`, lines 275?278; bases: DRIPException.

## app/core/logging.py

105 lines; SHA-256 `af06a89aa0957d02e095fce6073f06d7c0c56fbea83f52f770e53e63400113f5`. [Open source](../../app/core/logging.py).

Backend imports: `app.core.config`.

- `_scrub_sensitive` (sync), lines 32?41: Remove sensitive fields from log events before they are written.
  Calls: `event_dict.keys`, `key.lower`, `list`.
- `configure_logging` (sync), lines 56?97: Call once at application startup.
  Calls: `handler.setFormatter`, `logging.StreamHandler`, `logging.getLogger`, `logging.getLogger(name).setLevel`, `root_logger.setLevel`, `structlog.configure`, `structlog.dev.ConsoleRenderer`, `structlog.processors.JSONRenderer`, `structlog.stdlib.LoggerFactory`, `structlog.stdlib.ProcessorFormatter`.
- `get_logger` (sync), lines 100?101: No function docstring; consult the source body and layer walkthrough.
  Calls: `structlog.get_logger`.

## app/core/middleware.py

229 lines; SHA-256 `0c1849e31a3bc1f7f410225e409e181008e58ca83bb10e8e32db03d1b92409f6`. [Open source](../../app/core/middleware.py).

Backend imports: `app.core.config`, `app.core.logging`, `app.core.redis`.

- Class `SecurityHeadersMiddleware`, lines 31?57; bases: BaseHTTPMiddleware.
- `SecurityHeadersMiddleware.dispatch` (async), lines 53?57: No function docstring; consult the source body and layer walkthrough.
  Calls: `call_next`, `self._HEADERS.items`.
- Class `RequestIDMiddleware`, lines 62?81; bases: BaseHTTPMiddleware.
- `RequestIDMiddleware.dispatch` (async), lines 71?81: No function docstring; consult the source body and layer walkthrough.
  Calls: `call_next`, `request.headers.get`, `str`, `structlog.contextvars.bind_contextvars`, `structlog.contextvars.clear_contextvars`, `uuid.uuid4`.
- Class `LoggingMiddleware`, lines 86?120; bases: BaseHTTPMiddleware.
- `LoggingMiddleware.dispatch` (async), lines 95?112: No function docstring; consult the source body and layer walkthrough.
  Calls: `call_next`, `getattr`, `getattr(logger, level)`, `round`, `self._get_client_ip`, `time.perf_counter_ns`.
- `LoggingMiddleware._get_client_ip` (sync), lines 115?120: No function docstring; consult the source body and layer walkthrough.
  Calls: `forwarded.split`, `forwarded.split(',')[0].strip`, `request.headers.get`.
- Class `RateLimitMiddleware`, lines 139?229; bases: BaseHTTPMiddleware.
- `RateLimitMiddleware.dispatch` (async), lines 150?194: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `call_next`, `getattr`, `int`, `logger.warning`, `max`, `self._check`, `self._get_identifier`, `self._get_limit`, `str`, `time.time`.
- `RateLimitMiddleware._get_limit` (sync), lines 197?202: No function docstring; consult the source body and layer walkthrough.
  Calls: `path.startswith`.
- `RateLimitMiddleware._get_identifier` (sync), lines 205?215: No function docstring; consult the source body and layer walkthrough.
  Calls: `forwarded.split`, `forwarded.split(',')[0].strip`, `getattr`, `request.headers.get`.
- `RateLimitMiddleware._check` (async), lines 218?229: Increment the counter and return (allowed, current_count).
  Calls: `get_redis`, `redis.expire`, `redis.incr`.

## app/core/redis.py

144 lines; SHA-256 `0da58fc4ab1567a55e652f4bf1a543bd6d5fbe0408d9787205069d08e31cb14b`. [Open source](../../app/core/redis.py).

Backend imports: `app.core.config`, `app.core.logging`.

- `init_redis` (async), lines 23?41: Create the Redis connection pool. Called at app startup.
  Calls: `_redis.ping`, `aioredis.from_url`, `logger.error`, `logger.info`, `str`.
- `close_redis` (async), lines 44?50: Close the Redis connection pool. Called at app shutdown.
  Calls: `_redis.aclose`, `logger.info`.
- `get_redis` (sync), lines 53?57: Return the module-level Redis client. Raises if not initialised.
  Calls: `RuntimeError`.
- Class `RedisKeys`, lines 62?102; bases: .
- `RedisKeys.rate_limit` (sync), lines 69?70: No function docstring; consult the source body and layer walkthrough.
- `RedisKeys.jwt_blocklist` (sync), lines 73?74: No function docstring; consult the source body and layer walkthrough.
- `RedisKeys.email_verify_token` (sync), lines 77?78: No function docstring; consult the source body and layer walkthrough.
- `RedisKeys.password_reset_token` (sync), lines 81?82: No function docstring; consult the source body and layer walkthrough.
- `RedisKeys.product_cache` (sync), lines 85?86: No function docstring; consult the source body and layer walkthrough.
- `RedisKeys.catalogue_cache` (sync), lines 89?90: No function docstring; consult the source body and layer walkthrough.
- `RedisKeys.seller_dashboard_cache` (sync), lines 93?94: No function docstring; consult the source body and layer walkthrough.
- `RedisKeys.cod_timer` (sync), lines 97?98: No function docstring; consult the source body and layer walkthrough.
- `RedisKeys.login_attempts` (sync), lines 101?102: No function docstring; consult the source body and layer walkthrough.
- `cache_get` (async), lines 107?113: Get a cached value. Returns None on miss or Redis error.
  Calls: `get_redis`, `get_redis().get`, `logger.warning`, `str`.
- `cache_set` (async), lines 116?123: Set a cache value with TTL. Returns False on error (non-fatal).
  Calls: `get_redis`, `get_redis().setex`, `logger.warning`, `str`.
- `cache_delete` (async), lines 126?131: Invalidate a cache key. Silently ignores errors.
  Calls: `get_redis`, `get_redis().delete`, `logger.warning`, `str`.
  Mutation/I-O-related call names: `get_redis().delete`.
- `cache_delete_pattern` (async), lines 134?144: Delete all keys matching a pattern. Returns count of deleted keys.
  Calls: `get_redis`, `logger.warning`, `redis.delete`, `redis.keys`, `str`.
  Mutation/I-O-related call names: `redis.delete`.

## app/core/security.py

289 lines; SHA-256 `e97b903eaef65b098b73eec274a3285dba6824954d415b82e0656e1976f90c4e`. [Open source](../../app/core/security.py).

Backend imports: `app.core.config`, `app.core.exceptions`, `app.core.logging`, `app.core.redis`.

- `hash_password` (sync), lines 54?59: Hash a password with Argon2id.
  Calls: `_hasher.hash`.
- `verify_password` (sync), lines 62?70: Verify a plain password against an Argon2id hash.
  Calls: `_hasher.verify`.
- `password_needs_rehash` (sync), lines 73?78: Returns True if the hash was created with outdated parameters.
  Calls: `_hasher.check_needs_rehash`.
- `_load_private_key` (sync), lines 83?86: No function docstring; consult the source body and layer walkthrough.
  Calls: `key.replace`.
- `_load_public_key` (sync), lines 89?91: No function docstring; consult the source body and layer walkthrough.
  Calls: `key.replace`.
- `create_access_token` (sync), lines 94?126: Create a signed RS256 access token.
  Calls: `_load_private_key`, `claims.update`, `datetime.now`, `jwt.encode`, `secrets.token_hex`, `timedelta`.
- `decode_access_token` (sync), lines 129?148: Decode and verify a JWT access token.
  Calls: `TokenExpiredError`, `TokenInvalidError`, `_load_public_key`, `jwt.decode`, `str`, `str(exc).lower`.
- `is_token_revoked` (async), lines 151?159: Check if a token's jti is on the Redis blocklist.
  Calls: `ExternalServiceError`, `RedisKeys.jwt_blocklist`, `get_redis`, `get_redis().get`.
- `revoke_token` (async), lines 162?171: Add a jti to the Redis blocklist. TTL = remaining token lifetime.
  Calls: `(expires_at - now).total_seconds`, `ExternalServiceError`, `RedisKeys.jwt_blocklist`, `datetime.now`, `get_redis`, `get_redis().setex`, `int`, `max`.
- `generate_refresh_token` (sync), lines 176?178: Generate a 64-byte URL-safe opaque refresh token.
  Calls: `secrets.token_urlsafe`.
- `hash_refresh_token` (sync), lines 181?183: SHA-256 hex digest of the token. Only the hash is stored in the DB.
  Calls: `hashlib.sha256`, `hashlib.sha256(token.encode()).hexdigest`, `token.encode`.
- `create_email_verify_token` (sync), lines 188?202: Create a short-lived (24h) JWT for email verification links.
  Calls: `create_access_token`, `datetime.now`, `timedelta`.
- `decode_email_verify_token` (sync), lines 205?216: Decode email verify token and return user_id. Raises on invalid.
  Calls: `TokenInvalidError`, `_load_public_key`, `jwt.decode`, `str`.
- `create_password_reset_token` (sync), lines 219?230: Create a short-lived (1h) password reset token.
  Calls: `create_access_token`, `datetime.now`, `timedelta`.
- `decode_password_reset_token` (sync), lines 233?244: Decode password reset token and return user_id. Raises on invalid.
  Calls: `TokenInvalidError`, `_load_public_key`, `jwt.decode`, `str`.
- `generate_totp_secret` (sync), lines 249?251: Generate a new base32 TOTP secret.
  Calls: `pyotp.random_base32`.
- `get_totp_uri` (sync), lines 254?259: Return the otpauth:// URI for QR code generation.
  Calls: `pyotp.totp.TOTP`, `pyotp.totp.TOTP(secret).provisioning_uri`.
- `verify_totp` (sync), lines 262?271: Verify a 6-digit TOTP code.
  Calls: `TwoFactorInvalidError`, `pyotp.TOTP`, `totp.verify`.
- `get_cookie_params` (sync), lines 279?289: Return secure cookie parameters for the refresh token.

## fix_migration.py

43 lines; SHA-256 `48a21cea93eda632265557ad27aa88e1b3f1c7389ac9f2834103808ab605e793`. [Open source](../../fix_migration.py).

- `main` (sync), lines 16?39: No function docstring; consult the source body and layer walkthrough.
  Calls: `Config`, `action.add_argument`, `argparse.ArgumentParser`, `command.current`, `command.upgrade`, `config.set_main_option`, `load_dotenv`, `os.environ.get`, `parser.add_argument`, `parser.add_mutually_exclusive_group`, `parser.error`, `parser.parse_args` ? (15 distinct call expressions).

## main.py

214 lines; SHA-256 `58182bbdd30bb5fa1c7ce504213383d29b2b131f30cd5c44c279d75184cf7704`. [Open source](../../main.py).

Backend imports: `app.api.v1.router`, `app.core.config`, `app.core.database`, `app.core.exceptions`, `app.core.logging`, `app.core.middleware`, `app.core.redis`.

- `lifespan` (async), lines 47?78: Manage startup and shutdown of shared resources.
  Calls: `close_db`, `close_redis`, `configure_logging`, `init_db`, `init_redis`, `logger.info`, `sentry_sdk.init`.
- `create_application` (sync), lines 83?140: No function docstring; consult the source body and layer walkthrough.
  Calls: `FastAPI`, `_register_exception_handlers`, `app.add_middleware`, `app.include_router`.
- `_register_exception_handlers` (sync), lines 143?210: Register global exception handlers that produce consistent error JSON.
  Calls: `' → '.join`, `JSONResponse`, `ServerError`, `app.exception_handler`, `exc.errors`, `exc.to_response`, `getattr`, `isinstance`, `logger.error`, `logger.exception`, `server_error.to_response`, `str`.
- `_register_exception_handlers.drip_exception_handler` (async), lines 147?165: No function docstring; consult the source body and layer walkthrough.
  Calls: `JSONResponse`, `app.exception_handler`, `exc.to_response`, `getattr`, `isinstance`, `logger.error`, `str`.
- `_register_exception_handlers.validation_exception_handler` (async), lines 168?188: Convert Pydantic validation errors to DRIP error format.
  Calls: `' → '.join`, `JSONResponse`, `app.exception_handler`, `exc.errors`, `getattr`, `str`.
- `_register_exception_handlers.unhandled_exception_handler` (async), lines 191?210: Catch-all for unexpected exceptions.
  Calls: `JSONResponse`, `ServerError`, `app.exception_handler`, `getattr`, `logger.exception`, `server_error.to_response`.

## seed_users.py

82 lines; SHA-256 `837844ab09207ce55c7bec4fcde39d19400177588f9f7706d6c9a7a54de04e01`. [Open source](../../seed_users.py).

Backend imports: `app.schemas.auth`.

- `insert_user` (async), lines 22?35: Insert a new account; never change an existing account's password or role.
  Calls: `PasswordHasher`, `PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16).hash`, `ValueError`, `connection.fetchval`, `uuid4`.
- `seed` (async), lines 38?44: No function docstring; consult the source body and layer walkthrough.
  Calls: `asyncpg.connect`, `connection.close`, `connection.transaction`, `insert_user`.
- `main` (sync), lines 47?78: No function docstring; consult the source body and layer walkthrough.
  Calls: `RegisterRequest`, `argparse.ArgumentParser`, `asyncio.run`, `getpass.getpass`, `load_dotenv`, `os.environ.get`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `print`, `seed`, `sys.stdin.readline` ? (15 distinct call expressions).


