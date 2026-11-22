import { useState, useEffect } from "react";
import { CheckSquare, Square, ChevronDown, ChevronUp, Package, Save } from "lucide-react";
import { workerService } from "../../services/workerService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

const CHECKLIST_LABELS = {
  palletsStrapped: "Pallets strapped and secured",
  batchLabelsAffixed: "Batch / expiry labels affixed",
  invoiceAttached: "Invoice / delivery note attached",
  fragileMarkingChecked: "Fragile / handling markings verified",
};

const STATUS_BADGE = { "Pending": "warning", "In Progress": "info", "Completed": "success" };

function TaskProcessor({ task, onUpdatePicking, onUpdatePacking, saving }) {
  const [expanded, setExpanded] = useState(true);
  const [pickingForm, setPickingForm] = useState(
    task.items.map((it) => ({ pickedQty: it.pickedQty, isPicked: it.isPicked }))
  );

  const allPicked = pickingForm.every((it, i) => it.isPicked && it.pickedQty >= task.items[i].requestedQty);

  const updatePickQty = (i, val) => {
    setPickingForm((p) => {
      const updated = [...p];
      const reqd = task.items[i].requestedQty;
      const qty = Math.min(Number(val), reqd);
      updated[i] = { pickedQty: qty, isPicked: qty >= reqd };
      return updated;
    });
  };

  const handleSavePicking = async () => {
    for (let i = 0; i < pickingForm.length; i++) {
      await onUpdatePicking(task.id, i, pickingForm[i].pickedQty, pickingForm[i].isPicked);
    }
  };

  const handlePackingToggle = async (key, val) => {
    await onUpdatePacking(task.id, { [key]: val });
  };

  const packingDone = Object.values(task.packingChecklist || {}).every(Boolean);

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-3 flex-wrap cursor-pointer" onClick={() => setExpanded((p) => !p)}>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono font-semibold text-gray-700">{task.id}</span>
            <Badge variant={STATUS_BADGE[task.status] || "neutral"}>{task.status}</Badge>
          </div>
          <p className="text-sm text-gray-700 mt-0.5">{task.taskType} — {task.shopName}</p>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
      </div>

      {expanded && (
        <div className="mt-4 space-y-4 border-t border-gray-100 pt-4">
          {/* Picking Checklist */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2"><Package className="w-4 h-4 text-blue-600" /> Picking Progress</h4>
              <Button size="xs" variant="primary" icon={Save} onClick={handleSavePicking} disabled={saving}>Save</Button>
            </div>
            <div className="space-y-2">
              {task.items.map((item, i) => (
                <div key={i} className={`flex items-center justify-between p-3 rounded-lg ${pickingForm[i]?.isPicked ? "bg-green-50" : "bg-gray-50"}`}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800">{item.productName}</p>
                    <p className="text-xs text-gray-500">{item.aisleLocation} · Req: {item.requestedQty} {item.unit}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <input type="number" min={0} max={item.requestedQty} value={pickingForm[i]?.pickedQty ?? 0}
                      onChange={(e) => updatePickQty(i, e.target.value)}
                      className="w-20 border border-gray-300 rounded px-2 py-1 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <span className="text-xs text-gray-500 w-8">{item.unit}</span>
                    {pickingForm[i]?.isPicked && <span className="text-green-600 text-xs font-semibold">✓</span>}
                  </div>
                </div>
              ))}
            </div>
            {allPicked && <p className="text-xs text-green-700 font-medium mt-2">All items picked. Proceed to packing.</p>}
          </div>

          {/* Packing Checklist */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-purple-600" /> Packing Checklist
              {packingDone && <Badge variant="success" className="text-xs">Complete</Badge>}
            </h4>
            <div className="space-y-2">
              {Object.entries(task.packingChecklist || {}).map(([key, val]) => (
                <button key={key} onClick={() => handlePackingToggle(key, !val)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all text-left ${val ? "bg-green-50 border-green-200" : "bg-white border-gray-200 hover:border-gray-300"}`}>
                  {val ? <CheckSquare className="w-5 h-5 text-green-600 shrink-0" /> : <Square className="w-5 h-5 text-gray-400 shrink-0" />}
                  <span className={`text-sm ${val ? "text-green-800 line-through" : "text-gray-700"}`}>{CHECKLIST_LABELS[key] || key}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

export default function WorkerProcessing() {
  const { toast } = useToast();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    workerService.getTasks().then((all) => setTasks(all.filter((t) => t.status !== "Completed"))).finally(() => setLoading(false));
  }, []);

  const handleUpdatePicking = async (taskId, idx, qty, isPicked) => {
    setSaving(true);
    try {
      const updated = await workerService.updatePickingProgress(taskId, idx, qty, isPicked);
      setTasks((p) => p.map((t) => t.id === updated.id ? updated : t));
    } catch { toast.error("Failed to update picking progress."); }
    finally { setSaving(false); }
  };

  const handleUpdatePacking = async (taskId, updates) => {
    setSaving(true);
    try {
      const updated = await workerService.updatePackingChecklist(taskId, updates);
      setTasks((p) => p.map((t) => t.id === updated.id ? updated : t));
      if (Object.values(updated.packingChecklist || {}).every(Boolean)) {
        toast.success("Packing complete! Task marked as Completed.");
      }
    } catch { toast.error("Failed to update checklist."); }
    finally { setSaving(false); }
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <PageHeader title="Processing" subtitle="Mark orders as picked, packed, and ready for dispatch." />

      {loading ? (
        <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>
      ) : tasks.length === 0 ? (
        <Card className="p-16 text-center">
          <CheckSquare className="w-12 h-12 text-green-400 mx-auto mb-3" />
          <p className="text-gray-700 font-medium">All active tasks have been completed!</p>
          <p className="text-gray-500 text-sm mt-1">Check back with your supervisor for new assignments.</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => (
            <TaskProcessor key={task.id} task={task} onUpdatePicking={handleUpdatePicking} onUpdatePacking={handleUpdatePacking} saving={saving} />
          ))}
        </div>
      )}
    </div>
  );
}
