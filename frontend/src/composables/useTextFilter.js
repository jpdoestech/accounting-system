/**
 * useTextFilter
 *
 * A single search box that filters a list against several fields at
 * once (e.g. vendor name, bill number, description) -- there's no
 * server-side search endpoint, so this filters whatever's already
 * loaded. Case-insensitive substring match; empty query returns
 * everything unfiltered.
 *
 * Usage:
 *   const { query, filtered } = useTextFilter(items, (c) => [c.name, c.tin, c.email]);
 *   const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);
 *   // template: <input v-model="query" placeholder="Search...">
 */
import { computed, ref, unref } from "vue";

export function useTextFilter(sourceRef, getSearchableFields) {
  const query = ref("");

  const filtered = computed(() => {
    const q = query.value.trim().toLowerCase();
    const source = unref(sourceRef);
    if (!q) return source;
    return source.filter((item) => {
      const fields = getSearchableFields(item) || [];
      return fields.some((field) => String(field ?? "").toLowerCase().includes(q));
    });
  });

  return { query, filtered };
}
