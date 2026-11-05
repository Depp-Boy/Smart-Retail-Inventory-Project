import { useState, useEffect } from "react";
import { Eye, ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { workerService } from "../../services/workerService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

const STATUS_BADGE = { "Pending": "warning", "In Progress": "info", "Completed": "success" };
const PRIORITY_BADGE = { "High": "danger", "Normal": "info", "Low": "neutral" };
const STATUS_TRANSITIONS = { "Pending": "In Progress", "In Progress": "Completed" };

function TaskCard({ task, onStatusUpdate, updating }) {
  const [expanded, setExpanded] = useState(false);
  const nextStatus = STATUS_TRANSITIONS[task.status];

  return (
    <Card className={`p-4 transition-all ${task.status === "Pending" ? "border-l-4 border-l-orange-400" : task.status === "In Progress" ? "border-l-4 border-l-blue-500" : "border-l-4 border-l-green-500"}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono font-semibold text-gray-700 text-sm">{task.id}</span>
            <Badge variant={STATUS_BADGE[task.status] || "neutral"}>{task.status}</Badge>
            <Badge variant={PRIORITY_BADGE[task.priority] || "neutral"}>{task.priority}</Badge>
          </div>
          <p className="text-sm font-medium text-gray-900 mt-1">{task.taskType} — {task.shopName}</p>
          <p className="text-xs text-gray-500 mt-0.5">Due: {task.dueDate} · {task.items?.length} item(s)</p>
        </div>
        <div className="flex items-center gap-2">
          {nextStatus && (
            <Button size="xs" variant={task.status === "Pending" ? "primary" : "success"} icon={ArrowRight}
              onClick={() => onStatusUpdate(task.id, nextStatus)} disabled={updating === task.id}>
              {updating === task.id ? "…" : `Mark ${nextStatus}`}
            </Button>
          )}
          <button onClick={() => setExpanded((p) => !p)} className="text-gray-500 hover:text-gray-700 p-1">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 border-t border-gray-100 pt-4 space-y-3">
          <div>
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Items to Pick</p>
            <div className="space-y-2">
              {task.items?.map((item, i) => (
                <div key={i} className={`flex items-center justify-between p-3 rounded-lg ${item.isPicked ? "bg-green-50" : "bg-gray-50"}`}>
                  <div>
                    <p className="text-sm font-medium text-gray-800">{item.productName}</p>
                    <p className="text-xs text-gray-500">{item.aisleLocation} · {item.sku}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-semibold ${item.isPicked ? "text-green-700" : "text-gray-700"}`}>{item.pickedQty}/{item.requestedQty} {item.unit}</p>
                    <p className="text-xs text-gray-400">{item.isPicked ? "✓ Picked" : "Pending"}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          {task.notes && (
            <p className="text-xs text-gray-600 bg-yellow-50 border border-yellow-200 rounded-lg p-3 italic">{task.notes}</p>
          )}
        </div>
      )}
    </Card>
  );
}

export default function WorkerTasks() {
  const { toast } = useToast();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("All");
  const [updating, setUpdating] = useState(null);

  useEffect(() => {
    workerService.getTasks().then(setTasks).finally(() => setLoading(false));
  }, []);

  const tabs = ["All", "Pending", "In Progress", "Completed"];
  const filtered = statusFilter === "All" ? tasks : tasks.filter((t) => t.status === statusFilter);

  const handleStatusUpdate = async (taskId, newStatus) => {
    setUpdating(taskId);
    try {
      const updated = await workerService.updateTaskStatus(taskId, newStatus);
      setTasks((p) => p.map((t) => t.id === updated.id ? updated : t));
      toast.success(`Task ${taskId} marked as ${newStatus}.`);
    } catch { toast.error("Failed to update task."); }
    finally { setUpdating(null); }
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <PageHeader title="My Tasks" subtitle="View your assigned pick, pack, and dispatch tasks for today." />

      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button key={t} onClick={() => setStatusFilter(t)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${statusFilter === t ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {t}
            {t !== "All" && (
              <span className="ml-1.5 text-xs opacity-70">({tasks.filter((ts) => ts.status === t).length})</span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <Card className="p-16 text-center text-gray-500">No tasks in this category.</Card>
      ) : (
        <div className="space-y-3">
          {filtered.map((task) => (
            <TaskCard key={task.id} task={task} onStatusUpdate={handleStatusUpdate} updating={updating} />
          ))}
        </div>
      )}
    </div>
  );
}
