import { useState, useEffect } from "react";
import { CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp, Eye } from "lucide-react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Modal from "../../components/ui/Modal";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

const STATUS_BADGE = {
  "Pending": "warning",
  "Accepted": "success",
  "Partially Allocated": "info",
  "Dispatched": "info",
  "Delivered": "success",
  "Rejected": "danger",
};

function RequestRow({ req, onAccept, onReject }) {
  const [expanded, setExpanded] = useState(false);

  const isPending = req.status === "Pending";

  return (
    <Card className={`p-4 transition-all ${isPending ? "border-l-4 border-l-orange-400" : ""}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono font-semibold text-blue-700 text-sm">{req.orderNumber}</span>
            <Badge variant={STATUS_BADGE[req.status] || "neutral"}>{req.status}</Badge>
            {isPending && <Badge variant="warning">Action Required</Badge>}
          </div>
          <p className="text-sm text-gray-700 mt-1 font-medium">{req.shopName}</p>
          <p className="text-xs text-gray-500">{req.items?.length} item(s) · {req.totalRequestedUnits} units total · {req.priority} priority · Requested: {req.requestDate}</p>
        </div>
        <div className="flex items-center gap-2">
          {isPending && (
            <>
              <Button size="xs" variant="success" icon={CheckCircle} onClick={() => onAccept(req)}>Accept</Button>
              <Button size="xs" variant="danger" icon={XCircle} onClick={() => onReject(req)}>Reject</Button>
            </>
          )}
          <button onClick={() => setExpanded((p) => !p)} className="text-gray-500 hover:text-gray-700 p-1">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 border-t border-gray-100 pt-4">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Requested Items</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 text-xs border-b border-gray-200">
                  <th className="pb-1">Product</th>
                  <th className="pb-1">SKU</th>
                  <th className="pb-1 text-right">Requested</th>
                </tr>
              </thead>
              <tbody>
                {req.items?.map((item, i) => (
                  <tr key={i} className="border-b border-gray-100 last:border-0">
                    <td className="py-1.5 text-gray-800">{item.productName}</td>
                    <td className="py-1.5 font-mono text-gray-500">{item.sku}</td>
                    <td className="py-1.5 text-right text-gray-700 font-medium">{item.requestedQuantity} {item.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {req.notes && (
            <p className="mt-3 text-xs text-gray-600 bg-gray-50 rounded-lg p-2 italic">{req.notes}</p>
          )}
        </div>
      )}
    </Card>
  );
}

function AcceptModal({ req, onConfirm, onClose, loading }) {
  const [items, setItems] = useState(
    req ? req.items.map((it) => ({ ...it, allocatedQuantity: it.requestedQuantity })) : []
  );
  const [isPartial, setIsPartial] = useState(false);

  const updateQty = (i, val) => {
    const updated = items.map((it, idx) => idx === i ? { ...it, allocatedQuantity: Number(val) } : it);
    setItems(updated);
    setIsPartial(updated.some((it) => it.allocatedQuantity < it.requestedQuantity));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({ items, isPartial, unallocated: items.filter((it) => it.allocatedQuantity < it.requestedQuantity).map((it) => ({ ...it, pending: it.requestedQuantity - it.allocatedQuantity })) });
  };

  if (!req) return null;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-800">
        <p className="font-medium">Accepting: {req.orderNumber} from {req.shopName}</p>
        <p className="text-xs mt-0.5 text-blue-600">Adjust quantities below for partial allocation. Leave at full for complete fulfillment.</p>
      </div>
      <div className="space-y-2">
        {items.map((it, i) => (
          <div key={i} className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800">{it.productName}</p>
              <p className="text-xs text-gray-500">Requested: {it.requestedQuantity} {it.unit}</p>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500">Allocate:</label>
              <input type="number" min={0} max={it.requestedQuantity} value={it.allocatedQuantity}
                onChange={(e) => updateQty(i, e.target.value)}
                className="w-24 border border-gray-300 rounded px-2 py-1 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <span className="text-xs text-gray-500">{it.unit}</span>
            </div>
          </div>
        ))}
      </div>
      {isPartial && (
        <div className="flex items-center gap-2 text-orange-700 bg-orange-50 rounded-lg p-3 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <p>This will be a <strong>Partial Allocation</strong>. Remaining balance will be marked for alternative fulfillment.</p>
        </div>
      )}
      <div className="flex justify-end gap-3">
        <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
        <Button type="submit" variant="success" disabled={loading}>{loading ? "Confirming…" : isPartial ? "Confirm Partial Allocation" : "Confirm Full Acceptance"}</Button>
      </div>
    </form>
  );
}

export default function WarehouseRequests() {
  const { toast } = useToast();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("Pending");
  const [acceptReq, setAcceptReq] = useState(null);
  const [rejectReq, setRejectReq] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    warehouseService.getIncomingRequests().then(setRequests).finally(() => setLoading(false));
  }, []);

  const filtered = statusFilter === "All" ? requests : requests.filter((r) => r.status === statusFilter);
  const pendingCount = requests.filter((r) => r.status === "Pending").length;

  const handleAccept = async (allocationDetails) => {
    setSaving(true);
    try {
      const updated = await warehouseService.acceptRequest(acceptReq.id, allocationDetails);
      setRequests((p) => p.map((r) => r.id === updated.id ? updated : r));
      setAcceptReq(null);
      toast.success(`Order ${acceptReq.orderNumber} ${allocationDetails.isPartial ? "partially allocated" : "accepted in full"}.`);
    } catch { toast.error("Failed to process request."); }
    finally { setSaving(false); }
  };

  const handleReject = async (e) => {
    e.preventDefault();
    if (!rejectReason.trim()) { toast.error("Please provide a rejection reason."); return; }
    setSaving(true);
    try {
      const updated = await warehouseService.rejectRequest(rejectReq.id, rejectReason);
      setRequests((p) => p.map((r) => r.id === updated.id ? updated : r));
      setRejectReq(null);
      setRejectReason("");
      toast.success(`Order ${rejectReq.orderNumber} rejected.`);
    } catch { toast.error("Failed to reject request."); }
    finally { setSaving(false); }
  };

  const tabs = ["Pending", "Partially Allocated", "Accepted", "Dispatched", "Delivered", "Rejected", "All"];

  return (
    <div className="p-4 md:p-6 space-y-6">
      <PageHeader
        title="Replenishment Requests"
        subtitle="Review and respond to incoming replenishment requests from shops."
        badge={pendingCount > 0 ? { label: `${pendingCount} pending`, variant: "warning" } : null}
      />

      {/* Status tabs */}
      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button key={t} onClick={() => setStatusFilter(t)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${statusFilter === t ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {t}
            {t === "Pending" && pendingCount > 0 && (
              <span className="ml-1.5 bg-orange-500 text-white text-xs rounded-full px-1.5 py-0.5">{pendingCount}</span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-gray-500">No {statusFilter === "All" ? "" : statusFilter.toLowerCase()} requests found.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map((req) => (
            <RequestRow key={req.id} req={req} onAccept={setAcceptReq} onReject={setRejectReq} />
          ))}
        </div>
      )}

      {/* Accept Modal */}
      <Modal isOpen={!!acceptReq} onClose={() => setAcceptReq(null)} title="Process Replenishment Request" size="lg">
        <AcceptModal req={acceptReq} onConfirm={handleAccept} onClose={() => setAcceptReq(null)} loading={saving} />
      </Modal>

      {/* Reject Modal */}
      <Modal isOpen={!!rejectReq} onClose={() => { setRejectReq(null); setRejectReason(""); }} title={`Reject Request — ${rejectReq?.orderNumber}`} size="md">
        <form onSubmit={handleReject} className="space-y-4">
          <p className="text-sm text-gray-600">You are about to reject order <strong>{rejectReq?.orderNumber}</strong> from <strong>{rejectReq?.shopName}</strong>. Please provide a reason.</p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rejection Reason <span className="text-red-500">*</span></label>
            <textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} rows={3} required
              placeholder="e.g. Insufficient stock available for requested SKUs..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400" />
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => { setRejectReq(null); setRejectReason(""); }}>Cancel</Button>
            <Button type="submit" variant="danger" disabled={saving}>{saving ? "Rejecting…" : "Confirm Rejection"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
