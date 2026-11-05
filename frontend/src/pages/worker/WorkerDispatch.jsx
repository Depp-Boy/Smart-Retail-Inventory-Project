import { useState, useEffect } from "react";
import { Truck, CheckCircle, Clock, Package } from "lucide-react";
import { workerService } from "../../services/workerService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

const STATUS_BADGE = {
  "Staged": "neutral",
  "Ready for Dispatch": "warning",
  "In Transit": "info",
  "Delivered": "success",
};

export default function WorkerDispatch() {
  const { toast } = useToast();
  const [dispatches, setDispatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDispatch, setSelectedDispatch] = useState(null);
  const [stageNotes, setStageNotes] = useState("");
  const [marking, setMarking] = useState(false);

  useEffect(() => {
    workerService.getDispatchQueue().then(setDispatches).finally(() => setLoading(false));
  }, []);

  const handleMarkReady = async (e) => {
    e.preventDefault();
    setMarking(true);
    try {
      const updated = await workerService.markReadyForDispatch(selectedDispatch.id, stageNotes);
      setDispatches((p) => p.map((d) => d.id === updated.id ? updated : d));
      setSelectedDispatch(null);
      setStageNotes("");
      toast.success(`Dispatch ${updated.id} marked as Ready for Dispatch.`);
    } catch { toast.error("Failed to update dispatch status."); }
    finally { setMarking(false); }
  };

  if (loading) return <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>;

  const staged = dispatches.filter((d) => d.status === "Staged");
  const readyAndInTransit = dispatches.filter((d) => d.status !== "Staged" && d.status !== "Delivered");
  const delivered = dispatches.filter((d) => d.status === "Delivered");

  function DispatchCard({ d }) {
    return (
      <Card className="p-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-sm text-gray-700">{d.id}</span>
              <Badge variant={STATUS_BADGE[d.status] || "neutral"}>{d.status}</Badge>
            </div>
            <p className="text-sm font-medium text-gray-900 mt-1">{d.shopName}</p>
            <p className="text-xs text-gray-500 mt-0.5">Order: {d.orderNumber} · {d.totalItemsCount} items · {d.totalWeightKg} kg</p>
            <p className="text-xs text-gray-500">Carrier: {d.carrierName} · Vehicle: {d.vehicleNumber}</p>
            {d.dispatchedAt && <p className="text-xs text-gray-400 mt-0.5">Dispatched: {d.dispatchedAt}</p>}
            {d.estimatedArrival && <p className="text-xs text-gray-400">ETA: {d.estimatedArrival}</p>}
          </div>
          {d.status === "Staged" && (
            <Button size="sm" variant="warning" icon={CheckCircle} onClick={() => { setSelectedDispatch(d); setStageNotes(""); }}>
              Mark Ready
            </Button>
          )}
        </div>
      </Card>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      <PageHeader title="Dispatch Queue" subtitle="Confirm and complete outgoing order dispatches." />

      {/* Staged — needs action */}
      {staged.length > 0 && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Package className="w-5 h-5 text-orange-500" />
            Staged — Awaiting Your Confirmation
            <span className="ml-1 bg-orange-500 text-white text-xs rounded-full px-2 py-0.5">{staged.length}</span>
          </h3>
          <div className="space-y-3">
            {staged.map((d) => <DispatchCard key={d.id} d={d} />)}
          </div>
        </div>
      )}

      {/* In progress */}
      {readyAndInTransit.length > 0 && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2"><Truck className="w-5 h-5 text-blue-500" /> Active Dispatches</h3>
          <div className="space-y-3">
            {readyAndInTransit.map((d) => <DispatchCard key={d.id} d={d} />)}
          </div>
        </div>
      )}

      {/* Delivered */}
      {delivered.length > 0 && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2"><CheckCircle className="w-5 h-5 text-green-500" /> Delivered</h3>
          <div className="space-y-3">
            {delivered.map((d) => <DispatchCard key={d.id} d={d} />)}
          </div>
        </div>
      )}

      {dispatches.length === 0 && (
        <Card className="p-16 text-center">
          <Truck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No dispatches in queue.</p>
        </Card>
      )}

      {/* Mark Ready Modal */}
      <Modal isOpen={!!selectedDispatch} onClose={() => setSelectedDispatch(null)} title={`Mark Ready — ${selectedDispatch?.id}`} size="md">
        <form onSubmit={handleMarkReady} className="space-y-4">
          <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-800">
            <p>You are about to mark <strong>{selectedDispatch?.id}</strong> as <strong>Ready for Dispatch</strong>.</p>
            <p className="mt-1 text-blue-600 text-xs">Please verify the load has been inspected, pallets are strapped, and the vehicle is positioned at the dock.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Staging Notes (optional)</label>
            <textarea value={stageNotes} onChange={(e) => setStageNotes(e.target.value)} rows={3}
              placeholder="e.g. Inspected and staged at Dock Area 2. Driver confirmed presence."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setSelectedDispatch(null)}>Cancel</Button>
            <Button type="submit" variant="success" icon={CheckCircle} disabled={marking}>{marking ? "Confirming…" : "Confirm Ready for Dispatch"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
