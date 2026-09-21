"""
tests/load/locustfile.py
─────────────────────────
Locust load test scenarios for the DRIP Marketplace API.

Usage:
    # headless, 50 users, 10 spawn/sec, 2 minutes
    locust -f tests/load/locustfile.py \
        --headless -u 50 -r 10 -t 2m \
        --host http://localhost:8000

    # With web UI
    locust -f tests/load/locustfile.py --host http://localhost:8000

Scenarios:
  BrowseUser       — anonymous catalogue browsing (high volume, read-only)
  CustomerUser     — authenticated checkout flow  (medium volume)
  SellerUser       — seller dashboard + inventory (lower volume)
  AdminUser        — admin monitoring reads       (very low volume)

Environment variables (all optional):
  LOAD_TEST_CUSTOMER_EMAIL    / LOAD_TEST_CUSTOMER_PASSWORD
  LOAD_TEST_SELLER_EMAIL      / LOAD_TEST_SELLER_PASSWORD
  LOAD_TEST_ADMIN_EMAIL       / LOAD_TEST_ADMIN_PASSWORD
"""

from __future__ import annotations

import json
import os
import random
import string
from typing import Optional

from locust import HttpUser, between, events, task
from locust.contrib.fasthttp import FastHttpUser


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rnd(prefix: str = "", length: int = 8) -> str:
    return prefix + "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


PROVINCES = ["Sindh", "Punjab", "KPK", "Balochistan", "Islamabad"]

SAMPLE_ADDRESS = {
    "recipient_name": "Load Test User",
    "phone":          "03001234567",
    "street":         "House 12, Test Street, DHA Phase 4",
    "city":           "Karachi",
    "province":       "Sindh",
}


# ── Anonymous Browse User ─────────────────────────────────────────────────────

