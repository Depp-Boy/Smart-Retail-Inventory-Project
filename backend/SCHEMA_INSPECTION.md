# Supabase PostgreSQL Database Schema Inspection Report

**Generated at:** `2026-11-08 18:49:09 UTC`  
**Inspection Engine:** SQLAlchemy 2.x + Psycopg 3 via PostgreSQL Information Schema  

> [!NOTE]
> **Database Connection Verified:** Connected via `psycopg` dialect in 6226.65ms.

## 1. Discovered Tables Summary

- **Total Tables Discovered:** `18`
- **Total Columns Across All Tables:** `126`
- **Total Foreign Key Relationships:** `35`

### Table Verification Checklist

| Expected Table Name | Discovered in Database | Actual Case in DB | Status |
|---|---|---|---|
| `LOCATIONS` | `Yes` | `locations` | FOUND |
| `USERS` | `Yes` | `users` | FOUND |
| `SHOP_WAREHOUSE` | `Yes` | `shop_warehouse` | FOUND |
| `ALERTS` | `Yes` | `alerts` | FOUND |
| `PRODUCTS` | `Yes` | `products` | FOUND |
| `INVENTORY` | `Yes` | `inventory` | FOUND |
| `FORECASTS` | `Yes` | `forecasts` | FOUND |
| `SALES` | `Yes` | `sales` | FOUND |
| `SALE_ITEMS` | `Yes` | `sale_items` | FOUND |
| `ORDERS` | `Yes` | `orders` | FOUND |
| `ORDER_ITEMS` | `Yes` | `order_items` | FOUND |
| `DISPATCHES` | `Yes` | `dispatches` | FOUND |
| `ORDER_ALLOCATIONS` | `Yes` | `order_allocations` | FOUND |
| `WORKER_TASKS` | `Yes` | `worker_tasks` | FOUND |
| `DISPATCH_ITEMS` | `Yes` | `dispatch_items` | FOUND |
| `STOCK_RESERVATIONS` | `Yes` | `stock_reservations` | FOUND |
| `WORKER_TASK_ITEMS` | `Yes` | `worker_task_items` | FOUND |
| `STOCK_TRANSFERS` | `Yes` | `stock_transfers` | FOUND |

**Matches:** `18 / 18` expected tables found.

## 2. Table-by-Table Specifications

### Table: `alerts`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `alert_id` | `bigint` | `NO` | `None` | PK |
| `location_id` | `bigint` | `NO` | `None` |  |
| `product_id` | `bigint` | `YES` | `None` |  |
| `alert_type` | `character varying` | `NO` | `None` |  |
| `message` | `text` | `NO` | `None` |  |
| `created_at` | `timestamp with time zone` | `NO` | `now()` |  |
| `status` | `character varying` | `NO` | `'UNREAD'::character varying` |  |
| `user_id` | `bigint` | `YES` | `None` |  |

- **Primary Key:** `alert_id`
- **Foreign Keys:**
  - `location_id` -> `locations(location_id)` (Constraint: `fk_alert_location`)
  - `product_id` -> `products(product_id)` (Constraint: `fk_alert_product`)
  - `user_id` -> `users(user_id)` (Constraint: `fk_alert_user`)
- **Check Constraints:**
  - `2200_17888_1_not_null`: `alert_id IS NOT NULL`
  - `2200_17888_2_not_null`: `location_id IS NOT NULL`
  - `2200_17888_4_not_null`: `alert_type IS NOT NULL`
  - `2200_17888_5_not_null`: `message IS NOT NULL`
  - `2200_17888_6_not_null`: `created_at IS NOT NULL`
  - `2200_17888_7_not_null`: `status IS NOT NULL`
  - `chk_alert_status`: `((status)::text = ANY ((ARRAY['UNREAD'::character varying, 'READ'::character varying, 'DISMISSED'::character varying])::text[]))`
- **Indexes:**
  - `alerts_pkey`: `CREATE UNIQUE INDEX alerts_pkey ON public.alerts USING btree (alert_id)`
  - `idx_alerts_user_id`: `CREATE INDEX idx_alerts_user_id ON public.alerts USING btree (user_id)`

---

### Table: `dispatch_items`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `dispatch_item_id` | `bigint` | `NO` | `None` | PK |
| `dispatch_id` | `bigint` | `NO` | `None` |  |
| `allocation_id` | `bigint` | `NO` | `None` |  |
| `product_id` | `bigint` | `NO` | `None` |  |
| `quantity` | `numeric` | `NO` | `None` |  |

