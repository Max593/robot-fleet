import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import type { Pagination } from "../types";

type PaginationBarProps = {
  label: string;
  pagination: Pagination;
  onPageChange: (page: number) => void;
};

export function PaginationBar({ label, pagination, onPageChange }: PaginationBarProps) {
  const firstVisibleRow = pagination.total === 0 ? 0 : (pagination.page - 1) * pagination.page_size + 1;
  const lastVisibleRow = Math.min(pagination.page * pagination.page_size, pagination.total);

  return (
    <div className="paginationBar" aria-label={label}>
      <span>
        Rows {firstVisibleRow}-{lastVisibleRow} of {pagination.total}
      </span>
      <div className="paginationControls">
        <button
          className="pageButton"
          onClick={() => onPageChange(1)}
          disabled={pagination.page <= 1}
          title="First page"
          aria-label="First page"
          type="button"
        >
          <ChevronsLeft size={17} aria-hidden="true" />
        </button>
        <button
          className="pageButton"
          onClick={() => onPageChange(Math.max(1, pagination.page - 1))}
          disabled={pagination.page <= 1}
          title="Previous page"
          aria-label="Previous page"
          type="button"
        >
          <ChevronLeft size={17} aria-hidden="true" />
        </button>
        <span className="pageCount">
          Page {pagination.page} of {pagination.total_pages}
        </span>
        <button
          className="pageButton"
          onClick={() => onPageChange(Math.min(pagination.total_pages, pagination.page + 1))}
          disabled={pagination.page >= pagination.total_pages}
          title="Next page"
          aria-label="Next page"
          type="button"
        >
          <ChevronRight size={17} aria-hidden="true" />
        </button>
        <button
          className="pageButton"
          onClick={() => onPageChange(pagination.total_pages)}
          disabled={pagination.page >= pagination.total_pages}
          title="Last page"
          aria-label="Last page"
          type="button"
        >
          <ChevronsRight size={17} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
