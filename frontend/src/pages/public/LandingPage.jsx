import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Package2, Menu, X, ArrowRight, CheckCircle, BarChart2, Warehouse, RefreshCw,
  Layers, TrendingUp, Bell, Store, ClipboardList, Truck, ChevronRight,
  Database, Zap, Shield,
} from 'lucide-react';

// ─── Navbar ─────────────────────────────────────────────────────────────────
function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navLinks = [
    { label: 'Home',        href: '#home' },
    { label: 'Features',    href: '#features' },
    { label: 'How It Works',href: '#how-it-works' },
    { label: 'About',       href: '#about' },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-md border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <Package2 size={18} className="text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">StockSense</span>
          </div>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-7">
            {navLinks.map((l) => (
              <a key={l.label} href={l.href}
                className="text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors">
                {l.label}
              </a>
            ))}
          </div>

          {/* Desktop CTAs */}
          <div className="hidden md:flex items-center gap-3">
            <Link to="/login"
              className="text-sm font-medium text-gray-700 hover:text-blue-600 transition-colors px-3 py-1.5">
              Login
            </Link>
            <Link to="/register"
              className="inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
              Get Started <ArrowRight size={14} />
            </Link>
          </div>

          {/* Mobile toggle */}
          <button
            className="md:hidden p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-white border-t border-gray-200 px-4 py-4 space-y-1">
          {navLinks.map((l) => (
            <a key={l.label} href={l.href}
              onClick={() => setMobileOpen(false)}
              className="block px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors">
              {l.label}
            </a>
          ))}
          <div className="pt-3 flex flex-col gap-2">
            <Link to="/login" onClick={() => setMobileOpen(false)}
              className="block text-center text-sm font-medium text-gray-700 border border-gray-300 px-4 py-2.5 rounded-lg hover:bg-gray-50 transition-colors">
              Login
            </Link>
            <Link to="/register" onClick={() => setMobileOpen(false)}
              className="block text-center text-sm font-medium bg-blue-600 text-white px-4 py-2.5 rounded-lg hover:bg-blue-700 transition-colors">
              Get Started
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}

