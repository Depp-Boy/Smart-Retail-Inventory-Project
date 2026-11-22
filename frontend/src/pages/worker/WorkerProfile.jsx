import { useState, useEffect } from "react";
import { User, Phone, Mail, Briefcase, Calendar, Star } from "lucide-react";
import { workerService } from "../../services/workerService";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

const STATUS_BADGE = { "On Duty": "success", "Off Duty": "neutral", "On Leave": "warning" };

function ProfileField({ icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-xl">
      <div className="p-2 bg-white rounded-lg shadow-sm shrink-0"><Icon className="w-4 h-4 text-blue-600" /></div>
      <div>
        <p className="text-xs text-gray-500 mb-0.5">{label}</p>
        <p className="text-sm font-medium text-gray-900">{value || "—"}</p>
      </div>
    </div>
  );
}

export default function WorkerProfile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    workerService.getProfile().then(setProfile).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>;
  if (!profile) return null;

  const initials = profile.name?.split(" ").map((p) => p[0]).join("").slice(0, 2) || "W";

  return (
    <div className="p-4 md:p-6 space-y-6">
      <PageHeader title="My Profile" subtitle="Your worker profile, performance summary, and shift details." />

      {/* Profile header */}
      <Card className="p-6">
        <div className="flex items-start gap-6 flex-wrap">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-bold text-2xl shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <h2 className="text-xl font-bold text-gray-900">{profile.name}</h2>
                <p className="text-gray-500 text-sm">{profile.role}</p>
                <p className="text-gray-400 text-sm font-mono">{profile.workerCode}</p>
              </div>
              <Badge variant={STATUS_BADGE[profile.status] || "neutral"} className="text-sm">{profile.status}</Badge>
            </div>

            {/* Stats */}
            <div className="mt-4 flex flex-wrap gap-4">
              <div className="text-center bg-blue-50 rounded-xl px-5 py-3">
                <p className="text-2xl font-bold text-blue-700">{profile.activeTasksCount}</p>
                <p className="text-xs text-gray-500">Active Tasks</p>
              </div>
              <div className="text-center bg-green-50 rounded-xl px-5 py-3">
                <p className="text-2xl font-bold text-green-700">{profile.completedTasksCount}</p>
                <p className="text-xs text-gray-500">Completed</p>
              </div>
              <div className="text-center bg-yellow-50 rounded-xl px-5 py-3">
                <div className="flex items-center gap-1 justify-center">
                  <p className="text-2xl font-bold text-yellow-700">{profile.rating}</p>
                  <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                </div>
                <p className="text-xs text-gray-500">Rating</p>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Details */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ProfileField icon={Phone} label="Phone Number" value={profile.phone} />
        <ProfileField icon={Mail} label="Email Address" value={profile.email} />
        <ProfileField icon={Briefcase} label="Assigned Shift" value={profile.shift} />
        <ProfileField icon={Calendar} label="Joining Date" value={profile.joiningDate} />
        <ProfileField icon={User} label="Worker Code" value={profile.workerCode} />
      </div>

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-700">
        <strong>Note:</strong> Profile updates require manager authorization. Contact your warehouse supervisor to update any profile information.
      </div>
    </div>
  );
}