- **Primary Key:** `dispatch_item_id`
- **Foreign Keys:**
  - `allocation_id` -> `order_allocations(allocation_id)` (Constraint: `fk_dispatch_item_allocation`)
  - `dispatch_id` -> `dispatches(dispatch_id)` (Constraint: `fk_dispatch_item_dispatch`)
  - `product_id` -> `products(product_id)` (Constraint: `fk_dispatch_item_product`)
- **Unique Constraints:**
  - `allocation_id, dispatch_id` (Name: `uq_dispatch_allocation`)
- **Check Constraints:**
  - `2200_18051_1_not_null`: `dispatch_item_id IS NOT NULL`
  - `2200_18051_2_not_null`: `dispatch_id IS NOT NULL`
  - `2200_18051_3_not_null`: `allocation_id IS NOT NULL`
  - `2200_18051_4_not_null`: `product_id IS NOT NULL`
  - `2200_18051_5_not_null`: `quantity IS NOT NULL`
  - `chk_dispatch_item_quantity`: `(quantity > (0)::numeric)`
- **Indexes:**
  - `dispatch_items_pkey`: `CREATE UNIQUE INDEX dispatch_items_pkey ON public.dispatch_items USING btree (dispatch_item_id)`
  - `uq_dispatch_allocation`: `CREATE UNIQUE INDEX uq_dispatch_allocation ON public.dispatch_items USING btree (dispatch_id, allocation_id)`

---

### Table: `dispatches`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `dispatch_id` | `bigint` | `NO` | `None` | PK |
| `dispatch_code` | `character varying` | `NO` | `None` |  |
| `order_id` | `bigint` | `NO` | `None` |  |
| `source_location_id` | `bigint` | `NO` | `None` |  |
| `created_by_user_id` | `bigint` | `NO` | `None` |  |
| `status` | `character varying` | `NO` | `'PENDING'::character varying` |  |
| `dispatch_date` | `timestamp with time zone` | `YES` | `None` |  |
| `tracking_reference` | `character varying` | `YES` | `None` |  |
| `notes` | `text` | `YES` | `None` |  |
| `created_at` | `timestamp with time zone` | `NO` | `now()` |  |

- **Primary Key:** `dispatch_id`
- **Foreign Keys:**
  - `created_by_user_id` -> `users(user_id)` (Constraint: `fk_dispatch_creator`)
  - `order_id` -> `orders(order_id)` (Constraint: `fk_dispatch_order`)
  - `source_location_id` -> `locations(location_id)` (Constraint: `fk_dispatch_source`)
- **Unique Constraints:**
  - `dispatch_code` (Name: `dispatches_dispatch_code_key`)
- **Check Constraints:**
  - `2200_17965_10_not_null`: `created_at IS NOT NULL`
  - `2200_17965_1_not_null`: `dispatch_id IS NOT NULL`
  - `2200_17965_2_not_null`: `dispatch_code IS NOT NULL`
  - `2200_17965_3_not_null`: `order_id IS NOT NULL`
  - `2200_17965_4_not_null`: `source_location_id IS NOT NULL`
  - `2200_17965_5_not_null`: `created_by_user_id IS NOT NULL`
  - `2200_17965_6_not_null`: `status IS NOT NULL`
  - `chk_dispatch_status`: `((status)::text = ANY ((ARRAY['PENDING'::character varying, 'PACKING'::character varying, 'READY'::character varying, 'IN_TRANSIT'::character varying, 'DELIVERED'::character varying, 'CANCELLED'::character varying])::text[]))`
- **Indexes:**
  - `dispatches_dispatch_code_key`: `CREATE UNIQUE INDEX dispatches_dispatch_code_key ON public.dispatches USING btree (dispatch_code)`
  - `dispatches_pkey`: `CREATE UNIQUE INDEX dispatches_pkey ON public.dispatches USING btree (dispatch_id)`

---

### Table: `forecasts`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `forecast_id` | `bigint` | `NO` | `None` | PK |
| `shop_id` | `bigint` | `NO` | `None` |  |
| `product_id` | `bigint` | `NO` | `None` |  |
| `forecasted_demand` | `numeric` | `NO` | `None` |  |
| `forecast_period` | `date` | `NO` | `None` |  |
| `model_used` | `character varying` | `NO` | `None` |  |
| `generated_at` | `timestamp with time zone` | `NO` | `now()` |  |