// ─── Hero ────────────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section id="home" className="pt-24 pb-16 md:pt-32 md:pb-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left */}
          <div>
            <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-5 border border-blue-100">
              <Zap size={12} />
              DBMS Mini-Project — Smart Retail System
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 leading-tight tracking-tight">
              Smart Inventory.{' '}
              <span className="text-blue-600">Smarter Replenishment.</span>
            </h1>
            <p className="mt-5 text-lg text-gray-500 leading-relaxed max-w-xl">
              A centralized inventory management platform connecting retail shops and warehouses
              through intelligent stock management, seamless replenishment and demand forecasting.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <Link to="/register"
                className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-xl transition-colors text-sm">
                Get Started Free <ArrowRight size={16} />
              </Link>
              <a href="#features"
                className="inline-flex items-center justify-center gap-2 bg-gray-50 hover:bg-gray-100 text-gray-700 font-semibold px-6 py-3 rounded-xl border border-gray-200 transition-colors text-sm">
                Explore Features
              </a>
            </div>
            {/* Trust signals */}
            <div className="mt-8 flex flex-wrap gap-4">
              {['No credit card required', 'Three user roles', 'Real-time tracking'].map((t) => (
                <div key={t} className="flex items-center gap-1.5 text-sm text-gray-500">
                  <CheckCircle size={14} className="text-green-500 flex-shrink-0" />
                  {t}
                </div>
              ))}
            </div>
          </div>

          {/* Right — Dashboard illustration */}
          <div className="relative hidden lg:block">
            <div className="relative rounded-2xl overflow-hidden border border-gray-200 shadow-2xl bg-gray-50">
              {/* Mock dashboard header */}
              <div className="bg-white border-b border-gray-100 px-5 py-3 flex items-center gap-3">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-yellow-400" />
                  <div className="w-3 h-3 rounded-full bg-green-400" />
                </div>
                <div className="flex-1 bg-gray-100 rounded-md h-5 max-w-48 mx-auto" />
              </div>
              {/* Mock dashboard body */}
              <div className="flex h-72">
                {/* Sidebar mock */}
                <div className="w-14 bg-[#1e2a3b] flex flex-col items-center py-4 gap-3">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className={['w-7 h-7 rounded-lg', i === 0 ? 'bg-blue-600' : 'bg-white/10'].join(' ')} />
                  ))}
                </div>
                {/* Content mock */}
                <div className="flex-1 p-4 space-y-3">
                  {/* Stat cards */}
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { label: 'Total SKUs', val: '1,248', color: 'blue' },
                      { label: 'Low Stock', val: '23', color: 'orange' },
                      { label: 'Pending', val: '7', color: 'green' },
                    ].map((s) => (
                      <div key={s.label} className="bg-white rounded-lg p-2.5 border border-gray-100 shadow-sm">
                        <p className="text-[9px] text-gray-400 font-medium uppercase tracking-wide">{s.label}</p>
                        <p className={[
                          'text-base font-bold mt-0.5',
                          s.color === 'blue' ? 'text-blue-600' :
                          s.color === 'orange' ? 'text-orange-500' : 'text-green-600',
                        ].join(' ')}>{s.val}</p>
                      </div>
                    ))}
                  </div>
                  {/* Chart mock */}
                  <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-3 h-24">
                    <p className="text-[9px] text-gray-400 font-semibold uppercase tracking-wide mb-2">Stock Trend</p>
                    <div className="flex items-end gap-1 h-14">
                      {[40, 65, 45, 80, 55, 90, 70, 85, 60, 75, 95, 68].map((h, i) => (
                        <div key={i} className="flex-1 rounded-sm bg-blue-500/20 relative">
                          <div
                            className="absolute bottom-0 left-0 right-0 rounded-sm bg-blue-500"
                            style={{ height: `${h}%` }}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                  {/* Table mock */}
                  <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-3">
                    <p className="text-[9px] text-gray-400 font-semibold uppercase tracking-wide mb-2">Recent Orders</p>
                    <div className="space-y-1.5">
                      {[
                        { id: '#ORD-001', status: 'Delivered', color: 'bg-green-100 text-green-700' },
                        { id: '#ORD-002', status: 'Processing', color: 'bg-blue-100 text-blue-700' },
                        { id: '#ORD-003', status: 'Pending', color: 'bg-orange-100 text-orange-700' },
                      ].map((row) => (
                        <div key={row.id} className="flex items-center justify-between">
                          <span className="text-[10px] text-gray-600 font-medium">{row.id}</span>
                          <span className={['text-[9px] px-1.5 py-0.5 rounded-full font-medium', row.color].join(' ')}>
                            {row.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            {/* Floating badge */}
            <div className="absolute -bottom-4 -left-4 bg-white rounded-xl shadow-lg border border-gray-200 px-4 py-3 flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                <TrendingUp size={16} className="text-green-600" />
              </div>
              <div>
                <p className="text-xs font-bold text-gray-900">Demand Forecast</p>
                <p className="text-xs text-gray-500">+12% this week</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Problem & Solution ──────────────────────────────────────────────────────
function ProblemSolution() {
  const problems = [
    {
      icon: ClipboardList,
      title: 'Manual Stock Tracking',
      desc: 'Spreadsheets and paper-based records lead to counting errors, lost data, and wasted time.',
    },
    {
      icon: Warehouse,
      title: 'Supplier Communication Gaps',
      desc: "Reaching suppliers requires phone calls, emails, and guesswork — there's no single system.",
    },
    {
      icon: BarChart2,
      title: 'Zero Inventory Visibility',
      desc: 'Shop owners have no real-time view of what is in stock, what is moving, or what will run out.',
    },
    {
      icon: Bell,
      title: 'Reactive Replenishment',
      desc: 'Stock-outs happen because orders are only placed after shelves are already empty.',
    },
  ];

  const solutions = [
    'Real-time inventory tracking across all SKUs',
    'Direct replenishment requests to preferred warehouses',
    'Live order status and delivery tracking',
    'Demand forecasting to order before stock runs out',
    'Multi-role access for shop owners, managers & workers',
    'Unified dashboard for all inventory operations',
  ];

  return (
    <section className="py-16 md:py-24 bg-gray-50" id="about">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900">The Problem We Solve</h2>
          <p className="mt-3 text-gray-500 max-w-2xl mx-auto">
            Small retail businesses waste hours every week managing inventory manually. StockSense replaces
            the chaos with a streamlined, connected system.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-10 items-start">
          {/* Problems */}
          <div>
            <h3 className="text-sm font-semibold text-red-600 uppercase tracking-wide mb-5">
              Common pain points
            </h3>
            <div className="space-y-4">
              {problems.map((p) => {
                const Icon = p.icon;
                return (
                  <div key={p.title} className="flex gap-4 p-4 bg-white rounded-xl border border-gray-200">
                    <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Icon size={18} className="text-red-500" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{p.title}</p>
                      <p className="text-sm text-gray-500 mt-0.5 leading-relaxed">{p.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Solutions */}
          <div>
            <h3 className="text-sm font-semibold text-green-600 uppercase tracking-wide mb-5">
              How StockSense helps
            </h3>
            <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-3.5">
              {solutions.map((s) => (
                <div key={s} className="flex items-start gap-3">
                  <div className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <CheckCircle size={12} className="text-green-600" />
                  </div>
                  <p className="text-sm text-gray-700">{s}</p>
                </div>
              ))}
            </div>
            <div className="mt-5">
              <Link to="/register"
                className="inline-flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors">
                Start managing smarter <ChevronRight size={16} />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Features ────────────────────────────────────────────────────────────────
function Features() {
  const features = [
    {
      icon: Package2,
      color: 'blue',
      title: 'Inventory Management',
      desc: 'Track every SKU in real time. Get alerts for low stock, manage product categories, and maintain accurate counts effortlessly.',
    },
    {
      icon: Warehouse,
      color: 'purple',
      title: 'Warehouse Connectivity',
      desc: 'Connect directly with multiple warehouses. Browse available stock, set preferred suppliers, and build lasting supply relationships.',
    },
    {
      icon: RefreshCw,
      color: 'green',
      title: 'Smart Replenishment',
      desc: 'Place replenishment requests with a few clicks. Warehouses receive, accept, and process your orders — all tracked in real time.',
    },
    {
      icon: Layers,
      color: 'orange',
      title: 'Multi-Warehouse Allocation',
      desc: 'When one warehouse cannot fulfill an order, inventory is intelligently allocated across multiple sources to complete it.',
    },
    {
      icon: TrendingUp,
      color: 'blue',
      title: 'Demand Forecasting',
      desc: 'ML-powered predictions (next phase) will analyse your sales history to forecast when you need to reorder and how much.',
    },
    {
      icon: BarChart2,
      color: 'green',
      title: 'Analytics & Alerts',
      desc: 'Visual dashboards for sales trends, stock velocity, and order history. Configurable alerts keep you informed at every step.',
    },
  ];

  const colorMap = {
    blue:   { bg: 'bg-blue-50',   icon: 'text-blue-600' },
    purple: { bg: 'bg-purple-50', icon: 'text-purple-600' },
    green:  { bg: 'bg-green-50',  icon: 'text-green-600' },
    orange: { bg: 'bg-orange-50', icon: 'text-orange-600' },
  };

  return (
    <section id="features" className="py-16 md:py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900">Everything You Need</h2>
          <p className="mt-3 text-gray-500 max-w-2xl mx-auto">
            From daily stock tracking to intelligent forecasting — StockSense covers the full
            inventory lifecycle for retail shops and warehouses.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => {
            const Icon = f.icon;
            const c = colorMap[f.color];
            return (
              <div key={f.title}
                className="p-6 rounded-2xl border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all bg-white">
                <div className={['w-11 h-11 rounded-xl flex items-center justify-center mb-4', c.bg].join(' ')}>
                  <Icon size={22} className={c.icon} />
                </div>
                <h3 className="text-base font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─── How It Works ─────────────────────────────────────────────────────────────
function HowItWorks() {
  const steps = [
    {
      step: '01',
      icon: Package2,
      title: 'Shop Manages Inventory',
      desc: 'The shop owner logs in and tracks their current stock levels across all products in real time.',
    },
    {
      step: '02',
      icon: ClipboardList,
      title: 'Replenishment Request Placed',
      desc: 'When stock runs low, the shop places a replenishment request to their preferred warehouse.',
    },
    {
      step: '03',
      icon: Warehouse,
      title: 'Warehouse Receives Request',
      desc: 'The warehouse manager sees the incoming request and reviews available inventory.',
    },
    {
      step: '04',
      icon: CheckCircle,
      title: 'Request Accepted & Processed',
      desc: 'The manager accepts and assigns the task. Workers pick, pack, and prepare the order.',
    },
    {
      step: '05',
      icon: Truck,
      title: 'Shop Tracks Delivery',
      desc: 'The shop can track the order status in real time until it is marked as delivered.',
    },
  ];

  return (
    <section id="how-it-works" className="py-16 md:py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900">How It Works</h2>
          <p className="mt-3 text-gray-500 max-w-xl mx-auto">
            A simple five-step flow connects shop owners with their warehouses for frictionless replenishment.
          </p>
        </div>

        <div className="grid md:grid-cols-5 gap-0">
          {steps.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={s.step} className="flex md:flex-col items-start md:items-center gap-4 md:gap-0 relative pb-8 md:pb-0">
                {/* Connector */}
                {i < steps.length - 1 && (
                  <div className="hidden md:block absolute top-6 left-1/2 w-full h-px bg-gray-200" />
                )}
                {/* Icon */}
                <div className="relative flex-shrink-0 md:mx-auto">
                  <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center z-10 relative shadow-md">
                    <Icon size={20} className="text-white" />
                  </div>
                  <span className="absolute -top-2 -right-2 w-5 h-5 bg-white border-2 border-blue-600 rounded-full text-[9px] font-bold text-blue-600 flex items-center justify-center">
                    {i + 1}
                  </span>
                </div>
                {/* Text */}
                <div className="md:text-center md:mt-4 md:px-2 flex-1">
                  <p className="text-sm font-semibold text-gray-900">{s.title}</p>
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─── User Roles ───────────────────────────────────────────────────────────────
function UserRoles() {
  const roles = [
    {
      icon: Store,
      title: 'Shop Owner',
      color: 'blue',
      desc: 'Manage your shop\'s inventory, browse connected warehouses, place replenishment orders, and monitor delivery status — all from one dashboard.',
      capabilities: [
        'Real-time inventory dashboard',
        'Product and SKU management',
        'Replenishment order creation',
        'Order tracking and history',
        'Sales analytics',
        'Demand forecasting',
      ],
    },
    {
      icon: Warehouse,
      title: 'Warehouse Manager',
      color: 'purple',
      desc: 'Oversee all warehouse operations. Accept shop requests, manage stock levels, allocate inventory, and coordinate your worker team.',
      capabilities: [
        'Incoming request management',
        'Warehouse inventory control',
        'Worker assignment and oversight',
        'Multi-shop order fulfilment',
        'Dispatch and delivery management',
        'Operational analytics',
      ],
    },
    {
      icon: Shield,
      title: 'Warehouse Worker',
      color: 'green',
      desc: 'Execute warehouse tasks efficiently. Pick products, process orders, update inventory counts, and prepare dispatches as assigned by your manager.',
      capabilities: [
        'Task queue and assignment view',
        'Order picking and packing',
        'Inventory count updates',
        'Dispatch preparation',
        'Real-time task status updates',
        'Worker profile management',
      ],
    },
  ];

  const colorMap = {
    blue:   { bg: 'bg-blue-50',   border: 'border-blue-200',   icon: 'text-blue-600',   dot: 'bg-blue-500', header: 'bg-blue-600' },
    purple: { bg: 'bg-purple-50', border: 'border-purple-200', icon: 'text-purple-600', dot: 'bg-purple-500', header: 'bg-purple-600' },
    green:  { bg: 'bg-green-50',  border: 'border-green-200',  icon: 'text-green-600',  dot: 'bg-green-500', header: 'bg-green-600' },
  };

  return (
    <section className="py-16 md:py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900">Built for Three Roles</h2>
          <p className="mt-3 text-gray-500 max-w-xl mx-auto">
            StockSense serves every stakeholder in the retail supply chain with role-specific
            dashboards and permissions.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {roles.map((r) => {
            const Icon = r.icon;
            const c = colorMap[r.color];
            return (
              <div key={r.title} className={['rounded-2xl border overflow-hidden', c.border].join(' ')}>
                <div className={['p-6 flex items-center gap-3', c.bg].join(' ')}>
                  <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-sm">
                    <Icon size={20} className={c.icon} />
                  </div>
                  <h3 className="text-base font-bold text-gray-900">{r.title}</h3>
                </div>
                <div className="p-6 bg-white">
                  <p className="text-sm text-gray-500 leading-relaxed mb-4">{r.desc}</p>
                  <ul className="space-y-2">
                    {r.capabilities.map((cap) => (
                      <li key={cap} className="flex items-center gap-2.5 text-sm text-gray-700">
                        <span className={['w-1.5 h-1.5 rounded-full flex-shrink-0', c.dot].join(' ')} />
                        {cap}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─── CTA Banner ───────────────────────────────────────────────────────────────
function CTABanner() {
  return (
    <section className="py-16 bg-blue-600">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 className="text-3xl font-bold text-white mb-3">
          Ready to modernise your inventory?
        </h2>
        <p className="text-blue-100 mb-8 text-lg">
          Join StockSense and connect your retail shop with your warehouse today.
        </p>
        <div className="flex flex-col sm:flex-row justify-center gap-3">
          <Link to="/register"
            className="inline-flex items-center justify-center gap-2 bg-white text-blue-600 font-semibold px-7 py-3 rounded-xl hover:bg-blue-50 transition-colors text-sm">
            Create Account <ArrowRight size={16} />
          </Link>
          <Link to="/login"
            className="inline-flex items-center justify-center gap-2 border border-white/40 text-white font-semibold px-7 py-3 rounded-xl hover:bg-white/10 transition-colors text-sm">
            Sign In
          </Link>
        </div>
      </div>
    </section>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────────────
function Footer() {
  const links = {
    Product: ['Features', 'How It Works', 'Pricing'],
    Roles: ['Shop Owners', 'Warehouse Managers', 'Warehouse Workers'],
    Project: ['About', 'Documentation', 'Contact'],
  };

  return (
    <footer className="bg-gray-900 text-gray-400 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-10">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
                <Package2 size={15} className="text-white" />
              </div>
              <span className="text-sm font-bold text-white">StockSense</span>
            </div>
            <p className="text-xs leading-relaxed">
              A smart retail inventory management and demand forecasting system. Built as a DBMS
              mini-project.
            </p>
          </div>

          {/* Link groups */}
          {Object.entries(links).map(([group, items]) => (
            <div key={group}>
              <h4 className="text-xs font-semibold text-white uppercase tracking-wide mb-3">{group}</h4>
              <ul className="space-y-2">
                {items.map((item) => (
                  <li key={item}>
                    <span className="text-xs hover:text-gray-300 transition-colors cursor-default">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="pt-8 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <p>© {new Date().getFullYear()} StockSense — Smart Retail Inventory Project</p>
          <p>DBMS Mini-Project · Built with React, Vite & Tailwind CSS</p>
        </div>
      </div>
    </footer>
  );
}

// ─── Landing Page ─────────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <Hero />
      <ProblemSolution />
      <Features />
      <HowItWorks />
      <UserRoles />
      <CTABanner />
      <Footer />
    </div>
  );
}
