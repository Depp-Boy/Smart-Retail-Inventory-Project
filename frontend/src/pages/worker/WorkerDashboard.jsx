import { useState, useEffect } from "react";
import { ClipboardList, Clock, CheckCircle, AlertTriangle, Truck, RefreshCw } from "lucide-react";
import { workerService } from "../../services/workerService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card, StatCard } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

const TASK_TYPE_COLOR = {
  "Picking": "bg-blue-100 text-blue-700",
  "Packing & Staging": "bg-purple-100 text-purple-700",
  "Forklift Operation": "bg-orange-100 text-orange-700",
  "Inventory Audit": "bg-green-100 text-green-700",
};

const STATUS_BADGE = { "Pending": "warning", "In Progress": "info", "Completed": "success" };

export default function WorkerDashboard() {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { const d = await workerService.getDashboardSummary(); setData(d); }
    catch { toast.error("Failed to load dashboard."); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>;
  if (!data) return null;

  const { shiftInfo } = data;

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <PageHeader title="My Dashboard" subtitle={`Good morning, ${shiftInfo.workerName}! Here is your shift overview.`} />
        <button onClick={load} className="flex items-center gap-2 text-sm text-gray-600 hover:text-blue-600 border border-gray-300 hover:border-blue-400 px-3 py-1.5 rounded-lg transition-colors">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Shift Info Banner */}
      <Card className="p-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white border-0">
        <div className="flex items-start gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-lg">{shiftInfo.workerName}</p>
            <p className="text-blue-100 text-sm">{shiftInfo.workerCode} · {shiftInfo.role || "Warehouse Worker"}</p>
            <p className="text-blue-100 text-sm mt-1">{shiftInfo.shift}</p>
          </div>
          <div className="text-right">
            <p className="text-blue-200 text-xs">Zone Assignment</p>
            <p className="font-medium text-sm">{shiftInfo.assignedZone}</p>
            <p className="text-blue-200 text-xs mt-1">Supervisor: {shiftInfo.supervisor}</p>
          </div>
          <div className="shrink-0">
            <span className="inline-flex items-center gap-1.5 bg-green-500/80 text-white text-xs font-medium px-3 py-1.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              {shiftInfo.currentStatus}
            </span>
          </div>
        </div>
      </Card>

      {/* Task stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatCard title="Assigned" value={data.assignedCount} icon={ClipboardList} color="blue" />
        <StatCard title="Pending" value={data.pendingCount} icon={Clock} color="orange" />
        <StatCard title="In Progress" value={data.inProgressCount} icon={AlertTriangle} color="blue" trendLabel="active" />
        <StatCard title="Completed" value={data.completedCount} icon={CheckCircle} color="green" />
        <StatCard title="Ready for Dispatch" value={data.readyDispatchCount} icon={Truck} color="purple" />
      </div>

      {/* Urgent / Active Tasks */}
      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Active & Pending Tasks</h3>
        {data.urgentTasks.length === 0 ? (
          <div className="text-center py-8">
            <CheckCircle className="w-10 h-10 text-green-400 mx-auto mb-2" />
            <p className="text-gray-500">All tasks completed for this shift!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {data.urgentTasks.map((task) => (
              <div key={task.id} className="flex items-start gap-4 p-4 border border-gray-200 rounded-xl hover:border-blue-300 transition-colors">
                <div className={`px-2 py-1 rounded-lg text-xs font-semibold shrink-0 ${TASK_TYPE_COLOR[task.taskType] || "bg-gray-100 text-gray-700"}`}>
                  {task.taskType}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <p className="font-medium text-gray-900">{task.id} — {task.shopName}</p>
                    <Badge variant={STATUS_BADGE[task.status] || "neutral"}>{task.status}</Badge>
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">{task.items?.length} item(s) · Due: {task.dueDate}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{task.notes}</p>
                </div>
                <Badge variant={task.priority === "High" ? "danger" : task.priority === "Normal" ? "info" : "neutral"} className="shrink-0">{task.priority}</Badge>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