- **Primary Key:** `forecast_id`
- **Foreign Keys:**
  - `product_id` -> `products(product_id)` (Constraint: `fk_forecast_product`)
  - `shop_id` -> `locations(location_id)` (Constraint: `fk_forecast_shop`)
- **Unique Constraints:**
  - `shop_id, product_id, forecast_period, generated_at` (Name: `uq_shop_product_forecast`)
- **Check Constraints:**
  - `2200_17868_1_not_null`: `forecast_id IS NOT NULL`
  - `2200_17868_2_not_null`: `shop_id IS NOT NULL`
  - `2200_17868_3_not_null`: `product_id IS NOT NULL`
  - `2200_17868_4_not_null`: `forecasted_demand IS NOT NULL`
  - `2200_17868_5_not_null`: `forecast_period IS NOT NULL`
  - `2200_17868_6_not_null`: `model_used IS NOT NULL`
  - `2200_17868_7_not_null`: `generated_at IS NOT NULL`
  - `chk_forecast_demand`: `(forecasted_demand >= (0)::numeric)`
- **Indexes:**
  - `forecasts_pkey`: `CREATE UNIQUE INDEX forecasts_pkey ON public.forecasts USING btree (forecast_id)`
  - `uq_shop_product_forecast`: `CREATE UNIQUE INDEX uq_shop_product_forecast ON public.forecasts USING btree (shop_id, product_id, forecast_period, generated_at)`

---

### Table: `inventory`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `inventory_id` | `bigint` | `NO` | `None` | PK |
| `location_id` | `bigint` | `NO` | `None` |  |
| `product_id` | `bigint` | `NO` | `None` |  |
| `quantity` | `numeric` | `NO` | `0` |  |
| `reserved_quantity` | `numeric` | `NO` | `0` |  |
| `last_updated` | `timestamp with time zone` | `NO` | `now()` |  |

- **Primary Key:** `inventory_id`
- **Foreign Keys:**
  - `location_id` -> `locations(location_id)` (Constraint: `fk_inventory_location`)
  - `product_id` -> `products(product_id)` (Constraint: `fk_inventory_product`)
- **Unique Constraints:**
  - `product_id, location_id` (Name: `uq_location_product`)
- **Check Constraints:**
  - `2200_17661_1_not_null`: `inventory_id IS NOT NULL`
  - `2200_17661_2_not_null`: `location_id IS NOT NULL`
  - `2200_17661_3_not_null`: `product_id IS NOT NULL`
  - `2200_17661_4_not_null`: `quantity IS NOT NULL`
  - `2200_17661_5_not_null`: `reserved_quantity IS NOT NULL`
  - `2200_17661_6_not_null`: `last_updated IS NOT NULL`
  - `chk_inventory_quantity`: `(quantity >= (0)::numeric)`
  - `chk_reserved_not_exceed_stock`: `(reserved_quantity <= quantity)`
  - `chk_reserved_quantity`: `(reserved_quantity >= (0)::numeric)`
  - `chk_reserved_quantity`: `(quantity_reserved > (0)::numeric)`
- **Indexes:**
  - `inventory_pkey`: `CREATE UNIQUE INDEX inventory_pkey ON public.inventory USING btree (inventory_id)`
  - `uq_location_product`: `CREATE UNIQUE INDEX uq_location_product ON public.inventory USING btree (location_id, product_id)`

---

### Table: `locations`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `location_id` | `bigint` | `NO` | `None` | PK |
| `location_name` | `character varying` | `NO` | `None` |  |
| `location_type` | `character varying` | `NO` | `None` |  |
| `address` | `text` | `NO` | `None` |  |
| `parent_location_id` | `bigint` | `YES` | `None` |  |

- **Primary Key:** `location_id`
- **Foreign Keys:**
  - `parent_location_id` -> `locations(location_id)` (Constraint: `fk_parent_location`)
- **Check Constraints:**
  - `2200_17606_1_not_null`: `location_id IS NOT NULL`
  - `2200_17606_2_not_null`: `location_name IS NOT NULL`
  - `2200_17606_3_not_null`: `location_type IS NOT NULL`
  - `2200_17606_4_not_null`: `address IS NOT NULL`
  - `locations_location_type_check`: `((location_type)::text = ANY ((ARRAY['MAIN_WAREHOUSE'::character varying, 'SUB_WAREHOUSE'::character varying, 'SHOP'::character varying])::text[]))`
- **Indexes:**
  - `locations_pkey`: `CREATE UNIQUE INDEX locations_pkey ON public.locations USING btree (location_id)`

---