class BrowseUser(FastHttpUser):
    """
    Simulates a guest user browsing the catalogue.
    Most real traffic is this pattern: 70–80% of visits are read-only.
    Weight 70 = 70 virtual users out of every 100.
    """
    weight       = 70
    wait_time    = between(1, 4)

    @task(10)
    def browse_catalogue(self):
        """GET /products with random filters."""
        params = {"limit": 20, "sort": random.choice(["newest", "trending", "price_asc"])}
        if random.random() < 0.3:
            params["min_price"] = random.randint(500, 2000)
            params["max_price"] = random.randint(2001, 10000)
        with self.client.get("/api/v1/products", params=params, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Catalogue returned {resp.status_code}")

    @task(5)
    def search_products(self):
        queries = ["shirt", "jeans", "hoodie", "sneakers", "kurta", "abaya", "lawn"]
        q = random.choice(queries)
        self.client.get(f"/api/v1/products?q={q}&limit=20")

    @task(3)
    def search_suggestions(self):
        terms = ["sh", "je", "ho", "sn", "ku"]
        self.client.get(f"/api/v1/products/search/suggestions?q={random.choice(terms)}")

    @task(4)
    def view_product_detail(self):
        """Simulate loading a product detail page via a random slug."""
        slugs = [
            "white-cotton-kurta-summer",
            "black-slim-jeans",
            "embroidered-lawn-suit",
            "graphic-hoodie-drip",
        ]
        slug = random.choice(slugs)
        with self.client.get(f"/api/v1/products/slug/{slug}", catch_response=True) as resp:
            if resp.status_code in {200, 404}:
                resp.success()
            else:
                resp.failure(f"Product detail {resp.status_code}")

    @task(2)
    def health_check(self):
        self.client.get("/api/v1/health")


# ── Authenticated Customer User ───────────────────────────────────────────────

class CustomerUser(FastHttpUser):
    """
    Simulates a logged-in customer browsing, adding to cart, and checking out.
    Weight 25 = 25 virtual users out of every 100.
    """
    weight    = 25
    wait_time = between(2, 6)

    def on_start(self):
        """Log in at the start of each virtual user session."""
        email    = os.getenv("LOAD_TEST_CUSTOMER_EMAIL", f"loadtest_{_rnd()}@drip.test")
        password = os.getenv("LOAD_TEST_CUSTOMER_PASSWORD", "LoadTest123")

        # Register if no fixed credentials
        if "loadtest_" in email:
            self.client.post(
                "/api/v1/auth/register",
                json={
                    "first_name": "Load",
                    "last_name":  "Tester",
                    "email":      email,
                    "password":   password,
                },
            )

        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token", "")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(8)
    def browse_catalogue(self):
        self.client.get("/api/v1/products?limit=20", headers=self.headers)

    @task(4)
    def view_product(self):
        # Use a random UUID; 404s are expected and marked success
        from uuid import uuid4
        with self.client.get(
            f"/api/v1/products/{uuid4()}",
            headers=self.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code in {200, 404}:
                resp.success()

    @task(3)
    def view_my_orders(self):
        self.client.get("/api/v1/orders", headers=self.headers)

    @task(2)
    def view_profile(self):
        self.client.get("/api/v1/customers/me", headers=self.headers)

    @task(2)
    def view_wishlist(self):
        self.client.get("/api/v1/customers/me/wishlist", headers=self.headers)

    @task(1)
    def view_cart(self):
        self.client.get("/api/v1/cart", headers=self.headers)

    @task(1)
    def view_notifications(self):
        self.client.get("/api/v1/notifications", headers=self.headers)


# ── Seller User ───────────────────────────────────────────────────────────────

class SellerUser(FastHttpUser):
    """
    Simulates a seller checking their dashboard, orders, and inventory.
    Weight 4 = 4 virtual users out of every 100.
    """
    weight    = 4
    wait_time = between(3, 8)

    def on_start(self):
        email    = os.getenv("LOAD_TEST_SELLER_EMAIL", f"seller_{_rnd()}@drip.test")
        password = os.getenv("LOAD_TEST_SELLER_PASSWORD", "SellerTest123")

        if "seller_" in email:
            self.client.post(
                "/api/v1/seller/register",
                json={
                    "email":          email,
                    "password":       password,
                    "first_name":     "Load",
                    "brand_name":     f"Brand {_rnd()}",
                    "description":    "Load test seller brand",
                    "return_policy":  "No returns",
                    "whatsapp_number": "03001234567",
                    "extra_slots":    0,
                },
            )

        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token", "")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(5)
    def view_seller_dashboard(self):
        self.client.get(
            "/api/v1/seller/dashboard?period=month",
            headers=self.headers,
        )

    @task(4)
    def list_seller_orders(self):
        self.client.get("/api/v1/seller/orders", headers=self.headers)

    @task(3)
    def view_inventory(self):
        self.client.get("/api/v1/seller/inventory", headers=self.headers)

    @task(2)
    def view_low_stock(self):
        self.client.get("/api/v1/seller/inventory/low-stock", headers=self.headers)

    @task(2)
    def view_seller_profile(self):
        self.client.get("/api/v1/seller/me", headers=self.headers)

    @task(1)
    def view_wallet_balance(self):
        self.client.get("/api/v1/wallet/balance", headers=self.headers)

    @task(1)
    def view_bank_accounts(self):
        self.client.get("/api/v1/seller/bank-accounts", headers=self.headers)


# ── Admin User ────────────────────────────────────────────────────────────────

class AdminUser(FastHttpUser):
    """
    Simulates an admin reviewing the dashboard and order queues.
    Weight 1 = 1 virtual user out of every 100.
    """
    weight    = 1
    wait_time = between(5, 15)

    def on_start(self):
        email    = os.getenv("LOAD_TEST_ADMIN_EMAIL",    "admin@drip.pk")
        password = os.getenv("LOAD_TEST_ADMIN_PASSWORD", "AdminTest123")
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token", "")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(4)
    def view_admin_dashboard(self):
        self.client.get("/api/v1/admin/dashboard", headers=self.headers)

    @task(3)
    def view_admin_orders(self):
        self.client.get("/api/v1/admin/orders", headers=self.headers)

    @task(2)
    def view_cod_queue(self):
        self.client.get("/api/v1/admin/cod-queue", headers=self.headers)

    @task(2)
    def view_admin_inventory(self):
        self.client.get("/api/v1/admin/inventory", headers=self.headers)

    @task(1)
    def view_payouts(self):
        self.client.get("/api/v1/admin/payouts", headers=self.headers)


# ── Locust event hooks ────────────────────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(
        "\n🔥 DRIP Load Test Starting\n"
        "   Scenarios: BrowseUser(70%) | CustomerUser(25%) | SellerUser(4%) | AdminUser(1%)\n"
        f"   Target: {environment.host}\n"
    )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    print(
        "\n✅ DRIP Load Test Complete\n"
        f"   Total requests : {stats.total.num_requests}\n"
        f"   Total failures : {stats.total.num_failures}\n"
        f"   Failure rate   : {stats.total.fail_ratio * 100:.1f}%\n"
        f"   Median RPS     : {stats.total.current_rps:.1f}\n"
        f"   p50 latency    : {stats.total.get_response_time_percentile(0.5):.0f} ms\n"
        f"   p95 latency    : {stats.total.get_response_time_percentile(0.95):.0f} ms\n"
        f"   p99 latency    : {stats.total.get_response_time_percentile(0.99):.0f} ms\n"
    )

    # Fail CI if error rate > 1%
    if stats.total.fail_ratio > 0.01:
        print(f"❌ FAIL: Error rate {stats.total.fail_ratio * 100:.1f}% exceeds 1% threshold")
        environment.process_exit_code = 1
    else:
        print("✅ PASS: Error rate within acceptable limits")
