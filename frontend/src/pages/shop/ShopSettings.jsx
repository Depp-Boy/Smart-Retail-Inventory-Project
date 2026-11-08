import { useState, useEffect } from "react";
import { Settings, Bell, RefreshCw, Shield, Save, RotateCcw } from "lucide-react";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Button from "../../components/ui/Button";

const DEFAULT_SETTINGS = {
  autoReorderEnabled: false,
  autoReorderThresholdPercent: 20,
  autoReorderLeadDays: 3,
  preferredWarehouseOnly: true,
  notifyLowStock: true,
  notifyOutOfStock: true,
  notifyOrderAccepted: true,
  notifyOrderDispatched: true,
  notifyOrderDelivered: true,
  notifyForecastAlerts: false,
  notifyWeeklySummary: true,
  defaultLowStockThreshold: 20,
  defaultCriticalStockThreshold: 5,
  defaultReorderQuantityMultiplier: 2,
  currency: "INR",
  dateFormat: "DD/MM/YYYY",
  timezone: "Asia/Kolkata",
};

function ToggleSwitch({ checked, onChange }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${checked ? "bg-blue-600" : "bg-gray-300"}`}
    >
      <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition-transform duration-200 ease-in-out mt-0.5 ${checked ? "translate-x-5" : "translate-x-0.5"}`} />
    </button>
  );
}

function SectionCard({ icon: Icon, title, description, children }) {
  return (
    <Card className="p-6">
      <div className="flex items-start gap-3 mb-6">
        <div className="p-2 bg-blue-50 rounded-lg">
          <Icon className="w-5 h-5 text-blue-600" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900">{title}</h3>
          {description && <p className="text-sm text-gray-500 mt-0.5">{description}</p>}
        </div>
      </div>
      <div className="space-y-1">{children}</div>
    </Card>
  );
}