### Table: `order_allocations`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `allocation_id` | `bigint` | `NO` | `None` | PK |
| `order_item_id` | `bigint` | `NO` | `None` |  |
| `source_location_id` | `bigint` | `NO` | `None` |  |
| `allocated_quantity` | `numeric` | `NO` | `None` |  |
| `status` | `character varying` | `NO` | `'ALLOCATED'::character varying` |  |

- **Primary Key:** `allocation_id`
- **Foreign Keys:**
  - `order_item_id` -> `order_items(order_item_id)` (Constraint: `fk_allocation_order_item`)
  - `source_location_id` -> `locations(location_id)` (Constraint: `fk_allocation_warehouse`)
- **Check Constraints:**
  - `2200_17803_1_not_null`: `allocation_id IS NOT NULL`
  - `2200_17803_2_not_null`: `order_item_id IS NOT NULL`
  - `2200_17803_3_not_null`: `source_location_id IS NOT NULL`
  - `2200_17803_4_not_null`: `allocated_quantity IS NOT NULL`
  - `2200_17803_5_not_null`: `status IS NOT NULL`
  - `chk_allocation_quantity`: `(allocated_quantity > (0)::numeric)`
  - `chk_allocation_status`: `((status)::text = ANY ((ARRAY['ALLOCATED'::character varying, 'RESERVED'::character varying, 'DISPATCHED'::character varying, 'DELIVERED'::character varying, 'CANCELLED'::character varying])::text[]))`
- **Indexes:**
  - `order_allocations_pkey`: `CREATE UNIQUE INDEX order_allocations_pkey ON public.order_allocations USING btree (allocation_id)`

---

### Table: `order_items`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `order_item_id` | `bigint` | `NO` | `None` | PK |
| `order_id` | `bigint` | `NO` | `None` |  |
| `product_id` | `bigint` | `NO` | `None` |  |
| `quantity_requested` | `numeric` | `NO` | `None` |  |
| `quantity_allocated` | `numeric` | `NO` | `0` |  |

- **Primary Key:** `order_item_id`
- **Foreign Keys:**
  - `order_id` -> `orders(order_id)` (Constraint: `fk_order_items_order`)
  - `product_id` -> `products(product_id)` (Constraint: `fk_order_items_product`)
- **Unique Constraints:**
  - `order_id, product_id` (Name: `uq_order_product`)
- **Check Constraints:**
  - `2200_17775_1_not_null`: `order_item_id IS NOT NULL`
  - `2200_17775_2_not_null`: `order_id IS NOT NULL`
  - `2200_17775_3_not_null`: `product_id IS NOT NULL`
  - `2200_17775_4_not_null`: `quantity_requested IS NOT NULL`
  - `2200_17775_5_not_null`: `quantity_allocated IS NOT NULL`
  - `chk_allocated_quantity`: `((quantity_allocated >= (0)::numeric) AND (quantity_allocated <= quantity_requested))`
  - `chk_requested_quantity`: `(quantity_requested > (0)::numeric)`
- **Indexes:**
  - `order_items_pkey`: `CREATE UNIQUE INDEX order_items_pkey ON public.order_items USING btree (order_item_id)`
  - `uq_order_product`: `CREATE UNIQUE INDEX uq_order_product ON public.order_items USING btree (order_id, product_id)`

---

### Table: `orders`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `order_id` | `bigint` | `NO` | `None` | PK |
| `shop_id` | `bigint` | `NO` | `None` |  |
| `order_date` | `timestamp with time zone` | `NO` | `now()` |  |
| `status` | `character varying` | `NO` | `'PENDING'::character varying` |  |
| `total_amount` | `numeric` | `NO` | `0` |  |
| `expected_delivery` | `timestamp with time zone` | `YES` | `None` |  |

- **Primary Key:** `order_id`
- **Foreign Keys:**
  - `shop_id` -> `locations(location_id)` (Constraint: `fk_orders_shop`)
- **Check Constraints:**
  - `2200_17759_1_not_null`: `order_id IS NOT NULL`
  - `2200_17759_2_not_null`: `shop_id IS NOT NULL`
  - `2200_17759_3_not_null`: `order_date IS NOT NULL`
  - `2200_17759_4_not_null`: `status IS NOT NULL`
  - `2200_17759_5_not_null`: `total_amount IS NOT NULL`
  - `chk_order_status`: `((status)::text = ANY ((ARRAY['PENDING'::character varying, 'PROCESSING'::character varying, 'PARTIALLY_FULFILLED'::character varying, 'FULFILLED'::character varying, 'REJECTED'::character varying, 'CANCELLED'::character varying])::text[]))`
  - `chk_order_total`: `(total_amount >= (0)::numeric)`
