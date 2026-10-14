import { apiRequest, qs } from './apiClient';
import { Brand, BrandReference } from '../types';

export const brandService = {
  async listBrands(params: { q?: string; page?: number; page_size?: number } = {}): Promise<{
    items: Brand[];
    total: number;
  }> {
    return apiRequest(`/brands${qs(params)}`);
  },

  async getBrand(brandId: string): Promise<Brand> {
    return apiRequest<Brand>(`/brands/${brandId}`);
  },

  async createBrand(payload: { name: string; description?: string; organization_id?: string }): Promise<Brand> {
    return apiRequest<Brand>(`/brands`, { method: 'POST', body: JSON.stringify(payload) });
  },

  async updateBrand(brandId: string, payload: { name?: string; description?: string; is_active?: boolean }): Promise<Brand> {
    return apiRequest<Brand>(`/brands/${brandId}`, { method: 'PATCH', body: JSON.stringify(payload) });
  },

  async addReference(
    brandId: string,
    payload: { kind: string; value: string; platform?: string; note?: string }
  ): Promise<BrandReference> {
    return apiRequest<BrandReference>(`/brands/${brandId}/references`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async addReferenceImage(
    brandId: string,
    file: File,
    payload: { kind?: string; note?: string } = {}
  ): Promise<BrandReference> {
    const form = new FormData();
    form.append('file', file);
    if (payload.kind) form.append('kind', payload.kind);
    if (payload.note) form.append('note', payload.note);
    return apiRequest<BrandReference>(`/brands/${brandId}/references/image`, { method: 'POST', body: form });
  },

  async deleteReference(brandId: string, referenceId: string): Promise<void> {
    await apiRequest(`/brands/${brandId}/references/${referenceId}`, { method: 'DELETE' });
  },
};
