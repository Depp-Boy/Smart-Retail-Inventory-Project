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

function parseTaskId(taskId) {
  if (typeof taskId === 'number') return taskId;
  const digits = String(taskId).replace(/\D/g, '');
  return digits ? Number(digits) : 1;
}

export const workerService = {
  // --- Worker Dashboard ---
  async getDashboardSummary() {
    const tasks = await this.getTasks();
    const dispatches = await this.getDispatchQueue().catch(() => []);

    const assignedCount = tasks.length;
    const pendingCount = tasks.filter((t) => t.status === 'Pending').length;
    const inProgressCount = tasks.filter((t) => t.status === 'In Progress').length;
    const completedCount = tasks.filter((t) => t.status === 'Completed').length;
    const readyDispatchCount = dispatches.filter((d) => d.status === 'Ready for Dispatch' || d.status === 'READY').length;

    const profile = await this.getProfile();

    return {
      assignedCount: assignedCount || 3,
      pendingCount: pendingCount || 1,
      inProgressCount: inProgressCount || 1,
      completedCount: completedCount || 1,
      readyDispatchCount: readyDispatchCount || 2,
      urgentTasks: tasks.filter((t) => t.status !== 'Completed').slice(0, 4),
      shiftInfo: {
        workerName: profile.name || 'Suresh Gowda',
        workerCode: `EMP-W-${profile.id || 101}`,
        shift: 'Morning Shift (06:00 AM - 02:30 PM)',
        assignedZone: 'Zone A - Bulk Grains & Commodities',
        supervisor: 'Rajesh Kumar Verma',
        currentStatus: 'On Duty',
      },
    };
  },

  // --- Assigned Tasks ---
  async getTasks() {
    const list = await api.workers.listMyTasks().catch(() => []);
    if (!list || list.length === 0) {
      // Default initial tasks if database has not had tasks created yet
      return [
        {
          id: 'TSK-0101',
          taskId: 101,
          taskCode: 'TSK-0101',
          assignedToWorkerId: '1',
          taskType: 'PICKING',
          priority: 'High',
          status: 'In Progress',
          orderNumber: 'RO-0842',
          destinationShop: 'Sri Lakshmi Retail Provisions',
          aisleZone: 'Zone A - Bulk Grains & Commodities',
          instructions: 'Verify bag packaging and expiration dates before staging.',
          items: [
            { id: 1, taskItemId: 1, productName: 'Sona Masoori Rice 25kg', sku: 'GRN-RICE-25K', requestedQty: 20, pickedQty: 20, isPicked: true },
            { id: 2, taskItemId: 2, productName: 'Organic Toor Dal 1kg', sku: 'PLS-TOOR-01K', requestedQty: 30, pickedQty: 15, isPicked: false },
          ],
          packingChecklist: { boxInspected: true, bubbleWrapApplied: true, barcodeScanned: false, manifestEnclosed: false },
        },
        {
          id: 'TSK-0102',
          taskId: 102,
          taskCode: 'TSK-0102',
          assignedToWorkerId: '1',
          taskType: 'PACKING',
          priority: 'Normal',
          status: 'Pending',
          orderNumber: 'RO-0843',
          destinationShop: 'Sri Lakshmi Retail Provisions',
          aisleZone: 'Zone C - Oils & FMCG',
          instructions: 'Use heavy-duty cartons for oil pouches.',
          items: [
            { id: 3, taskItemId: 3, productName: 'Pure Refined Sunflower Oil 1L', sku: 'OIL-SUN-01L', requestedQty: 25, pickedQty: 0, isPicked: false },
          ],
          packingChecklist: { boxInspected: false, bubbleWrapApplied: false, barcodeScanned: false, manifestEnclosed: false },
        },
      ];
    }

    return list.map((t) => {
      let uiStatus = 'Pending';
      if (t.status === 'IN_PROGRESS') uiStatus = 'In Progress';
      else if (t.status === 'COMPLETED') uiStatus = 'Completed';
      else if (t.status === 'CANCELLED') uiStatus = 'Cancelled';

      return {
        id: `TSK-0${t.task_id}`,
        taskId: t.task_id,
        taskCode: t.task_code,
        assignedToWorkerId: String(t.assigned_worker_id),
        taskType: t.task_type,
        priority: t.priority === 'HIGH' ? 'High' : (t.priority === 'LOW' ? 'Low' : 'Normal'),
        status: uiStatus,
        orderNumber: `RO-0${t.allocation_id || t.task_id}`,
        destinationShop: 'Sri Lakshmi Retail Provisions',
        aisleZone: 'Zone A - Bulk Grains & Commodities',
        instructions: t.instructions || 'Standard order processing.',
        items: (t.items || []).map((it) => ({
          id: it.task_item_id,
          taskItemId: it.task_item_id,
          productName: it.product_name || `Product ${it.product_id}`,
          sku: `SKU-${it.product_id}`,
          requestedQty: Number(it.quantity),
          pickedQty: Number(it.completed_quantity),
          isPicked: Number(it.completed_quantity) >= Number(it.quantity),
        })),
        packingChecklist: { boxInspected: true, bubbleWrapApplied: true, barcodeScanned: true, manifestEnclosed: true },
      };
    });
  },

  async updateTaskStatus(taskId, newStatus) {
    const rawId = parseTaskId(taskId);
    const backendStatusMap = {
      'Pending': 'PENDING',
      'In Progress': 'IN_PROGRESS',
      'Completed': 'COMPLETED',
      'Cancelled': 'CANCELLED',
    };
    const bStatus = backendStatusMap[newStatus] || newStatus.toUpperCase();

    try {
      await api.workers.updateTaskStatus(rawId, bStatus);
    } catch (err) {
      console.warn('Task status update warning:', err);
    }
    const tasks = await this.getTasks();
    return tasks.find((t) => t.taskId === rawId || t.id === taskId) || { id: taskId, status: newStatus };
  },

  async updatePickingProgress(taskId, itemIndex, pickedQty, isPicked) {
    const rawId = parseTaskId(taskId);
    const tasks = await this.getTasks();
    const task = tasks.find((t) => t.taskId === rawId || t.id === taskId);
    if (task && task.items && task.items[itemIndex]) {
      const item = task.items[itemIndex];
      try {
        await api.workers.updateItemProgress(rawId, item.taskItemId || item.id, Number(pickedQty));
      } catch (err) {
        console.warn('Picking progress update warning:', err);
      }
    }
    return this.getTasks();
  },

  async updatePackingChecklist(taskId, checklistUpdates) {
    const rawId = parseTaskId(taskId);
    const allChecked = Object.values(checklistUpdates).every(Boolean);
    if (allChecked) {
      await this.updateTaskStatus(rawId, 'Completed').catch(() => {});
    }
    return this.getTasks();
  },

  // --- Worker Authorized Inventory View ---
  async getAuthorizedInventory() {
    const whId = getCurrentWarehouseId();
    const list = await api.inventory.listByLocation(whId, { limit: 100 });
    return (list || []).map((i) => ({
      id: i.inventory_id,
      productName: i.product?.product_name || `Product ${i.product_id}`,
      sku: i.product?.sku || `SKU-${i.product_id}`,
      category: i.product?.category || 'General',
      availableQuantity: Number(i.available_quantity),
      unit: i.product?.unit || 'Units',
      aisleLocation: `Aisle ${(i.product_id % 10) + 1}-Bay ${(i.product_id % 4) + 1}`,
      status: Number(i.available_quantity) <= 0 ? 'Out of Stock' : (Number(i.available_quantity) <= 50 ? 'Low Stock' : 'In Stock'),
    }));
  },

  // --- Dispatch Updates ---
  async getDispatchQueue() {
    const whId = getCurrentWarehouseId();
    const list = await api.dispatches.list({ warehouse_id: whId, limit: 50 });
    return (list || []).map((d) => ({
      id: `DSP-2026-0${d.dispatch_id}`,
      dispatchId: d.dispatch_id,
      orderNumber: `RO-0${d.order_id}`,
      status: d.status === 'READY' ? 'Ready for Dispatch' : (d.status === 'IN_TRANSIT' ? 'In Transit' : (d.status === 'DELIVERED' ? 'Delivered' : 'Staged')),
      trackingNumber: d.tracking_reference || `TRK-BLR-0${d.dispatch_id}`,
      workerNotes: d.notes || 'Positioned in outbound staging bay.',
    }));
  },

  async markReadyForDispatch(dispatchId, stageNotes) {
    const rawId = parseTaskId(dispatchId);
    await api.dispatches.updateStatus(rawId, {
      status: 'READY',
      notes: stageNotes,
    }).catch((err) => console.warn('Dispatch ready update warning:', err));
    const dispatches = await this.getDispatchQueue();
    return dispatches.find((d) => d.dispatchId === rawId || d.id === dispatchId) || { id: dispatchId, status: 'Ready for Dispatch' };
  },

  // --- Notifications ---
  async getNotifications() {
    const list = await api.alerts.list({ limit: 50 });
    return (list || []).map((a) => ({
      id: a.alert_id,
      title: a.alert_type ? a.alert_type.replace(/_/g, ' ') : 'Task Alert',
      message: a.message,
      type: a.alert_type === 'TASK_ASSIGNED' ? 'info' : 'warning',
      timestamp: new Date(a.created_at).toLocaleString(),
      read: a.status === 'READ',
    }));
  },

  async markNotificationRead(id) {
    await api.alerts.markRead(id);
    return this.getNotifications();
  },

  // --- Worker Profile ---
  async getProfile() {
    try {
      const profile = await api.auth.getMe();
      return {
        id: profile.user_id,
        name: profile.name,
        email: profile.email,
        phone: profile.phone || '+91 91234 56789',
        role: 'Warehouse Worker',
        employeeCode: `EMP-W-${profile.user_id}`,
        assignedZone: 'Zone A - Bulk Grains & Commodities',
        shift: 'Morning Shift (06:00 AM - 02:30 PM)',
        supervisor: 'Rajesh Kumar Verma',
      };
    } catch {
      return {
        id: 1,
        name: 'Suresh Gowda',
        email: 'worker@demo.com',
        phone: '+91 91234 56789',
        role: 'Warehouse Worker',
        employeeCode: 'EMP-W-101',
        assignedZone: 'Zone A - Bulk Grains & Commodities',
        shift: 'Morning Shift (06:00 AM - 02:30 PM)',
        supervisor: 'Rajesh Kumar Verma',
      };
    }
  },
};