- **Indexes:**
  - `orders_pkey`: `CREATE UNIQUE INDEX orders_pkey ON public.orders USING btree (order_id)`

---

### Table: `products`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `product_id` | `bigint` | `NO` | `None` | PK |
| `product_name` | `character varying` | `NO` | `None` |  |
| `category` | `character varying` | `YES` | `None` |  |
| `unit` | `character varying` | `NO` | `None` |  |
| `price` | `numeric` | `NO` | `0` |  |
| `reorder_threshold` | `numeric` | `NO` | `0` |  |
| `sku` | `character varying` | `YES` | `None` |  |
| `cost_price` | `numeric` | `YES` | `None` |  |
| `description` | `text` | `YES` | `None` |  |
| `storage_conditions` | `text` | `YES` | `None` |  |

- **Primary Key:** `product_id`
- **Foreign Keys:** None
- **Check Constraints:**
  - `2200_17651_1_not_null`: `product_id IS NOT NULL`
  - `2200_17651_2_not_null`: `product_name IS NOT NULL`
  - `2200_17651_4_not_null`: `unit IS NOT NULL`
  - `2200_17651_5_not_null`: `price IS NOT NULL`
  - `2200_17651_6_not_null`: `reorder_threshold IS NOT NULL`
  - `chk_product_cost_price`: `((cost_price IS NULL) OR (cost_price >= (0)::numeric))`
  - `chk_product_price`: `(price >= (0)::numeric)`
  - `chk_reorder_threshold`: `(reorder_threshold >= (0)::numeric)`
- **Indexes:**
  - `products_pkey`: `CREATE UNIQUE INDEX products_pkey ON public.products USING btree (product_id)`
  - `uq_products_sku`: `CREATE UNIQUE INDEX uq_products_sku ON public.products USING btree (sku) WHERE (sku IS NOT NULL)`

---

### Table: `sale_items`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `sale_item_id` | `bigint` | `NO` | `None` | PK |
| `sale_id` | `bigint` | `NO` | `None` |  |
| `product_id` | `bigint` | `NO` | `None` |  |
| `quantity` | `numeric` | `NO` | `None` |  |
| `unit_price` | `numeric` | `NO` | `None` |  |

- **Primary Key:** `sale_item_id`
- **Foreign Keys:**
  - `product_id` -> `products(product_id)` (Constraint: `fk_sale_items_product`)
  - `sale_id` -> `sales(sale_id)` (Constraint: `fk_sale_items_sale`)
- **Check Constraints:**
  - `2200_17732_1_not_null`: `sale_item_id IS NOT NULL`
  - `2200_17732_2_not_null`: `sale_id IS NOT NULL`
  - `2200_17732_3_not_null`: `product_id IS NOT NULL`
  - `2200_17732_4_not_null`: `quantity IS NOT NULL`
  - `2200_17732_5_not_null`: `unit_price IS NOT NULL`
  - `chk_sale_item_price`: `(unit_price >= (0)::numeric)`
  - `chk_sale_item_quantity`: `(quantity > (0)::numeric)`
- **Indexes:**
  - `sale_items_pkey`: `CREATE UNIQUE INDEX sale_items_pkey ON public.sale_items USING btree (sale_item_id)`

---

### Table: `sales`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `sale_id` | `bigint` | `NO` | `None` | PK |
| `shop_id` | `bigint` | `NO` | `None` |  |
| `sale_date` | `timestamp with time zone` | `NO` | `now()` |  |
| `total_amount` | `numeric` | `NO` | `0` |  |
| `customer_name` | `character varying` | `YES` | `None` |  |
| `customer_phone` | `character varying` | `YES` | `None` |  |
| `payment_method` | `character varying` | `YES` | `None` |  |
| `subtotal` | `numeric` | `NO` | `0` |  |
| `tax_amount` | `numeric` | `NO` | `0` |  |
| `discount_amount` | `numeric` | `NO` | `0` |  |
| `status` | `character varying` | `NO` | `'COMPLETED'::character varying` |  |

- **Primary Key:** `sale_id`
- **Foreign Keys:**
  - `shop_id` -> `locations(location_id)` (Constraint: `fk_sales_shop`)
