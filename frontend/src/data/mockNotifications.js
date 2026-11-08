/**
 * Mock Notifications Data categorized for all three roles.
 */

export const initialShopNotifications = [
  {
    id: 'notif-s-001',
    category: 'Low stock',
    title: 'Critical Stock Alert: Toor Dal Premium',
    message: 'Toor Dal Premium Unpolished is currently at 0 kg (Out of Stock). Restock replenishment is urgently recommended.',
    timestamp: '10 mins ago',
    read: false,
    link: '/shop/orders',
  },
  {
    id: 'notif-s-002',
    category: 'Order dispatched',
    title: 'Order Dispatched: RO-0839',
    message: 'Your replenishment order RO-0839 from Apex Central Hub has been dispatched. Carrier: FastTrack Fleet (#FT-TRK-99201).',
    timestamp: '1 hour ago',
    read: false,
    link: '/shop/tracking',
  },
  {
    id: 'notif-s-003',
    category: 'Order accepted',
    title: 'Order Partially Allocated: RO-0841',
    message: 'Apex Central Hub accepted RO-0841 with partial fulfillment. 80 kg Rice has been rerouted to Metro East Depot.',
    timestamp: '3 hours ago',
    read: false,
    link: '/shop/tracking',
  },
  {
    id: 'notif-s-004',
    category: 'Forecast alerts',
    title: 'Demand Spike Forecasted: Sona Masoori Rice',
    message: 'Projected demand is expected to increase by 18% over the next 14 days due to festive seasons. Expected stockout in 4 days.',
    timestamp: 'Yesterday',
    read: true,
    link: '/shop/forecast',
  },
  {
    id: 'notif-s-005',
    category: 'Order delivered',
    title: 'Order Delivered: RO-0835',
    message: 'Replenishment order RO-0835 containing 50 units was marked as delivered and verified by store staff.',
    timestamp: '3 days ago',
    read: true,
    link: '/shop/tracking',
  },
  {
    id: 'notif-s-006',
    category: 'Order rejected',
    title: 'Order Rejected: RO-0830',
    message: 'North Suburban Buffer Center rejected RO-0830 due to capacity limitations. Recommended alternative: Apex Central.',
    timestamp: 'Oct 25',
    read: true,
    link: '/shop/warehouses',
  },
];

export const initialWarehouseNotifications = [
  {
    id: 'notif-w-001',
    category: 'Incoming requests',
    title: 'New Restock Request: Ganesh General Supermarket',
    message: 'Order RO-0842 received requesting 280 units (Refined Sugar and Salt). Awaiting manager acceptance.',
    timestamp: '15 mins ago',
    read: false,
    link: '/warehouse/requests',
  },
  {
    id: 'notif-w-002',
    category: 'Low stock warnings',
    title: 'Warehouse Low Available Stock: Toor Dal Unpolished',
    message: 'Available quantity dropped to 30 kg due to allocation on order RO-0841. Total stock: 350 kg (320 kg reserved).',
    timestamp: '2 hours ago',
    read: false,
    link: '/warehouse/inventory',
  },
  {
    id: 'notif-w-003',
    category: 'Dispatch confirmations',
    title: 'Dispatch Confirmed: RO-0839',
    message: 'Truck KA-04-E-8819 departed loading dock with 160 kg commodity consignment for Sri Lakshmi Provisions.',
    timestamp: '3 hours ago',
    read: true,
    link: '/warehouse/dispatch',
  },
  {
    id: 'notif-w-004',
    category: 'Shift updates',
    title: 'Morning Shift Task Completion: 94%',
    message: 'Morning shift workers completed 28 of 30 assigned picking and palletizing tasks on schedule.',
    timestamp: 'Yesterday',
    read: true,
    link: '/warehouse/workers',
  },
];

export const initialWorkerNotifications = [
  {
    id: 'notif-wk-001',
    category: 'Task assignment',
    title: 'New High Priority Task Assigned: TSK-1092',
    message: 'Manager assigned order RO-0841 picking list (Rice, Toor Dal, Sunflower Oil). Due by 02:00 PM.',
    timestamp: '30 mins ago',
    read: false,
    link: '/worker/tasks',
  },
  {
    id: 'notif-wk-002',
    category: 'Manager instructions',
    title: 'Dock 3 Pallet Staging Notice',
    message: 'Please ensure all packed boxes for FastTrack carrier are staged in Bay 3B with moisture barrier wrap.',
    timestamp: '2 hours ago',
    read: true,
    link: '/worker/processing',
  },
  {
    id: 'notif-wk-003',
    category: 'Shift updates',
    title: 'Tomorrow Shift Roster Confirmed',
    message: 'Your schedule is confirmed for Morning Shift (06:00 AM - 02:30 PM) in Zone A.',
    timestamp: 'Yesterday',
    read: true,
    link: '/worker/profile',
  },
];
