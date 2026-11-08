import { initialTasks, initialWorkers, initialDispatches } from '../data/mockWorkersAndTasks';
import { initialWarehouseInventory } from '../data/mockInventory';
import { initialWorkerNotifications } from '../data/mockNotifications';

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

export const workerService = {
  // --- Worker Dashboard ---
  async getDashboardSummary(workerId = 'wrk-001') {
    const tasks = getStored('wh_tasks', initialTasks);
    const workerTasks = tasks.filter((t) => t.assignedToWorkerId === workerId);
    const dispatches = getStored('wh_dispatches', initialDispatches);

    const assignedCount = workerTasks.length;
    const pendingCount = workerTasks.filter((t) => t.status === 'Pending').length;
    const inProgressCount = workerTasks.filter((t) => t.status === 'In Progress').length;
    const completedCount = workerTasks.filter((t) => t.status === 'Completed').length;
    const readyDispatchCount = dispatches.filter((d) => d.status === 'Ready for Dispatch').length;

    return {
      assignedCount,
      pendingCount,
      inProgressCount,
      completedCount,
      readyDispatchCount,
      urgentTasks: workerTasks.filter((t) => t.status !== 'Completed').slice(0, 4),
      shiftInfo: {
        workerName: 'Suresh Gowda',
        workerCode: 'EMP-W-101',
        shift: 'Morning Shift (06:00 AM - 02:30 PM)',
        assignedZone: 'Zone A - Bulk Grains & Commodities',
        supervisor: 'Rajesh Kumar Verma',
        currentStatus: 'On Duty',
      },
    };
  },

  // --- Assigned Tasks ---
  async getTasks(workerId = 'wrk-001') {
    const tasks = getStored('wh_tasks', initialTasks);
    return tasks.filter((t) => t.assignedToWorkerId === workerId || !t.assignedToWorkerId);
  },

  async updateTaskStatus(taskId, newStatus) {
    const tasks = getStored('wh_tasks', initialTasks);
    const updated = tasks.map((t) => {
      if (t.id === taskId) {
        return {
          ...t,
          status: newStatus,
        };
      }
      return t;
    });
    setStored('wh_tasks', updated);
    return updated.find((t) => t.id === taskId);
  },

  async updatePickingProgress(taskId, itemIndex, pickedQty, isPicked) {
    const tasks = getStored('wh_tasks', initialTasks);
    const updated = tasks.map((t) => {
      if (t.id === taskId) {
        const items = [...t.items];
        items[itemIndex] = {
          ...items[itemIndex],
          pickedQty: Number(pickedQty),
          isPicked: Boolean(isPicked),
        };
        const allPicked = items.every((i) => i.isPicked && i.pickedQty >= i.requestedQty);
        return {
          ...t,
          items,
          status: allPicked ? 'In Progress' : t.status,
        };
      }
      return t;
    });
    setStored('wh_tasks', updated);
    return updated.find((t) => t.id === taskId);
  },

  async updatePackingChecklist(taskId, checklistUpdates) {
    const tasks = getStored('wh_tasks', initialTasks);
    const updated = tasks.map((t) => {
      if (t.id === taskId) {
        const packingChecklist = {
          ...t.packingChecklist,
          ...checklistUpdates,
        };
        const allChecked = Object.values(packingChecklist).every(Boolean);
        return {
          ...t,
          packingChecklist,
          status: allChecked ? 'Completed' : t.status,
        };
      }
      return t;
    });
    setStored('wh_tasks', updated);
    return updated.find((t) => t.id === taskId);
  },

  // --- Worker Authorized Inventory View ---
  async getAuthorizedInventory() {
    const inventory = getStored('wh_inventory', initialWarehouseInventory);
    // Worker view only exposes operational storage info (read-only)
    return inventory.map((i) => ({
      id: i.id,
      productName: i.productName,
      sku: i.sku,
      category: i.category,
      availableQuantity: i.availableQuantity,
      unit: i.unit,
      aisleLocation: i.aisleLocation,
      status: i.status,
    }));
  },

  // --- Dispatch Updates ---
  async getDispatchQueue() {
    return getStored('wh_dispatches', initialDispatches);
  },

  async markReadyForDispatch(dispatchId, stageNotes) {
    const dispatches = getStored('wh_dispatches', initialDispatches);
    const updated = dispatches.map((d) => {
      if (d.id === dispatchId) {
        return {
          ...d,
          status: 'Ready for Dispatch',
          workerNotes: stageNotes || 'Inspected and positioned in outbound staging bay.',
        };
      }
      return d;
    });
    setStored('wh_dispatches', updated);
    return updated.find((d) => d.id === dispatchId);
  },

  // --- Notifications ---
  async getNotifications() {
    return getStored('wk_notifications', initialWorkerNotifications);
  },

  async markNotificationRead(id) {
    const current = getStored('wk_notifications', initialWorkerNotifications);
    const updated = current.map((n) => n.id === id ? { ...n, read: true } : n);
    setStored('wk_notifications', updated);
    return updated;
  },

  // --- Worker Profile ---
  async getProfile() {
    const workers = getStored('wh_workers', initialWorkers);
    return workers[0] || initialWorkers[0];
  },
};