- **Check Constraints:**
  - `2200_17718_10_not_null`: `discount_amount IS NOT NULL`
  - `2200_17718_11_not_null`: `status IS NOT NULL`
  - `2200_17718_1_not_null`: `sale_id IS NOT NULL`
  - `2200_17718_2_not_null`: `shop_id IS NOT NULL`
  - `2200_17718_3_not_null`: `sale_date IS NOT NULL`
  - `2200_17718_4_not_null`: `total_amount IS NOT NULL`
  - `2200_17718_8_not_null`: `subtotal IS NOT NULL`
  - `2200_17718_9_not_null`: `tax_amount IS NOT NULL`
  - `chk_sales_discount`: `(discount_amount >= (0)::numeric)`
  - `chk_sales_payment_method`: `((payment_method IS NULL) OR ((payment_method)::text = ANY ((ARRAY['CASH'::character varying, 'UPI'::character varying, 'CARD'::character varying, 'OTHER'::character varying])::text[])))`
  - `chk_sales_status`: `((status)::text = ANY ((ARRAY['COMPLETED'::character varying, 'CANCELLED'::character varying, 'REFUNDED'::character varying])::text[]))`
  - `chk_sales_subtotal`: `(subtotal >= (0)::numeric)`
  - `chk_sales_tax`: `(tax_amount >= (0)::numeric)`
  - `chk_sales_total`: `(total_amount >= (0)::numeric)`
- **Indexes:**
  - `sales_pkey`: `CREATE UNIQUE INDEX sales_pkey ON public.sales USING btree (sale_id)`

---

### Table: `shop_warehouse`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `relationship_id` | `bigint` | `NO` | `None` | PK |
| `shop_id` | `bigint` | `NO` | `None` |  |
| `warehouse_id` | `bigint` | `NO` | `None` |  |
| `is_preferred` | `boolean` | `NO` | `false` |  |
| `priority` | `integer` | `NO` | `1` |  |

- **Primary Key:** `relationship_id`
- **Foreign Keys:**
  - `shop_id` -> `locations(location_id)` (Constraint: `fk_shop`)
  - `warehouse_id` -> `locations(location_id)` (Constraint: `fk_warehouse`)
- **Unique Constraints:**
  - `warehouse_id, shop_id` (Name: `uq_shop_warehouse`)
- **Check Constraints:**
  - `2200_17686_1_not_null`: `relationship_id IS NOT NULL`
  - `2200_17686_2_not_null`: `shop_id IS NOT NULL`
  - `2200_17686_3_not_null`: `warehouse_id IS NOT NULL`
  - `2200_17686_4_not_null`: `is_preferred IS NOT NULL`
  - `2200_17686_5_not_null`: `priority IS NOT NULL`
  - `chk_priority`: `(priority > 0)`
  - `chk_shop_warehouse_different`: `(shop_id <> warehouse_id)`
- **Indexes:**
  - `shop_warehouse_pkey`: `CREATE UNIQUE INDEX shop_warehouse_pkey ON public.shop_warehouse USING btree (relationship_id)`
  - `uq_one_preferred_warehouse_per_shop`: `CREATE UNIQUE INDEX uq_one_preferred_warehouse_per_shop ON public.shop_warehouse USING btree (shop_id) WHERE (is_preferred = true)`
  - `uq_shop_warehouse`: `CREATE UNIQUE INDEX uq_shop_warehouse ON public.shop_warehouse USING btree (shop_id, warehouse_id)`

---

### Table: `stock_reservations`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `reservation_id` | `bigint` | `NO` | `None` | PK |
| `allocation_id` | `bigint` | `NO` | `None` |  |
| `quantity_reserved` | `numeric` | `NO` | `None` |  |
| `reserved_at` | `timestamp with time zone` | `NO` | `now()` |  |
| `expires_at` | `timestamp with time zone` | `YES` | `None` |  |
| `status` | `character varying` | `NO` | `'ACTIVE'::character varying` |  |

- **Primary Key:** `reservation_id`
- **Foreign Keys:**
  - `allocation_id` -> `order_allocations(allocation_id)` (Constraint: `fk_reservation_allocation`)
- **Check Constraints:**
  - `2200_17826_1_not_null`: `reservation_id IS NOT NULL`
  - `2200_17826_2_not_null`: `allocation_id IS NOT NULL`
  - `2200_17826_3_not_null`: `quantity_reserved IS NOT NULL`
  - `2200_17826_4_not_null`: `reserved_at IS NOT NULL`
  - `2200_17826_6_not_null`: `status IS NOT NULL`
  - `chk_reservation_expiry`: `((expires_at IS NULL) OR (expires_at > reserved_at))`
  - `chk_reservation_status`: `((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'CONFIRMED'::character varying, 'RELEASED'::character varying, 'EXPIRED'::character varying])::text[]))`
  - `chk_reserved_quantity`: `(quantity_reserved > (0)::numeric)`
  - `chk_reserved_quantity`: `(reserved_quantity >= (0)::numeric)`
