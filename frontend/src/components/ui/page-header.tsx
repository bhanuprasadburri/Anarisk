import React from 'react';
import { cn } from '../../lib/utils';

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

export const Breadcrumbs: React.FC<{ items: BreadcrumbItem[] }> = ({ items }) => (
  <nav aria-label="Breadcrumb" className="mb-1.5 flex items-center gap-1.5 text-[12px] font-medium text-faint">
    {items.map((item, i) => (
      <React.Fragment key={i}>
        {i > 0 && <span aria-hidden="true">/</span>}
        {item.to ? (
          <a href={item.to} className="transition-colors hover:text-brand-600">
            {item.label}
          </a>
        ) : (
          <span className="text-muted">{item.label}</span>
        )}
      </React.Fragment>
    ))}
  </nav>
);

export interface PageHeaderProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  className?: string;
  children?: React.ReactNode; // optional toolbar row below
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  actions,
  breadcrumbs,
  className,
  children,
}) => (
  <div className={cn('mb-6', className)}>
    {breadcrumbs && breadcrumbs.length > 0 && <Breadcrumbs items={breadcrumbs} />}
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-xl font-extrabold tracking-tight text-ink sm:text-2xl">{title}</h1>
        {description && <p className="mt-1 text-[13px] text-muted sm:text-sm">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2.5">{actions}</div>}
    </div>
    {children}
  </div>
);

export default PageHeader;
