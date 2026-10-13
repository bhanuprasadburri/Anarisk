import React, { useEffect, useState } from 'react';
import {
  Shield,
  Plus,
  Trash2,
  Globe,
  Share2,
  Smartphone,
  Image as ImageIcon,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { brandService } from '../services/brandService';
import { Brand, BrandReference, ReferenceKind } from '../types';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Modal } from '../components/ui/modal';
import { formatDate } from '../lib/formatters';

export const BrandProtectionPage: React.FC = () => {
  const { activeBrand } = useAuth();
  const [brand, setBrand] = useState<Brand | null>(null);
  const [references, setReferences] = useState<BrandReference[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Add Reference Modal
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [newRef, setNewRef] = useState({
    kind: 'domain' as ReferenceKind,
    value: '',
    note: '',
  });

  const loadBrandData = async () => {
    setIsLoading(true);
    try {
      const b = await brandService.getBrand(activeBrand?.id || 'b-001');
      setBrand(b);
      setReferences(b.references || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadBrandData();
  }, [activeBrand]);

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brand) return;
    try {
      const created = await brandService.addReference(brand.id, newRef);
      setReferences([...references, created]);
      setIsAddOpen(false);
      setNewRef({ kind: 'domain', value: '', note: '' });
    } catch (err) {
      alert('Failed to add reference: ' + (err as Error).message);
    }
  };

  const handleDelete = async (refId: string) => {
    if (!brand) return;
    if (!window.confirm('Delete this official registered reference?')) return;
    try {
      await brandService.deleteReference(brand.id, refId);
      setReferences(references.filter((r) => r.id !== refId));
    } catch (err) {
      alert('Failed to delete reference: ' + (err as Error).message);
    }
  };

  const getRefTypeIcon = (type: ReferenceKind) => {
    switch (type) {
      case 'domain':
        return Globe;
      case 'handle':
      case 'name':
      case 'bio':
        return Share2;
      case 'app_package':
      case 'publisher':
        return Smartphone;
      case 'image':
        return ImageIcon;
      default:
        return Shield;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Brand Protection & Official Reference Assets
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Registered baseline truth: official domains, handles, APK packages and perceptual logo hashes.
          </p>
        </div>
        <Button variant="teal" onClick={() => setIsAddOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Register Reference Asset
        </Button>
      </div>

      {/* Brand Identity Card */}
      {brand && (
        <Card>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-500/10 border border-teal-500/30 text-teal-400">
                <Shield className="h-7 w-7" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold text-white">{brand.name}</h3>
                  <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800">
                    <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                    Verified Protected Brand
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1 max-w-xl">
                  {brand.description || 'Monitored corporate identity for spoofing and impersonation protection.'}
                </p>
              </div>
            </div>

            <div className="text-right text-xs font-mono text-slate-400">
              <div>Protected Assets: <strong className="text-slate-200">{references.length}</strong></div>
              <div className="mt-1">Registered: {formatDate(brand.created_at)}</div>
            </div>
          </div>
        </Card>
      )}

      {/* References Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Registered Official References ({references.length})
          </CardTitle>
          <p className="text-xs text-slate-400">
            Detection signals calculate similarity (RapidFuzz edit distance, normalized homoglyphs, and pHash Hamming distance) against these registered baseline items.
          </p>
        </CardHeader>
        <CardContent>
          {references.length === 0 ? (
            <p className="text-slate-400 text-sm italic">No official references registered yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 text-xs font-mono uppercase text-slate-400">
                  <tr>
                    <th className="pb-3 pl-2">Asset Kind</th>
                    <th className="pb-3">Reference Value</th>
                    <th className="pb-3">Context / Note</th>
                    <th className="pb-3">Registered At</th>
                    <th className="pb-3 text-right pr-2">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {references.map((ref) => {
                    const Icon = getRefTypeIcon(ref.kind);
                    return (
                      <tr key={ref.id} className="hover:bg-slate-800/20 transition-colors">
                        <td className="py-3.5 pl-2">
                          <span className="flex items-center gap-2 font-mono text-xs text-teal-300 capitalize">
                            <Icon className="h-4 w-4 text-teal-400" />
                            {ref.kind.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-3.5 font-mono text-xs font-bold text-slate-100">
                          {ref.value}
                        </td>
                        <td className="py-3.5 text-xs text-slate-400">
                          {ref.note || '—'}
                        </td>
                        <td className="py-3.5 font-mono text-xs text-slate-500">
                          {formatDate(ref.created_at)}
                        </td>
                        <td className="py-3.5 text-right pr-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(ref.id)}
                            className="h-7 w-7 text-red-400 hover:text-red-300 hover:bg-red-950/30"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Reference Modal */}
      <Modal
        isOpen={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        title="Register Brand Reference Asset"
        description="Add an official name, handle, web domain, or app ID to calculate lookalikes against"
      >
        <form onSubmit={handleAddSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Asset Kind</label>
            <select
              value={newRef.kind}
              onChange={(e) => setNewRef({ ...newRef, kind: e.target.value as ReferenceKind })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            >
              <option value="domain">Official Domain (e.g. acmebank.com)</option>
              <option value="handle">Official Social Handle (e.g. acmebank)</option>
              <option value="name">Official Brand Name (e.g. AcmeBank)</option>
              <option value="app_package">Mobile App Package (e.g. com.acmebank.mobile)</option>
              <option value="publisher">Official Publisher Name</option>
              <option value="bio">Official Bio / Tagline</option>
              <option value="image">Official Logo / Visual Asset</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Reference Value</label>
            <input
              type="text"
              required
              placeholder="e.g. acmebank.example.com"
              value={newRef.value}
              onChange={(e) => setNewRef({ ...newRef, value: e.target.value })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Notes / Description</label>
            <input
              type="text"
              placeholder="e.g. Primary retail banking domain"
              value={newRef.note}
              onChange={(e) => setNewRef({ ...newRef, note: e.target.value })}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 outline-none focus:border-teal-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <Button type="button" variant="ghost" onClick={() => setIsAddOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="teal">
              Add Reference Asset
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