- **Indexes:**
  - `stock_reservations_pkey`: `CREATE UNIQUE INDEX stock_reservations_pkey ON public.stock_reservations USING btree (reservation_id)`

---

### Table: `stock_transfers`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `transfer_id` | `bigint` | `NO` | `None` | PK |
| `source_location_id` | `bigint` | `NO` | `None` |  |
| `destination_location_id` | `bigint` | `NO` | `None` |  |
| `product_id` | `bigint` | `NO` | `None` |  |
| `quantity` | `numeric` | `NO` | `None` |  |
| `transfer_date` | `timestamp with time zone` | `NO` | `now()` |  |
| `status` | `character varying` | `NO` | `'PENDING'::character varying` |  |

- **Primary Key:** `transfer_id`
- **Foreign Keys:**
  - `destination_location_id` -> `locations(location_id)` (Constraint: `fk_transfer_destination`)
  - `product_id` -> `products(product_id)` (Constraint: `fk_transfer_product`)
  - `source_location_id` -> `locations(location_id)` (Constraint: `fk_transfer_source`)
- **Check Constraints:**
  - `2200_17842_1_not_null`: `transfer_id IS NOT NULL`
  - `2200_17842_2_not_null`: `source_location_id IS NOT NULL`
  - `2200_17842_3_not_null`: `destination_location_id IS NOT NULL`
  - `2200_17842_4_not_null`: `product_id IS NOT NULL`
  - `2200_17842_5_not_null`: `quantity IS NOT NULL`
  - `2200_17842_6_not_null`: `transfer_date IS NOT NULL`
  - `2200_17842_7_not_null`: `status IS NOT NULL`
  - `chk_transfer_locations`: `(source_location_id <> destination_location_id)`
  - `chk_transfer_quantity`: `(quantity > (0)::numeric)`
  - `chk_transfer_status`: `((status)::text = ANY ((ARRAY['PENDING'::character varying, 'IN_TRANSIT'::character varying, 'COMPLETED'::character varying, 'CANCELLED'::character varying])::text[]))`
- **Indexes:**
  - `stock_transfers_pkey`: `CREATE UNIQUE INDEX stock_transfers_pkey ON public.stock_transfers USING btree (transfer_id)`

---

### Table: `users`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `user_id` | `bigint` | `NO` | `None` | PK |
| `name` | `character varying` | `NO` | `None` |  |
| `email` | `character varying` | `NO` | `None` |  |
| `password_hash` | `character varying` | `NO` | `None` |  |
| `role` | `character varying` | `NO` | `None` |  |
| `location_id` | `bigint` | `YES` | `None` |  |
| `phone` | `character varying` | `YES` | `None` |  |

- **Primary Key:** `user_id`
- **Foreign Keys:**
  - `location_id` -> `locations(location_id)` (Constraint: `fk_user_location`)
- **Unique Constraints:**
  - `email` (Name: `users_email_key`)
- **Check Constraints:**
  - `2200_17623_1_not_null`: `user_id IS NOT NULL`
  - `2200_17623_2_not_null`: `name IS NOT NULL`
  - `2200_17623_3_not_null`: `email IS NOT NULL`
  - `2200_17623_4_not_null`: `password_hash IS NOT NULL`
  - `2200_17623_5_not_null`: `role IS NOT NULL`
  - `users_role_check`: `((role)::text = ANY ((ARRAY['SHOP_OWNER'::character varying, 'WAREHOUSE_MANAGER'::character varying, 'WAREHOUSE_WORKER'::character varying, 'ADMIN'::character varying])::text[]))`
- **Indexes:**
  - `users_email_key`: `CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email)`
  - `users_pkey`: `CREATE UNIQUE INDEX users_pkey ON public.users USING btree (user_id)`

---

### Table: `worker_task_items`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `task_item_id` | `bigint` | `NO` | `None` | PK |
| `task_id` | `bigint` | `NO` | `None` |  |
| `product_id` | `bigint` | `NO` | `None` |  |
| `quantity` | `numeric` | `NO` | `None` |  |
| `completed_quantity` | `numeric` | `NO` | `0` |  |

