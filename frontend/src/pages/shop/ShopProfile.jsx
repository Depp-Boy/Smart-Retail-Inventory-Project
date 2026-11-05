import { useState, useEffect } from 'react';
import { Store, User, Phone, MapPin, Mail, Save, Building } from 'lucide-react';
import { shopService } from '../../services/shopService';
import PageHeader from '../../components/ui/PageHeader';
import Button from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import { useToast } from '../../context/ToastContext';

export default function ShopProfile() {
  const { toast } = useToast();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function loadProfile() {
      try {
        setLoading(true);
        const data = await shopService.getProfile();
        setProfile(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadProfile();
  }, []);

  const handleChange = (field, val) => {
    setProfile((prev) => ({ ...prev, [field]: val }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      await shopService.updateProfile(profile);
      toast.success('Shop profile updated successfully.');
    } catch (err) {
      toast.error('Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 flex justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12 max-w-3xl mx-auto">
      <PageHeader
        title="Shop Profile"
        subtitle="Manage retail enterprise identity, owner credentials, and physical dispatch delivery coordinates."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Profile' }]}
      />

      <form onSubmit={handleSave} className="space-y-6">
        {/* Enterprise Identification Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-gray-100">
            <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0">
              <Store size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900">Retail Establishment</h3>
              <p className="text-xs text-gray-500">Commercial enterprise name and registration data</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Shop Commercial Name"
              value={profile.shopName}
              required
              onChange={(e) => handleChange('shopName', e.target.value)}
            />
            <Input
              label="GSTIN / Tax Registration ID"
              value={profile.gstin}
              onChange={(e) => handleChange('gstin', e.target.value)}
            />
          </div>

          <Input
            label="Operating Hours"
            value={profile.operatingHours}
            onChange={(e) => handleChange('operatingHours', e.target.value)}
          />
        </div>

        {/* Owner Credentials */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-gray-100">
            <div className="w-10 h-10 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center flex-shrink-0">
              <User size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900">Proprietor Information</h3>
              <p className="text-xs text-gray-500">Authorized primary contact person for supplier communications</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Proprietor / Manager Full Name"
              value={profile.ownerName}
              required
              onChange={(e) => handleChange('ownerName', e.target.value)}
            />
            <Input
              label="Direct Mobile Contact"
              value={profile.phone}
              required
              onChange={(e) => handleChange('phone', e.target.value)}
            />
          </div>

          <Input
            label="Registered Business Email"
            type="email"
            value={profile.email}
            required
            onChange={(e) => handleChange('email', e.target.value)}
          />
        </div>

        {/* Physical Address / Delivery Coordinates */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-gray-100">
            <div className="w-10 h-10 rounded-xl bg-green-100 text-green-600 flex items-center justify-center flex-shrink-0">
              <MapPin size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900">Physical Delivery Location</h3>
              <p className="text-xs text-gray-500">Destination address utilized by warehouse carriers for order unloading</p>
            </div>
          </div>

          <Input
            label="Street Address / Door Number"
            value={profile.address}
            required
            onChange={(e) => handleChange('address', e.target.value)}
          />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Input
              label="Locality / Neighborhood"
              value={profile.locality}
              onChange={(e) => handleChange('locality', e.target.value)}
            />
            <Input
              label="City"
              value={profile.city}
              required
              onChange={(e) => handleChange('city', e.target.value)}
            />
            <Input
              label="Postal Pincode"
              value={profile.pincode}
              required
              onChange={(e) => handleChange('pincode', e.target.value)}
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <Button
            type="submit"
            size="md"
            variant="primary"
            icon={Save}
            loading={saving}
          >
            Save Profile Updates
          </Button>
        </div>
      </form>
    </div>
  );
}
