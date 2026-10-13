import { apiRequest } from './apiClient';
import { Brand, BrandReference } from '../types';
import { mockStore } from '../mocks/mockStore';

export const brandService = {
  async listBrands(): Promise<Brand[]> {
    try {
      return await apiRequest<Brand[]>('/brands');
    } catch {
      return mockStore.brands;
    }
  },

  async getBrand(brandId: string): Promise<Brand> {
    try {
      return await apiRequest<Brand>(`/brands/${brandId}`);
    } catch {
      const b = mockStore.brands.find((item) => item.id === brandId);
      if (!b) throw new Error('Brand not found');
      return b;
    }
  },

  async createBrand(payload: { name: string; slug?: string; description?: string }): Promise<Brand> {
    try {
      return await apiRequest<Brand>('/brands', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      const newBrand: Brand = {
        id: `b-${Date.now().toString(36)}`,
        organization_id: mockStore.currentUser.organization_id || 'org-001',
        name: payload.name,
        slug: payload.slug || payload.name.toLowerCase().replace(/[^a-z0-9]/g, '-'),
        description: payload.description || null,
        is_active: true,
        is_synthetic: true,
        created_at: new Date().toISOString(),
        entity_count: 0,
        references: [],
      };
      mockStore.brands.push(newBrand);
      mockStore.addAuditLog('brand:create', 'brand', newBrand.id, { name: payload.name });
      return newBrand;
    }
  },

  async addReference(brandId: string, payload: Partial<BrandReference>): Promise<BrandReference> {
    try {
      return await apiRequest<BrandReference>(`/brands/${brandId}/references`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      const ref: BrandReference = {
        id: `ref-${Date.now().toString(36)}`,
        brand_id: brandId,
        kind: payload.kind || 'name',
        value: payload.value || '',
        platform: payload.platform || null,
        perceptual_hash: payload.perceptual_hash || null,
        note: payload.note || null,
        provenance: 'manual',
        created_at: new Date().toISOString(),
      };
      const b = mockStore.brands.find((item) => item.id === brandId);
      if (b) {
        b.references = b.references || [];
        b.references.push(ref);
      }
      mockStore.addAuditLog('brand:reference:add', 'brand_reference', ref.id, { kind: ref.kind, value: ref.value });
      return ref;
    }
  },

  async deleteReference(brandId: string, refId: string): Promise<void> {
    try {
      await apiRequest<void>(`/brands/${brandId}/references/${refId}`, {
        method: 'DELETE',
      });
    } catch {
      const b = mockStore.brands.find((item) => item.id === brandId);
      if (b && b.references) {
        b.references = b.references.filter((r) => r.id !== refId);
      }
      mockStore.addAuditLog('brand:reference:delete', 'brand_reference', refId, {});
    }
  },
};