- **Primary Key:** `task_item_id`
- **Foreign Keys:**
  - `product_id` -> `products(product_id)` (Constraint: `fk_task_item_product`)
  - `task_id` -> `worker_tasks(task_id)` (Constraint: `fk_task_item_task`)
- **Unique Constraints:**
  - `task_id, product_id` (Name: `uq_task_product`)
- **Check Constraints:**
  - `2200_18030_1_not_null`: `task_item_id IS NOT NULL`
  - `2200_18030_2_not_null`: `task_id IS NOT NULL`
  - `2200_18030_3_not_null`: `product_id IS NOT NULL`
  - `2200_18030_4_not_null`: `quantity IS NOT NULL`
  - `2200_18030_5_not_null`: `completed_quantity IS NOT NULL`
  - `chk_completed_quantity`: `((completed_quantity >= (0)::numeric) AND (completed_quantity <= quantity))`
  - `chk_task_item_quantity`: `(quantity > (0)::numeric)`
- **Indexes:**
  - `uq_task_product`: `CREATE UNIQUE INDEX uq_task_product ON public.worker_task_items USING btree (task_id, product_id)`
  - `worker_task_items_pkey`: `CREATE UNIQUE INDEX worker_task_items_pkey ON public.worker_task_items USING btree (task_item_id)`

---

### Table: `worker_tasks`

| Column Name | Data Type | Nullable | Default | PK |
|---|---|---|---|---|
| `task_id` | `bigint` | `NO` | `None` | PK |
| `task_code` | `character varying` | `NO` | `None` |  |
| `assigned_worker_id` | `bigint` | `NO` | `None` |  |
| `assigned_by_user_id` | `bigint` | `NO` | `None` |  |
| `allocation_id` | `bigint` | `YES` | `None` |  |
| `dispatch_id` | `bigint` | `YES` | `None` |  |
| `task_type` | `character varying` | `NO` | `None` |  |
| `priority` | `character varying` | `NO` | `'NORMAL'::character varying` |  |
| `status` | `character varying` | `NO` | `'PENDING'::character varying` |  |
| `due_at` | `timestamp with time zone` | `YES` | `None` |  |
| `instructions` | `text` | `YES` | `None` |  |
| `created_at` | `timestamp with time zone` | `NO` | `now()` |  |
| `completed_at` | `timestamp with time zone` | `YES` | `None` |  |

- **Primary Key:** `task_id`
- **Foreign Keys:**
  - `allocation_id` -> `order_allocations(allocation_id)` (Constraint: `fk_task_allocation`)
  - `assigned_by_user_id` -> `users(user_id)` (Constraint: `fk_task_manager`)
  - `assigned_worker_id` -> `users(user_id)` (Constraint: `fk_task_worker`)
  - `dispatch_id` -> `dispatches(dispatch_id)` (Constraint: `fk_task_dispatch`)
- **Unique Constraints:**
  - `task_code` (Name: `worker_tasks_task_code_key`)
- **Check Constraints:**
  - `2200_17993_12_not_null`: `created_at IS NOT NULL`
  - `2200_17993_1_not_null`: `task_id IS NOT NULL`
  - `2200_17993_2_not_null`: `task_code IS NOT NULL`
  - `2200_17993_3_not_null`: `assigned_worker_id IS NOT NULL`
  - `2200_17993_4_not_null`: `assigned_by_user_id IS NOT NULL`
  - `2200_17993_7_not_null`: `task_type IS NOT NULL`
  - `2200_17993_8_not_null`: `priority IS NOT NULL`
  - `2200_17993_9_not_null`: `status IS NOT NULL`
  - `chk_task_priority`: `((priority)::text = ANY ((ARRAY['LOW'::character varying, 'NORMAL'::character varying, 'HIGH'::character varying])::text[]))`
  - `chk_task_reference`: `((allocation_id IS NOT NULL) OR (dispatch_id IS NOT NULL))`
  - `chk_task_status`: `((status)::text = ANY ((ARRAY['PENDING'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying, 'CANCELLED'::character varying])::text[]))`
  - `chk_task_type`: `((task_type)::text = ANY ((ARRAY['PICKING'::character varying, 'PACKING'::character varying, 'DISPATCH'::character varying])::text[]))`
- **Indexes:**
  - `worker_tasks_pkey`: `CREATE UNIQUE INDEX worker_tasks_pkey ON public.worker_tasks USING btree (task_id)`
  - `worker_tasks_task_code_key`: `CREATE UNIQUE INDEX worker_tasks_task_code_key ON public.worker_tasks USING btree (task_code)`

---
