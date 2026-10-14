import React from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Inbox } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from './button';

/* ---------------- Pagination ---------------- */

export interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
  pageSize?: number;
  onPageSizeChange?: (size: number) => void;
  className?: string;
}

export const Pagination: React.FC<PaginationProps> = ({
  page,
  pages,
  total,
  onPageChange,
  pageSize,
  onPageSizeChange,
  className,
}) => {
  const pageNumbers = React.useMemo(() => {
    const out: (number | '…')[] = [];
    const push = (n: number | '…') => {
      if (n !== '…' && (n < 1 || n > pages)) return;
      if (out[out.length - 1] === n) return;
      out.push(n);
    };
    push(1);
    if (page > 3) push('…');
    for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) push(i);
    if (page < pages - 2) push('…');
    push(pages);
    return out;
  }, [page, pages]);

  if (pages <= 1 && total === 0) return null;

  return (
    <div className={cn('flex flex-wrap items-center justify-between gap-3 px-5 py-3.5', className)}>
      <div className="text-[13px] text-muted">
        {total === 0 ? 'No results' : `${total.toLocaleString()} result${total === 1 ? '' : 's'}`}
        {pageSize && onPageSizeChange && (
          <select
            aria-label="Rows per page"
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="ml-3 rounded-lg border border-line bg-white px-2 py-1 text-[12px] font-semibold text-ink-700 focus-ring"
          >
            {[10, 20, 50, 100].map((s) => (
              <option key={s} value={s}>
                {s} / page
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="flex items-center gap-1">
        <button
          aria-label="First page"
          disabled={page <= 1}
          onClick={() => onPageChange(1)}
          className="rounded-lg p-1.5 text-muted transition-colors hover:bg-line-soft hover:text-ink disabled:opacity-30 focus-ring"
        >
          <ChevronsLeft className="h-4 w-4" />
        </button>
        <button
          aria-label="Previous page"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="rounded-lg p-1.5 text-muted transition-colors hover:bg-line-soft hover:text-ink disabled:opacity-30 focus-ring"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        {pageNumbers.map((n, i) =>
          n === '…' ? (
            <span key={`e${i}`} className="px-1.5 text-xs text-faint">
              …
            </span>
          ) : (
            <button
              key={n}
              onClick={() => onPageChange(n)}
              aria-current={n === page ? 'page' : undefined}
              className={cn(
                'min-w-[32px] rounded-lg px-2 py-1.5 text-[13px] font-semibold transition-colors focus-ring',
                n === page ? 'bg-brand-gradient text-white shadow-sm' : 'text-muted hover:bg-line-soft hover:text-ink'
              )}
            >
              {n}
            </button>
          )
        )}
        <button
          aria-label="Next page"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
          className="rounded-lg p-1.5 text-muted transition-colors hover:bg-line-soft hover:text-ink disabled:opacity-30 focus-ring"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <button
          aria-label="Last page"
          disabled={page >= pages}
          onClick={() => onPageChange(pages)}
          className="rounded-lg p-1.5 text-muted transition-colors hover:bg-line-soft hover:text-ink disabled:opacity-30 focus-ring"
        >
          <ChevronsRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

/* ---------------- DataTable ---------------- */

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
  headerClassName?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  sort?: string | null;
  order?: 'asc' | 'desc';
  onSortChange?: (key: string) => void;
  onRowClick?: (row: T) => void;
  isRowSelected?: (row: T) => boolean;
  loading?: boolean;
  emptyState?: React.ReactNode;
  className?: string;
}

export const DataTable = <T,>({
  columns,
  rows,
  rowKey,
  sort,
  order = 'desc',
  onSortChange,
  onRowClick,
  isRowSelected,
  loading,
  emptyState,
  className,
}: DataTableProps<T>) => {
  if (!loading && rows.length === 0 && emptyState) {
    return <div className="px-5 py-12">{emptyState}</div>;
  }

  return (
    <div className={cn('overflow-x-auto scrollbar-thin', className)}>
      <table className="w-full min-w-[640px] border-collapse text-left">
        <thead>
          <tr className="border-y border-line-soft bg-bg/60">
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={cn(
                  'whitespace-nowrap px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-faint',
                  c.headerClassName
                )}
              >
                {c.sortable && onSortChange ? (
                  <button
                    onClick={() => onSortChange(c.key)}
                    className={cn(
                      'inline-flex items-center gap-1 uppercase tracking-wider transition-colors hover:text-ink focus-ring rounded',
                      sort === c.key ? 'text-brand-600' : ''
                    )}
                  >
                    {c.header}
                    <span className="text-[10px]">
                      {sort === c.key ? (order === 'asc' ? '▲' : '▼') : '↕'}
                    </span>
                  </button>
                ) : (
                  c.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading
            ? Array.from({ length: 6 }).map((_, i) => (
                <tr key={`sk${i}`} className="border-b border-line-soft">
                  {columns.map((c) => (
                    <td key={c.key} className="px-4 py-3.5">
                      <div className="skeleton h-4 rounded-md" style={{ width: `${50 + ((i * 13) % 40)}%` }} />
                    </td>
                  ))}
                </tr>
              ))
            : rows.map((row) => {
                const selected = isRowSelected?.(row);
                return (
                  <tr
                    key={rowKey(row)}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={cn(
                      'border-b border-line-soft transition-colors',
                      onRowClick && 'cursor-pointer',
                      selected ? 'bg-brand-50/70' : 'hover:bg-bg/80'
                    )}
                  >
                    {columns.map((c) => (
                      <td key={c.key} className={cn('px-4 py-3.5 text-sm text-ink-700', c.className)}>
                        {c.cell(row)}
                      </td>
                    ))}
                  </tr>
                );
              })}
        </tbody>
      </table>
    </div>
  );
};

/* ---------------- Empty / error states ---------------- */

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
}) => (
  <div className={cn('flex flex-col items-center justify-center text-center', className)}>
    <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient-soft text-brand-500">
      {icon || <Inbox className="h-6 w-6" />}
    </div>
    <h3 className="text-[15px] font-bold text-ink">{title}</h3>
    {description && <p className="mt-1 max-w-sm text-[13px] text-muted">{description}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message = 'We could not load this data. Check your connection and try again.',
  onRetry,
  className,
}) => (
  <EmptyState
    className={className}
    icon={<span className="text-xl">⚠️</span>}
    title={title}
    description={message}
    action={
      onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )
    }
  />
);

export default DataTable;