function SettingRow({ label, description, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 border-b border-gray-100 last:border-b-0">
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-700">{label}</p>
        {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function NumInput({ value, onChange, min, max, step, disabled }) {
  return (
    <input
      type="number"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      disabled={disabled}
      className="w-20 border border-gray-300 rounded-lg px-3 py-1.5 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
    />
  );
}

function SelectInput({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

export default function ShopSettings() {
  const { toast } = useToast();
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("stocksense_shop_settings");
    if (stored) {
      try { setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(stored) }); }
      catch { setSettings(DEFAULT_SETTINGS); }
    }
  }, []);

  const update = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 600));
    localStorage.setItem("stocksense_shop_settings", JSON.stringify(settings));
    setSaving(false);
    setDirty(false);
    toast.success("Settings saved successfully.");
  };

  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS);
    setDirty(true);
    toast.info("Settings reset to defaults. Click Save to apply.");
  };

  const notifications = [
    { key: "notifyLowStock", label: "Low Stock Alerts", description: "Alert when a product falls below reorder threshold." },
    { key: "notifyOutOfStock", label: "Out of Stock Alerts", description: "Immediate alert when a product reaches zero stock." },
    { key: "notifyOrderAccepted", label: "Order Accepted", description: "Notify when warehouse confirms your restock order." },
    { key: "notifyOrderDispatched", label: "Order Dispatched", description: "Notify when the delivery vehicle is en route." },
    { key: "notifyOrderDelivered", label: "Order Delivered", description: "Notify on successful delivery confirmation." },
    { key: "notifyForecastAlerts", label: "Forecast Alerts", description: "Notify for predicted stockouts 7+ days in advance." },
    { key: "notifyWeeklySummary", label: "Weekly Summary Report", description: "Receive a weekly digest of sales and inventory health." },
  ];

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <PageHeader title="Shop Settings" subtitle="Configure auto-reorder rules, notification preferences, and inventory thresholds." />
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={handleReset} icon={RotateCcw}>Reset to Defaults</Button>
          <Button variant="primary" size="sm" onClick={handleSave} disabled={saving || !dirty} icon={Save}>
            {saving ? "Saving…" : "Save Changes"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SectionCard icon={RefreshCw} title="Auto-Reorder Rules" description="Automatically generate restock orders when stock falls below threshold.">
          <SettingRow label="Enable Auto-Reorder" description="System will create draft orders when stock is critically low.">
            <ToggleSwitch checked={settings.autoReorderEnabled} onChange={(v) => update("autoReorderEnabled", v)} />
          </SettingRow>
          <SettingRow label="Trigger Threshold" description="Auto-reorder fires when available stock falls below this % of reorder point.">
            <div className="flex items-center gap-2">
              <NumInput value={settings.autoReorderThresholdPercent} onChange={(v) => update("autoReorderThresholdPercent", v)} min={5} max={50} disabled={!settings.autoReorderEnabled} />
              <span className="text-sm text-gray-500">%</span>
            </div>
          </SettingRow>
          <SettingRow label="Lead Time Buffer" description="Add extra days to delivery estimates for safety stock calculation.">
            <div className="flex items-center gap-2">
              <NumInput value={settings.autoReorderLeadDays} onChange={(v) => update("autoReorderLeadDays", v)} min={1} max={14} disabled={!settings.autoReorderEnabled} />
              <span className="text-sm text-gray-500">days</span>
            </div>
          </SettingRow>
          <SettingRow label="Preferred Warehouse Only" description="Restrict auto-reorder to your designated preferred warehouse.">
            <ToggleSwitch checked={settings.preferredWarehouseOnly} onChange={(v) => update("preferredWarehouseOnly", v)} />
          </SettingRow>
        </SectionCard>

        <SectionCard icon={Bell} title="Notification Preferences" description="Choose which events trigger in-app and email notifications.">
          {notifications.map(({ key, label, description }) => (
            <SettingRow key={key} label={label} description={description}>
              <ToggleSwitch checked={settings[key]} onChange={(v) => update(key, v)} />
            </SettingRow>
          ))}
        </SectionCard>

        <SectionCard icon={Shield} title="Default Stock Thresholds" description="These values apply to newly added products unless overridden individually.">
          <SettingRow label="Low Stock Threshold" description="Products below this quantity are marked as Low Stock.">
            <div className="flex items-center gap-2">
              <NumInput value={settings.defaultLowStockThreshold} onChange={(v) => update("defaultLowStockThreshold", v)} min={1} max={500} />
              <span className="text-sm text-gray-500">units</span>
            </div>
          </SettingRow>
          <SettingRow label="Critical Stock Threshold" description="Products below this quantity trigger urgent alerts.">
            <div className="flex items-center gap-2">
              <NumInput value={settings.defaultCriticalStockThreshold} onChange={(v) => update("defaultCriticalStockThreshold", v)} min={0} max={100} />
              <span className="text-sm text-gray-500">units</span>
            </div>
          </SettingRow>
          <SettingRow label="Reorder Quantity Multiplier" description="Auto-reorder quantity = (reorder threshold x multiplier).">
            <div className="flex items-center gap-2">
              <NumInput value={settings.defaultReorderQuantityMultiplier} onChange={(v) => update("defaultReorderQuantityMultiplier", v)} min={1} max={10} step={0.5} />
              <span className="text-sm text-gray-500">x</span>
            </div>
          </SettingRow>
        </SectionCard>

        <SectionCard icon={Settings} title="Display & Regional" description="Locale and formatting preferences for your shop dashboard.">
          <SettingRow label="Currency" description="Currency symbol displayed across the application.">
            <SelectInput value={settings.currency} onChange={(v) => update("currency", v)} options={[
              { value: "INR", label: "INR — Indian Rupee (₹)" },
              { value: "USD", label: "USD — US Dollar ($)" },
              { value: "EUR", label: "EUR — Euro (€)" },
            ]} />
          </SettingRow>
          <SettingRow label="Date Format" description="Date display format across the application.">
            <SelectInput value={settings.dateFormat} onChange={(v) => update("dateFormat", v)} options={[
              { value: "DD/MM/YYYY", label: "DD/MM/YYYY (Indian Standard)" },
              { value: "MM/DD/YYYY", label: "MM/DD/YYYY (US Format)" },
              { value: "YYYY-MM-DD", label: "YYYY-MM-DD (ISO 8601)" },
            ]} />
          </SettingRow>
          <SettingRow label="Timezone" description="All timestamps will be displayed in this timezone.">
            <SelectInput value={settings.timezone} onChange={(v) => update("timezone", v)} options={[
              { value: "Asia/Kolkata", label: "Asia/Kolkata (IST, UTC+5:30)" },
              { value: "UTC", label: "UTC (Coordinated Universal Time)" },
              { value: "America/New_York", label: "America/New_York (EST)" },
            ]} />
          </SettingRow>
        </SectionCard>
      </div>

      {dirty && (
        <div className="fixed bottom-6 right-6 z-50">
          <div className="flex items-center gap-3 bg-gray-900 text-white px-4 py-3 rounded-xl shadow-2xl">
            <span className="text-sm">You have unsaved changes.</span>
            <button onClick={handleSave} disabled={saving}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors disabled:opacity-50">
              {saving ? "Saving…" : "Save Now"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
