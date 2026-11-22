/**
 * Centralized API Client
 *
 * - Uses native fetch with Authorization: Bearer token from localStorage.
 * - Maps all backend endpoints verified against actual FastAPI routes and Pydantic schemas.
 * - Snake_case backend fields are exposed as-is; adapters in services convert to camelCase.
 * - Throws structured errors: { status, detail } matching FastAPI HTTPException shape.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const TOKEN_KEY = 'stocksense_token';

// ─── Token helpers ────────────────────────────────────────────────────────────
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// ─── Core fetch wrapper ────────────────────────────────────────────────────────
async function request(method, path, body = undefined, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...options,
  });

  // 204 No Content
  if (res.status === 204) return null;

  let data;
  try {
    data = await res.json();
  } catch {
    data = { detail: res.statusText || 'Unknown error' };
  }

  if (!res.ok) {
    const err = new Error(data?.detail || `HTTP ${res.status}`);
    err.status = res.status;
    err.detail = data?.detail || `HTTP ${res.status}`;
    err.response = data;
    throw err;
  }

  return data;
}

const get = (path, params) => {
  const qs = params ? '?' + new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null))
  ).toString() : '';
  return request('GET', path + qs);
};
const post = (path, body) => request('POST', path, body);
const put = (path, body) => request('PUT', path, body);
const patch = (path, body) => request('PATCH', path, body);

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email, password) =>
    post('/auth/login', { email, password }),

  register: (payload) =>
    post('/auth/register', payload),

  getMe: () =>
    get('/auth/me'),

  updateProfile: (name, phone) =>
    put('/auth/profile', { name, phone }),

  changePassword: (current_password, new_password) =>
    post('/auth/change-password', { current_password, new_password }),

  logout: () =>
    post('/auth/logout', {}),

  seedDemo: () =>
    post('/auth/seed-demo', {}),
};

// ─── Locations ────────────────────────────────────────────────────────────────
export const locationsApi = {
  list: (params) => get('/locations', params),
  listWarehouses: (params) => get('/locations/warehouses', params),
  listShops: (params) => get('/locations/shops', params),
  getById: (id) => get(`/locations/${id}`),
};

// ─── Warehouses ───────────────────────────────────────────────────────────────
export const warehousesApi = {
  listAll: () => get('/warehouses'),
  listForShop: (shopId) => get(`/warehouses/shops/${shopId}/warehouses`),
  getPreferred: (shopId) => get(`/warehouses/shops/${shopId}/preferred-warehouse`),
  getAlternatives: (shopId) => get(`/warehouses/shops/${shopId}/alternative-warehouses`),
  setPreferred: (shopId, warehouseId) =>
    put(`/warehouses/shops/${shopId}/preferred-warehouse/${warehouseId}`, {}),
  addLink: (shopId, payload) =>
    post(`/warehouses/shops/${shopId}/warehouses`, payload),
  listShopsForWarehouse: (warehouseId) =>
    get(`/warehouses/warehouses/${warehouseId}/shops`),
};

// ─── Products ─────────────────────────────────────────────────────────────────
export const productsApi = {
  list: (params) => get('/products', params),
  getById: (id) => get(`/products/${id}`),
  create: (payload) => post('/products', payload),
  update: (id, payload) => put(`/products/${id}`, payload),
};

// ─── Inventory ────────────────────────────────────────────────────────────────
export const inventoryApi = {
  listAll: (params) => get('/inventory', params),
  listByLocation: (locationId, params) =>
    get(`/inventory/locations/${locationId}`, params),
  getSummary: (locationId) =>
    get(`/inventory/locations/${locationId}/summary`),
  adjustStock: (locationId, payload) =>
    post(`/inventory/locations/${locationId}/adjust`, payload),
};

// ─── Sales ────────────────────────────────────────────────────────────────────
export const salesApi = {
  list: (params) => get('/sales', params),
  getById: (id) => get(`/sales/${id}`),
  record: (payload) => post('/sales', payload),
  cancel: (id) => post(`/sales/${id}/cancel`, {}),
  refund: (id) => post(`/sales/${id}/refund`, {}),
};

// ─── Orders ───────────────────────────────────────────────────────────────────
export const ordersApi = {
  list: (params) => get('/orders', params),
  getById: (id) => get(`/orders/${id}`),
  create: (payload) => post('/orders', payload),
  cancel: (id) => post(`/orders/${id}/cancel`, {}),
};

// ─── Allocations ──────────────────────────────────────────────────────────────
export const allocationsApi = {
  allocate: (payload) => post('/allocations', payload),
  cancel: (allocationId) => post(`/allocations/${allocationId}/cancel`, {}),
  listByOrder: (orderId) => get(`/allocations/order/${orderId}`),
  listByWarehouse: (warehouseId, params) =>
    get(`/allocations/warehouse/${warehouseId}`, params),
  getOrderSummary: (orderId) =>
    get(`/allocations/order/${orderId}/summary`),
};

// ─── Reservations ─────────────────────────────────────────────────────────────
export const reservationsApi = {
  list: (params) => get('/reservations', params),
  create: (payload) => post('/reservations', payload),
  release: (id) => post(`/reservations/${id}/release`, {}),
  confirm: (id) => post(`/reservations/${id}/confirm`, {}),
  listByAllocation: (allocationId) =>
    get(`/reservations/allocation/${allocationId}`),
};

// ─── Dispatches ───────────────────────────────────────────────────────────────
export const dispatchesApi = {
  list: (params) => get('/dispatches', params),
  getById: (id) => get(`/dispatches/${id}`),
  create: (payload) => post('/dispatches', payload),
  updateStatus: (id, payload) => patch(`/dispatches/${id}/status`, payload),
};

// ─── Workers & Tasks ──────────────────────────────────────────────────────────
export const workersApi = {
  list: (params) => get('/workers', params),
  listTasks: (workerId, params) => get(`/workers/${workerId}/tasks`, params),
  listWarehouseTasks: (warehouseId, params) =>
    get(`/workers/warehouse/${warehouseId}/tasks`, params),
  listMyTasks: (params) => get('/tasks', params),
  getTask: (id) => get(`/tasks/${id}`),
  createTask: (payload) => post('/tasks', payload),
  updateItemProgress: (taskId, taskItemId, completed_quantity) =>
    patch(`/tasks/${taskId}/items/${taskItemId}/progress`, { completed_quantity }),
  updateTaskStatus: (taskId, status) =>
    patch(`/tasks/${taskId}/status`, { status }),
};

// ─── Forecasts ────────────────────────────────────────────────────────────────
export const forecastsApi = {
  list: (params) => get('/forecasts', params),
  generate: (payload) => post('/forecasts/generate', payload),
  getReorderRecommendation: (shopId, productId, period) =>
    get('/forecasts/reorder-recommendation', {
      shop_id: shopId,
      product_id: productId,
      period,
    }),
};

// ─── Alerts ───────────────────────────────────────────────────────────────────
export const alertsApi = {
  list: (params) => get('/alerts', params),
  create: (payload) => post('/alerts', payload),
  markRead: (id) => patch(`/alerts/${id}/read`, {}),
  dismiss: (id) => patch(`/alerts/${id}/dismiss`, {}),
};

// ─── Default export (namespace object) ───────────────────────────────────────
const api = {
  auth: authApi,
  locations: locationsApi,
  warehouses: warehousesApi,
  products: productsApi,
  inventory: inventoryApi,
  sales: salesApi,
  orders: ordersApi,
  allocations: allocationsApi,
  reservations: reservationsApi,
  dispatches: dispatchesApi,
  workers: workersApi,
  forecasts: forecastsApi,
  alerts: alertsApi,
};

export default api;

