import { initialProducts } from '../data/mockProducts';
import { initialShopInventory } from '../data/mockInventory';
import { initialWarehouses } from '../data/mockWarehouses';
import { initialOrders } from '../data/mockOrders';
import { initialSales, monthlySalesChartData, categorySalesDistribution } from '../data/mockSales';
import { forecastProducts, historicalVsForecastData } from '../data/mockForecast';
import { initialShopNotifications } from '../data/mockNotifications';

// In-memory / localStorage persistence helper
function getStored(key, fallback) {
  try {
    const item = localStorage.getItem(`stocksense_${key}`);
    return item ? JSON.parse(item) : fallback;
  } catch {
    return fallback;
  }
}

function setStored(key, value) {
  try {
    localStorage.setItem(`stocksense_${key}`, JSON.stringify(value));
  } catch (err) {
    console.warn('LocalStorage error:', err);
  }
}

export const shopService = {
  // --- Dashboard ---
  async getDashboardSummary() {
    const inventory = getStored('shop_inventory', initialShopInventory);
    const orders = getStored('shop_orders', initialOrders);
    const sales = getStored('shop_sales', initialSales);

    const totalProducts = inventory.length;
    const totalInventoryUnits = inventory.reduce((sum, item) => sum + item.quantity, 0);
    const lowStockCount = inventory.filter((item) => item.status === 'Low Stock' || item.status === 'Out of Stock').length;
    const pendingOrdersCount = orders.filter((o) => o.status === 'Pending' || o.status === 'Partially Allocated').length;
    const monthlySalesTotal = sales.reduce((sum, s) => sum + s.total, 0) + 57400; // Simulated monthly run rate

    return {
      totalProducts,
      totalInventoryUnits,
      lowStockCount,
      pendingOrdersCount,
      monthlySalesTotal,
      salesChartData: monthlySalesChartData,
      categoryDistribution: categorySalesDistribution,
      lowStockAlerts: inventory.filter((i) => i.status === 'Low Stock' || i.status === 'Out of Stock').slice(0, 4),
      recentSales: sales.slice(0, 5),
      recentOrders: orders.slice(0, 4),
      reorderRecommendations: forecastProducts.filter((f) => f.recommendedReorder > 0).slice(0, 4),
    };
  },

  // --- Inventory ---
  async getInventory() {
    return getStored('shop_inventory', initialShopInventory);
  },

  async updateInventoryItem(id, updateData) {
    const current = getStored('shop_inventory', initialShopInventory);
    const updated = current.map((item) => {
      if (item.id === id) {
        const newQty = updateData.quantity !== undefined ? Number(updateData.quantity) : item.quantity;
        const threshold = updateData.reorderThreshold !== undefined ? Number(updateData.reorderThreshold) : item.reorderThreshold;
        let status = 'In Stock';
        if (newQty <= 0) status = 'Out of Stock';
        else if (newQty <= threshold) status = 'Low Stock';

        return {
          ...item,
          ...updateData,
          quantity: newQty,
          reorderThreshold: threshold,
          status,
          lastUpdated: new Date().toISOString().replace('T', ' ').substring(0, 16),
        };
      }
      return item;
    });
    setStored('shop_inventory', updated);
    return updated.find((i) => i.id === id);
  },

  async addInventoryItem(newItem) {
    const current = getStored('shop_inventory', initialShopInventory);
    const id = `sinv-${Date.now()}`;
    const qty = Number(newItem.quantity || 0);
    const threshold = Number(newItem.reorderThreshold || 50);
    let status = 'In Stock';
    if (qty <= 0) status = 'Out of Stock';
    else if (qty <= threshold) status = 'Low Stock';

    const itemToAdd = {
      id,
      ...newItem,
      quantity: qty,
      reorderThreshold: threshold,
      status,
      lastUpdated: new Date().toISOString().replace('T', ' ').substring(0, 16),
    };
    const updated = [itemToAdd, ...current];
    setStored('shop_inventory', updated);
    return itemToAdd;
  },

  // --- Products Catalog ---
  async getProducts() {
    return getStored('shop_products', initialProducts);
  },

  async addProduct(newProduct) {
    const current = getStored('shop_products', initialProducts);
    const item = {
      ...newProduct,
      id: `prod-${Date.now()}`,
      unitPrice: Number(newProduct.unitPrice),
      costPrice: Number(newProduct.costPrice || newProduct.unitPrice * 0.8),
      minThreshold: Number(newProduct.minThreshold || 50),
    };
    const updated = [item, ...current];
    setStored('shop_products', updated);
    return item;
  },

  async updateProduct(id, productData) {
    const current = getStored('shop_products', initialProducts);
    const updated = current.map((p) => p.id === id ? { ...p, ...productData } : p);
    setStored('shop_products', updated);
    return updated.find((p) => p.id === id);
  },

  // --- Sales ---
  async getSales() {
    return getStored('shop_sales', initialSales);
  },

  async recordSale(saleData) {
    const current = getStored('shop_sales', initialSales);
    const id = `SALE-2026-${Math.floor(1400 + Math.random() * 900)}`;
    const saleNumber = `INV-${Math.floor(1400 + Math.random() * 900)}`;
    const newSale = {
      id,
      saleNumber,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 16),
      status: 'Completed',
      ...saleData,
    };
    const updated = [newSale, ...current];
    setStored('shop_sales', updated);

    // Also deduct quantities from shop inventory
    const inventory = getStored('shop_inventory', initialShopInventory);
    const updatedInventory = inventory.map((inv) => {
      const soldItem = saleData.items.find((si) => si.productId === inv.productId);
      if (soldItem) {
        const newQty = Math.max(0, inv.quantity - Number(soldItem.quantity));
        let status = 'In Stock';
        if (newQty <= 0) status = 'Out of Stock';
        else if (newQty <= inv.reorderThreshold) status = 'Low Stock';
        return { ...inv, quantity: newQty, status };
      }
      return inv;
    });
    setStored('shop_inventory', updatedInventory);

    return newSale;
  },

  // --- Warehouses ---
  async getWarehouses() {
    return getStored('shop_warehouses', initialWarehouses);
  },

  async setPreferredWarehouse(warehouseId) {
    const current = getStored('shop_warehouses', initialWarehouses);
    const updated = current.map((w) => ({
      ...w,
      isPreferred: w.id === warehouseId,
    }));
    setStored('shop_warehouses', updated);
    return updated;
  },

  async updateWarehouseRankings(rankingsMap) {
    const current = getStored('shop_warehouses', initialWarehouses);
    const updated = current.map((w) => ({
      ...w,
      ranking: rankingsMap[w.id] || w.ranking,
    }));
    setStored('shop_warehouses', updated);
    return updated;
  },

  // --- Restock Orders ---
  async getOrders() {
    return getStored('shop_orders', initialOrders);
  },

  async getOrderById(orderId) {
    const orders = getStored('shop_orders', initialOrders);
    return orders.find((o) => o.id === orderId || o.orderNumber === orderId);
  },

  async createRestockOrder(orderPayload) {
    const current = getStored('shop_orders', initialOrders);
    const num = Math.floor(843 + Math.random() * 150);
    const orderId = `ORD-2026-0${num}`;
    const orderNumber = `RO-0${num}`;

    const totalUnits = orderPayload.items.reduce((sum, i) => sum + Number(i.requestedQuantity), 0);
    const totalAmount = orderPayload.items.reduce((sum, i) => sum + (Number(i.requestedQuantity) * (i.unitPrice || 45)), 0);

    const newOrder = {
      id: orderId,
      orderNumber,
      shopId: 'shop-001',
      shopName: 'Sri Lakshmi Retail Provisions',
      destinationWarehouseId: orderPayload.destinationWarehouseId,
      destinationWarehouseName: orderPayload.destinationWarehouseName,
      orderDate: new Date().toISOString().replace('T', ' ').substring(0, 16),
      status: 'Pending',
      paymentStatus: 'Credit Terms (15 Days)',
      priority: orderPayload.priority || 'Normal',
      notes: orderPayload.notes || '',
      items: orderPayload.items.map((it) => ({
        ...it,
        allocatedQuantity: 0,
      })),
      totalRequestedUnits: totalUnits,
      totalAllocatedUnits: 0,
      totalAmount,
      allocations: [],
      unallocatedBalance: [],
      timeline: [
        {
          status: 'Pending',
          date: new Date().toISOString().replace('T', ' ').substring(0, 16),
          note: `Restock request submitted to ${orderPayload.destinationWarehouseName}`,
        },
      ],
    };

    const updated = [newOrder, ...current];
    setStored('shop_orders', updated);
    return newOrder;
  },

  async rerouteToAlternativeWarehouse(orderId, targetWarehouseId, targetWarehouseName) {
    const orders = getStored('shop_orders', initialOrders);
    const updated = orders.map((o) => {
      if (o.id === orderId) {
        return {
          ...o,
          destinationWarehouseId: targetWarehouseId,
          destinationWarehouseName: targetWarehouseName,
          status: 'Pending',
          timeline: [
            ...o.timeline,
            {
              status: 'Pending',
              date: new Date().toISOString().replace('T', ' ').substring(0, 16),
              note: `Shop owner rerouted unfulfilled order to alternative warehouse: ${targetWarehouseName}`,
            },
          ],
        };
      }
      return o;
    });
    setStored('shop_orders', updated);
    return updated.find((o) => o.id === orderId);
  },

  // --- Demand Forecast ---
  async getForecastData() {
    return {
      products: forecastProducts,
      historicalVsForecast: historicalVsForecastData,
    };
  },

  // --- Notifications ---
  async getNotifications() {
    return getStored('shop_notifications', initialShopNotifications);
  },

  async markNotificationRead(id) {
    const current = getStored('shop_notifications', initialShopNotifications);
    const updated = current.map((n) => n.id === id ? { ...n, read: true } : n);
    setStored('shop_notifications', updated);
    return updated;
  },

  async markAllNotificationsRead() {
    const current = getStored('shop_notifications', initialShopNotifications);
    const updated = current.map((n) => ({ ...n, read: true }));
    setStored('shop_notifications', updated);
    return updated;
  },

  // --- Shop Profile & Settings ---
  async getProfile() {
    return getStored('shop_profile', {
      shopName: 'Sri Lakshmi Retail Provisions',
      ownerName: 'Chethan Suhas',
      phone: '+91 98451 90812',
      email: 'chethan.suhas@lakshmiprovisions.in',
      address: 'Shop #14, 5th Main Road, 8th Cross',
      locality: 'Malleshwaram',
      city: 'Bengaluru',
      state: 'Karnataka',
      pincode: '560003',
      gstin: '29AABCL1429Q1Z8',
      operatingHours: '07:30 AM - 10:00 PM (Daily)',
      autoReorderEnabled: true,
      defaultThreshold: 50,
      notificationSms: true,
      notificationEmail: true,
    });
  },

  async updateProfile(profileData) {
    setStored('shop_profile', profileData);
    return profileData;
  },
};
