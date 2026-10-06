package com.example.studentmanagement.service;

import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

public final class OffsetLimitPageable implements Pageable {
    private final long offset;
    private final int limit;
    private final Sort sort;
    public OffsetLimitPageable(long offset, int limit) { this(offset, limit, Sort.by("id").ascending()); }
    private OffsetLimitPageable(long offset, int limit, Sort sort) { this.offset = offset; this.limit = limit; this.sort = sort; }
    @Override public int getPageNumber() { return (int) (offset / limit); }
    @Override public int getPageSize() { return limit; }
    @Override public long getOffset() { return offset; }
    @Override public Sort getSort() { return sort; }
    @Override public Pageable next() { return new OffsetLimitPageable(offset + limit, limit, sort); }
    @Override public Pageable previousOrFirst() { return hasPrevious() ? new OffsetLimitPageable(Math.max(0, offset - limit), limit, sort) : first(); }
    @Override public Pageable first() { return new OffsetLimitPageable(0, limit, sort); }
    @Override public Pageable withPage(int pageNumber) { return new OffsetLimitPageable((long) pageNumber * limit, limit, sort); }
    @Override public boolean hasPrevious() { return offset > 0; }
}
