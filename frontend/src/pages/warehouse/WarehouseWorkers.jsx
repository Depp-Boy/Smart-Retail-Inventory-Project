import { useState, useEffect } from "react";
import { UserPlus, ClipboardList, Star } from "lucide-react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import DataTable from "../../components/common/DataTable";

const STATUS_BADGE = { "On Duty": "success", "Off Duty": "neutral", "On Leave": "warning" };
const SHIFTS = ["Morning Shift (06:00 AM - 02:30 PM)", "General Shift (09:00 AM - 05:30 PM)", "Evening Shift (02:00 PM - 10:30 PM)", "Night Shift (10:00 PM - 06:00 AM)"];
const TASK_TYPES = ["Picking", "Packing & Staging", "Forklift Operation", "Inventory Audit", "Bay Loading"];
const PRIORITIES = ["High", "Normal", "Low"];

const EMPTY_WORKER = { name: "", role: "", phone: "", email: "", password: "", shift: SHIFTS[1] };
const EMPTY_TASK = { assignedToWorkerId: "", taskType: TASK_TYPES[0], priority: PRIORITIES[1], dueDate: "", notes: "" };

function WorkerCard({ worker }) {
  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm shrink-0">
          {worker.name.split(" ").map((p) => p[0]).join("").slice(0, 2)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <p className="font-semibold text-gray-900">{worker.name}</p>
            <Badge variant={STATUS_BADGE[worker.status] || "neutral"}>{worker.status}</Badge>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{worker.role}</p>
          <p className="text-xs text-gray-500 font-mono mt-0.5">{worker.workerCode}</p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        <div className="bg-blue-50 rounded-lg py-2">
          <p className="text-lg font-bold text-blue-700">{worker.activeTasksCount}</p>
          <p className="text-xs text-gray-500">Active</p>
        </div>
        <div className="bg-green-50 rounded-lg py-2">
          <p className="text-lg font-bold text-green-700">{worker.completedTasksCount}</p>
          <p className="text-xs text-gray-500">Done</p>
        </div>
        <div className="bg-yellow-50 rounded-lg py-2">
          <div className="flex items-center justify-center gap-0.5">
            <p className="text-lg font-bold text-yellow-700">{worker.rating}</p>
            <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" />
          </div>
          <p className="text-xs text-gray-500">Rating</p>
        </div>
      </div>
      <p className="mt-2 text-xs text-gray-500">{worker.shift}</p>
    </Card>
  );
}

export default function WarehouseWorkers() {
  const { toast } = useToast();
  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [workerForm, setWorkerForm] = useState(EMPTY_WORKER);
  const [taskForm, setTaskForm] = useState(EMPTY_TASK);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    warehouseService.getWorkers().then(setWorkers).finally(() => setLoading(false));
  }, []);

  const handleAddWorker = async (e) => {
    e.preventDefault();
    if (!workerForm.password || workerForm.password.length < 6) {
      toast.error("Please enter a password of at least 6 characters.");
      return;
    }
    setSaving(true);
    try {
      const worker = await warehouseService.addWorker(workerForm);
      setWorkers((p) => [worker, ...p]);
      setAddOpen(false);
      setWorkerForm(EMPTY_WORKER);
      toast.success(`Worker ${worker.name} added.`);
    } catch (err) {
      toast.error(err?.detail || err?.message || "Failed to add worker.");
    } finally {
      setSaving(false);
    }
  };

  const handleAssignTask = async (e) => {
    e.preventDefault();
    if (!taskForm.assignedToWorkerId) { toast.error("Please select a worker."); return; }
    setSaving(true);
    try {
      const worker = workers.find((w) => w.id === taskForm.assignedToWorkerId);
      const task = await warehouseService.assignTask({ ...taskForm, assignedToWorkerName: worker?.name || "" });
      setWorkers((p) => p.map((w) => w.id === taskForm.assignedToWorkerId ? { ...w, activeTasksCount: w.activeTasksCount + 1 } : w));
      setAssignOpen(false);
      setTaskForm(EMPTY_TASK);
      toast.success(`Task ${task.id} assigned to ${worker?.name}.`);
    } catch { toast.error("Failed to assign task."); }
    finally { setSaving(false); }
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <PageHeader title="Workers" subtitle="Manage your warehouse worker team — add, assign, and monitor tasks." />
        <div className="flex gap-3">
          <Button variant="ghost" size="sm" icon={ClipboardList} onClick={() => { setTaskForm(EMPTY_TASK); setAssignOpen(true); }}>Assign Task</Button>
          <Button variant="primary" size="sm" icon={UserPlus} onClick={() => { setWorkerForm(EMPTY_WORKER); setAddOpen(true); }}>Add Worker</Button>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map((i) => <div key={i} className="h-40 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {workers.map((w) => <WorkerCard key={w.id} worker={w} />)}
        </div>
      )}

      {/* Add Worker Modal */}
      <Modal isOpen={addOpen} onClose={() => setAddOpen(false)} title="Add New Worker" size="md">
        <form onSubmit={handleAddWorker} className="space-y-4">
          {[
            { key: "name", label: "Full Name", type: "text", required: true },
            { key: "role", label: "Role / Designation", type: "text", required: true },
            { key: "email", label: "Email Address", type: "email", required: true },
            { key: "password", label: "Temporary Password", type: "password", required: true, minLength: 6 },
            { key: "phone", label: "Phone Number", type: "tel" },
          ].map(({ key, label, type, required, minLength }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}{required && <span className="text-red-500 ml-0.5">*</span>}</label>
              <input
                type={type}
                minLength={minLength}
                value={workerForm[key] ?? ""}
                onChange={(e) => setWorkerForm((p) => ({ ...p, [key]: e.target.value }))}
                required={!!required}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ))}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Assigned Shift</label>
            <select value={workerForm.shift} onChange={(e) => setWorkerForm((p) => ({ ...p, shift: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              {SHIFTS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>{saving ? "Adding…" : "Add Worker"}</Button>
          </div>
        </form>
      </Modal>

      {/* Assign Task Modal */}
      <Modal isOpen={assignOpen} onClose={() => setAssignOpen(false)} title="Assign Task to Worker" size="md">
        <form onSubmit={handleAssignTask} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Worker <span className="text-red-500">*</span></label>
            <select value={taskForm.assignedToWorkerId} onChange={(e) => setTaskForm((p) => ({ ...p, assignedToWorkerId: e.target.value }))} required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">— Select worker —</option>
              {workers.filter((w) => w.status === "On Duty").map((w) => (
                <option key={w.id} value={w.id}>{w.name} ({w.workerCode})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Task Type</label>
            <select value={taskForm.taskType} onChange={(e) => setTaskForm((p) => ({ ...p, taskType: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              {TASK_TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
            <select value={taskForm.priority} onChange={(e) => setTaskForm((p) => ({ ...p, priority: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Due Date/Time</label>
            <input type="datetime-local" value={taskForm.dueDate} onChange={(e) => setTaskForm((p) => ({ ...p, dueDate: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea value={taskForm.notes} onChange={(e) => setTaskForm((p) => ({ ...p, notes: e.target.value }))} rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setAssignOpen(false)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>{saving ? "Assigning…" : "Assign Task"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
