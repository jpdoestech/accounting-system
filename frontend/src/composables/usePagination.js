/**
 * usePagination
 *
 * Client-side pagination over a reactive array. Every list view in this
 * app loads its full result set in one request (there's no server-side
 * paging in the API), so pagination here just controls how much of an
 * already-loaded array is rendered at once -- it keeps large tables
 * from becoming a giant unpaginated wall of rows.
 *
 * Usage:
 *   const { page, pageSize, pagedItems, totalItems } = usePagination(items);
 *   // template: v-for="row in pagedItems"
 *   // template: <PaginationBar v-model:page="page" v-model:page-size="pageSize" :total-items="totalItems" />
 */
import { computed, ref, unref, watch } from "vue";

export const PAGE_SIZE_OPTIONS = [25, 50, 100, 200, 500, 1000];

export function usePagination(sourceRef, defaultPageSize = 25) {
  const page = ref(1);
  const pageSize = ref(defaultPageSize);

  const totalItems = computed(() => unref(sourceRef).length);
  const totalPages = computed(() => Math.max(1, Math.ceil(totalItems.value / pageSize.value)));

  const pagedItems = computed(() => {
    const start = (page.value - 1) * pageSize.value;
    return unref(sourceRef).slice(start, start + pageSize.value);
  });

  // Changing the page size always jumps back to page 1 -- otherwise
  // "page 3 of 25-per-page" could land past the end of a 100-per-page view.
  watch(pageSize, () => {
    page.value = 1;
  });

  // If the underlying list shrinks (e.g. a row gets deleted) and the
  // current page no longer exists, pull back to the new last page.
  watch(totalItems, () => {
    if (page.value > totalPages.value) page.value = totalPages.value;
  });

  return { page, pageSize, totalItems, totalPages, pagedItems };
}
