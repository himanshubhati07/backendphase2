package com.ems.dto;

import java.util.List;
import java.util.function.Function;
import org.springframework.data.domain.Page;

/**
 * Offset-pagination response envelope used by every list/search endpoint.
 *
 * @param <T> the type of each element in {@link #content}
 */
public class PageResponse<T> {

	private final List<T> content;
	private final int page;
	private final int limit;
	private final long totalElements;
	private final int totalPages;

	public PageResponse(List<T> content, int page, int limit, long totalElements, int totalPages) {
		this.content = content;
		this.page = page;
		this.limit = limit;
		this.totalElements = totalElements;
		this.totalPages = totalPages;
	}

	/**
	 * Builds a {@link PageResponse} directly from a Spring Data {@link Page} whose
	 * element type already matches the desired DTO type.
	 */
	public static <T> PageResponse<T> of(Page<T> page) {
		return new PageResponse<>(
				page.getContent(),
				page.getNumber(),
				page.getSize(),
				page.getTotalElements(),
				page.getTotalPages());
	}

	/**
	 * Builds a {@link PageResponse}, mapping each persistence-layer element of the
	 * source {@link Page} to its response DTO via the supplied mapper.
	 */
	public static <E, T> PageResponse<T> of(Page<E> page, Function<E, T> mapper) {
		List<T> mapped = page.getContent().stream().map(mapper).toList();
		return new PageResponse<>(
				mapped,
				page.getNumber(),
				page.getSize(),
				page.getTotalElements(),
				page.getTotalPages());
	}

	public List<T> getContent() {
		return content;
	}

	public int getPage() {
		return page;
	}

	public int getLimit() {
		return limit;
	}

	public long getTotalElements() {
		return totalElements;
	}

	public int getTotalPages() {
		return totalPages;
	}
}
