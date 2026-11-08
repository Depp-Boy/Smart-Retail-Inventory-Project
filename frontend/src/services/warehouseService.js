import { initialProducts } from '../data/mockProducts';
import { initialWarehouseInventory } from '../data/mockInventory';
import { initialOrders } from '../data/mockOrders';
import { initialWorkers, initialTasks, initialDispatches } from '../data/mockWorkersAndTasks';
import { initialWarehouseNotifications } from '../data/mockNotifications';

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

export const warehouseService = {
  // --- Dashboard ---
  async getDashboardSummary() {
    const inventory = getStored('wh_inventory', initialWarehouseInventory);
    const orders = getStored('shop_orders', initialOrders);
    const dispatches = getStored('wh_dispatches', initialDispatches);

    const totalProducts = inventory.length;
    const totalStock = inventory.reduce((sum, item) => sum + item.totalQuantity, 0);
    const reservedStock = inventory.reduce((sum, item) => sum + item.reservedQuantity, 0);
    const availableStock = inventory.reduce((sum, item) => sum + item.availableQuantity, 0);
    const incomingRequestsCount = orders.filter((o) => o.status === 'Pending').length;
    const pendingDispatchesCount = dispatches.filter((d) => d.status === 'Ready for Dispatch' || d.status === 'Staged').length;

    return {
      totalProducts,
      totalStock,
      availableStock,
      reservedStock,
      incomingRequestsCount,
      pendingDispatchesCount,
      inventoryDistribution: [
        { name: 'Grains & Cereals', value: 4300, color: '#2563eb' },
        { name: 'Sweeteners', value: 4200, color: '#10b981' },
        { name: 'Flour & Grains', value: 3100, color: '#f59e0b' },
        { name: 'Spices & Salt', value: 1800, color: '#8b5cf6' },
        { name: 'Edible Oils & FMCG', value: 1840, color: '#ec4899' },
      ],
      stockMovementChart: [
        { month: 'Jun', inbound: 12400, outbound: 10800 },
        { month: 'Jul', inbound: 14200, outbound: 13100 },
        { month: 'Aug', inbound: 15800, outbound: 14900 },
        { month: 'Sep', inbound: 13900, outbound: 12600 },
        { month: 'Oct', inbound: 18500, outbound: 16800 },
        { month: 'Nov (Mtd)', inbound: 6200, outbound: 5400 },
      ],
      recentRequests: orders.filter((o) => o.status === 'Pending').slice(0, 5),
      recentDispatches: dispatches.slice(0, 4),
      lowStockProducts: inventory.filter((i) => i.availableQuantity <= 50),
    };
  },

  // --- Warehouse Inventory ---
  async getInventory() {
    return getStored('wh_inventory', initialWarehouseInventory);
  },

  async updateStock(id, updateData) {
    const current = getStored('wh_inventory', initialWarehouseInventory);
    const updated = current.map((item) => {
      if (item.id === id) {
        const total = updateData.totalQuantity !== undefined ? Number(updateData.totalQuantity) : item.totalQuantity;
        const reserved = updateData.reservedQuantity !== undefined ? Number(updateData.reservedQuantity) : item.reservedQuantity;
        const available = Math.max(0, total - reserved);
        let status = 'In Stock';
        if (available <= 0) status = 'Out of Stock';
        else if (available <= 50) status = 'Low Stock';

        return {
          ...item,
          ...updateData,
          totalQuantity: total,
          reservedQuantity: reserved,
          availableQuantity: available,
          status,
          lastAuditDate: new Date().toISOString().substring(0, 10),
        };
      }
      return item;
    });
    setStored('wh_inventory', updated);
    return updated.find((i) => i.id === id);
  },

  async addStockEntry(newEntry) {
    const current = getStored('wh_inventory', initialWarehouseInventory);
    const id = `winv-${Date.now()}`;
    const total = Number(newEntry.totalQuantity || 0);
    const reserved = Number(newEntry.reservedQuantity || 0);
    const available = Math.max(0, total - reserved);
    let status = 'In Stock';
    if (available <= 0) status = 'Out of Stock';
    else if (available <= 50) status = 'Low Stock';

    const itemToAdd = {
      id,
      warehouseId: 'wh-001',
      ...newEntry,
      totalQuantity: total,
      reservedQuantity: reserved,
      availableQuantity: available,
      status,
      lastAuditDate: new Date().toISOString().substring(0, 10),
    };
    const updated = [itemToAdd, ...current];
    setStored('wh_inventory', updated);
    return itemToAdd;
  },

  // --- Products ---
  async getProducts() {
    return getStored('wh_products', initialProducts);
  },

  async addProduct(newProduct) {
    const current = getStored('wh_products', initialProducts);
    const item = {
      ...newProduct,
      id: `prod-${Date.now()}`,
    };
    const updated = [item, ...current];
    setStored('wh_products', updated);
    return item;
  },

  // --- Incoming Requests ---
  async getIncomingRequests() {
    const orders = getStored('shop_orders', initialOrders);
    return orders;
  },

  async acceptRequest(orderId, allocationDetails) {
    const orders = getStored('shop_orders', initialOrders);
    const updatedOrders = orders.map((o) => {
      if (o.id === orderId) {
        const isPartial = allocationDetails.isPartial;
        const newStatus = isPartial ? 'Partially Allocated' : 'Accepted';
        const allocatedUnits = allocationDetails.items.reduce((s, i) => s + Number(i.allocatedQuantity), 0);

        const newAllocations = [
          {
            warehouseId: 'wh-001',
            warehouseName: 'Apex Central Logistics Hub',
            isPreferred: true,
            items: allocationDetails.items.map((it) => ({
              productName: it.productName,
              quantity: Number(it.allocatedQuantity),
              unit: it.unit,
            })),
            status: 'Confirmed',
            dispatchTarget: 'Today, 05:00 PM',
          },
        ];

        return {
          ...o,
          status: newStatus,
          totalAllocatedUnits: allocatedUnits,
          allocations: newAllocations,
          unallocatedBalance: allocationDetails.unallocated || [],
          timeline: [
            ...o.timeline,
            {
              status: newStatus,
              date: new Date().toISOString().replace('T', ' ').substring(0, 16),
              note: isPartial
                ? `Accepted with partial fulfillment (${allocatedUnits}/${o.totalRequestedUnits} units allocated). Balance pending alternative warehouse fulfillment.`
                : 'Accepted in full. Inventory reserved for picking.',
            },
          ],
        };
      }
      return o;
    });
    setStored('shop_orders', updatedOrders);

    // Also update warehouse inventory reserved quantities
    const inv = getStored('wh_inventory', initialWarehouseInventory);
    const updatedInv = inv.map((item) => {
      const match = allocationDetails.items?.find((ai) => ai.productId === item.productId);
      if (match) {
        const newReserved = item.reservedQuantity + Number(match.allocatedQuantity);
        const newAvailable = Math.max(0, item.totalQuantity - newReserved);
        return {
          ...item,
          reservedQuantity: newReserved,
          availableQuantity: newAvailable,
        };
      }
      return item;
    });
    setStored('wh_inventory', updatedInv);

    return updatedOrders.find((o) => o.id === orderId);
  },

  async rejectRequest(orderId, rejectionReason) {
    const orders = getStored('shop_orders', initialOrders);
    const updatedOrders = orders.map((o) => {
      if (o.id === orderId) {
        return {
          ...o,
          status: 'Rejected',
          rejectionReason,
          timeline: [
            ...o.timeline,
            {
              status: 'Rejected',
              date: new Date().toISOString().replace('T', ' ').substring(0, 16),
              note: `Rejected by warehouse manager: ${rejectionReason}`,
            },
          ],
        };
      }
      return o;
    });
    setStored('shop_orders', updatedOrders);
    return updatedOrders.find((o) => o.id === orderId);
  },

  // --- Orders ---
  async getOrders() {
    return getStored('shop_orders', initialOrders);
  },

  async updateOrderStatus(orderId, newStatus, note) {
    const orders = getStored('shop_orders', initialOrders);
    const updatedOrders = orders.map((o) => {
      if (o.id === orderId) {
        return {
          ...o,
          status: newStatus,
          timeline: [
            ...o.timeline,
            {
              status: newStatus,
              date: new Date().toISOString().replace('T', ' ').substring(0, 16),
              note: note || `Order marked as ${newStatus}`,
            },
          ],
        };
      }
      return o;
    });
    setStored('shop_orders', updatedOrders);
    return updatedOrders.find((o) => o.id === orderId);
  },

  // --- Stock Allocation ---
  async getAllocations() {
    const orders = getStored('shop_orders', initialOrders);
    const inventory = getStored('wh_inventory', initialWarehouseInventory);

    // Filter orders that have allocations
    const activeAllocations = orders
      .filter((o) => o.allocations && o.allocations.length > 0)
      .map((o) => ({
        orderId: o.id,
        orderNumber: o.orderNumber,
        shopName: o.shopName,
        status: o.status,
        items: o.items,
        allocations: o.allocations,
        unallocatedBalance: o.unallocatedBalance,
      }));

    return { activeAllocations, inventory };
  },

  // --- Dispatches ---
  async getDispatches() {
    return getStored('wh_dispatches', initialDispatches);
  },

  async createDispatch(dispatchData) {
    const current = getStored('wh_dispatches', initialDispatches);
    const id = `DSP-2026-${Math.floor(505 + Math.random() * 100)}`;
    const newDispatch = {
      id,
      ...dispatchData,
      status: 'Ready for Dispatch',
      dispatchedAt: 'Pending Driver Pickup',
    };
    const updated = [newDispatch, ...current];
    setStored('wh_dispatches', updated);
    return newDispatch;
  },

  async updateDispatchStatus(dispatchId, newStatus, trackingNumber) {
    const current = getStored('wh_dispatches', initialDispatches);
    const updated = current.map((d) => {
      if (d.id === dispatchId) {
        return {
          ...d,
          status: newStatus,
          trackingNumber: trackingNumber || d.trackingNumber,
          dispatchedAt: newStatus === 'In Transit' ? new Date().toISOString().replace('T', ' ').substring(0, 16) : d.dispatchedAt,
        };
      }
      return d;
    });
    setStored('wh_dispatches', updated);
    return updated.find((d) => d.id === dispatchId);
  },

  // --- Workers ---
  async getWorkers() {
    return getStored('wh_workers', initialWorkers);
  },

  async addWorker(workerData) {
    const current = getStored('wh_workers', initialWorkers);
    const id = `wrk-${Date.now()}`;
    const code = `EMP-W-${Math.floor(105 + Math.random() * 50)}`;
    const newWorker = {
      id,
      workerCode: code,
      activeTasksCount: 0,
      completedTasksCount: 0,
      rating: 5.0,
      joiningDate: new Date().toISOString().substring(0, 10),
      status: 'On Duty',
      assignedWarehouseId: 'wh-001',
      ...workerData,
    };
    const updated = [newWorker, ...current];
    setStored('wh_workers', updated);
    return newWorker;
  },

  async assignTask(taskPayload) {
    const currentTasks = getStored('wh_tasks', initialTasks);
    const taskId = `TSK-${Math.floor(1095 + Math.random() * 50)}`;
    const newTask = {
      id: taskId,
      assignedDate: new Date().toISOString().replace('T', ' ').substring(0, 16),
      status: 'Pending',
      ...taskPayload,
    };
    const updatedTasks = [newTask, ...currentTasks];
    setStored('wh_tasks', updatedTasks);

    // Increment worker active tasks
    const workers = getStored('wh_workers', initialWorkers);
    const updatedWorkers = workers.map((w) => {
      if (w.id === taskPayload.assignedToWorkerId) {
        return { ...w, activeTasksCount: w.activeTasksCount + 1 };
      }
      return w;
    });
    setStored('wh_workers', updatedWorkers);

    return newTask;
  },

  // --- Analytics ---
  async getAnalytics() {
    return {
      metrics: {
        totalOrdersReceived: 184,
        fulfilledOrders: 168,
        fulfillmentRate: 91.3,
        rejectedRequests: 6,
        avgTurnaroundHours: 3.4,
        inventoryTurnoverRate: '6.8x/yr (Industry benchmark: 6.2x)',
      },
      monthlyThroughput: [
        { month: 'Jun', received: 110, fulfilled: 102, turnaroundHrs: 4.2 },
        { month: 'Jul', received: 135, fulfilled: 124, turnaroundHrs: 3.8 },
        { month: 'Aug', received: 148, fulfilled: 138, turnaroundHrs: 3.6 },
        { month: 'Sep', received: 130, fulfilled: 120, turnaroundHrs: 3.5 },
        { month: 'Oct', received: 172, fulfilled: 161, turnaroundHrs: 3.3 },
        { month: 'Nov (Mtd)', received: 48, fulfilled: 45, turnaroundHrs: 3.1 },
      ],
      rejectionReasons: [
        { reason: 'Insufficient Stock', count: 4, percentage: 66 },
        { reason: 'Exceeded Max Distance', count: 1, percentage: 17 },
        { reason: 'Dock Maintenance', count: 1, percentage: 17 },
      ],
    };
  },

  // --- Notifications ---
  async getNotifications() {
    return getStored('wh_notifications', initialWarehouseNotifications);
  },

  async markNotificationRead(id) {
    const current = getStored('wh_notifications', initialWarehouseNotifications);
    const updated = current.map((n) => n.id === id ? { ...n, read: true } : n);
    setStored('wh_notifications', updated);
    return updated;
  },

  // --- Settings ---
  async getSettings() {
    return getStored('wh_settings', {
      warehouseName: 'Apex Central Logistics Hub',
      code: 'WH-BLR-01',
      managerName: 'Rajesh Kumar Verma',
      phone: '+91 80 2839 4410',
      email: 'peenya.hub@stocksense-logistics.in',
      address: 'Plot #42-B, 3rd Phase, Peenya Industrial Area',
      city: 'Bengaluru',
      state: 'Karnataka',
      pincode: '560058',
      totalCapacitySqFt: 45000,
      maxPalletsCapacity: 1200,
      operatingHours: '06:00 AM - 10:00 PM (Mon-Sat)',
      autoNotifyManagers: true,
      partialAllocationAllowed: true,
    });
  },

  async updateSettings(settings) {
    setStored('wh_settings', settings);
    return settings;
  },
};
