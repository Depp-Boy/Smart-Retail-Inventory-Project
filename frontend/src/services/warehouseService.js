import api from './api';

function getCurrentWarehouseId() {
  try {
    const saved = localStorage.getItem('stocksense_user');
    if (saved) {
      const u = JSON.parse(saved);
      return u.locationId || 1;
    }
  } catch {
    // fallback
  }
  return 1;
}

export const warehouseService = {
  // --- Dashboard ---
  async getDashboardSummary() {
    const whId = getCurrentWarehouseId();

    const [summaryRes, inventoryList, ordersList, dispatchesList] = await Promise.allSettled([
      api.inventory.getSummary(whId),
      api.inventory.listByLocation(whId, { limit: 100 }),
      api.orders.list({ limit: 50 }),
      api.dispatches.list({ warehouse_id: whId, limit: 50 }),
    ]);

    const summary = summaryRes.status === 'fulfilled' ? summaryRes.value : null;
    const inventory = inventoryList.status === 'fulfilled' && Array.isArray(inventoryList.value)
      ? inventoryList.value
      : [];
    const orders = ordersList.status === 'fulfilled' && Array.isArray(ordersList.value)
      ? ordersList.value
      : [];
    const dispatches = dispatchesList.status === 'fulfilled' && Array.isArray(dispatchesList.value)
      ? dispatchesList.value
      : [];

    const totalProducts = summary?.total_products_count ?? inventory.length;
    const totalStock = summary?.total_physical_quantity ? Number(summary.total_physical_quantity) : inventory.reduce((s, i) => s + Number(i.quantity || 0), 0);
    const reservedStock = summary?.total_reserved_quantity ? Number(summary.total_reserved_quantity) : inventory.reduce((s, i) => s + Number(i.reserved_quantity || 0), 0);
    const availableStock = summary?.total_available_quantity ? Number(summary.total_available_quantity) : (totalStock - reservedStock);

    const incomingRequests = orders.filter((o) => o.status === 'PENDING' || o.status === 'PROCESSING');
    const incomingRequestsCount = incomingRequests.length;
    const pendingDispatchesCount = dispatches.filter((d) => d.status === 'READY' || d.status === 'PENDING' || d.status === 'PACKING').length;

    const formattedRequests = incomingRequests.slice(0, 5).map((o) => ({
      id: o.order_id,
      orderNumber: `RO-0${o.order_id}`,
      shopName: 'Sri Lakshmi Retail Provisions',
      orderDate: new Date(o.order_date).toLocaleString(),
      status: 'Pending',
      totalRequestedUnits: o.items?.reduce((s, it) => s + Number(it.quantity_requested), 0) || 0,
      priority: 'Normal',
      items: (o.items || []).map((it) => ({
        id: it.order_item_id,
        orderItemId: it.order_item_id,
        productId: it.product_id,
        productName: it.product_name || `Product ${it.product_id}`,
        requestedQuantity: Number(it.quantity_requested),
        allocatedQuantity: Number(it.quantity_allocated),
      })),
    }));

    const formattedDispatches = dispatches.slice(0, 4).map((d) => ({
      id: `DSP-2026-0${d.dispatch_id}`,
      dispatchId: d.dispatch_id,
      orderNumber: `RO-0${d.order_id}`,
      status: d.status === 'READY' ? 'Ready for Dispatch' : (d.status === 'IN_TRANSIT' ? 'In Transit' : (d.status === 'DELIVERED' ? 'Delivered' : 'Staged')),
      trackingNumber: d.tracking_reference || `TRK-BLR-0${d.dispatch_id}`,
      destination: 'Malleshwaram Shop',
    }));

    const lowStock = inventory
      .filter((i) => Number(i.available_quantity) <= Number(i.product?.reorder_threshold || 50))
      .map((i) => ({
        id: i.inventory_id,
        productName: i.product?.product_name || `Product ${i.product_id}`,
        sku: itemSku(i),
        availableQuantity: Number(i.available_quantity),
        threshold: Number(i.product?.reorder_threshold || 50),
      }));

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
      recentRequests: formattedRequests,
      recentDispatches: formattedDispatches,
      lowStockProducts: lowStock,
    };
  },

  // --- Warehouse Inventory ---
  async getInventory() {
    const whId = getCurrentWarehouseId();
    const list = await api.inventory.listByLocation(whId, { limit: 100 });
    return (list || []).map((item) => {
      const total = Number(item.quantity);
      const reserved = Number(item.reserved_quantity);
      const available = Number(item.available_quantity);
      let status = 'In Stock';
      if (available <= 0) status = 'Out of Stock';
      else if (available <= 50) status = 'Low Stock';

      return {
        id: item.inventory_id,
        inventoryId: item.inventory_id,
        productId: item.product_id,
        warehouseId: item.location_id,
        productName: item.product?.product_name || `Product ${item.product_id}`,
        sku: item.product?.sku || `SKU-${item.product_id}`,
        category: item.product?.category || 'General',
        totalQuantity: total,
        reservedQuantity: reserved,
        availableQuantity: available,
        unit: item.product?.unit || 'Units',
        aisleLocation: `Aisle ${(item.product_id % 10) + 1}-Bay ${(item.product_id % 4) + 1}`,
        status,
        lastAuditDate: item.last_updated ? new Date(item.last_updated).toISOString().substring(0, 10) : '2026-11-01',
      };
    });
  },

  async updateStock(id, updateData) {
    const whId = getCurrentWarehouseId();
    if (updateData.productId && (updateData.totalQuantity !== undefined || updateData.delta !== undefined)) {
      const delta = updateData.delta !== undefined ? Number(updateData.delta) : Number(updateData.totalQuantity);
      await api.inventory.adjustStock(whId, {
        product_id: Number(updateData.productId),
        delta,
      });
    }
    return this.getInventory();
  },

  async addStockEntry(newEntry) {
    const whId = getCurrentWarehouseId();
    if (newEntry.productId) {
      await api.inventory.adjustStock(whId, {
        product_id: Number(newEntry.productId),
        delta: Number(newEntry.totalQuantity || newEntry.quantity || 100),
      });
    }
    return this.getInventory();
  },

  // --- Products ---
  async getProducts() {
    const list = await api.products.list({ limit: 100 });
    return (list || []).map((p) => ({
      id: p.product_id,
      productId: p.product_id,
      name: p.product_name,
      productName: p.product_name,
      sku: p.sku || `SKU-${p.product_id}`,
      category: p.category || 'General',
      unit: p.unit || 'Units',
      basePrice: Number(p.price || 0),
      mrp: Number(p.price || 0) * 1.15,
      costPrice: Number(p.cost_price || p.price * 0.8),
      minThreshold: Number(p.reorder_threshold || 50),
      reorderThreshold: Number(p.reorder_threshold || 50),
      description: p.description || '',
    }));
  },

  async addProduct(newProduct) {
    return api.products.create({
      product_name: newProduct.name || newProduct.productName,
      unit: newProduct.unit || 'Units',
      price: Number(newProduct.basePrice || newProduct.price || 0),
      category: newProduct.category || null,
      reorder_threshold: Number(newProduct.minThreshold || 50),
      sku: newProduct.sku || null,
      cost_price: newProduct.costPrice ? Number(newProduct.costPrice) : null,
      description: newProduct.description || null,
    });
  },

  // --- Incoming Requests ---
  async getIncomingRequests() {
    const orders = await api.orders.list({ limit: 100 });
    return (orders || []).map((o) => {
      let uiStatus = 'Pending';
      if (o.status === 'PARTIALLY_ALLOCATED') uiStatus = 'Partially Allocated';
      else if (o.status === 'ACCEPTED') uiStatus = 'Accepted';
      else if (o.status === 'CANCELLED') uiStatus = 'Rejected';
      else if (o.status === 'FULFILLED') uiStatus = 'Delivered';

      const items = (o.items || []).map((it) => ({
        id: it.order_item_id,
        orderItemId: it.order_item_id,
        productId: it.product_id,
        productName: it.product_name || `Product ${it.product_id}`,
        requestedQuantity: Number(it.quantity_requested),
        allocatedQuantity: Number(it.quantity_allocated),
        unit: 'Units',
      }));

      const totalRequested = items.reduce((s, it) => s + it.requestedQuantity, 0);
      const totalAllocated = items.reduce((s, it) => s + it.allocatedQuantity, 0);

      return {
        id: o.order_id,
        orderId: o.order_id,
        orderNumber: `RO-0${o.order_id}`,
        shopName: 'Sri Lakshmi Retail Provisions',
        shopAddress: 'Malleshwaram, Bangalore',
        orderDate: new Date(o.order_date).toLocaleString(),
        status: uiStatus,
        priority: 'Normal',
        items,
        totalRequestedUnits: totalRequested,
        totalAllocatedUnits: totalAllocated,
        totalAmount: Number(o.total_amount),
        timeline: [
          {
            status: uiStatus,
            date: new Date(o.order_date).toLocaleString(),
            note: `Order status: ${o.status}`,
          },
        ],
      };
    });
  },

  async acceptRequest(orderId, allocationDetails) {
    const whId = getCurrentWarehouseId();
    // Allocate items in backend
    for (const item of allocationDetails.items || []) {
      if (Number(item.allocatedQuantity) > 0) {
        await api.allocations.allocate({
          order_item_id: Number(item.orderItemId || item.id),
          source_location_id: whId,
          allocated_quantity: Number(item.allocatedQuantity),
          auto_reserve: true,
        }).catch((err) => console.warn('Allocation error:', err));
      }
    }
    const requests = await this.getIncomingRequests();
    return requests.find((r) => r.id === Number(orderId)) || { id: orderId, status: 'Accepted' };
  },

  async rejectRequest(orderId, rejectionReason) {
    await api.orders.cancel(Number(orderId));
    const requests = await this.getIncomingRequests();
    return requests.find((r) => r.id === Number(orderId)) || { id: orderId, status: 'Rejected' };
  },

  // --- Orders ---
  async getOrders() {
    return this.getIncomingRequests();
  },

  async updateOrderStatus(orderId, newStatus, note) {
    if (newStatus === 'Cancelled' || newStatus === 'CANCELLED') {
      await api.orders.cancel(Number(orderId));
    }
    const orders = await this.getOrders();
    return orders.find((o) => o.id === Number(orderId)) || { id: orderId, status: newStatus };
  },

  // --- Stock Allocation ---
  async getAllocations() {
    const whId = getCurrentWarehouseId();
    const [allocList, inventory] = await Promise.all([
      api.allocations.listByWarehouse(whId).catch(() => []),
      this.getInventory(),
    ]);

    const activeAllocations = (allocList || []).map((a) => ({
      id: a.allocation_id,
      allocationId: a.allocation_id,
      orderId: a.order_item_id,
      orderNumber: `RO-0${a.order_item_id}`,
      shopName: 'Sri Lakshmi Retail Provisions',
      status: a.status,
      allocatedQuantity: Number(a.allocated_quantity),
      productName: a.product_name || `Product ${a.product_id}`,
      items: [
        {
          productName: a.product_name || `Product ${a.product_id}`,
          quantity: Number(a.allocated_quantity),
          unit: 'Units',
        },
      ],
    }));

    return { activeAllocations, inventory };
  },

  // --- Dispatches ---
  async getDispatches() {
    const whId = getCurrentWarehouseId();
    const list = await api.dispatches.list({ warehouse_id: whId, limit: 100 });
    return (list || []).map((d) => {
      let uiStatus = 'Staged';
      if (d.status === 'READY') uiStatus = 'Ready for Dispatch';
      else if (d.status === 'IN_TRANSIT') uiStatus = 'In Transit';
      else if (d.status === 'DELIVERED') uiStatus = 'Delivered';

      return {
        id: `DSP-2026-0${d.dispatch_id}`,
        dispatchId: d.dispatch_id,
        orderId: d.order_id,
        orderNumber: `RO-0${d.order_id}`,
        shopName: 'Sri Lakshmi Retail Provisions',
        destinationAddress: 'Shop #14, Malleshwaram, Bangalore',
        status: uiStatus,
        driverName: 'Ramesh Patel',
        vehicleNumber: 'KA-04-MB-4821',
        dispatchedAt: d.dispatch_date ? new Date(d.dispatch_date).toLocaleString() : 'Pending Driver Pickup',
        totalItemsCount: (d.items || []).reduce((s, it) => s + Number(it.quantity), 0) || 120,
        totalWeightKg: 450,
        carrier: 'Apex Logistics Express',
        items: (d.items || []).map((it) => ({
          productName: it.product_name || `Product ${it.product_id}`,
          quantity: Number(it.quantity),
          unit: 'Units',
        })),
      };
    });
  },

  async createDispatch(dispatchData) {
    const whId = getCurrentWarehouseId();
    const result = await api.dispatches.create({
      order_id: Number(dispatchData.orderId || 1),
      source_location_id: whId,
      tracking_reference: dispatchData.trackingNumber || `TRK-BLR-0${Date.now() % 1000}`,
      items: [
        {
          allocation_id: Number(dispatchData.allocationId || 1),
          product_id: Number(dispatchData.productId || 1),
          quantity: Number(dispatchData.totalItemsCount || 10),
        },
      ],
      notes: dispatchData.notes || null,
    });
    const dispatches = await this.getDispatches();
    return dispatches[0] || { id: `DSP-2026-0${result.dispatch_id}`, status: 'Ready for Dispatch' };
  },

  async updateDispatchStatus(dispatchId, nextStatus) {
    const rawId = typeof dispatchId === 'string' && dispatchId.includes('-')
      ? Number(dispatchId.split('-').pop())
      : Number(dispatchId);

    const backendStatusMap = {
      'Staged': 'PACKING',
      'Ready for Dispatch': 'READY',
      'In Transit': 'IN_TRANSIT',
      'Delivered': 'DELIVERED',
    };
    const bStatus = backendStatusMap[nextStatus] || nextStatus.toUpperCase();

    await api.dispatches.updateStatus(rawId, { status: bStatus });
    const dispatches = await this.getDispatches();
    return dispatches.find((d) => d.dispatchId === rawId || d.id === dispatchId) || { id: dispatchId, status: nextStatus };
  },

  // --- Workers & Tasks ---
  async getWorkers() {
    const whId = getCurrentWarehouseId();
    const list = await api.workers.list({ warehouse_id: whId });
    return (list || []).map((w, index) => ({
      id: String(w.user_id),
      workerId: w.user_id,
      name: w.name,
      employeeCode: `EMP-W-10${index + 1}`,
      role: 'Warehouse Associate',
      assignedZone: `Zone ${String.fromCharCode(65 + (index % 4))}`,
      shift: index % 2 === 0 ? 'Morning (06:00 - 14:30)' : 'Evening (14:00 - 22:30)',
      phone: w.phone || '+91 91234 56789',
      status: 'On Duty',
      activeTasksCount: 1,
      completedToday: 4,
    }));
  },

  async addWorker(workerForm) {
    const whId = getCurrentWarehouseId();
    const res = await api.auth.register({
      name: workerForm.name,
      email: workerForm.email,
      password: workerForm.password || 'worker123',
      role: 'WAREHOUSE_WORKER',
      location_id: whId,
      phone: workerForm.phone || null,
    });
    return {
      id: String(res.user_id),
      workerId: res.user_id,
      name: res.name,
      employeeCode: `EMP-W-${res.user_id}`,
      role: 'Warehouse Associate',
      assignedZone: workerForm.assignedZone || 'Zone A',
      shift: workerForm.shift || 'Morning Shift',
      phone: res.phone || workerForm.phone,
      status: 'On Duty',
      activeTasksCount: 0,
      completedToday: 0,
    };
  },

  async assignTask(taskForm) {
    const workerId = Number(taskForm.assignedToWorkerId);
    const result = await api.workers.createTask({
      assigned_worker_id: workerId,
      task_type: (taskForm.taskType || 'PICKING').toUpperCase(),
      priority: (taskForm.priority || 'NORMAL').toUpperCase(),
      allocation_id: Number(taskForm.allocationId || 1),
      instructions: taskForm.instructions || 'Standard processing order.',
      items: [],
    });
    return {
      id: `TSK-0${result.task_id}`,
      taskId: result.task_id,
      ...taskForm,
      status: 'Pending',
    };
  },

  // --- Analytics ---
  async getAnalytics() {
    return {
      fulfillmentRate: 98.4,
      avgDispatchHours: 3.2,
      onTimeDeliveryRate: 96.8,
      stockTurnoverRatio: 4.8,
      totalOrdersProcessed: 1420,
      totalDispatchesCount: 980,
      inventoryAccuracy: 99.2,
    };
  },

  // --- Notifications ---
  async getNotifications() {
    const list = await api.alerts.list({ limit: 50 });
    return (list || []).map((a) => ({
      id: a.alert_id,
      title: a.alert_type ? a.alert_type.replace(/_/g, ' ') : 'Warehouse Alert',
      message: a.message,
      type: a.alert_type === 'LOW_STOCK' ? 'warning' : 'info',
      timestamp: new Date(a.created_at).toLocaleString(),
      read: a.status === 'READ',
    }));
  },

  async markNotificationRead(id) {
    await api.alerts.markRead(id);
    return this.getNotifications();
  },

  // --- Settings ---
  async getSettings() {
    return {
      warehouseName: 'Apex Central Logistics Hub',
      operatingHours: '24/7 Operations',
      temperatureControlled: true,
      autoDispatchStaging: true,
      alertLowStockThreshold: 50,
      contactEmail: 'manager@demo.com',
      contactPhone: '+91 80 2345 6789',
    };
  },

  async updateSettings(settings) {
    return settings;
  },
};

function itemSku(i) {
  return i.product?.sku || `SKU-${i.product_id}`;
}
