package com.ems.exception;

/**
 * Raised when an operation would violate a uniqueness constraint (e.g. an email
 * already in use). Translated to HTTP 409 by {@link GlobalExceptionHandler}.
 */
public class DuplicateResourceException extends RuntimeException {

	public DuplicateResourceException(String message) {
		super(message);
	}

	public DuplicateResourceException(String message, Throwable cause) {
		super(message, cause);
	}
}
