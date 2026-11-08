import { useState, useEffect } from "react";
import { Save, RotateCcw, Building2, MapPin, Settings, Bell } from "lucide-react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Button from "../../components/ui/Button";

function ToggleSwitch({ checked, onChange }) {
  return (
    <button role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${checked ? "bg-blue-600" : "bg-gray-300"}`}>
      <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition-transform duration-200 ease-in-out mt-0.5 ${checked ? "translate-x-5" : "translate-x-0.5"}`} />
    </button>
  );
}

function SectionCard({ icon: Icon, title, description, children }) {
  return (
    <Card className="p-6">
      <div className="flex items-start gap-3 mb-5">
        <div className="p-2 bg-blue-50 rounded-lg"><Icon className="w-5 h-5 text-blue-600" /></div>
        <div>
          <h3 className="font-semibold text-gray-900">{title}</h3>
          {description && <p className="text-sm text-gray-500 mt-0.5">{description}</p>}
        </div>
      </div>
      <div className="space-y-4">{children}</div>
    </Card>
  );
}

function Field({ label, value, onChange, type = "text", required }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
      <input type={type} value={value ?? ""} onChange={(e) => onChange(e.target.value)} required={!!required}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
    </div>
  );
}

function ToggleRow({ label, description, checked, onChange }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 border-b border-gray-100 last:border-b-0">
      <div><p className="text-sm font-medium text-gray-700">{label}</p>{description && <p className="text-xs text-gray-500">{description}</p>}</div>
      <ToggleSwitch checked={checked} onChange={onChange} />
    </div>
  );
}

export default function WarehouseSettings() {
  const { toast } = useToast();
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    warehouseService.getSettings().then(setSettings);
  }, []);

  if (!settings) return null;

  const upd = (key, val) => { setSettings((p) => ({ ...p, [key]: val })); setDirty(true); };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await warehouseService.updateSettings(settings);
      setDirty(false);
      toast.success("Warehouse settings saved.");
    } catch { toast.error("Failed to save settings."); }
    finally { setSaving(false); }
  };

  return (
    <form onSubmit={handleSave}>
      <div className="p-4 md:p-6 space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <PageHeader title="Warehouse Settings" subtitle="Configure warehouse details, worker permissions, and operational preferences." />
          <div className="flex gap-3">
            <Button type="button" variant="ghost" size="sm" icon={RotateCcw} onClick={() => { warehouseService.getSettings().then(setSettings); setDirty(false); }}>Reset</Button>
            <Button type="submit" variant="primary" size="sm" icon={Save} disabled={saving || !dirty}>{saving ? "Saving…" : "Save Changes"}</Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Warehouse Identity */}
          <SectionCard icon={Building2} title="Warehouse Identity" description="Core identification details for this warehouse.">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Warehouse Name" value={settings.warehouseName} onChange={(v) => upd("warehouseName", v)} required />
              <Field label="Warehouse Code" value={settings.code} onChange={(v) => upd("code", v)} required />
              <Field label="Manager Name" value={settings.managerName} onChange={(v) => upd("managerName", v)} />
              <Field label="Phone" value={settings.phone} onChange={(v) => upd("phone", v)} />
              <Field label="Email" value={settings.email} onChange={(v) => upd("email", v)} type="email" />
              <Field label="Operating Hours" value={settings.operatingHours} onChange={(v) => upd("operatingHours", v)} />
            </div>
          </SectionCard>

          {/* Location */}
          <SectionCard icon={MapPin} title="Location & Address" description="Physical address and location details.">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <Field label="Street Address" value={settings.address} onChange={(v) => upd("address", v)} />
              </div>
              <Field label="City" value={settings.city} onChange={(v) => upd("city", v)} />
              <Field label="State" value={settings.state} onChange={(v) => upd("state", v)} />
              <Field label="Pincode" value={settings.pincode} onChange={(v) => upd("pincode", v)} />
            </div>
          </SectionCard>

          {/* Capacity */}
          <SectionCard icon={Settings} title="Capacity & Operations" description="Warehouse physical capacity specifications.">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Total Area (sq ft)" value={settings.totalCapacitySqFt} onChange={(v) => upd("totalCapacitySqFt", v)} type="number" />
              <Field label="Max Pallet Capacity" value={settings.maxPalletsCapacity} onChange={(v) => upd("maxPalletsCapacity", v)} type="number" />
            </div>
          </SectionCard>

          {/* Operational preferences */}
          <SectionCard icon={Bell} title="Operational Preferences" description="Fulfilment rules and notification settings.">
            <ToggleRow label="Auto-Notify Shop Managers" description="Automatically notify shops when their order status changes." checked={settings.autoNotifyManagers} onChange={(v) => upd("autoNotifyManagers", v)} />
            <ToggleRow label="Allow Partial Allocations" description="Accept shop orders even when full stock is not available; allocate what is available." checked={settings.partialAllocationAllowed} onChange={(v) => upd("partialAllocationAllowed", v)} />
          </SectionCard>
        </div>
      </div>
    </form>
  );
}
